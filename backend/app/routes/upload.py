from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException, Depends
from pydantic import EmailStr, TypeAdapter
from typing import List, Optional
from app.services.nextcloud import NextcloudService
from app.services.email_service import EmailService
from app.models.upload import UploadResponse
from app.config import settings
from app.utils.auth import verify_token
from app.limiter import limiter
from datetime import datetime
import filetype
import os
import json
import re
import structlog

from app.logging_config import hmac_sha256_hex

_email_adapter = TypeAdapter(EmailStr)

# Mapping of allowed file extensions to permitted MIME types (magic-bytes check).
# Prevents extension spoofing (CWE-434 / OWASP A01).
_ALLOWED_MIME_BY_EXT: dict[str, set[str]] = {
    ".pdf":  {"application/pdf"},
    ".doc":  {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".odt":  {"application/vnd.oasis.opendocument.text"},
    ".ods":  {"application/vnd.oasis.opendocument.spreadsheet"},
    ".odp":  {"application/vnd.oasis.opendocument.presentation"},
    ".odf":  {"application/vnd.oasis.opendocument.formula"},
    ".zip":  {"application/zip"},
    ".png":  {"image/png"},
    ".jpg":  {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".csv":  {"text/plain", "text/csv", "application/csv"},
}


def _check_magic_bytes(data: bytes, extension: str) -> bool:
    """
    Verify that the file's magic bytes match the declared extension.
    Returns True if valid, False if the content type does not match.
    CSV files have no unique magic bytes and are allowed through as-is.
    """
    allowed_mimes = _ALLOWED_MIME_BY_EXT.get(extension)
    if allowed_mimes is None:
        return False
    # CSV: no magic bytes – trust the extension (size/content limits still apply)
    if extension == ".csv":
        return True
    kind = filetype.guess(data)
    if kind is None:
        # filetype couldn't detect – only allow CSV (handled above) and plain text
        return False
    return kind.mime in allowed_mimes


def _sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent path traversal (CWE-22 / OWASP A01).
    Strips directory components and replaces unsafe characters.
    """
    # Take only the basename – discard any path components (e.g. "../../etc/passwd.pdf")
    name = os.path.basename(filename)
    # Replace characters that are dangerous in file-system paths
    name = re.sub(r'[^\w.\-]', '_', name)
    # Collapse multiple dots to prevent extension spoofing like "file..pdf"
    name = re.sub(r'\.{2,}', '.', name)
    # Limit length to avoid filesystem issues
    if len(name) > 200:
        stem, sep, suffix = name.rpartition('.')
        name = stem[:196] + sep + suffix if sep else name[:200]
    return name or "file"

logger = structlog.get_logger(__name__)

router = APIRouter()
nextcloud = NextcloudService()
email_service = EmailService()

@router.post("/upload", response_model=UploadResponse, dependencies=[Depends(verify_token)])
@limiter.limit("10/hour")  # Rate limit: max 10 uploads per IP per hour (OWASP A04)
async def upload_documents(
    request: Request,
    email: str = Form(...),
    uploader_name: str = Form(None),
    project_title: str = Form(...),
    institution: str = Form(...),
    is_prospective_study: bool = Form(False),
    project_details: str = Form(None),
    files: List[UploadFile] = File(...),
    file_categories: str = Form(None),
    project_type: str = Form("new"),
    language: str = Form("de")
):
    """
    Upload data protection documents to Nextcloud
    """
    # Validate email format (OWASP A03 – Injection / input validation)
    try:
        email = _email_adapter.validate_python(email)
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid email address")

    # Restrict project_type to known values to prevent unexpected behaviour
    if project_type not in ("new", "existing"):
        raise HTTPException(status_code=422, detail="Invalid project_type")

    # Restrict language to known values
    if language not in ("de", "en"):
        raise HTTPException(status_code=422, detail="Invalid language")

    email_hash = hmac_sha256_hex(email, settings.log_redaction_secret)
    logger.info(
        "upload_received",
        email_hash=email_hash,
        files_count=len(files),
        project_type=project_type,
        is_prospective_study=is_prospective_study,
            language=language,
    )
    
    try:
        # Sanitize project title for folder name
        # Replace non-alphanumeric characters (except spaces, dashes, underscores) with underscore
        safe_title = re.sub(r'[^a-zA-Z0-9 \-_]', '_', project_title)
        # Replace spaces with underscores
        safe_title = safe_title.replace(' ', '_')
        # Remove multiple underscores
        safe_title = re.sub(r'_+', '_', safe_title)
        # Trim underscores
        safe_title = safe_title.strip('_')
        
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        if project_type == 'existing':
            folder_name = f"RE_{safe_title}_{date_str}"
        else:
            folder_name = f"{safe_title}_{date_str}"
            
        # Use folder_name as project_id for consistency with storage
        project_id = folder_name
        logger.debug("project_id_generated", project_id=project_id)
        
        # Parse categories if provided
        categories_map = {}
        if file_categories:
            try:
                categories_map = json.loads(file_categories)
                logger.debug("file_categories_parsed", mappings_count=len(categories_map))
            except Exception as e:
                logger.warning("file_categories_parse_failed", exc_info=True)
                pass
        
        # Validate files
        logger.debug("files_validating", files_count=len(files))
        for file in files:
            if file.size > settings.max_file_size:
                logger.warning("file_too_large", file_size=file.size, max_size=settings.max_file_size)
                raise HTTPException(
                    status_code=413,
                    detail=f"File {file.filename} exceeds maximum size of 50 MB"
                )

            # Sanitize filename before extension check to prevent path traversal (OWASP A01 / CWE-22)
            safe_name = _sanitize_filename(file.filename or "upload")
            file_ext = os.path.splitext(safe_name)[1].lower()
            if file_ext not in settings.allowed_file_types:
                logger.warning("file_extension_disallowed", file_extension=file_ext)
                raise HTTPException(
                    status_code=400,
                    detail=f"File type {file_ext} not allowed"
                )

            # Magic-bytes check: verify actual file content matches the declared extension (CWE-434)
            header = await file.read(261)  # 261 bytes is sufficient for filetype detection
            await file.seek(0)
            if not _check_magic_bytes(header, file_ext):
                logger.warning("file_magic_bytes_mismatch", file_extension=file_ext)
                raise HTTPException(
                    status_code=400,
                    detail=f"File content does not match declared type {file_ext}"
                )

        logger.info("files_validation_passed")
        
        # Create project folder structure
        project_path = f"{settings.nextcloud_base_path}/{project_id}"
        logger.info("nextcloud_project_folder_creating", project_id=project_id)
        
        # Test connection before attempting folder creation
        connection_ok, connection_msg = nextcloud.test_connection()
        if not connection_ok:
            logger.error("nextcloud_connection_failed", project_id=project_id)
            raise HTTPException(
                status_code=503,
                detail=f"Nextcloud connection failed. Please check Nextcloud configuration and credentials. Error: {connection_msg}"
            )
        
        if not nextcloud.create_folder(project_path):
            logger.error("nextcloud_project_folder_create_failed", project_id=project_id)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create project folder in Nextcloud at path: {project_path}. Please check Nextcloud permissions and ensure the base path exists."
            )
        
        # Upload files directly to project folder (no subfolders)
        uploaded_files = []
        logger.info("files_upload_started", project_id=project_id, files_count=len(files))
        for idx, file in enumerate(files, 1):
            # Sanitize the filename to prevent path traversal on the remote storage (OWASP A01 / CWE-22)
            safe_name = _sanitize_filename(file.filename or "upload")
            category = categories_map.get(file.filename, categories_map.get(safe_name, "sonstiges"))
            logger.debug("file_uploading", project_id=project_id, index=idx, total=len(files), category=category)

            # Upload directly to project folder, no category subfolders
            file_path = f"{project_path}/{safe_name}"
            if not await nextcloud.upload_file(file, file_path):
                logger.error("file_upload_failed", project_id=project_id, category=category)
                raise HTTPException(status_code=500, detail=f"Failed to upload file: {safe_name}")
            
            uploaded_files.append({
                "filename": safe_name,
                "category": category,
                "path": file_path
            })
        
        logger.info("files_upload_completed", project_id=project_id, uploaded_count=len(uploaded_files))
        
        # Create metadata file
        logger.debug("metadata_creating", project_id=project_id)
        metadata = {
            "project_id": project_id,
            "email": email,
            "uploader_name": uploader_name,
            "project_title": project_title,
            "project_details": project_details,
            "institution": institution,
            "is_prospective_study": is_prospective_study,
            "upload_timestamp": datetime.now().isoformat(),
            "files": uploaded_files,
            "project_type": project_type,
            "language": language
        }
        
        metadata_path = f"{project_path}/metadata.json"
        if not await nextcloud.upload_metadata(metadata, metadata_path):
            logger.error("metadata_upload_failed", project_id=project_id)
            raise HTTPException(status_code=500, detail="Failed to upload metadata")

        # Create README.md
        logger.debug("readme_creating", project_id=project_id)
        readme_content = f"""# {project_title}

**Projekt-ID:** {project_id}
**Datum:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
**Typ:** {'Nachreichung' if project_type == 'existing' else 'Neueinreichung'}

## Kontaktinformationen
- **Name:** {uploader_name if uploader_name else 'Nicht angegeben'}
- **E-Mail:** {email}
- **Institution:** {institution}

## Projektdetails
{project_details if project_details else 'Keine weiteren Details angegeben.'}

## Hochgeladene Dateien
"""
        
        for file_info in uploaded_files:
            readme_content += f"- **{file_info['category']}:** {file_info['filename']}\n"

        readme_path = f"{project_path}/README.md"
        if not await nextcloud.upload_content(readme_content, readme_path):
            logger.error("readme_upload_failed", project_id=project_id)
            raise HTTPException(status_code=500, detail="Failed to upload README.md")
        
        # Send confirmation email to user
        logger.info("confirmation_email_sending", project_id=project_id, email_hash=email_hash)
        try:
            await email_service.send_confirmation_email(
                to_email=email,
                project_id=project_id,
                project_title=project_title,
                uploader_name=uploader_name,
                files=uploaded_files,
                project_type=project_type,
                language=language
            )
            logger.info("confirmation_email_sent", project_id=project_id, email_hash=email_hash)
        except Exception as e:
            logger.error("confirmation_email_send_failed", project_id=project_id, exc_info=True)
            # Don't fail the upload if email fails
        
        # Send notification to team
        logger.info("team_notification_sending", project_id=project_id)
        try:
            await email_service.send_team_notification(
                project_id=project_id,
                project_title=project_title,
                uploader_email=email,
                file_names=[f["filename"] for f in uploaded_files],
            )
            logger.info("team_notification_sent", project_id=project_id)
        except Exception as e:
            logger.error("team_notification_send_failed", project_id=project_id, exc_info=True)
            # Don't fail the upload if email fails
        
        logger.info("upload_completed", project_id=project_id, files_uploaded=len(files))
        return UploadResponse(
            success=True,
            project_id=project_id,
            timestamp=datetime.now(),
            files_uploaded=len(files),
            message="Documents uploaded successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error("upload_unexpected_error", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.get("/upload/status/{project_id}", dependencies=[Depends(verify_token)])
async def get_upload_status(project_id: str):
    """
    Get upload status for a project
    """
    try:
        metadata = await nextcloud.get_metadata(project_id)
        return metadata
    except Exception:
        raise HTTPException(status_code=404, detail="Project not found")

import aiosmtplib
import html as html_lib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader, select_autoescape
from app.config import settings
from app.logging_config import hmac_sha256_hex
from typing import List, Dict, Any, Literal, Optional, Sequence
from datetime import datetime
import structlog
from urllib.parse import quote, urlsplit

logger = structlog.get_logger(__name__)

ProjectType = Literal["new", "existing"]

class EmailService:
    def __init__(self):
        # Ensure templates directory exists or handle missing templates gracefully
        try:
            self.template_env = Environment(
                loader=FileSystemLoader('app/templates'),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except Exception as e:
            logger.error(f"Failed to initialize Jinja2 environment: {e}")
            self.template_env = None
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        *,
        mail_kind: Optional[str] = None,
        project_id: Optional[str] = None,
        recipient_hash: Optional[str] = None,
    ) -> bool:
        """
        Send an email via SMTP
        """
        if recipient_hash is None:
            recipient_hash = hmac_sha256_hex(to_email, settings.log_redaction_secret)

        try:
            message = MIMEMultipart('alternative')
            message['From'] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Configure encryption based on settings
            smtp_kwargs = {
                "hostname": settings.smtp_host,
                "port": settings.smtp_port,
                "username": settings.smtp_username,
                "password": settings.smtp_password,
            }
            
            if settings.smtp_encryption == "starttls":
                # STARTTLS: Upgrade unencrypted connection to TLS (typically port 587)
                smtp_kwargs["start_tls"] = True
                smtp_kwargs["use_tls"] = False
            elif settings.smtp_encryption == "ssl":
                # SSL: Direct SSL/TLS connection (typically port 465)
                smtp_kwargs["use_tls"] = True
                smtp_kwargs["ssl_context"] = ssl.create_default_context()
            else:  # none
                smtp_kwargs["use_tls"] = False
                smtp_kwargs["start_tls"] = False
            
            await aiosmtplib.send(message, **smtp_kwargs)
            
            return True
        except Exception as e:
            logger.error(
                "email_send_failed",
                mail_kind=mail_kind,
                project_id=project_id,
                recipient_hash=recipient_hash,
                error_type=type(e).__name__,
                error_message=str(e),
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                smtp_encryption=settings.smtp_encryption,
                exc_info=True,
            )
            return False

    async def send_template_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        context: Dict[str, Any],
        *,
        mail_kind: Optional[str] = None,
        project_id: Optional[str] = None,
        recipient_hash: Optional[str] = None,
    ) -> bool:
        """
        Send an email using a Jinja2 template
        """
        if not self.template_env:
            logger.error("email_template_env_not_initialized")
            return False
            
        try:
            template = self.template_env.get_template(template_name)
            html_content = template.render(**context)
            return await self.send_email(
                to_email,
                subject,
                html_content,
                mail_kind=mail_kind,
                project_id=project_id,
                recipient_hash=recipient_hash,
            )
        except Exception as e:
            logger.error(
                "email_template_render_failed",
                template_name=template_name,
                mail_kind=mail_kind,
                project_id=project_id,
                recipient_hash=recipient_hash,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True,
            )
            return False
    
    async def send_confirmation_email(
        self,
        to_email: str,
        project_id: str,
        project_title: str,
        uploader_name: str,
        files: List[Dict],
        project_type: ProjectType = "new",
        language: str = "de",
    ) -> bool:
        """
        Send confirmation email to user.
        For resubmissions (existing projects), we use a dedicated template/subject with the same base layout.
        """
        is_resubmission = project_type == "existing"
        use_english = language == "en"

        if use_english:
            subject_prefix = "Resubmission Confirmation" if is_resubmission else "Upload Confirmation"
            template_name = (
                "email_confirmation_resubmission_en.html"
                if is_resubmission
                else "email_confirmation_en.html"
            )
        else:
            subject_prefix = "Bestätigung Nachreichung" if is_resubmission else "Bestätigung Upload"
            template_name = (
                "email_confirmation_resubmission_de.html"
                if is_resubmission
                else "email_confirmation_de.html"
            )

        subject = f"{subject_prefix}: {project_title} (ID: {project_id})"
        
        context = {
            "project_id": project_id,
            "project_title": project_title,
            "uploader_name": uploader_name,
            "files": files,
            "files_count": len(files),
            "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "project_type": project_type,
        }
        
        recipient_hash = hmac_sha256_hex(to_email, settings.log_redaction_secret)
        return await self.send_template_email(
            to_email,
            subject,
            template_name,
            context,
            mail_kind="confirmation",
            project_id=project_id,
            recipient_hash=recipient_hash,
        )
    
    async def send_missing_documents_email(
        self,
        to_email: str,
        project_id: str,
        project_title: str,
        uploader_name: str,
        missing_items: List[str]
    ) -> bool:
        """
        Send email requesting missing documents
        """
        subject = f"Nachreichung erforderlich: {project_title} (ID: {project_id})"
        
        context = {
            "project_id": project_id,
            "project_title": project_title,
            "uploader_name": uploader_name,
            "missing_items": missing_items,
            "portal_url": "https://datenschutz.uni-frankfurt.de" # Should be in settings ideally
        }
        
        return await self.send_template_email(
            to_email,
            subject,
            "missing_documents.html",
            context
        )

    async def send_user_info_email(
        self,
        to_email: str,
        name: str
    ) -> bool:
        """
        Send general information email
        """
        subject = "Informationen zum Datenschutzportal"
        
        context = {
            "name": name
        }
        
        return await self.send_template_email(
            to_email,
            subject,
            "user_info.html",
            context
        )
    
    async def send_team_notification(
        self,
        project_id: str,
        project_title: str,
        uploader_email: str,
        file_names: Sequence[str],
    ) -> bool:
        """
        Send notification to data protection team
        """
        subject = f"Neuer Dokument-Upload: {project_title} (ID: {project_id})"

        folder_url = self._build_nextcloud_web_ui_folder_url(
            folder_path=f"{settings.nextcloud_base_path}/{project_id}"
        )
        # Escape all user-supplied values before embedding in HTML (OWASP A03 – XSS / CWE-79)
        esc = html_lib.escape
        files_html = "\n".join(f"<li>{esc(name)}</li>" for name in file_names)

        # We can also use a template for this eventually
        html_content = f"""
        <html>
        <body>
            <h2>Neuer Dokument-Upload</h2>
            <p><strong>Projekt-ID:</strong> {esc(project_id)}</p>
            <p><strong>Projekttitel:</strong> {esc(project_title)}</p>
            <p><strong>Uploader E-Mail:</strong> {esc(uploader_email)}</p>
            <p><strong>Dateien:</strong></p>
            <ul>
                {files_html}
            </ul>
            <p><a href="{esc(folder_url)}">Open folder in next.Hessenbox</a></p>
        </body>
        </html>
        """
        
        total_count = len(settings.notification_emails)
        failed_count = 0

        for email in settings.notification_emails:
            success = await self.send_email(
                email,
                subject,
                html_content,
                mail_kind="team_notification",
                project_id=project_id,
                recipient_hash=hmac_sha256_hex(email, settings.log_redaction_secret),
            )
            if not success:
                failed_count += 1

        if failed_count == 0:
            return True

        if 0 < failed_count < total_count:
            logger.error(
                "team_notification_partial_failure",
                project_id=project_id,
                failed_count=failed_count,
                total_count=total_count,
            )

        return False

    @staticmethod
    def _build_nextcloud_web_ui_folder_url(folder_path: str) -> str:
        """
        Build a Nextcloud Web UI URL for a folder. This ensures we link to the normal UI and not a WebDAV endpoint.

        The base is derived from NEXTCLOUD_URL, which is often configured as a WebDAV/DAV endpoint like:
        - https://example.com/remote.php/webdav/
        - https://example.com/remote.php/dav/files/<user>
        """
        url = str(settings.nextcloud_url).strip()
        parts = urlsplit(url)
        base = f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else url.rstrip("/")
        normalized_folder = folder_path if folder_path.startswith("/") else f"/{folder_path}"
        return f"{base}/index.php/apps/files/?dir={quote(normalized_folder, safe='')}"

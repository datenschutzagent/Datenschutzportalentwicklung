from webdav3.client import Client
from app.config import settings
import json
from typing import Dict, Any, Tuple
from fastapi import UploadFile
import tempfile
import os
import structlog
from app.logging_config import hmac_sha256_hex

logger = structlog.get_logger(__name__)

class NextcloudService:
    def __init__(self):
        self.client = Client({
            'webdav_hostname': settings.nextcloud_url,
            'webdav_login': settings.nextcloud_username,
            'webdav_password': settings.nextcloud_password,
            'webdav_timeout': 30
        })
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the connection to Nextcloud and verify credentials.
        Returns (success: bool, message: str)
        """
        try:
            # Try to list the root directory to verify connection
            self.client.list('/')
            logger.info("nextcloud_connection_test_successful")
            return True, "Connection successful"
        except Exception as e:
            error_msg = f"Failed to connect to Nextcloud: {e}"
            logger.error("nextcloud_connection_test_failed", exc_info=True)
            return False, error_msg
    
    def create_folder(self, path: str) -> bool:
        """
        Create a folder in Nextcloud, including all parent directories if needed.
        """
        try:
            # Normalize path: remove leading/trailing slashes and split
            normalized_path = path.strip('/')
            if not normalized_path:
                logger.error("nextcloud_create_folder_empty_path")
                return False
            
            path_parts = normalized_path.split('/')
            
            # Create each directory in the path hierarchy
            current_path = ""
            for part in path_parts:
                if not part:
                    continue
                    
                if current_path:
                    current_path = f"{current_path}/{part}"
                else:
                    current_path = part
                
                # Ensure path starts with / for WebDAV
                full_path = f"/{current_path}"
                
                try:
                    if not self.client.check(full_path):
                        logger.debug(
                            "nextcloud_folder_creating",
                            folder_path_hash=hmac_sha256_hex(full_path, settings.log_redaction_secret)[:16],
                        )
                        self.client.mkdir(full_path)
                        logger.debug(
                            "nextcloud_folder_created",
                            folder_path_hash=hmac_sha256_hex(full_path, settings.log_redaction_secret)[:16],
                        )
                    else:
                        logger.debug(
                            "nextcloud_folder_exists",
                            folder_path_hash=hmac_sha256_hex(full_path, settings.log_redaction_secret)[:16],
                        )
                except Exception as e:
                    logger.error(
                        "nextcloud_folder_create_failed",
                        folder_path_hash=hmac_sha256_hex(full_path, settings.log_redaction_secret)[:16],
                        exc_info=True,
                    )
                    raise
            
            logger.info("nextcloud_folder_structure_ensured")
            return True
        except Exception as e:
            logger.error("nextcloud_create_folder_failed", exc_info=True)
            return False 
    
    async def upload_file(self, file: UploadFile, remote_path: str) -> bool:
        """
        Upload a file to Nextcloud
        """
        tmp_path = None
        try:
            logger.debug(
                "nextcloud_upload_started",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                file_size=file.size,
            )
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                content = await file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            # Upload to Nextcloud
            self.client.upload_sync(remote_path=remote_path, local_path=tmp_path)
            logger.info(
                "nextcloud_upload_completed",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                file_size=file.size,
            )
            
            # Clean up
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return True
        except Exception as e:
            logger.error(
                "nextcloud_upload_failed",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                exc_info=True,
            )
            # Clean up on error
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return False
    
    async def upload_metadata(self, metadata: Dict[Any, Any], remote_path: str) -> bool:
        """
        Upload metadata JSON to Nextcloud
        """
        tmp_path = None
        try:
            logger.debug(
                "nextcloud_metadata_upload_started",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
            )
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as tmp_file:
                json.dump(metadata, tmp_file, indent=2)
                tmp_path = tmp_file.name
            
            self.client.upload_sync(remote_path=remote_path, local_path=tmp_path)
            logger.info(
                "nextcloud_metadata_upload_completed",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
            )
            
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return True
        except Exception as e:
            logger.error(
                "nextcloud_metadata_upload_failed",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                exc_info=True,
            )
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return False

    async def upload_content(self, content: str, remote_path: str) -> bool:
        """
        Upload text content to Nextcloud
        """
        tmp_path = None
        try:
            logger.debug(
                "nextcloud_content_upload_started",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                chars=len(content),
            )
            with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8') as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            self.client.upload_sync(remote_path=remote_path, local_path=tmp_path)
            logger.info(
                "nextcloud_content_upload_completed",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                chars=len(content),
            )
            
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            return True
        except Exception as e:
            logger.error(
                "nextcloud_content_upload_failed",
                remote_path_hash=hmac_sha256_hex(remote_path, settings.log_redaction_secret)[:16],
                exc_info=True,
            )
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return False
    
    def list_files(self, path: str) -> list:
        """
        List files in a Nextcloud directory
        """
        try:
            files = self.client.list(path)
            logger.debug(
                "nextcloud_list_files_completed",
                files_count=len(files),
                path_hash=hmac_sha256_hex(path, settings.log_redaction_secret)[:16],
            )
            return files
        except Exception as e:
            logger.error(
                "nextcloud_list_files_failed",
                path_hash=hmac_sha256_hex(path, settings.log_redaction_secret)[:16],
                exc_info=True,
            )
            raise

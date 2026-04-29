import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from unittest.mock import MagicMock, patch, AsyncMock
from app.config import settings
import json

@pytest.mark.asyncio
async def test_upload_documents():
    # Mock NextcloudService and EmailService
    with patch("app.routes.upload.nextcloud") as mock_nextcloud, \
         patch("app.routes.upload.email_service") as mock_email:
        
        # Setup mocks to be awaitable
        mock_nextcloud.test_connection = MagicMock(return_value=(True, "Connection successful"))
        mock_nextcloud.create_folder = MagicMock(return_value=True) # create_folder is sync in my impl
        mock_nextcloud.upload_file = AsyncMock(return_value=True)
        mock_nextcloud.upload_metadata = AsyncMock(return_value=True)
        mock_nextcloud.upload_content = AsyncMock(return_value=True)
        mock_nextcloud.get_metadata = AsyncMock(return_value={})
        
        mock_email.send_confirmation_email = AsyncMock(return_value=True)
        mock_email.send_team_notification = AsyncMock(return_value=True)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            files = [
                ("files", ("test.pdf", b"fake pdf content", "application/pdf")),
                ("files", ("concept.pdf", b"fake concept", "application/pdf"))
            ]
            
            categories_map = {
                "test.pdf": "sonstiges",
                "concept.pdf": "datenschutzkonzept"
            }
            
            data = {
                "email": "test@uni-frankfurt.de",
                "project_title": "Test Project",
                "institution": "university",
                "is_prospective_study": "false",
                "file_categories": json.dumps(categories_map)
            }
            
            # Test without token (should fail)
            response = await client.post("/api/upload", data=data, files=files)
            assert response.status_code in [401, 403] # Depends on exact failure (missing vs invalid)
            
            # Test with token
            headers = {"Authorization": f"Bearer {settings.api_token}"}
            # We need to recreate files iterator as it was consumed
            files = [
                ("files", ("test.pdf", b"fake pdf content", "application/pdf")),
                ("files", ("concept.pdf", b"fake concept", "application/pdf"))
            ]
            
            response = await client.post("/api/upload", data=data, files=files, headers=headers)
            
            if response.status_code != 200:
                print(f"Response error: {response.text}")
            
            assert response.status_code == 200
            result = response.json()
            assert result["success"]
            assert "project_id" in result
            assert result["files_uploaded"] == 2
            
            # Verify mock calls
            assert mock_nextcloud.create_folder.call_count >= 1
            assert mock_nextcloud.upload_file.call_count == 2


@pytest.mark.asyncio
async def test_upload_allows_payload_when_extension_is_allowed():
    """
    The upload endpoint only validates file extensions (no magic-bytes validation).
    This test documents the expected behavior to avoid reintroducing content-based checks
    that might cause false negatives (e.g. Office/ODF ZIP containers).
    """
    with patch("app.routes.upload.nextcloud") as mock_nextcloud, \
         patch("app.routes.upload.email_service") as mock_email:

        mock_nextcloud.test_connection = MagicMock(return_value=(True, "Connection successful"))
        mock_nextcloud.create_folder = MagicMock(return_value=True)
        mock_nextcloud.upload_file = AsyncMock(return_value=True)
        mock_nextcloud.upload_metadata = AsyncMock(return_value=True)
        mock_nextcloud.upload_content = AsyncMock(return_value=True)
        mock_nextcloud.get_metadata = AsyncMock(return_value={})

        mock_email.send_confirmation_email = AsyncMock(return_value=True)
        mock_email.send_team_notification = AsyncMock(return_value=True)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {settings.api_token}"}
            files = [
                ("files", ("test.pdf", b"definitely not a real PDF", "application/pdf")),
            ]
            data = {
                "email": "test@uni-frankfurt.de",
                "project_title": "Test Project",
                "institution": "university",
                "is_prospective_study": "false",
                "file_categories": json.dumps({"test.pdf": "sonstiges"}),
            }

            response = await client.post("/api/upload", data=data, files=files, headers=headers)
            if response.status_code != 200:
                print(f"Response error: {response.text}")
            assert response.status_code == 200


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_extension():
    with patch("app.routes.upload.nextcloud") as mock_nextcloud, \
         patch("app.routes.upload.email_service") as mock_email:

        # Even though Nextcloud is mocked, the request should fail before any storage actions.
        mock_nextcloud.test_connection = MagicMock(return_value=(True, "Connection successful"))
        mock_nextcloud.create_folder = MagicMock(return_value=True)
        mock_nextcloud.upload_file = AsyncMock(return_value=True)
        mock_nextcloud.upload_metadata = AsyncMock(return_value=True)
        mock_nextcloud.upload_content = AsyncMock(return_value=True)
        mock_nextcloud.get_metadata = AsyncMock(return_value={})

        mock_email.send_confirmation_email = AsyncMock(return_value=True)
        mock_email.send_team_notification = AsyncMock(return_value=True)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = {"Authorization": f"Bearer {settings.api_token}"}
            files = [
                ("files", ("shell.php", b"<?php echo 'hi';", "application/x-php")),
            ]
            data = {
                "email": "test@uni-frankfurt.de",
                "project_title": "Test Project",
                "institution": "university",
                "is_prospective_study": "false",
                "file_categories": json.dumps({"shell.php": "sonstiges"}),
            }

            response = await client.post("/api/upload", data=data, files=files, headers=headers)
            assert response.status_code == 400

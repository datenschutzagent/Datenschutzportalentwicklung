import pytest
from unittest.mock import AsyncMock, patch

from structlog.testing import capture_logs

from app.config import settings
from app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_send_email_logs_context_on_smtp_failure():
    service = EmailService()

    with patch("app.services.email_service.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.side_effect = ConnectionRefusedError("Connection refused")
        with capture_logs() as cap_logs:
            result = await service.send_email(
                "recipient@example.com",
                "Test Subject",
                "<p>Test</p>",
                mail_kind="confirmation",
                project_id="Test_Project_2026-05-19",
            )

    assert result is False
    failed_logs = [log for log in cap_logs if log.get("event") == "email_send_failed"]
    assert len(failed_logs) == 1
    log = failed_logs[0]
    assert log["mail_kind"] == "confirmation"
    assert log["project_id"] == "Test_Project_2026-05-19"
    assert log["error_type"] == "ConnectionRefusedError"
    assert "Connection refused" in log["error_message"]
    assert "smtp_host" in log
    assert "smtp_port" in log
    assert "smtp_encryption" in log
    assert "recipient_hash" in log


@pytest.mark.asyncio
async def test_send_team_notification_returns_false_when_any_recipient_fails():
    service = EmailService()

    with patch.object(settings, "notification_emails", ["team1@example.com", "team2@example.com"]), \
         patch.object(service, "send_email", new_callable=AsyncMock) as mock_send_email:
        mock_send_email.side_effect = [True, False]

        with capture_logs() as cap_logs:
            result = await service.send_team_notification(
                project_id="Test_Project_2026-05-19",
                project_title="Test Project",
                uploader_email="uploader@example.com",
                file_names=["test.pdf"],
            )

    assert result is False
    partial_logs = [log for log in cap_logs if log.get("event") == "team_notification_partial_failure"]
    assert len(partial_logs) == 1
    assert partial_logs[0]["failed_count"] == 1
    assert partial_logs[0]["total_count"] == 2


@pytest.mark.asyncio
async def test_send_team_notification_returns_false_when_all_recipients_fail():
    service = EmailService()

    with patch.object(settings, "notification_emails", ["team1@example.com"]), \
         patch.object(service, "send_email", new_callable=AsyncMock, return_value=False):
        result = await service.send_team_notification(
            project_id="Test_Project_2026-05-19",
            project_title="Test Project",
            uploader_email="uploader@example.com",
            file_names=["test.pdf"],
        )

    assert result is False

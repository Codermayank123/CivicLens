from __future__ import annotations

from html import escape
from functools import lru_cache

import structlog

from app.config import Settings, get_settings
from app.email.base import EmailAttachment, EmailMessage
from app.email.registry import build_email_provider

logger = structlog.get_logger()


class EmailService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._provider = build_email_provider(self._settings)

    async def send(
        self,
        to: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
        attachments: tuple[EmailAttachment, ...] = (),
        *,
        raise_on_failure: bool = False,
    ) -> None:
        if not to:
            return
        html_body = html_body or _default_html(subject, text_body)
        message = EmailMessage(to=to, subject=subject, text_body=text_body, html_body=html_body, reply_to=self._settings.EMAIL_REPLY_TO or None, attachments=attachments)
        try:
            return await self._provider.send(message)
        except Exception as exc:
            logger.error("email.send_failed", subject=subject, error=type(exc).__name__)
            if raise_on_failure or self._settings.is_production:
                raise
        return None

    async def send_otp(self, *, to: str, code: str, expires_in_minutes: int) -> str | None:
        return await self.send(
            to=to,
            subject=f"{self._settings.APP_NAME} verification code",
            text_body=(
                f"Your CivicLens verification code is {code}. It expires in "
                f"{expires_in_minutes} minutes. If you did not request this, ignore this email."
            ),
            html_body=_otp_html(self._settings.APP_NAME, code, expires_in_minutes),
            raise_on_failure=True,
        )

    async def send_welcome(self, *, to: str, name: str) -> str | None:
        return await self.send(
            to=to,
            subject=f"Welcome to {self._settings.APP_NAME}",
            text_body=f"Welcome to CivicLens, {name}. Your account is ready.",
            html_body=_welcome_html(self._settings.APP_NAME, name),
            raise_on_failure=False,
        )

    async def send_password_reset(self, *, to: str, reset_url: str, expires_in_minutes: int) -> str | None:
        return await self.send(
            to=to,
            subject=f"{self._settings.APP_NAME} password reset",
            text_body=f"Reset your CivicLens password: {reset_url}\nThis link expires in {expires_in_minutes} minutes.",
            html_body=_action_html(self._settings.APP_NAME, "Reset your password", "Use the secure link below to continue.", reset_url, "Reset password"),
            raise_on_failure=True,
        )

    async def send_security_alert(self, *, to: str, message: str) -> str | None:
        return await self.send(
            to=to,
            subject=f"{self._settings.APP_NAME} account security alert",
            text_body=message,
            html_body=_default_html(f"{self._settings.APP_NAME} account security alert", message),
            raise_on_failure=False,
        )

    async def send_complaint_update(
        self,
        *,
        to: str,
        name: str | None,
        public_id: str,
        status: str,
        remarks: str | None,
        updated_at: str,
        department: str | None,
        tracking_url: str,
        attachments: tuple[EmailAttachment, ...] = (),
    ) -> str | None:
        subject = f"{self._settings.APP_NAME} complaint #{public_id}: {status.replace('_', ' ').title()}"
        text = (
            f"Hello {name or 'Citizen'},\n\nComplaint #{public_id} has an update.\n"
            f"Status: {status.replace('_', ' ').title()}\n"
            f"Department: {department or 'Not assigned'}\n"
            f"Updated: {updated_at}\n"
            f"Remarks: {remarks or 'No additional remarks.'}\n\n"
            f"Track your complaint securely: {tracking_url}"
        )
        return await self.send(
            to=to,
            subject=subject,
            text_body=text,
            html_body=_complaint_html(self._settings.APP_NAME, name, public_id, status, remarks, updated_at, department, tracking_url, bool(attachments)),
            attachments=attachments,
            raise_on_failure=False,
        )


@lru_cache
def get_email_service() -> EmailService:
    return EmailService()


def _default_html(subject: str, text_body: str) -> str:
    paragraphs = "".join(f"<p>{escape(line)}</p>" for line in text_body.splitlines() if line.strip())
    return f"""<!doctype html><html><body style=\"margin:0;background:#f4e8d5;font-family:Arial,sans-serif;color:#29232b\">
      <div style=\"max-width:640px;margin:24px auto;background:#fffdf6;border:1px solid #dcc6a7\">
        <div style=\"padding:20px 24px;background:#4b205b;color:#fff\"><strong>CivicLens</strong></div>
        <main style=\"padding:24px\"><h1 style=\"font-size:20px\">{escape(subject)}</h1>{paragraphs}</main>
        <footer style=\"padding:16px 24px;color:#66565f;font-size:12px;border-top:1px solid #dcc6a7\">CivicLens civic resolution services</footer>
      </div></body></html>"""


def _otp_html(app_name: str, code: str, expires: int) -> str:
    return _default_html(f"{app_name} verification code", f"Your verification code is {code}. It expires in {expires} minutes.")


def _welcome_html(app_name: str, name: str) -> str:
    return _default_html(f"Welcome to {app_name}", f"Welcome to CivicLens, {name}. Your account is ready.")


def _action_html(app_name: str, title: str, message: str, url: str, label: str) -> str:
    return f"""<!doctype html><html><body style='margin:0;background:#f4e8d5;font-family:Arial,sans-serif;color:#29232b'><div style='max-width:640px;margin:24px auto;background:#fffdf6;border:1px solid #dcc6a7'><div style='padding:20px 24px;background:#4b205b;color:#fff'><strong>{escape(app_name)}</strong></div><main style='padding:24px'><h1>{escape(title)}</h1><p>{escape(message)}</p><p><a href='{escape(url)}' style='display:inline-block;padding:12px 18px;background:#4b205b;color:#fff;text-decoration:none;border-radius:6px'>{escape(label)}</a></p></main></div></body></html>"""


def _complaint_html(app_name: str, name: str | None, public_id: str, status: str, remarks: str | None, updated_at: str, department: str | None, tracking_url: str, has_attachments: bool) -> str:
    attachment_note = "Final resolution photographs are attached." if has_attachments else "Final evidence is available through the secure tracking link."
    return f"""<!doctype html><html><body style='margin:0;background:#f4e8d5;font-family:Arial,sans-serif;color:#29232b'><div style='max-width:640px;margin:24px auto;background:#fffdf6;border:1px solid #dcc6a7'><div style='padding:20px 24px;background:#4b205b;color:#fff'><strong>{escape(app_name)}</strong></div><main style='padding:24px'><p>Hello {escape(name or 'Citizen')},</p><h1>Complaint #{escape(public_id)} update</h1><p>Your complaint is now <strong>{escape(status.replace('_', ' ').title())}</strong>.</p><table style='width:100%;border-collapse:collapse'><tr><td style='padding:8px 0'><strong>Department</strong></td><td>{escape(department or 'Not assigned')}</td></tr><tr><td style='padding:8px 0'><strong>Updated</strong></td><td>{escape(updated_at)}</td></tr><tr><td style='padding:8px 0'><strong>Remarks</strong></td><td>{escape(remarks or 'No additional remarks.')}</td></tr></table><p>{escape(attachment_note)}</p><p><a href='{escape(tracking_url)}' style='display:inline-block;padding:12px 18px;background:#4b205b;color:#fff;text-decoration:none;border-radius:6px'>View complaint securely</a></p></main><footer style='padding:16px 24px;color:#66565f;font-size:12px;border-top:1px solid #dcc6a7'>CivicLens civic resolution services</footer></div></body></html>"""

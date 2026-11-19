from __future__ import annotations

from app.config import Settings
from app.email.base import EmailProvider
from app.email.providers.mock import MockEmailProvider
from app.email.providers.brevo import BrevoEmailProvider
from app.email.providers.resend import ResendEmailProvider
from app.email.providers.smtp import SmtpEmailProvider


def build_email_provider(settings: Settings) -> EmailProvider:
    provider = settings.EMAIL_PROVIDER.strip().lower()
    if provider == "mock":
        return MockEmailProvider()
    if provider == "smtp":
        if not settings.SMTP_HOST.strip():
            raise ValueError("SMTP_HOST is required when EMAIL_PROVIDER=smtp")
        return SmtpEmailProvider(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            from_address=settings.EMAIL_FROM,
        )
    if provider == "resend":
        if not settings.RESEND_API_KEY.strip():
            raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER=resend")
        return ResendEmailProvider(api_key=settings.RESEND_API_KEY, from_address=settings.EMAIL_FROM)
    if provider == "brevo":
        if not all((settings.BREVO_API_KEY.strip(), settings.BREVO_SENDER_EMAIL.strip(), settings.BREVO_SENDER_NAME.strip())):
            raise ValueError("BREVO_API_KEY, BREVO_SENDER_EMAIL and BREVO_SENDER_NAME are required when EMAIL_PROVIDER=brevo")
        return BrevoEmailProvider(
            api_key=settings.BREVO_API_KEY,
            sender_email=settings.BREVO_SENDER_EMAIL,
            sender_name=settings.BREVO_SENDER_NAME,
        )
    raise ValueError(f"Unsupported EMAIL_PROVIDER: {settings.EMAIL_PROVIDER}")

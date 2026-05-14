from __future__ import annotations

from typing import Optional

from django.conf import settings

from .resend_client import ResendError, send_resend_email
from .templates import EmailPayload


def _get_admin_emails() -> list[str]:
    import logging
    logger = logging.getLogger(__name__)
    
    raw = getattr(settings, "EMAILING_ADMIN_EMAILS", None)
    if raw:
        if isinstance(raw, str):
            emails = [e.strip() for e in raw.split(",") if e.strip()]
        else:
            emails = [e.strip() for e in raw if e and e.strip()]
        
        if emails:
            logger.info(f"Admin emails configured: {emails}")
            return emails
        else:
            logger.warning("EMAILING_ADMIN_EMAILS is set but empty - no admin notifications will be sent!")
            return []
    
    logger.warning("EMAILING_ADMIN_EMAILS not configured - no admin notifications will be sent!")
    return []


def send_email(payload: EmailPayload, *, to_email: str) -> None:
    """
    Low-level send. Raises ResendError on failure so caller can decide whether to swallow.
    """
    if not to_email:
        raise ValueError("to_email is required")

    send_resend_email(
        to_emails=[to_email],
        subject=payload.subject,
        html=payload.html,
        text=payload.text,
    )


def send_email_to_admin(payload: EmailPayload) -> None:
    admin_emails = _get_admin_emails()
    if not admin_emails:
        raise ResendError("EMAILING_ADMIN_EMAILS is missing or empty")

    send_resend_email(
        to_emails=admin_emails,
        subject=payload.subject,
        html=payload.html,
        text=payload.text,
    )

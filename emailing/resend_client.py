from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import requests
from django.conf import settings


@dataclass(frozen=True)
class ResendConfig:
    api_key: str
    from_email: str


class ResendError(RuntimeError):
    pass


def get_resend_config() -> ResendConfig:
    # Use Django settings first, fallback to environment variables
    import logging
    logger = logging.getLogger(__name__)
    
    api_key = getattr(settings, "RESEND_API_KEY", "").strip()
    from_email = getattr(settings, "RESEND_FROM_EMAIL", "").strip()

    if not api_key:
        logger.error("RESEND_API_KEY is missing - emails cannot be sent!")
        raise ResendError("RESEND_API_KEY is missing")
    if not from_email:
        logger.error("RESEND_FROM_EMAIL is missing - emails cannot be sent!")
        raise ResendError("RESEND_FROM_EMAIL is missing")

    logger.info(f"Resend configured with from_email: {from_email}")
    return ResendConfig(api_key=api_key, from_email=from_email)


def send_resend_email(
    *,
    to_emails: Iterable[str],
    subject: str,
    html: str,
    text: Optional[str] = None,
) -> dict:
    """
    Sends an email via Resend.

    Resend API docs (send endpoint): https://resend.com/docs
    """
    cfg = get_resend_config()
    to_list = [e.strip() for e in to_emails if e and e.strip()]
    if not to_list:
        raise ResendError("No recipient email addresses provided")

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": cfg.from_email,
        "to": to_list,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    resp = requests.post(url, json=payload, headers=headers, timeout=20)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        raise ResendError(f"Resend send failed ({resp.status_code}): {data}")

    return data

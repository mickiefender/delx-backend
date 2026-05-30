import json
import logging
import os
from typing import Any, Dict, Optional

from firebase_admin import credentials, initialize_app, messaging
from firebase_admin.exceptions import FirebaseError
from firebase_admin import get_app

logger = logging.getLogger(__name__)

_APP_INITIALIZED = False


def _get_service_account_json() -> Optional[dict]:
    """
    Reads Firebase service account JSON from env.

    Expected env var:
      - FIREBASE_SERVICE_ACCOUNT_JSON

    It can be either:
      - raw JSON string
      - or a path to a JSON file
    """
    value = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not value:
        return None

    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.exception("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON")
            return None

    # Treat as file path
    try:
        with open(value, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # Try resolving relative paths from the backend1 directory
        try:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            alt_path = os.path.join(base_dir, value)
            with open(alt_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Failed to read FIREBASE_SERVICE_ACCOUNT_JSON from relative file path")
            return None
    except Exception:
        logger.exception("Failed to read FIREBASE_SERVICE_ACCOUNT_JSON from file path")
        return None


def init_firebase_admin() -> None:
    """
    Initializes Firebase Admin SDK once per process.
    Safe to call multiple times.
    """
    global _APP_INITIALIZED
    if _APP_INITIALIZED:
        return

    sa = _get_service_account_json()
    if sa is None:
        logger.warning(
            "Firebase Admin SDK not initialized: missing FIREBASE_SERVICE_ACCOUNT_JSON env var."
        )
        _APP_INITIALIZED = True
        return

    try:
        # If already initialized elsewhere, don't re-init.
        try:
            get_app()
            _APP_INITIALIZED = True
            return
        except Exception:
            pass

        cred = credentials.Certificate(sa)
        initialize_app(cred)
        _APP_INITIALIZED = True
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception:
        logger.exception("Failed to initialize Firebase Admin SDK.")
        _APP_INITIALIZED = True


def send_fcm_to_tokens(
    *,
    registration_tokens: list[str],
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Sends a notification to multiple FCM device tokens.

    Returns:
      {
        "success_count": int,
        "failure_count": int,
        "responses": list[messaging.SendResponse|Exception]
      }
    """
    if not registration_tokens:
        return {"success_count": 0, "failure_count": 0, "responses": []}

    init_firebase_admin()
    try:
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            tokens=registration_tokens,
        )

        response = messaging.send_multicast(message, dry_run=False)
        responses: list[Any] = list(response.responses)

        return {
            "success_count": int(response.success_count),
            "failure_count": int(response.failure_count),
            "responses": responses,
        }
    except FirebaseError as e:
        logger.error("FCM send failed with FirebaseError: %s", e, exc_info=e)
        return {"success_count": 0, "failure_count": len(registration_tokens), "responses": [e]}
    except Exception as e:
        logger.error("FCM send failed: %s", e, exc_info=e)
        return {"success_count": 0, "failure_count": len(registration_tokens), "responses": [e]}

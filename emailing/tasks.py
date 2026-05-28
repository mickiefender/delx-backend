from __future__ import annotations

import logging
from functools import wraps
from typing import Optional

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from celery.utils.log import get_task_logger

from analytics.models import AbandonedCart
from .resend_client import ResendError
from .service import send_email, send_email_to_admin
from .templates import (
    abandoned_cart_reminder_email,
    login_email,
    order_success_admin_email,
    order_success_customer_email,
    signup_email,
    tracking_update_customer_email,
    password_reset_email,
    password_reset_confirmation_email,
    low_stock_warning_admin_email,
)

logger = get_task_logger(__name__)


# Decorator for tasks that need to handle Resend errors with retry
def task_with_resend_retry(func):
    """
    Decorator that adds retry logic for Resend API errors.
    
    Tasks decorated with this will retry on ResendError up to 3 times.
    """
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        self = kwargs.pop("_self", None)
        try:
            return func(*args, **kwargs)
        except ResendError as e:
            if self:
                try:
                    logger.warning(
                        f"Resend error in {func.__name__}: {e}. Retrying...",
                        exc_info=e,
                    )
                    raise self.retry(exc=e, countdown=60, max_retries=3)
                except MaxRetriesExceededError:
                    logger.error(
                        f"Task {func.__name__} exceeded max retries",
                        exc_info=e,
                    )
            raise
    
    return wrapper


class BaseEmailTask(shared_task):
    """
    Base task class for email tasks with retry logic.
    """

    # Retry settings for email tasks
    autoretry_for = (ResendError, ConnectionError, TimeoutError)
    retry_backoff = True
    retry_backoff_max = 300  # 5 minutes max backoff
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails after all retries exhausted."""
        logger.error(
            f"Email task {self.name}[{task_id}] failed permanently: {exc}",
            exc_info=exc,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@shared_task(
    bind=True,
    base=BaseEmailTask,
    autoretry_for=(ResendError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    name="emailing.send_signup_email",
)
def send_signup_email_task(
    self, *, user_id: int, user_email: str, username: str
) -> Optional[dict]:
    if not user_email:
        return {"status": "skipped", "reason": "no email"}
    
    try:
        payload = signup_email(user_email=user_email, username=username)
        send_email(payload, to_email=user_email)
        logger.info(f"Sent signup email to {user_email}")
        return {"status": "sent", "email": user_email}
    except (ResendError, ConnectionError, TimeoutError) as e:
        logger.warning(
            f"Failed to send signup email to {user_email}: {e}. Retrying...",
            exc_info=e,
        )
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    base=BaseEmailTask,
    autoretry_for=(ResendError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    name="emailing.send_login_email",
)
def send_login_email_task(
    self, *, user_id: int, user_email: str, username: str
) -> Optional[dict]:
    if not user_email:
        return {"status": "skipped", "reason": "no email"}
    
    try:
        payload = login_email(user_email=user_email, username=username)
        send_email(payload, to_email=user_email)
        logger.info(f"Sent login email to {user_email}")
        return {"status": "sent", "email": user_email}
    except (ResendError, ConnectionError, TimeoutError) as e:
        logger.warning(
            f"Failed to send login email to {user_email}: {e}. Retrying...",
            exc_info=e,
        )
        raise self.retry(exc=e)


def send_order_confirmed_customer_task(
    *,
    order_id: str,
    shipping_email: str,
    shipping_first_name: str,
    shipping_last_name: str,
    status: str,
) -> Optional[dict]:
    """
    Send order confirmation to customer.
    
    Uses synchronous execution with fallback to ensure emails send
    even when Celery broker is unavailable.
    """
    if not shipping_email:
        logger.warning(f"Skipping order confirmation - no email for order {order_id}")
        return {"status": "skipped", "reason": "no email"}
    
    try:
        from types import SimpleNamespace

        order = SimpleNamespace(
            order_id=order_id,
            shipping_first_name=shipping_first_name,
            shipping_last_name=shipping_last_name,
            shipping_email=shipping_email,
            status=status,
        )
        payload = order_success_customer_email(order)
        
        # Try async first (Celery), fall back to sync if that fails
        try:
            send_email(payload, to_email=shipping_email)
        except Exception as async_error:
            logger.warning(
                f"Celery/async failed for order {order_id}: {async_error}. "
                "Falling back to synchronous send."
            )
            # Synchronous fallback - send directly
            from .resend_client import send_resend_email
            send_resend_email(
                to_emails=[shipping_email],
                subject=payload.subject,
                html=payload.html,
                text=payload.text,
            )
        
        logger.info(f"Sent order confirmation to {shipping_email}")
        return {"status": "sent", "email": shipping_email, "order_id": order_id}
    except Exception as e:
        logger.error(
            f"Failed to send order confirmation to {shipping_email}: {e}",
            exc_info=e,
        )
        return {"status": "failed", "error": str(e)}


def send_order_confirmed_admin_task(
    *,
    order_id: str,
    shipping_email: str,
    status: str,
) -> Optional[dict]:
    """
    Send order confirmation notification to admin.
    
    Uses synchronous execution with fallback to ensure emails send
    even when Celery broker is unavailable.
    """
    try:
        from types import SimpleNamespace

        order = SimpleNamespace(
            order_id=order_id,
            shipping_email=shipping_email,
            status=status,
        )
        payload = order_success_admin_email(order)
        
        # Try async first (Celery), fall back to sync if that fails
        try:
            send_email_to_admin(payload)
        except Exception as async_error:
            logger.warning(
                f"Celery/async failed for admin notification (order {order_id}): {async_error}. "
                "Falling back to synchronous send."
            )
            # Synchronous fallback - send directly
            from .resend_client import send_resend_email
            from .service import _get_admin_emails
            
            admin_emails = _get_admin_emails()
            if admin_emails:
                send_resend_email(
                    to_emails=admin_emails,
                    subject=payload.subject,
                    html=payload.html,
                    text=payload.text,
                )
        
        logger.info(f"Sent order admin notification for order {order_id}")
        return {"status": "sent", "order_id": order_id}
    except Exception as e:
        logger.error(
            f"Failed to send order admin notification for {order_id}: {e}",
            exc_info=e,
        )
        return {"status": "failed", "error": str(e)}


def send_tracking_update_customer_task(
    *,
    order_id: str,
    shipping_email: str,
    shipping_first_name: str,
    shipping_last_name: str,
    new_status: str,
    message: str,
    location: str,
) -> Optional[dict]:
    """
    Send tracking status update email to customer.
    
    Uses synchronous execution with fallback to ensure emails send
    even when Celery broker is unavailable.
    """
    if not shipping_email:
        logger.warning(f"Skipping tracking update - no email for order {order_id}")
        return {"status": "skipped", "reason": "no email"}
    
    try:
        from types import SimpleNamespace

        order = SimpleNamespace(
            order_id=order_id,
            shipping_first_name=shipping_first_name,
            shipping_last_name=shipping_last_name,
            shipping_email=shipping_email,
            status=new_status,
        )
        payload = tracking_update_customer_email(
            order=order,
            new_status=new_status,
            message=message,
            location=location or "",
        )
        
        # Try email sending - with fallback to sync if Celery fails
        try:
            send_email(payload, to_email=shipping_email)
        except Exception as async_error:
            logger.warning(
                f"Celery/async failed for tracking update (order {order_id}): {async_error}. "
                "Falling back to synchronous send."
            )
            # Synchronous fallback - send directly via Resend API
            from .resend_client import send_resend_email
            send_resend_email(
                to_emails=[shipping_email],
                subject=payload.subject,
                html=payload.html,
                text=payload.text,
            )
        
        logger.info(f"Sent tracking update to {shipping_email}")
        return {"status": "sent", "email": shipping_email, "order_id": order_id}
    except Exception as e:
        logger.error(
            f"Failed to send tracking update to {shipping_email}: {e}",
            exc_info=e,
        )
        return {"status": "failed", "error": str(e)}


@shared_task(
    bind=True,
    base=BaseEmailTask,
    autoretry_for=(ResendError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    name="emailing.send_abandoned_cart_reminders_batch",
)
def send_abandoned_cart_reminders_batch(self) -> int:
    """
    Sends abandoned cart reminders for carts older than 3 days
    that haven't been emailed yet. Returns number sent.
    """
    from datetime import timedelta
    from django.utils import timezone

    now = timezone.now()
    cutoff = now - timedelta(days=3)

    qs = (
        AbandonedCart.objects.filter(
            recovery_email_sent=False,
            created_at__lte=cutoff,
            user__is_active=True,
        )
        .select_related("user")
        .order_by("created_at")[:1000]
    )

    sent = 0
    failed = 0

    for cart in qs:
        user = cart.user
        if not user or not user.email:
            continue

        try:
            payload = abandoned_cart_reminder_email(
                order_email=user.email,
                username=user.username,
                total_value=str(cart.total_value),
            )
            send_email(payload, to_email=user.email)
            cart.recovery_email_sent = True
            cart.recovery_email_sent_at = now
            cart.save(update_fields=["recovery_email_sent", "recovery_email_sent_at"])
            sent += 1
        except (ResendError, ConnectionError, TimeoutError) as e:
            logger.warning(
                f"Failed to send abandoned cart email to {user.email}: {e}. "
                "Will retry later.",
                exc_info=e,
)
            failed += 1
            # Don't mark as sent on failure - will retry next run
    
            logger.info(
                f"Abandoned cart reminder batch complete: sent={sent}, failed={failed}"
            )
            return sent


@shared_task(
    bind=True,
    base=BaseEmailTask,
    autoretry_for=(ResendError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    name="emailing.send_password_reset_email",
)
def send_password_reset_email_task(
    self, *, user_email: str, username: str, reset_url: str
) -> Optional[dict]:
    """Send password reset email to user."""
    if not user_email:
        return {"status": "skipped", "reason": "no email"}
    
    try:
        payload = password_reset_email(
            user_email=user_email,
            username=username,
            reset_url=reset_url,
        )
        send_email(payload, to_email=user_email)
        logger.info(f"Sent password reset email to {user_email}")
        return {"status": "sent", "email": user_email}
    except (ResendError, ConnectionError, TimeoutError) as e:
        logger.warning(
            f"Failed to send password reset email to {user_email}: {e}. Retrying...",
            exc_info=e,
        )
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    base=BaseEmailTask,
    autoretry_for=(ResendError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    name="emailing.send_password_reset_confirmation_email",
)
def send_password_reset_confirmation_email_task(
    self, *, user_email: str, username: str
) -> Optional[dict]:
    """Send password reset confirmation email to user."""
    if not user_email:
        return {"status": "skipped", "reason": "no email"}
    
    try:
        payload = password_reset_confirmation_email(
            user_email=user_email,
            username=username,
        )
        send_email(payload, to_email=user_email)
        logger.info(f"Sent password reset confirmation email to {user_email}")
        return {"status": "sent", "email": user_email}
    except (ResendError, ConnectionError, TimeoutError) as e:
        logger.warning(
            f"Failed to send password reset confirmation to {user_email}: {e}. Retrying...",
            exc_info=e,
        )
        raise self.retry(exc=e)


def send_low_stock_warning_admin_task(
    *,
    order_id: str,
    low_stock_products: list,
) -> Optional[dict]:
    """
    Send low stock warning email to admin.
    
    Called when product stock falls to 10 or below after a purchase.
    Uses synchronous execution with fallback to ensure emails send
    even when Celery broker is unavailable.
    """
    if not low_stock_products:
        logger.warning(f"No low stock products to report for order {order_id}")
        return {"status": "skipped", "reason": "no low stock products"}
    
    try:
        payload = low_stock_warning_admin_email(
            order_id=order_id,
            low_stock_products=low_stock_products,
        )
        
        # Try async first (Celery), fall back to sync if that fails
        try:
            send_email_to_admin(payload)
        except Exception as async_error:
            logger.warning(
                f"Celery/async failed for low stock warning (order {order_id}): {async_error}. "
                "Falling back to synchronous send."
            )
            # Synchronous fallback - send directly
            from .resend_client import send_resend_email
            from .service import _get_admin_emails
            
            admin_emails = _get_admin_emails()
            if admin_emails:
                send_resend_email(
                    to_emails=admin_emails,
                    subject=payload.subject,
                    html=payload.html,
                    text=payload.text,
                )
        
        logger.info(f"Sent low stock warning for order {order_id}: {len(low_stock_products)} products")
        return {"status": "sent", "order_id": order_id, "products_count": len(low_stock_products)}
    except Exception as e:
        logger.error(
            f"Failed to send low stock warning for order {order_id}: {e}",
            exc_info=e,
        )
        return {"status": "failed", "error": str(e)}

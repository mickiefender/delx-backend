from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from analytics.models import AbandonedCart
from emailing.service import send_email
from emailing.templates import abandoned_cart_reminder_email


class Command(BaseCommand):
    help = "Send reminder emails to customers who left items in cart for 3 days (and haven't been emailed yet)."

    def handle(self, *args, **options):
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
        skipped = 0

        for cart in qs:
            user = cart.user
            if not user or not user.email:
                skipped += 1
                continue

            payload = abandoned_cart_reminder_email(
                order_email=user.email,
                username=user.username,
                total_value=str(cart.total_value),
            )

            try:
                send_email(payload, to_email=user.email)
                cart.recovery_email_sent = True
                cart.recovery_email_sent_at = now
                cart.save(update_fields=["recovery_email_sent", "recovery_email_sent_at"])
                sent += 1
            except Exception as exc:
                # Avoid stopping the whole batch on one failure.
                skipped += 1
                self.stderr.write(f"Failed sending reminder to {user.email}: {exc}")

        self.stdout.write(self.style.SUCCESS(f"Done. Sent={sent}, Skipped={skipped}"))

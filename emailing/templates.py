from __future__ import annotations

from dataclasses import dataclass
import html as html_lib
from typing import Optional

from orders.models import Order


@dataclass(frozen=True)
class EmailPayload:
    subject: str
    html: str
    text: Optional[str] = None


def _esc(value: str) -> str:
    # Use stdlib escaping; avoid custom escape utilities.
    return html_lib.escape(value or "", quote=True)


def signup_email(user_email: str, username: str) -> EmailPayload:
    name = username or user_email
    subject = "Welcome to Delchris — your account is ready"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Welcome, {_esc(name)}!</h2>
      <p>Thanks for signing up with Delchris Ecommerce.</p>
      <p>You can now log in and start shopping.</p>
      <hr />
      <p style="color:#555;">If you didn’t create this account, ignore this email.</p>
    </div>
    """.strip()
    text = f"Welcome, {name}! Thanks for signing up with Delchris Ecommerce."
    return EmailPayload(subject=subject, html=html, text=text)


def login_email(user_email: str, username: str) -> EmailPayload:
    name = username or user_email
    subject = "Delchris login confirmation"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Hi {_esc(name)}!</h2>
      <p>You successfully logged in.</p>
      <p>If this wasn’t you, please secure your account.</p>
      <hr />
      <p style="color:#555;">Delchris Ecommerce</p>
    </div>
    """.strip()
    text = f"Hi {name}! You successfully logged in."
    return EmailPayload(subject=subject, html=html, text=text)


def order_success_customer_email(order: Order) -> EmailPayload:
    subject = f"Order confirmed: {order.order_id}"
    customer_name = (
        f"{order.shipping_first_name} {order.shipping_last_name}".strip()
        or order.shipping_email
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Thanks {_esc(customer_name)}!</h2>
      <p>Your order has been successfully confirmed.</p>
      <p><strong>Order ID:</strong> {_esc(str(order.order_id))}</p>
      <p><strong>Status:</strong> {_esc(order.status)}</p>
      <p>You can track your order using your Order ID.</p>
      <hr />
      <p style="color:#555;">Delchris Ecommerce</p>
    </div>
    """.strip()
    text = f"Your order {order.order_id} has been confirmed."
    return EmailPayload(subject=subject, html=html, text=text)


def order_success_admin_email(order: Order) -> EmailPayload:
    subject = f"[ADMIN] New order confirmed: {order.order_id}"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Admin alert</h2>
      <p>A customer order was confirmed successfully.</p>
      <p><strong>Order ID:</strong> {_esc(str(order.order_id))}</p>
      <p><strong>Customer email:</strong> {_esc(order.shipping_email)}</p>
      <p><strong>Status:</strong> {_esc(order.status)}</p>
      <hr />
      <p style="color:#555;">Delchris Ecommerce</p>
    </div>
    """.strip()
    text = f"Order {order.order_id} confirmed for {order.shipping_email}."
    return EmailPayload(subject=subject, html=html, text=text)


def tracking_update_customer_email(
    order: Order,
    new_status: str,
    message: str,
    location: str = "",
) -> EmailPayload:
    customer_name = (
        f"{order.shipping_first_name} {order.shipping_last_name}".strip()
        or order.shipping_email
    )
    subject = f"Update on your order {order.order_id}: {new_status}"
    loc_part = (
        f"<p><strong>Location:</strong> {_esc(location)}</p>" if location else ""
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Hi {_esc(customer_name)}!</h2>
      <p>Your order status has been updated.</p>
      <p><strong>Order ID:</strong> {_esc(str(order.order_id))}</p>
      <p><strong>New status:</strong> {_esc(new_status)}</p>
      {loc_part}
      <p><strong>Message:</strong> {_esc(message)}</p>
      <hr />
      <p style="color:#555;">Delchris Ecommerce</p>
    </div>
    """.strip()
    text = f"Order {order.order_id} updated to {new_status}: {message}"
    return EmailPayload(subject=subject, html=html, text=text)


def abandoned_cart_reminder_email(order_email: str, username: str, total_value: str) -> EmailPayload:
    name = username or order_email
    subject = "You left items in your cart — complete your purchase"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Hi {_esc(name)}!</h2>
      <p>Looks like you left items in your cart.</p>
      <p><strong>Cart value:</strong> {_esc(total_value)}</p>
      <p>Complete your purchase today.</p>
      <hr />
      <p style="color:#555;">Delchris Ecommerce</p>
    </div>
    """.strip()
    text = f"Hi {name}! You left items in your cart worth {total_value}."
    return EmailPayload(subject=subject, html=html, text=text)


def password_reset_email(user_email: str, username: str, reset_url: str) -> EmailPayload:
    name = username or user_email
    subject = "Reset your Delchris password"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Hi {_esc(name)}!</h2>
      <p>We received a request to reset your password.</p>
      <p>Click the button below to create a new password:</p>
      <p style="margin: 20px 0;">
        <a href="{_esc(reset_url)}" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
          Reset Password
        </a>
      </p>
      <p>Or copy and paste this link in your browser:</p>
      <p style="word-break: break-all; font-size: 12px; color: #666;">{_esc(reset_url)}</p>
      <hr />
      <p style="color:#555;">If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
    </div>
    """.strip()
    text = f"Hi {name}! Reset your Delchris password using this link: {reset_url}"
    return EmailPayload(subject=subject, html=html, text=text)


def password_reset_confirmation_email(user_email: str, username: str) -> EmailPayload:
    name = username or user_email
    subject = "Your Delchris password has been reset"
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.5;">
      <h2>Hi {_esc(name)}!</h2>
      <p>Your password has been successfully reset.</p>
      <p>If you didn't do this, please contact us immediately.</p>
      <hr />
      <p style="color:#555;">Delchris Ecommerce</p>
    </div>
    """.strip()
    text = f"Hi {name}! Your password has been successfully reset."
    return EmailPayload(subject=subject, html=html, text=text)

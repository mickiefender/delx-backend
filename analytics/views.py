from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK

from orders.models import Order
from payments.models import Payment
from products.models import Product
from users.models import CustomUser

from analytics.models import PageView, ClickEvent

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status


def _safe_decimal(value: Any) -> Decimal:
    try:
        return value if isinstance(value, Decimal) else Decimal(value or 0)
    except Exception:
        return Decimal("0")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_metrics(request):
    """
    Returns top-level dashboard metrics (global, not user-scoped).
    Revenue is computed from verified successful payments.
    """
    revenue_qs = Payment.objects.filter(status="success", is_verified=True)
    total_revenue = revenue_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    total_orders = Order.objects.all().count()

    # Customers with at least one order
    total_customers = (
        CustomUser.objects.filter(orders__isnull=False).distinct().count()
        if hasattr(CustomUser, "orders")
        else Order.objects.values("user_id").distinct().count()
    )

    products_listed = Product.objects.count()

    # Percent change vs previous month (very simple baseline)
    # If previous month has 0 revenue, change is reported as null.
    now = timezone.now()
    current_month = now.month
    current_year = now.year

    prev_month_dt = (now.replace(day=1) - timezone.timedelta(days=1))
    prev_month = prev_month_dt.month
    prev_year = prev_month_dt.year

    current_revenue = (
        revenue_qs.filter(
            created_at__year=current_year,
            created_at__month=current_month,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )
    previous_revenue = (
        revenue_qs.filter(
            created_at__year=prev_year,
            created_at__month=prev_month,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )

    revenue_change = None
    if previous_revenue > 0:
        revenue_change = ((current_revenue - previous_revenue) / previous_revenue) * 100

    # For the rest of the metrics, we also compute last-month deltas (counts)
    current_orders = Order.objects.filter(created_at__year=current_year, created_at__month=current_month).count()
    previous_orders = Order.objects.filter(created_at__year=prev_year, created_at__month=prev_month).count()
    orders_change = None
    if previous_orders > 0:
        orders_change = ((current_orders - previous_orders) / previous_orders) * 100

    # Customers change (distinct users with orders)
    current_customers = (
        Order.objects.filter(created_at__year=current_year, created_at__month=current_month)
        .values("user_id")
        .distinct()
        .count()
    )
    previous_customers = (
        Order.objects.filter(created_at__year=prev_year, created_at__month=prev_month)
        .values("user_id")
        .distinct()
        .count()
    )
    customers_change = None
    if previous_customers > 0:
        customers_change = ((current_customers - previous_customers) / previous_customers) * 100

    # Products change: active products count vs previous? Products are not time-versioned,
    # so we approximate with "created products in last month".
    current_products_listed = Product.objects.filter(created_at__year=current_year, created_at__month=current_month).count()
    previous_products_listed = Product.objects.filter(created_at__year=prev_year, created_at__month=prev_month).count()
    products_listed_change = None
    if previous_products_listed > 0:
        products_listed_change = ((current_products_listed - previous_products_listed) / previous_products_listed) * 100

    return Response(
        {
            "total_revenue": str(total_revenue),
            "total_orders": total_orders,
            "total_customers": total_customers,
            "products_listed": products_listed,
            "changes": {
                "revenue_percent": revenue_change,
                "orders_percent": orders_change,
                "customers_percent": customers_change,
                "products_listed_percent": products_listed_change,
            },
        },
        status=HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_sales_overview(request):
    """
    Returns a simple monthly overview for the last 6 months:
    - sales: number of orders
    - revenue: sum of verified successful payment amounts
    """
    now = timezone.now()
    start = now - timezone.timedelta(days=180)
    # payments/revenue uses payment created_at
    payments = Payment.objects.filter(status="success", is_verified=True, created_at__gte=start)
    orders = Order.objects.filter(created_at__gte=start)

    # Revenue by month
    revenue_by_month = (
        payments.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(revenue=Sum("amount"))
        .order_by("month")
    )

    # Orders by month
    sales_by_month = (
        orders.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(sales=Count("id"))
        .order_by("month")
    )

    revenue_map = {row["month"]: _safe_decimal(row.get("revenue")) for row in revenue_by_month}
    sales_map = {row["month"]: int(row.get("sales") or 0) for row in sales_by_month}

    # Build contiguous months buckets for the last ~6 months
    buckets: List[Any] = []
    cursor = start.replace(day=1)
    # ensure at least 6 months buckets
    for _ in range(6):
        buckets.append(cursor)
        # move to next month
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    data: List[Dict[str, Any]] = []
    for month_start in buckets:
        key = month_start.replace(hour=0, minute=0, second=0, microsecond=0)
        sales = sales_map.get(key, 0)
        revenue = revenue_map.get(key, Decimal("0"))
        data.append(
            {
                "month": key.strftime("%b"),
                "sales": sales,
                "revenue": str(revenue),
            }
        )

    return Response({"data": data}, status=HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_sales_daily(request):
    """
    Returns daily sales overview for the last 14 days (global, not user-scoped):
    - sales: number of orders per day
    - revenue: sum of verified successful payment amounts per day
    """
    now = timezone.now()
    days = 14
    start = (now - timezone.timedelta(days=days - 1)).date()

    # Only include verified successful payments for revenue
    payments = Payment.objects.filter(
        status="success",
        is_verified=True,
        created_at__date__gte=start,
    )

    orders = Order.objects.filter(
        created_at__date__gte=start,
    )

    # Group by date using created_at__date
    revenue_by_day = (
        payments
        .values("created_at__date")
        .annotate(revenue=Sum("amount"))
        .order_by("created_at__date")
    )

    sales_by_day = (
        orders
        .values("created_at__date")
        .annotate(sales=Count("id"))
        .order_by("created_at__date")
    )

    revenue_map: Dict[Any, Decimal] = {row["created_at__date"]: _safe_decimal(row.get("revenue")) for row in revenue_by_day}
    sales_map: Dict[Any, int] = {row["created_at__date"]: int(row.get("sales") or 0) for row in sales_by_day}

    data: List[Dict[str, Any]] = []
    for i in range(days):
        day = start + timezone.timedelta(days=i)
        data.append(
            {
                "date": day.isoformat(),
                "sales": sales_map.get(day, 0),
                "revenue": str(revenue_map.get(day, Decimal("0"))),
            }
        )

    return Response({"data": data}, status=HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_recent_orders(request):
    """
    Returns the latest orders globally (limit 5),
    joined with the latest verified successful payment when available.

    Also returns a small preview of the purchased items (product_image/name)
    so the admin dashboard can render them next to each recent order.
    """
    limit = int(request.query_params.get("limit", "5"))

    orders = Order.objects.all().order_by("-created_at").select_related().prefetch_related("items")[:limit]

    # Map order_id -> verified payment amount (take first found)
    payments = Payment.objects.filter(order__in=orders, status="success", is_verified=True)
    payment_by_order_id: Dict[str, Payment] = {}
    for p in payments.select_related("order"):
        payment_by_order_id[str(p.order.order_id)] = p

    response_orders: List[Dict[str, Any]] = []
    for o in orders:
        payment = payment_by_order_id.get(str(o.order_id))
        amount = str(payment.amount) if payment else str(o.total_amount)
        customer = f"{o.shipping_first_name} {o.shipping_last_name}".strip()

        # items preview
        # - include up to 3 items so the dashboard stays compact
        item_previews: List[Dict[str, Any]] = []
        for it in o.items.all()[:3]:
            item_previews.append(
                {
                    "id": it.id,
                    "product_name": it.product_name,
                    "product_image": it.product_image,
                    "quantity": it.quantity,
                }
            )

        response_orders.append(
            {
                "id": str(o.order_id),
                "customer": customer or "Customer",
                "amount": amount,
                "status": o.status,
                "date": o.created_at.date().isoformat(),
                "items": item_previews,
            }
        )

    return Response({"data": response_orders}, status=HTTP_200_OK)


# -----------------------------
# Tracking (write endpoints)
# -----------------------------

@api_view(["POST"])
@permission_classes([])
def track_page_view(request):
    """
    Records a page view event.

    Payload:
    - page_name (required)
    - page_path (required)
    - session_id (optional)
    - referrer (optional)
    - device (optional)
    - browser (optional)
    """
    page_name = str(request.data.get("page_name") or "").strip()[:255]
    page_path = str(request.data.get("page_path") or "").strip()[:500]

    if not page_name or not page_path:
        return Response(
            {"detail": "page_name and page_path are required"},
            status=400,
        )

    session_id = str(request.data.get("session_id") or "").strip()[:255]
    referrer = str(request.data.get("referrer") or "").strip()[:500]
    device = str(request.data.get("device") or "").strip()[:50]
    browser = str(request.data.get("browser") or "").strip()[:50]

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip_address = None
    if forwarded:
        ip_address = forwarded.split(",")[0].strip() or None
    else:
        ip_address = (request.META.get("REMOTE_ADDR") or None)

    PageView.objects.create(
        page_name=page_name,
        page_path=page_path,
        user=None,
        session_id=session_id,
        referrer=referrer,
        ip_address=ip_address,
        device=device,
        browser=browser,
    )

    return Response({"ok": True}, status=201)


@api_view(["POST"])
@permission_classes([])
def track_click(request):
    """
    Records a click event.

    Payload:
    - page_path (required)
    - element_label (optional)
    - session_id (optional)
    - device (optional)
    - browser (optional)
    """
    page_path = str(request.data.get("page_path") or "").strip()[:500]
    element_label = str(request.data.get("element_label") or "").strip()[:255]

    if not page_path:
        return Response(
            {"detail": "page_path is required"},
            status=400,
        )

    session_id = str(request.data.get("session_id") or "").strip()[:255]
    device = str(request.data.get("device") or "").strip()[:50]
    browser = str(request.data.get("browser") or "").strip()[:50]

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    ip_address = None
    if forwarded:
        ip_address = forwarded.split(",")[0].strip() or None
    else:
        ip_address = (request.META.get("REMOTE_ADDR") or None)

    ClickEvent.objects.create(
        page_path=page_path,
        session_id=session_id,
        user=None,
        ip_address=ip_address,
        device=device,
        browser=browser,
        element_label=element_label,
    )

    return Response({"ok": True}, status=201)


# -----------------------------
# Performance (read endpoints)
# -----------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def performance_summary(request):
    """
    Returns total clicks + total page views for the last 30 days by default.
    """
    days = int(request.query_params.get("days", "30"))
    since = timezone.now() - timezone.timedelta(days=days)

    total_clicks = ClickEvent.objects.filter(timestamp__gte=since).count()
    total_page_views = PageView.objects.filter(timestamp__gte=since).count()

    return Response(
        {
            "total_clicks": total_clicks,
            "total_page_views": total_page_views,
            "window_days": days,
        },
        status=HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def performance_breakdown(request):
    """
    Returns breakdowns for top:
    - devices
    - browsers
    - page_path
    - ip_address
    - users (if any)

    Query params:
    - days (default 30)
    """
    days = int(request.query_params.get("days", "30"))
    since = timezone.now() - timezone.timedelta(days=days)
    limit = int(request.query_params.get("limit", "10"))

    # Click breakdowns
    top_devices_clicks = (
        ClickEvent.objects.filter(timestamp__gte=since)
        .exclude(device="")
        .values("device")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_browsers_clicks = (
        ClickEvent.objects.filter(timestamp__gte=since)
        .exclude(browser="")
        .values("browser")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_pages_clicks = (
        ClickEvent.objects.filter(timestamp__gte=since)
        .values("page_path")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_ips_clicks = (
        ClickEvent.objects.filter(timestamp__gte=since)
        .exclude(ip_address__isnull=True)
        .exclude(ip_address="")
        .values("ip_address")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_users_clicks = (
        ClickEvent.objects.filter(timestamp__gte=since)
        .exclude(user__isnull=True)
        .values("user_id")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )

    # Page view breakdowns
    top_devices_views = (
        PageView.objects.filter(timestamp__gte=since)
        .exclude(device="")
        .values("device")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_browsers_views = (
        PageView.objects.filter(timestamp__gte=since)
        .exclude(browser="")
        .values("browser")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_pages_views = (
        PageView.objects.filter(timestamp__gte=since)
        .values("page_path")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_ips_views = (
        PageView.objects.filter(timestamp__gte=since)
        .exclude(ip_address__isnull=True)
        .exclude(ip_address="")
        .values("ip_address")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    top_users_views = (
        PageView.objects.filter(timestamp__gte=since)
        .exclude(user__isnull=True)
        .values("user_id")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )

    def _map(rows, key):
        return [{"label": r[key], "count": r["count"]} for r in rows]

    return Response(
        {
            "window_days": days,
            "clicks": {
                "devices": _map(top_devices_clicks, "device"),
                "browsers": _map(top_browsers_clicks, "browser"),
                "pages": _map(top_pages_clicks, "page_path"),
                "ips": _map(top_ips_clicks, "ip_address"),
                "users": _map(top_users_clicks, "user_id"),
            },
            "page_views": {
                "devices": _map(top_devices_views, "device"),
                "browsers": _map(top_browsers_views, "browser"),
                "pages": _map(top_pages_views, "page_path"),
                "ips": _map(top_ips_views, "ip_address"),
                "users": _map(top_users_views, "user_id"),
            },
        },
        status=HTTP_200_OK,
    )

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
import logging

from .models import Order, OrderTracking
from .serializers import OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer

from emailing.service import send_email_to_admin
from emailing.service import send_email
from emailing.templates import (
    order_success_admin_email,
    order_success_customer_email,
    tracking_update_customer_email,
)

logger = logging.getLogger(__name__)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet for orders"""
    serializer_class = OrderListSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUser()]
        return super().get_permissions()

    def get_queryset(self):
        """
        - staff/admin: all orders
        - authenticated customer: only their orders
        - guest: orders matching ?guest_id=... OR ?order_id=... OR ?paystack_reference=...
        """
        request = self.request

        if request.user and request.user.is_authenticated and request.user.is_staff:
            return Order.objects.all()

        if request.user and request.user.is_authenticated:
            return Order.objects.filter(user=request.user)

        # Allow guest lookups by order_id or paystack_reference (for success page verification)
        guest_order_id = request.query_params.get('order_id')
        if guest_order_id:
            return Order.objects.filter(order_id=guest_order_id)

        guest_paystack_ref = request.query_params.get('paystack_reference')
        if guest_paystack_ref:
            return Order.objects.filter(paystack_reference=guest_paystack_ref)

        guest_id = request.query_params.get('guest_id')
        if guest_id:
            return Order.objects.filter(guest_id=guest_id)

        return Order.objects.none()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OrderDetailSerializer
        elif self.action == 'create':
            return OrderCreateSerializer
        elif self.action == 'list':
            # If the client is doing a "lookup" by public order_id/paystack_reference/guest_id,
            # return the full detail serializer so the frontend can render items + tracking history.
            # Keep the list serializer for normal authenticated "my orders" browsing.
            if (
                self.request.query_params.get('order_id')
                or self.request.query_params.get('paystack_reference')
                or self.request.query_params.get('guest_id')
            ):
                return OrderDetailSerializer
        return OrderListSerializer

    def perform_create(self, serializer):
        """
        Create order:
        - authenticated customer -> attach order to request.user
        - guest -> leave user=NULL; guest_id is provided in payload
        """
        if self.request.user and self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save(user=None)

    @action(detail=True, methods=['get'])
    def tracking(self, request, pk=None):
        """Get order tracking information"""
        order = self.get_object()
        tracking_history = order.tracking_history.all()
        from orders.serializers import OrderTrackingSerializer

        serializer = OrderTrackingSerializer(tracking_history, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):

        order = self.get_object()
        if order.status in ['pending', 'confirmed']:
            order.status = 'cancelled'
            order.save()
            return Response({'message': 'Order cancelled successfully'})
        return Response(
            {'error': 'Cannot cancel order in current status'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(detail=True, methods=['post'], url_path='update-status')
    def update_status(self, request, pk=None):
        """
        Admin endpoint to update an order status and append an entry to tracking history.
        Customer order tracking UI depends on this tracking_history.
        """
        order = self.get_object()

        new_status = request.data.get('status')
        message = request.data.get('message') or f"Order status updated to {new_status}"

        if not new_status:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)

        valid_statuses = {choice[0] for choice in Order.STATUS_CHOICES}
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status: {new_status}', 'valid_statuses': sorted(valid_statuses)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = new_status
        order.save(update_fields=['status'])

        location = request.data.get('location') or ''
        OrderTracking.objects.create(
            order=order,
            status=new_status,
            message=message,
            location=location,
        )

        # Send push notification to the authenticated customer (if possible)
        try:
            if order.user_id:
                from users.models import DeviceToken
                from core.fcm_utils import send_fcm_to_tokens

                registration_tokens = list(
                    DeviceToken.objects.filter(user_id=order.user_id).values_list("token", flat=True)
                )

                if registration_tokens:
                    send_fcm_to_tokens(
                        registration_tokens=registration_tokens,
                        title="Order update",
                        body=message or f"Your order status changed to {new_status}.",
                        data={
                            "type": "order",
                            "route": f"/orders/{order.order_id}/tracking",
                            "order_id": str(order.order_id),
                            "status": new_status,
                        },
                    )
        except Exception as e:
            logger.error(f"Failed to send FCM notification for order {order.order_id}: {e}")

        # Email customer with tracking update (sync with fallback; fail gracefully)
        if order.shipping_email:
            try:
                from emailing.tasks import send_tracking_update_customer_task

                result = send_tracking_update_customer_task(
                    order_id=order.order_id,
                    shipping_email=order.shipping_email,
                    shipping_first_name=order.shipping_first_name,
                    shipping_last_name=order.shipping_last_name,
                    new_status=new_status,
                    message=message,
                    location=location,
                )

                logger.info(f"Tracking update email result for {order.order_id}: {result}")
            except Exception as e:
                logger.error(f"Failed to send tracking update email for {order.order_id}: {e}")

        return Response({'message': 'Order updated', 'status': order.status}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='tracking-by-order-id')
    def tracking_by_order_id(self, request):
        """
        Customer-friendly tracking endpoint.
        Fetch tracking history using the public `order_id` (string).
        """
        order_id = request.query_params.get('order_id')
        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        tracking_history = order.tracking_history.all()
        from orders.serializers import OrderTrackingSerializer

        serializer = OrderTrackingSerializer(tracking_history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='confirm-by-id')
    def confirm_by_id(self, request):
        """
        Confirm an order using its public `order_id`.
        Used by the Paystack webhook.
        
        IMPORTANT: Only confirms orders that are in 'awaiting_payment' status.
        This prevents double-confirmation and ensures orders are only confirmed
        AFTER payment has been verified.
        """
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({'error': 'order_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        # Only confirm orders that are in a pre-confirmation state.
        # Some flows may create orders as 'pending' instead of 'awaiting_payment'.
        if order.status not in ['awaiting_payment', 'pending']:
            return Response(
                {'message': f'Order already in status: {order.status}', 'order_id': order.order_id},
                status=status.HTTP_200_OK,
            )

        # Update status
        order.status = 'confirmed'
        order.save(update_fields=['status'])

        # (Optional) add to tracking history if you want a timeline later
        OrderTracking.objects.create(
            order=order,
            status='confirmed',
            message='Payment confirmed via Paystack webhook',
        )

        # Update product stock quantities
        low_stock_products = []
        for item in order.items.all():
            if item.product:
                product = item.product
                # Deduct stock based on quantity purchased
                new_stock = max(0, product.stock_quantity - item.quantity)
                old_stock = product.stock_quantity
                product.stock_quantity = new_stock
                product.save(update_fields=['stock_quantity'])
                
                logger.info(f"Stock updated for {product.name}: {old_stock} -> {new_stock}")
                
                # Check if stock is now 10 or below (low stock warning)
                if new_stock <= 10:
                    low_stock_products.append({
                        'name': product.name,
                        'sku': product.sku,
                        'current_stock': new_stock,
                    })

        # Send low stock warning to admin if any products are low
        if low_stock_products:
            try:
                from emailing.tasks import send_low_stock_warning_admin_task
                send_low_stock_warning_admin_task(
                    order_id=order.order_id,
                    low_stock_products=low_stock_products,
                )
                logger.info(f"Low stock warning sent for order {order.order_id}")
            except Exception as e:
                logger.error(f"Failed to send low stock warning for {order.order_id}: {e}")

        # Emails: customer + admin (sync with fallback)
        if order.shipping_email:
            try:
                from emailing.tasks import (
                    send_order_confirmed_customer_task,
                    send_order_confirmed_admin_task,
                )
                
                # Send to customer
                customer_result = send_order_confirmed_customer_task(
                    order_id=order.order_id,
                    shipping_email=order.shipping_email,
                    shipping_first_name=order.shipping_first_name,
                    shipping_last_name=order.shipping_last_name,
                    status=order.status,
                )
                logger.info(f"Customer email result for {order.order_id}: {customer_result}")
                
                # Send to admin
                admin_result = send_order_confirmed_admin_task(
                    order_id=order.order_id,
                    shipping_email=order.shipping_email,
                    status=order.status,
                )
                logger.info(f"Admin email result for {order.order_id}: {admin_result}")
            except Exception as e:
                logger.error(f"Failed to send order confirmation emails for {order.order_id}: {e}")

        return Response(
            {'message': 'Order confirmed successfully', 'order_id': order.order_id},
            status=status.HTTP_200_OK,
        )

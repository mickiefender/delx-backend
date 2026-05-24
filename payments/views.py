from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import requests
import logging
import hashlib
import hmac

from .models import Payment, Refund
from .serializers import PaymentSerializer, PaymentInitializeSerializer, RefundSerializer, RefundCreateSerializer

logger = logging.getLogger(__name__)


class AllowGuestWithPaystackReferencePermission(BasePermission):
    """
    Custom permission that allows unauthenticated access when a valid paystack_reference
    query parameter is provided. This enables the success page to fetch payment
    data after successful payment without requiring user authentication.
    """
    message = "Authentication required to view payments"

    def has_permission(self, request, view):
        # Allow if user is authenticated
        if request.user and request.user.is_authenticated:
            return True
        
        # Allow GET (list/retrieve) requests with valid paystack_reference
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            paystack_ref = request.query_params.get('paystack_reference')
            if paystack_ref:
                return True
        
        return False


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payments"""
    serializer_class = PaymentSerializer
    permission_classes = [AllowGuestWithPaystackReferencePermission]

    def get_queryset(self):
        """Get payments - filter by user for authenticated, by paystack_reference for guests"""
        request = self.request
        
        # Authenticated users see only their own payments
        if request.user and request.user.is_authenticated:
            return Payment.objects.filter(user=request.user)
        
        # Guests can query by paystack_reference
        paystack_ref = request.query_params.get('paystack_reference')
        if paystack_ref:
            return Payment.objects.filter(paystack_reference=paystack_ref)
        
        # Guests without paystack_reference get empty queryset
        return Payment.objects.none()

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Initialize payment with Paystack"""
        serializer = PaymentInitializeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create payment row (set user explicitly; serializer.create sets order/payment fields)
        payment = serializer.create(serializer.validated_data)
        payment.user = request.user
        payment.status = 'pending'
        payment.save()

        paystack_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not paystack_key:
            return Response(
                {'success': False, 'error': 'Paystack secret key is missing on the server'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        headers = {'Authorization': f'Bearer {paystack_key}'}

        payload = {
            'email': serializer.validated_data['email'],
            'amount': int(payment.amount * 100),  # Paystack uses cents
            'reference': str(payment.id),
        }

        try:
            response = requests.post(
                'https://api.paystack.co/transaction/initialize',
                json=payload,
                headers=headers,
                timeout=15,
            )
            if response.status_code == 200:
                data = response.json()
                payment.paystack_reference = data['data']['reference']
                payment.paystack_authorization_url = data['data']['authorization_url']
                payment.paystack_access_code = data['data']['access_code']
                payment.save()

                # Match frontend contract
                return Response(
                    {
                        'success': True,
                        'data': {
                            'authorizationUrl': data['data']['authorization_url'],
                            'accessCode': data['data']['access_code'],
                            'reference': data['data']['reference'],
                        },
                    },
                    status=status.HTTP_200_OK,
                )

            return Response(
                {'success': False, 'error': 'Failed to initialize payment', 'details': response.text},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except requests.exceptions.RequestException:
            return Response(
                {
                    'success': False,
                    'error': 'Unable to reach Paystack right now. Please try again in a few seconds.',
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("Paystack initialize failed")
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def verify(self, request):
        """Verify payment with Paystack
        
        This endpoint allows unauthenticated verification because:
        - The payment reference itself serves as a security token
        - The webhook handler already uses AllowAny for the same reason
        - This enables frontend callback verification without user login
        
        Lookup priority:
        1. First tries Payment by paystack_reference
        2. Fallback: Try to find Order by order_id (same as reference for guest checkout)
        3. If order exists, check if it has a related payment, otherwise create one
        """
        from orders.models import Order
        
        reference = request.data.get('reference')
        if not reference:
            return Response({'error': 'Reference is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Try to find Payment by paystack_reference
        payment = None
        try:
            payment = Payment.objects.get(paystack_reference=reference)
        except Payment.DoesNotExist:
            payment = None
        
        # Fallback: Try to find by order_id (reference IS the order_id in guest checkout)
        if not payment:
            try:
                order = Order.objects.get(order_id=reference)
                # Try to get related payment - some orders have payment via OneToOne
                if hasattr(order, 'payment') and order.payment:
                    payment = order.payment
                else:
                    # No payment exists yet - create a placeholder Payment for verification
                    # This handles the case where frontend initialize created order but not Payment
                    payment = Payment.objects.create(
                        order=order,
                        user=order.user,
                        amount=order.total_amount,
                        currency='GHS',
                        payment_method='card',
                        status='pending',
                        paystack_reference=reference,
                    )
                    logger.info(f"Created placeholder Payment for order {reference}")
            except Order.DoesNotExist:
                pass
        
        # If still no payment found, try one more approach: search for any payment with matching order
        if not payment:
            try:
                # Find order by paystack_reference field (order may have it set)
                order = Order.objects.filter(paystack_reference=reference).first()
                if order:
                    if hasattr(order, 'payment') and order.payment:
                        payment = order.payment
                    else:
                        payment = Payment.objects.create(
                            order=order,
                            user=order.user,
                            amount=order.total_amount,
                            currency='GHS',
                            payment_method='card',
                            status='pending',
                            paystack_reference=reference,
                        )
            except Exception as e:
                logger.warning(f"Error searching order by paystack_reference: {e}")
        
        if not payment:
            return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)

        paystack_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not paystack_key:
            return Response(
                {'error': 'Paystack secret key is missing on the server'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        headers = {'Authorization': f'Bearer {paystack_key}'}

        try:
            response = requests.get(
                f'https://api.paystack.co/transaction/verify/{reference}',
                headers=headers,
                timeout=15,
            )

            if response.status_code == 200:
                data = response.json()
                if data['data']['status'] == 'success':
                    payment.status = 'success'
                    payment.is_verified = True
                    payment.response_data = data['data']
                    payment.save()

                    # Update order with paystack_reference and change status from awaiting_payment to confirmed
                    if payment.order.status == 'awaiting_payment':
                        # Set the paystack_reference on the order so it can be looked up on success page
                        payment.order.paystack_reference = payment.paystack_reference
                        payment.order.status = 'confirmed'
                        payment.order.save(update_fields=['paystack_reference', 'status'])

                    # Send confirmation emails to customer and admin (sync with fallback)
                    order = payment.order
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
                            # Log error but don't fail the payment verification
                            logger.error(f"Failed to send order confirmation emails: {e}")

                    return Response({'message': 'Payment verified successfully'}, status=status.HTTP_200_OK)

                payment.status = 'failed'
                payment.error_message = data['data'].get('gateway_response')
                payment.save()

                return Response(
                    {'error': 'Payment verification failed', 'details': data['data']},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                {'error': 'Payment verification failed', 'details': response.text},
                status=status.HTTP_400_BAD_REQUEST
            )

        except requests.exceptions.RequestException:
            return Response(
                {'error': 'Unable to reach Paystack right now. Please try again in a few seconds.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class RefundViewSet(viewsets.ModelViewSet):
    """ViewSet for refunds"""
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Refund.objects.filter(payment__user=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a refund request"""
        serializer = RefundCreateSerializer(data=request.data)
        if serializer.is_valid():
            refund = serializer.save()
            return Response(RefundSerializer(refund).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    """
    Paystack Webhook Handler
    
    This endpoint receives webhook events from Paystack for server-to-server
    notification about payment status changes.
    
    Events handled:
    - charge.success: Payment was successful
    - charge.failed: Payment failed
    """
    from django.http import JsonResponse
    
    # Get Paystack signature from header
    paystack_signature = request.headers.get('x-paystack-signature', '')
    
    if not paystack_signature:
        logger.warning("Paystack webhook received without signature")
        return Response({'error': 'Missing signature'}, status=status.HTTP_401_UNAUTHORIZED)
    
    # Validate webhook signature
    secret_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
    if not secret_key:
        logger.error("Paystack secret key not configured")
        return Response({'error': 'Server configuration error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    try:
        # Get raw payload for signature validation
        raw_body = request.body
        
        # Compute expected signature
        computed_signature = hmac.new(
            secret_key.encode('utf-8'),
            raw_body,
            hashlib.sha512
        ).hexdigest()
        
        # Verify signature (in production, use constant-time comparison)
        if not hmac_compare_digest_compat(paystack_signature, computed_signature):
            logger.warning("Paystack webhook signature verification failed")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Parse the event data
        event_data = request.data
        event_type = event_data.get('event')
        
        if event_type == 'charge.success':
            # Payment successful - find and update payment
            data = event_data.get('data', {})
            reference = data.get('reference')
            
            if not reference:
                logger.warning("Paystack webhook missing reference")
                return Response({'error': 'Missing reference'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                payment = Payment.objects.get(paystack_reference=reference)
            except Payment.DoesNotExist:
                logger.warning(f"Payment not found for reference: {reference}")
                return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
            
            # Update payment status
            payment.status = 'success'
            payment.is_verified = True
            payment.response_data = data
            
            # Store card info if available
            authorization = data.get('authorization', {})
            if authorization:
                payment.card_last_four = authorization.get('last4', '')
                payment.card_brand = authorization.get('brand', '')
            
            payment.save()
            
            # Update order with paystack_reference and change status from awaiting_payment to confirmed
            order = payment.order
            if order.status == 'awaiting_payment':
                # Set the paystack_reference on the order so it can be looked up on success page
                order.paystack_reference = payment.paystack_reference
                order.status = 'confirmed'
                order.save(update_fields=['paystack_reference', 'status'])
            
            logger.info(f"Payment verified via webhook: {reference}")
            
            # Send confirmation emails (best effort - don't fail the webhook response)
            try:
                from emailing.tasks import (
                    send_order_confirmed_customer_task,
                    send_order_confirmed_admin_task,
                )
                
                send_order_confirmed_customer_task(
                    order_id=order.order_id,
                    shipping_email=order.shipping_email,
                    shipping_first_name=order.shipping_first_name,
                    shipping_last_name=order.shipping_last_name,
                    status=order.status,
                )
                
                send_order_confirmed_admin_task(
                    order_id=order.order_id,
                    shipping_email=order.shipping_email,
                    status=order.status,
                )
            except Exception as e:
                logger.error(f"Failed to send order confirmation emails: {e}")
            
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        
        elif event_type == 'charge.failed':
            # Payment failed
            data = event_data.get('data', {})
            reference = data.get('reference')
            
            if reference:
                try:
                    payment = Payment.objects.get(paystack_reference=reference)
                    payment.status = 'failed'
                    payment.error_message = data.get('gateway_response', 'Payment failed')
                    payment.save()
                    logger.info(f"Payment failed via webhook: {reference}")
                except Payment.DoesNotExist:
                    logger.warning(f"Payment not found for reference: {reference}")
            
            return Response({'status': 'processed'}, status=status.HTTP_200_OK)
        
        else:
            logger.info(f"Paystack webhook event received: {event_type}")
            return Response({'status': 'accepted'}, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.exception("Paystack webhook processing error")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def hmac_compare_digest_compat(a: str, b: str) -> bool:
    """Compatibility wrapper for hmac.compare_digest (Django 4.1+)"""
    try:
        return hmac.compare_digest(a, b)
    except AttributeError:
        # Fallback for older Django versions
        return a == b

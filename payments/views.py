from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import requests
import logging

from .models import Payment, Refund
from .serializers import PaymentSerializer, PaymentInitializeSerializer, RefundSerializer, RefundCreateSerializer

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for payments"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def initialize(self, request):
        """Initialize payment with Paystack"""
        serializer = PaymentInitializeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        payment = serializer.save(user=request.user, status='pending')

        # Call Paystack API
        paystack_key = getattr(settings, 'PAYSTACK_SECRET_KEY', '')
        if not paystack_key:
            return Response(
                {'error': 'Paystack secret key is missing on the server'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        headers = {'Authorization': f'Bearer {paystack_key}'}

        payload = {
            'email': request.user.email,
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

                return Response({
                    'payment': PaymentSerializer(payment).data,
                    'authorization_url': data['data']['authorization_url'],
                }, status=status.HTTP_200_OK)

            return Response(
                {'error': 'Failed to initialize payment', 'details': response.text},
                status=status.HTTP_400_BAD_REQUEST
            )
        except requests.exceptions.RequestException:
            return Response(
                {'error': 'Unable to reach Paystack right now. Please try again in a few seconds.'},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def verify(self, request):
        """Verify payment with Paystack"""
        reference = request.data.get('reference')
        if not reference:
            return Response({'error': 'Reference is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = Payment.objects.get(paystack_reference=reference)
        except Payment.DoesNotExist:
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

                    # Update order status
                    payment.order.status = 'confirmed'
                    payment.order.save()

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

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend

from .models import Review
from .serializers import ReviewListSerializer, ReviewDetailSerializer, ReviewCreateSerializer


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for reviews"""
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating', 'is_verified_purchase']
    ordering_fields = ['created_at', 'helpful_count', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Review.objects.filter(is_approved=True)
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ReviewDetailSerializer
        elif self.action == 'create':
            return ReviewCreateSerializer
        return ReviewListSerializer
    
    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated()]
        return [AllowAny()]
    
    def perform_create(self, serializer):
        """Create review with current user"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured reviews for homepage display - top rated reviews"""
        # Get top reviews ordered by rating (desc) and helpful_count (desc)
        reviews = Review.objects.filter(
            is_approved=True,
            rating__gte=4  # Only include 4-5 star reviews
        ).select_related('user', 'product').order_by('-rating', '-helpful_count')[:6]
        
        serializer = ReviewListSerializer(reviews, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_helpful(self, request, pk=None):
        """Mark review as helpful"""
        review = self.get_object()
        review.helpful_count += 1
        review.save()
        return Response({'message': 'Marked as helpful'})
    
    @action(detail=True, methods=['post'])
    def mark_unhelpful(self, request, pk=None):
        """Mark review as unhelpful"""
        review = self.get_object()
        review.unhelpful_count += 1
        review.save()
        return Response({'message': 'Marked as unhelpful'})

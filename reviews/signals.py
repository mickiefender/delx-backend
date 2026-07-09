from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Avg

from .models import Review


def update_product_rating(product):
    """Recalculate and update product rating + review_count from approved reviews."""
    approved_reviews = product.reviews.filter(is_approved=True)
    count = approved_reviews.count()

    if count == 0:
        product.rating = 0
        product.review_count = 0
    else:
        avg_rating = approved_reviews.aggregate(avg=Avg('rating'))['avg']
        product.rating = round(float(avg_rating), 2)
        product.review_count = count

    # Use update() to avoid triggering save signals recursively
    from products.models import Product
    Product.objects.filter(pk=product.pk).update(
        rating=product.rating,
        review_count=product.review_count,
    )


@receiver(post_save, sender=Review)
def review_post_save(sender, instance, created, **kwargs):
    """Update product rating when a review is created or updated."""
    update_product_rating(instance.product)


@receiver(post_delete, sender=Review)
def review_post_delete(sender, instance, **kwargs):
    """Update product rating when a review is deleted."""
    update_product_rating(instance.product)

"""
Management command to recalculate product ratings and review counts
from existing approved reviews.
"""
from django.core.management.base import BaseCommand
from django.db.models import Avg

from products.models import Product
from reviews.models import Review


class Command(BaseCommand):
    help = 'Recalculate rating and review_count for all products from existing reviews'

    def handle(self, *args, **options):
        products = Product.objects.all()
        updated = 0

        for product in products:
            approved_reviews = Review.objects.filter(
                product=product,
                is_approved=True,
            )
            count = approved_reviews.count()

            if count == 0:
                new_rating = 0
                new_count = 0
            else:
                avg_rating = approved_reviews.aggregate(avg=Avg('rating'))['avg']
                new_rating = round(float(avg_rating), 2)
                new_count = count

            if product.rating != new_rating or product.review_count != new_count:
                Product.objects.filter(pk=product.pk).update(
                    rating=new_rating,
                    review_count=new_count,
                )
                updated += 1
                self.stdout.write(
                    f'  Updated Product #{product.id} "{product.name}": '
                    f'rating {product.rating}→{new_rating}, '
                    f'reviews {product.review_count}→{new_count}'
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Updated {updated} of {products.count()} products.'
            )
        )

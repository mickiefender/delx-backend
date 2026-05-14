from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from decimal import Decimal

from users.models import CustomUser
from products.models import Category, ProductAttribute


class ProductCreateUpdateValidationTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

        # Create an admin user (create/update requires IsAdminUser)
        self.admin = CustomUser.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password123",
        )
        self.token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        # Create a category (required FK)
        self.category = Category.objects.create(
            name="Test Category",
            slug="test-category",
            description="desc",
            is_active=True,
            is_featured=False,
        )

        # Create a product attribute (optional, but keeps payload realistic)
        self.attribute = ProductAttribute.objects.create(
            name="Color",
            slug="color",
            values=["Red", "Blue"],
            is_active=True,
        )

    def test_post_product_with_overlong_sku_returns_400(self) -> None:
        """
        Regression test for: DataError value too long for character varying(100)
        on POST /api/v1/products/
        """
        url = reverse("product-list")  # router basename='product'

        payload = {
            "name": "Test Product",
            "category": self.category.id,
            "description": "A product description that is fine.",
            "short_description": "short",
            "price": str(Decimal("10.00")),
            "original_price": None,
            "sku": "X" * 101,  # Product.sku max_length=100 (DB varchar(100))
            "stock_quantity": 1,
            "is_featured": False,
            "collection": "none",
            "status": "active",
            "image": None,  # model requires image; DRF should validate before DB write
            "attributes": [self.attribute.id],
        }

        response = self.client.post(url, payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("sku", response.data)

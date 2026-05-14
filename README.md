# Delchris Ecommerce - Django REST API Backend

This is the Django REST Framework backend for the Delchris ecommerce platform. It provides a comprehensive REST API for managing products, users, orders, payments, and reviews.

## Architecture

```
backend/
├── config/              # Django project settings and configuration
├── users/               # User management app
├── products/            # Product catalog app
├── orders/              # Order management app
├── payments/            # Payment processing app
├── reviews/             # Product reviews app
├── analytics/           # Analytics tracking app
└── venv/               # Python virtual environment
```

## Features

### Users Management
- User registration and authentication
- Token-based authentication
- User profiles with extended information
- Multiple address management (shipping/billing)
- Wishlist functionality
- Newsletter subscriptions

### Products
- Product catalog with categories
- Advanced filtering (price, category, rating)
- Product variants and images
- Search functionality
- Featured products
- Best sellers tracking

### Orders
- Order creation and management
- Order tracking and history
- Multiple payment methods support
- Order status management (pending, confirmed, shipped, delivered, etc.)
- Order cancellation

### Payments
- Paystack integration for payment processing
- Support for:
  - Credit/Debit cards
  - Mobile Money (MTN MoMo, Telecel, AirtelTigo)
  - Bank transfers
- Payment verification
- Refund management
- Payment history tracking

### Reviews & Ratings
- Product reviews with 1-5 star ratings
- Review images
- Helpful/unhelpful voting
- Admin responses to reviews
- Verified purchase badges

### Analytics
- Sales metrics tracking
- Product performance metrics
- User activity tracking
- Category performance
- Page view tracking
- Abandoned cart tracking

## Setup Instructions

### 1. Create Virtual Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the backend directory:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Supabase PostgreSQL
SUPABASE_DB_NAME=postgres
SUPABASE_DB_USER=postgres
SUPABASE_DB_PASSWORD=your-password
SUPABASE_DB_HOST=your-supabase-host.supabase.co
SUPABASE_DB_PORT=5432

# Paystack
PAYSTACK_SECRET_KEY=your-paystack-secret-key
PAYSTACK_PUBLIC_KEY=your-paystack-public-key

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 4. Run Migrations
```bash
python manage.py migrate
```

### 5. Create Superuser
```bash
python manage.py createsuperuser
```

### 6. Start Development Server
```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/v1/`

## API Endpoints

### Authentication
- `POST /api/v1/users/register/` - Register new user
- `POST /api/v1/users/login/` - Login user
- `POST /api/v1/users/logout/` - Logout user
- `GET /api/v1/users/me/` - Get current user profile
- `PUT /api/v1/users/me/` - Update user profile

### Products
- `GET /api/v1/products/` - List all products
- `GET /api/v1/products/{slug}/` - Get product details
- `GET /api/v1/products/featured/` - Get featured products
- `GET /api/v1/products/best_sellers/` - Get best selling products
- `GET /api/v1/categories/` - List categories
- `GET /api/v1/categories/{slug}/products/` - Get products by category

### Orders
- `GET /api/v1/orders/` - List user orders
- `POST /api/v1/orders/` - Create new order
- `GET /api/v1/orders/{id}/` - Get order details
- `POST /api/v1/orders/{id}/cancel/` - Cancel order
- `GET /api/v1/orders/{id}/tracking/` - Get order tracking

### Payments
- `POST /api/v1/payments/initialize/` - Initialize payment
- `POST /api/v1/payments/verify/` - Verify payment
- `GET /api/v1/payments/` - List user payments

### Reviews
- `GET /api/v1/reviews/` - List reviews
- `POST /api/v1/reviews/` - Create review
- `GET /api/v1/reviews/{id}/` - Get review details
- `POST /api/v1/reviews/{id}/mark_helpful/` - Mark as helpful
- `POST /api/v1/reviews/{id}/mark_unhelpful/` - Mark as unhelpful

### Users
- `GET /api/v1/users/{id}/addresses/` - Get user addresses
- `POST /api/v1/users/{id}/addresses/` - Create address
- `GET /api/v1/users/{id}/wishlist/` - Get user wishlist
- `POST /api/v1/users/{id}/wishlist/add_product/` - Add to wishlist

## Database Models

### CustomUser
Extended Django User with additional fields like phone, bio, preferred currency, etc.

### UserAddress
Shipping and billing addresses for users.

### UserWishlist
User's wishlist of favorite products.

### Category
Product categories with slugs and descriptions.

### Product
Main product model with pricing, images, and stock management.

### ProductImage
Additional images for products.

### ProductVariant
Product variants like size, color, etc.

### Order
Customer orders with shipping and billing information.

### OrderItem
Individual items in an order.

### OrderTracking
Track order status changes and shipping updates.

### Payment
Payment information linked to orders.

### Refund
Refund requests and processing.

### Review
Product reviews with ratings and images.

### ReviewImage
Images attached to reviews.

### ReviewResponse
Admin/seller responses to customer reviews.

## Security

- Token-based authentication using Django REST Framework
- CORS enabled for frontend communication
- SSL/TLS for Supabase connections
- Secure password hashing with bcrypt
- Input validation and sanitization
- CSRF protection

## Performance

- Database connection pooling
- Query optimization with select_related and prefetch_related
- Pagination support (20 items per page)
- Caching headers for static content
- Indexed database fields for common queries

## Testing

Run tests:
```bash
python manage.py test
```

## Admin Panel

Access Django admin at `/admin/` with your superuser credentials.

## Deployment

See `DEPLOYMENT.md` for production deployment instructions.

## Support

For issues or questions, please contact the development team.

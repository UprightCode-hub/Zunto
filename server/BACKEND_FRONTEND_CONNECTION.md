# Backend-Frontend Connection Guide

## Overview
This document explains how the React frontend (client) is connected to the Django backend (Zunto).

## Architecture

```
Frontend (React)                Backend (Django)
├── client/                      ├── accounts/        (Authentication)
├── src/                         ├── market/          (Products)
├── services/                    ├── cart/            (Shopping Cart)
└── api.js (API client)          ├── orders/          (Orders)
                                 ├── reviews/         (Reviews)
                                 ├── notifications/   (Notifications)
                                 ├── chat/            (Chat)
                                 └── assistant/       (AI Assistant)
```

## Getting Started

### 1. Start the Backend Server

```bash
cd c:\Users\DELL USER\Desktop\Zunto

# Install dependencies (if not done)
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Run the server
python manage.py runserver
```

The backend will run at `http://localhost:8000`

### 2. Start the Frontend Server

```bash
cd c:\Users\DELL USER\Desktop\Zunto\client

# Install dependencies (if not done)
npm install

# Run the development server
npm run dev
```

The frontend will run at `http://localhost:5174` (or next available port)

## API Endpoints Reference

### Authentication (`/`)
- `POST /register/` - User registration
- `POST /login/` - User login
- `POST /logout/` - User logout
- `POST /token/refresh/` - Refresh JWT token
- `GET /profile/` - Get user profile
- `PUT /profile/` - Update user profile

### Products (`/api/market/`)
- `GET /products/` - List all products
- `POST /products/` - Create a new product
- `GET /products/{slug}/` - Get product details
- `PUT /products/{slug}/` - Update product
- `DELETE /products/{slug}/` - Delete product
- `GET /products/my-products/` - Get user's products
- `GET /products/featured/` - Get featured products
- `GET /products/boosted/` - Get boosted products
- `GET /products/{slug}/similar/` - Get similar products
- `POST /products/{slug}/mark-sold/` - Mark product as sold
- `POST /products/{slug}/reactivate/` - Reactivate product

### Categories & Locations (`/api/market/`)
- `GET /categories/` - List all categories
- `GET /locations/` - List all locations

### Product Media (`/api/market/`)
- `POST /products/{slug}/images/` - Upload product image
- `DELETE /products/{slug}/images/{image_id}/` - Delete product image
- `POST /products/{slug}/videos/` - Upload product video

### Favorites (`/api/market/`)
- `POST /products/{slug}/favorite/` - Toggle favorite
- `GET /favorites/` - Get user's favorites

### Product Reports (`/api/market/`)
- `POST /products/{slug}/report/` - Report a product

### Cart (`/api/cart/`)
- `GET /` - Get user's cart
- `POST /add/` - Add item to cart
- `PUT /update/{item_id}/` - Update cart item quantity
- `DELETE /remove/{item_id}/` - Remove item from cart
- `DELETE /clear/` - Clear entire cart

### Orders (`/api/orders/`)
- `GET /` - List user's orders
- `POST /` - Create a new order
- `GET /{order_id}/` - Get order details
- `PUT /{order_id}/` - Update order
- `POST /{order_id}/cancel/` - Cancel order

### Reviews (`/api/reviews/`)
- `GET /product/{product_id}/` - Get product reviews
- `POST /product/{product_id}/` - Create review
- `PUT /{review_id}/` - Update review
- `DELETE /{review_id}/` - Delete review

### Notifications (`/api/notifications/`)
- `GET /` - Get user's notifications
- `POST /{notification_id}/read/` - Mark notification as read
- `DELETE /{notification_id}/` - Delete notification

### Chat (`/chat/`)
- `GET /conversations/` - Get user's conversations
- `GET /conversations/{id}/messages/` - Get conversation messages
- `POST /conversations/{id}/messages/` - Send message

### Assistant (`/assistant/`)
- `POST /chat/` - Send message to AI assistant

### Payments (`/api/payments/`)
- `POST /initiate/` - Initiate payment
- `GET /verify/{payment_id}/` - Verify payment

## Authentication Flow

The frontend uses JWT (JSON Web Tokens) for authentication:

1. User logs in with email and password
2. Backend returns `access` and `refresh` tokens
3. Frontend stores tokens in localStorage
4. All subsequent API requests include the `access` token in the Authorization header
5. If token expires, use `refresh` token to get a new one

### Token Storage
```javascript
// Stored in localStorage
access_token     // Used for API requests
refresh_token    // Used to refresh access token
user            // User profile data (email, name, etc.)
```

### Authorization Header
```javascript
Authorization: Bearer {access_token}
```

## API Service Usage

The frontend uses a centralized API service at `src/services/api.js`

### Example: Fetching Products
```javascript
import { getProducts } from '../services/api';

try {
  const products = await getProducts({ featured: true, limit: 8 });
  console.log(products);
} catch (error) {
  console.error('Error fetching products:', error);
}
```

### Example: Creating a Product (Seller)
```javascript
import { createProduct } from '../services/api';

const newProduct = {
  name: 'Product Name',
  description: 'Product description',
  price: 9999,
  category: 1,
  location: 1,
};

try {
  const result = await createProduct(newProduct);
  console.log('Product created:', result);
} catch (error) {
  console.error('Error creating product:', error);
}
```

### Example: Adding to Cart
```javascript
import { addToCart } from '../services/api';

try {
  const result = await addToCart('product-slug', 1); // slug, quantity
  console.log('Item added to cart:', result);
} catch (error) {
  console.error('Error adding to cart:', error);
}
```

### Example: Authentication
```javascript
import { useAuth } from '../context/AuthContext';

function LoginComponent() {
  const { login } = useAuth();

  const handleLogin = async (email, password) => {
    const result = await login(email, password);
    if (result.success) {
      console.log('Logged in successfully');
    } else {
      console.error('Login failed:', result.error);
    }
  };

  // Component code...
}
```

## CORS Configuration

Make sure your Django backend has CORS enabled. Check `ZuntoProject/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    # ...
]

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
]
```

## Environment Variables

Configure environment variables in `.env.local`:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Zunto
VITE_APP_VERSION=1.0.0
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_CHAT=true
VITE_ENABLE_NOTIFICATIONS=true
```

## Debugging

### Check Network Requests
1. Open Developer Tools (F12)
2. Go to Network tab
3. Make a request and check:
   - Status code (should be 200 for success, 4xx for client errors, 5xx for server errors)
   - Request headers (should include Authorization header)
   - Response body (check for error messages)

### Common Issues

**Issue: 404 Not Found**
- Check the endpoint URL is correct
- Verify backend is running
- Check URL path matches backend routes

**Issue: 401 Unauthorized**
- User not logged in
- Token expired or invalid
- Token not included in request header

**Issue: CORS Error**
- Backend CORS settings not configured
- Frontend URL not in CORS_ALLOWED_ORIGINS
- Check browser console for details

**Issue: Connection Refused**
- Backend server not running
- Backend running on different port
- Check firewall settings

## Testing the Connection

### Quick Test
```javascript
// In browser console
fetch('http://localhost:8000/health/')
  .then(r => r.json())
  .then(data => console.log(data))
  .catch(err => console.error(err))
```

Expected response: `{status: 'ok'}`

## Next Steps

1. ✅ Backend running at `http://localhost:8000`
2. ✅ Frontend running at `http://localhost:5174`
3. ✅ API service configured
4. ✅ Auth context set up
5. Test features:
   - [ ] User registration
   - [ ] User login
   - [ ] Browse products
   - [ ] Add to cart
   - [ ] Create order
   - [ ] Create product (seller)

## Support

For issues or questions:
1. Check the console for error messages
2. Review network requests in DevTools
3. Check backend logs for server errors
4. Verify all services are running

---

**Last Updated:** January 23, 2026

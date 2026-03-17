# System Architecture Diagram

## Complete System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ZUNTO ECOMMERCE PLATFORM                        │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────┐   ┌──────────────────────────┐
│      FRONTEND (React + Vite)             │   │    BACKEND (Django DRF)  │
│      http://localhost:5174               │   │  http://localhost:8000   │
├──────────────────────────────────────────┤   ├──────────────────────────┤
│                                          │   │                          │
│  ┌────────────────────────────────────┐ │   │  ┌────────────────────┐  │
│  │     User Interface Layer           │ │   │  │  API Views Layer   │  │
│  │  ├─ Pages (Home, Shop, Cart...)    │ │   │  ├─ accounts/        │  │
│  │  ├─ Components (Navbar, Footer...) │ │   │  ├─ market/          │  │
│  │  └─ Modals & Forms                 │ │   │  ├─ cart/            │  │
│  └──────────────────────────────────────┘ │   │  ├─ orders/         │  │
│                ▲                          │   │  ├─ reviews/        │  │
│                │                          │   │  ├─ notifications/  │  │
│  ┌─────────────┴──────────────────────┐  │   │  └─ chat/           │  │
│  │    State Management Layer          │  │   │  └────────────────────┘  │
│  │  ├─ ThemeContext (dark/light)      │  │   │           ▲              │
│  │  ├─ AuthContext (user, tokens)     │  │   │           │              │
│  │  └─ CartContext (shopping cart)    │  │   │  ┌────────┴─────────┐    │
│  └──────────────────────────────────────┘  │   │ Serializers/Models│    │
│                ▲                          │   │  ├─ User Model     │    │
│                │                          │   │  ├─ Product Model  │    │
│  ┌─────────────┴──────────────────────┐  │   │  ├─ Order Model    │    │
│  │    API Service Layer               │  │   │  └─ etc...         │    │
│  │  ├─ getProducts()                  │  │   │  └────────────────────┘  │
│  │  ├─ login()                        │  │   │           ▲              │
│  │  ├─ addToCart()                    │  │   │           │              │
│  │  ├─ createOrder()                  │  │   │  ┌────────┴─────────┐    │
│  │  └─ ... 30+ endpoints              │  │   │ Database Layer     │    │
│  └──────────────────────────────────────┘  │   │  └─ PostgreSQL    │    │
│                ▲                          │   │     or SQLite      │    │
│                │                          │   │  └────────────────────┘  │
│  ┌─────────────┴──────────────────────┐  │   │                          │
│  │  HTTP Client (Fetch API)           │  │   │  ┌────────────────────┐  │
│  │  ├─ Handles requests               │  │   │  │ Authentication     │  │
│  │  ├─ Adds Authorization header      │  │   │  │ ├─ JWT Tokens     │  │
│  │  └─ Manages tokens (localStorage) │  │   │  │ └─ Token Refresh   │  │
│  └──────────────────────────────────────┘  │   │  └────────────────────┘  │
│                │                          │   │                          │
└────────────────┼──────────────────────────┘   └──────────────────────────┘
                 │
                 │ HTTP/REST API
                 │ JSON Payloads
                 │ JWT Authorization
                 │
    ┌────────────▼────────────┐
    │    CORS Configuration   │
    │ ├─ http://localhost:5173│
    │ ├─ http://localhost:5174│
    │ └─ http://127.0.0.1:*   │
    └────────────┬────────────┘
                 │
```

## Request-Response Flow

### 1. User Registration Flow
```
User Input (Email, Password)
    ↓
RegisterForm Component
    ↓
useAuth() hook
    ↓
register() function (api.js)
    ↓
HTTP POST /register/
    ↓
[Network → Backend]
    ↓
Backend: UserRegistrationView
    ↓
Database: Create User
    ↓
Response: { access, refresh, user }
    ↓
[Network ← Backend]
    ↓
localStorage.setItem('access_token', token)
localStorage.setItem('user', userData)
    ↓
AuthContext.setUser(user)
    ↓
Navigate to Home
```

### 2. Product Fetch Flow
```
Product List Page Load
    ↓
useEffect Hook
    ↓
getProducts() (api.js)
    ↓
HTTP GET /api/market/products/
    ↓
[Network → Backend]
    ↓
Backend: ProductListCreateView
    ↓
Database: Fetch Products
    ↓
Response: { count, results: [...products] }
    ↓
[Network ← Backend]
    ↓
setFeaturedProducts(data.results)
    ↓
Render Product Cards
    ↓
User sees products displayed
```

### 3. Add to Cart Flow
```
Click "Add to Cart" Button
    ↓
addToCart('product-slug', 1) (api.js)
    ↓
HTTP POST /api/cart/add/
{ product_id: 'slug', quantity: 1 }
    ↓
[Network → Backend + Bearer Token]
    ↓
Backend: CartView
    ↓
Database: Update/Create CartItem
    ↓
Response: { cart_id: ..., items: [...] }
    ↓
[Network ← Backend]
    ↓
CartContext.addItem(product)
    ↓
Show Toast: "Item added to cart"
    ↓
Update Cart Badge
```

### 4. Place Order Flow
```
Click "Checkout" Button
    ↓
createOrder(orderData) (api.js)
    ↓
HTTP POST /api/orders/
{ items, shipping_address, ... }
    ↓
[Network → Backend + Bearer Token]
    ↓
Backend: OrderCreateView
    ↓
Database: Create Order + OrderItems
    ↓
Response: { order_id: ..., total: ... }
    ↓
[Network ← Backend]
    ↓
Navigate to Order Confirmation
    ↓
Display Order Details
    ↓
Clear Cart
```

## Data Flow Architecture

```
                    ┌─────────────┐
                    │   Browser   │
                    │ localStorage│
                    │ ├─ tokens   │
                    │ ├─ user     │
                    │ └─ prefs    │
                    └──────┬──────┘
                           │
                ┌──────────┼──────────┐
                │                     │
         ┌──────▼──────┐      ┌──────▼──────┐
         │   Frontend  │      │   Backend   │
         │   State     │◄────►│   Database  │
         └─────┬───────┘      └─────┬──────┘
               │                    │
        ┌──────┴────────┐      ┌────┴───────┐
        │                │      │             │
    ┌───▼──┐  ┌────┐  ┌─▼──┐  ┌──▼──┐  ┌──┐
    │User  │  │Cart│  │Auth│  │User │  │DB│
    │Data  │  │    │  │    │  │Data │  │  │
    └──────┘  └────┘  └────┘  └─────┘  └──┘
```

## API Endpoint Hierarchy

```
http://localhost:8000
├── / (Root)
│   ├── POST register/          (Register user)
│   ├── POST login/             (Login user)
│   ├── POST logout/            (Logout)
│   ├── GET profile/            (Get profile)
│   ├── PUT profile/            (Update profile)
│   └── POST token/refresh/     (Refresh JWT)
│
├── /api (API Prefix)
│   ├── /market/
│   │   ├── GET products/       (List products)
│   │   ├── POST products/      (Create product)
│   │   ├── GET products/{slug}/ (Get product)
│   │   ├── PUT products/{slug}/ (Update)
│   │   ├── DELETE products/{slug}/ (Delete)
│   │   ├── GET categories/     (Categories)
│   │   ├── GET locations/      (Locations)
│   │   └── ... (more endpoints)
│   │
│   ├── /cart/
│   │   ├── GET /               (Get cart)
│   │   ├── POST add/           (Add item)
│   │   ├── PUT update/{id}/    (Update item)
│   │   ├── DELETE remove/{id}/ (Remove item)
│   │   └── DELETE clear/       (Clear cart)
│   │
│   ├── /orders/
│   │   ├── GET /               (List orders)
│   │   ├── POST /              (Create order)
│   │   ├── GET {id}/           (Get order)
│   │   ├── PUT {id}/           (Update order)
│   │   └── POST {id}/cancel/   (Cancel order)
│   │
│   ├── /reviews/
│   │   ├── GET product/{id}/   (Get reviews)
│   │   ├── POST product/{id}/  (Create review)
│   │   ├── PUT {id}/           (Update review)
│   │   └── DELETE {id}/        (Delete review)
│   │
│   ├── /notifications/         (Notifications)
│   └── /payments/              (Payments)
│
├── /chat/                      (Chat conversations)
├── /assistant/                 (AI Assistant)
└── /health/                    (Health check)
```

## Authentication & Token Flow

```
┌─────────────────────────────────────────────┐
│      JWT Authentication Flow                │
└─────────────────────────────────────────────┘

Client Side                    Server Side
────────────────────────────────────────────

User Input (email, pwd)
    │
    ├─────────────────────►  /login/
                             ├─ Verify credentials
                             └─ Generate JWT Pair
    │
    ◄─────────────────────  {
                             "access": "eyJ...",
                             "refresh": "eyJ...",
                             "user": {...}
                            }
    │
Save to localStorage
├─ access_token
├─ refresh_token
└─ user

                        Request to Protected Endpoint
    │
    ├─────────────────────►  /api/cart/ +
                             Authorization: Bearer {access_token}
                             │
                             ├─ Verify token
                             └─ Process request
    │
    ◄─────────────────────  {
                             "items": [...],
                             "total": 9999
                            }

                        Token Expired?
    │
    ├─────────────────────►  /token/refresh/ +
                             {"refresh": {refresh_token}}
                             │
                             └─ Generate new access
    │
    ◄─────────────────────  {
                             "access": "eyJ...",
                             "refresh": "eyJ..."
                            }
    │
Update localStorage
└─ access_token
```

## Component Connection Map

```
App.jsx (Root)
│
├─ ThemeProvider (Dark/Light Mode)
│  └─ AuthProvider (Authentication)
│     └─ Router (React Router)
│        │
│        ├─ Home.jsx (Uses: getProducts, getCategories)
│        ├─ Shop.jsx (Uses: getProducts, filters)
│        ├─ ProductDetail.jsx (Uses: getProductDetail, addToCart)
│        ├─ Cart.jsx (Uses: getCart, updateCart, removeFromCart)
│        ├─ Checkout.jsx (Uses: createOrder)
│        ├─ Login.jsx (Uses: login from useAuth)
│        ├─ Register.jsx (Uses: register from useAuth)
│        ├─ Profile.jsx (Uses: getUserProfile, updateProfile)
│        ├─ AdminDashboard.jsx (Uses: admin endpoints)
│        ├─ SellerDashboard.jsx (Uses: createProduct, getMyProducts)
│        └─ ... other pages
│
└─ Navbar (Uses: useAuth, useCart, useTheme)
   └─ ThemeToggle (Uses: useTheme)
```

## File Structure & Connections

```
Frontend (client/)
├── src/
│   ├── App.jsx              (Main app, providers)
│   │
│   ├── services/
│   │   └── api.js           (30+ API functions)
│   │                         └─ Fetches from localhost:8000
│   │
│   ├── context/
│   │   ├── AuthContext.jsx  (User auth, tokens, login/logout)
│   │   ├── ThemeContext.jsx (Dark/light mode toggle)
│   │   └── CartContext.jsx  (Shopping cart state)
│   │
│   ├── components/
│   │   ├── common/
│   │   │   ├── Navbar.jsx   (Uses: useAuth, useCart)
│   │   │   ├── Footer.jsx
│   │   │   └── ThemeToggle.jsx (Uses: useTheme)
│   │   │
│   │   └── ... other components
│   │
│   └── pages/
│       ├── Home.jsx         (Uses: getProducts)
│       ├── Shop.jsx         (Uses: getProducts, filters)
│       ├── Cart.jsx         (Uses: cart endpoints)
│       ├── AdminDashboard.jsx
│       ├── SellerDashboard.jsx
│       └── ... other pages
│
└── .env.local               (Config: VITE_API_BASE_URL)


Backend (Zunto/)
├── ZuntoProject/
│   ├── settings.py          (CORS, Database, Auth config)
│   └── urls.py              (Route configuration)
│
├── accounts/                (/register, /login, /profile)
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
│
├── market/                  (/api/market/products, etc.)
│   ├── views.py
│   ├── serializers.py
│   └── urls.py
│
├── cart/                    (/api/cart/)
│   ├── views.py
│   └── urls.py
│
├── orders/                  (/api/orders/)
│   ├── views.py
│   └── urls.py
│
├── reviews/                 (/api/reviews/)
│   ├── views.py
│   └── urls.py
│
├── notifications/           (/api/notifications/)
│   ├── views.py
│   └── urls.py
│
├── chat/                    (/chat/)
│   ├── views.py
│   ├── consumers.py         (WebSocket)
│   └── urls.py
│
└── manage.py                (Django CLI)
```

---

**This architecture ensures:**
✅ Clean separation of concerns
✅ Easy to test and maintain
✅ Scalable and extensible
✅ Secure JWT authentication
✅ Real-time capabilities
✅ Admin management features

*Last Updated: January 23, 2026*

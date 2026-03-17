# 🚀 Quick Reference Card

## 📦 Installation & Setup

```bash
# Backend Setup
cd c:\Users\DELL USER\Desktop\Zunto
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

# Frontend Setup
cd client
npm install
npm run dev
```

## 🔌 Connections

| Component | URL | Status |
|-----------|-----|--------|
| Backend | http://localhost:8000 | ✅ Ready |
| Frontend | http://localhost:5173 | ✅ Ready |
| Admin Panel | http://localhost:8000/admin | ✅ Ready |
| API Base | http://localhost:8000 | ✅ Connected |

## 📡 Common API Calls

```javascript
// Import API functions
import { 
  getProducts, 
  getCategories, 
  login, 
  register,
  addToCart,
  createOrder 
} from '../services/api';

// Get Products
const products = await getProducts({ featured: true });

// Get Categories
const categories = await getCategories();

// Register User
const user = await register({
  email: 'user@example.com',
  password: 'SecurePass123!',
  password2: 'SecurePass123!',
  first_name: 'John',
  last_name: 'Doe'
});

// Login
const auth = await login('user@example.com', 'SecurePass123!');

// Add to Cart
const cart = await addToCart('product-slug', 1);

// Create Order
const order = await createOrder({
  items: [{ product: 1, quantity: 2 }],
  shipping_address: '123 Main St'
});
```

## 🔐 Authentication

```javascript
import { useAuth } from '../context/AuthContext';

function MyComponent() {
  const { user, login, logout, isAuthenticated } = useAuth();

  const handleLogin = async () => {
    const result = await login('email@example.com', 'password');
    if (result.success) {
      console.log('Logged in!');
    }
  };

  return (
    <div>
      {isAuthenticated ? (
        <p>Welcome, {user.email}!</p>
      ) : (
        <button onClick={handleLogin}>Login</button>
      )}
    </div>
  );
}
```

## 🧪 Test Connection

```javascript
// In browser console
fetch('http://localhost:8000/health/')
  .then(r => r.json())
  .then(data => console.log('✅', data))
  .catch(err => console.error('❌', err))
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `src/services/api.js` | All API endpoints |
| `src/context/AuthContext.jsx` | User authentication |
| `src/context/ThemeContext.jsx` | Dark/light mode |
| `.env.local` | Configuration |
| `BACKEND_FRONTEND_CONNECTION.md` | Full integration guide |
| `TESTING_CONNECTION.md` | Testing procedures |

## 🔗 Endpoint Reference

### Auth
- `POST /register/` - Register
- `POST /login/` - Login
- `POST /logout/` - Logout
- `GET /profile/` - Get profile
- `PUT /profile/` - Update profile

### Products
- `GET /api/market/products/` - List
- `POST /api/market/products/` - Create
- `GET /api/market/products/{slug}/` - Detail
- `PUT /api/market/products/{slug}/` - Update
- `DELETE /api/market/products/{slug}/` - Delete
- `GET /api/market/categories/` - Categories

### Cart & Orders
- `GET /api/cart/` - Get cart
- `POST /api/cart/add/` - Add item
- `DELETE /api/cart/remove/{id}/` - Remove item
- `POST /api/orders/` - Create order
- `GET /api/orders/` - List orders

### Other
- `GET /api/reviews/product/{id}/` - Reviews
- `POST /api/notifications/` - Notifications
- `GET /chat/conversations/` - Chat
- `POST /assistant/chat/` - AI Chat

## ⚡ Troubleshooting

| Issue | Solution |
|-------|----------|
| CORS Error | Restart backend |
| 404 Not Found | Check endpoint URL |
| 401 Unauthorized | Login required |
| Connection Refused | Start backend |
| Token Expired | Auto-refresh or login again |

## 🎯 Next Features to Test

- [ ] User registration
- [ ] User login
- [ ] Browse products
- [ ] Add to cart
- [ ] Create order
- [ ] Write review
- [ ] Create product (seller)
- [ ] Upload images
- [ ] Chat feature
- [ ] Admin dashboard

## 📞 Quick Links

- Documentation: See `BACKEND_FRONTEND_CONNECTION.md`
- Testing Guide: See `TESTING_CONNECTION.md`
- Setup: Run `setup.ps1` (Windows) or `setup.sh` (Mac/Linux)

---

**Ready to go! 🚀**

# Testing Backend-Frontend Connection

This guide helps you verify that your backend and frontend are properly connected.

## ✅ Pre-Connection Checklist

- [ ] Django backend installed with all dependencies
- [ ] React frontend installed with all dependencies
- [ ] Backend migrations applied
- [ ] CORS properly configured in Django settings
- [ ] `.env.local` file exists in client directory

## 🚀 Starting Services

### Terminal 1: Start Backend
```bash
cd c:\Users\DELL USER\Desktop\Zunto
python manage.py runserver
```

Expected output:
```
Starting development server at http://127.0.0.1:8000/
Quit the server with CTRL-BREAK.
```

### Terminal 2: Start Frontend
```bash
cd c:\Users\DELL USER\Desktop\Zunto\client
npm run dev
```

Expected output:
```
  VITE v6.4.1  ready in XXX ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

## 🧪 Test 1: Health Check

### Via Browser
Open: `http://localhost:8000/health/`

Expected response:
```json
{"status": "ok"}
```

### Via JavaScript Console
```javascript
fetch('http://localhost:8000/health/')
  .then(r => r.json())
  .then(data => console.log('✅ Backend is running:', data))
  .catch(err => console.error('❌ Backend error:', err))
```

## 🧪 Test 2: Fetch Products

### Via JavaScript Console
```javascript
// Test fetching products
fetch('http://localhost:8000/api/market/products/')
  .then(r => r.json())
  .then(data => {
    if (data.results) {
      console.log('✅ API working! Products:', data.results.length);
    } else {
      console.log('✅ API working! Response:', data);
    }
  })
  .catch(err => console.error('❌ API Error:', err))
```

## 🧪 Test 3: Fetch Categories

### Via JavaScript Console
```javascript
// Test fetching categories
fetch('http://localhost:8000/api/market/categories/')
  .then(r => r.json())
  .then(data => {
    console.log('✅ Categories loaded:', data);
  })
  .catch(err => console.error('❌ Category error:', err))
```

## 🧪 Test 4: User Registration

### Via JavaScript Console
```javascript
// Test user registration
const registerData = {
  email: 'testuser@example.com',
  password: 'TestPassword123!',
  password2: 'TestPassword123!',
  first_name: 'Test',
  last_name: 'User'
};

fetch('http://localhost:8000/register/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(registerData)
})
  .then(r => r.json())
  .then(data => {
    if (data.access) {
      console.log('✅ Registration successful!');
      console.log('Access token:', data.access);
    } else {
      console.log('Registration response:', data);
    }
  })
  .catch(err => console.error('❌ Registration error:', err))
```

## 🧪 Test 5: User Login

### Via JavaScript Console
```javascript
// Test user login
const loginData = {
  email: 'testuser@example.com',
  password: 'TestPassword123!'
};

fetch('http://localhost:8000/login/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify(loginData)
})
  .then(r => r.json())
  .then(data => {
    if (data.access) {
      console.log('✅ Login successful!');
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      console.log('Tokens saved to localStorage');
    } else {
      console.log('Login response:', data);
    }
  })
  .catch(err => console.error('❌ Login error:', err))
```

## 🧪 Test 6: Protected Route (Get Profile)

### Via JavaScript Console
```javascript
// Test getting user profile (requires token)
const token = localStorage.getItem('access_token');

if (!token) {
  console.log('❌ No token found. Please login first.');
} else {
  fetch('http://localhost:8000/profile/', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  })
    .then(r => r.json())
    .then(data => {
      console.log('✅ Profile data:', data);
    })
    .catch(err => console.error('❌ Profile error:', err))
}
```

## 🧪 Test 7: Frontend API Service

### Test via React Component
```jsx
import { useEffect } from 'react';
import { getProducts, getCategories } from '../services/api';

function TestComponent() {
  useEffect(() => {
    const test = async () => {
      try {
        const products = await getProducts();
        console.log('✅ Products:', products);
        
        const categories = await getCategories();
        console.log('✅ Categories:', categories);
      } catch (error) {
        console.error('❌ Error:', error);
      }
    };
    
    test();
  }, []);

  return <div>Check console for results</div>;
}

export default TestComponent;
```

## 🐛 Troubleshooting

### ❌ "Failed to fetch" or "Network error"
**Cause:** Backend not running or wrong URL
```bash
# Check backend is running
python manage.py runserver
# Should see "Starting development server at http://127.0.0.1:8000/"
```

### ❌ CORS Error
**Cause:** Frontend URL not in CORS_ALLOWED_ORIGINS
```
Access to fetch at 'http://localhost:8000/...' from origin 'http://localhost:5173' 
has been blocked by CORS policy
```

**Solution:** Update CORS settings in `ZuntoProject/settings.py`
```python
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
]
```

### ❌ 404 Not Found
**Cause:** Wrong endpoint URL
- Check URL is correct in api.js
- Verify endpoint exists in backend urls.py
- Check HTTP method (GET, POST, etc.)

Example:
```
❌ Wrong: http://localhost:8000/api/products/
✅ Right: http://localhost:8000/api/market/products/
```

### ❌ 401 Unauthorized
**Cause:** Missing or invalid token
```javascript
// Make sure token is set in Authorization header
fetch('http://localhost:8000/profile/', {
  headers: {
    'Authorization': `Bearer ${token}` // ✅ Required for protected routes
  }
})
```

### ❌ 500 Internal Server Error
**Cause:** Backend error
- Check backend terminal for error messages
- Check database is accessible
- Check migrations are applied: `python manage.py migrate`

## ✅ Verification Checklist

- [ ] Health check returns `{"status": "ok"}`
- [ ] Can fetch products from `/api/market/products/`
- [ ] Can fetch categories from `/api/market/categories/`
- [ ] Can register a new user
- [ ] Can login with credentials
- [ ] Can fetch user profile with token
- [ ] Frontend React components load successfully
- [ ] No CORS errors in browser console
- [ ] Network requests show correct URLs and methods

## 📊 Expected Response Formats

### Products Endpoint
```json
{
  "count": 10,
  "next": "...",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Product Name",
      "slug": "product-name",
      "price": 9999,
      "description": "...",
      "image": "...",
      "category": "...",
      "created_at": "2024-01-23T...",
      "updated_at": "2024-01-23T..."
    }
  ]
}
```

### Login Response
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe"
  }
}
```

### Profile Response
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890",
  "avatar": "...",
  "created_at": "2024-01-23T...",
  "updated_at": "2024-01-23T..."
}
```

## 🎯 Next Steps

Once all tests pass:

1. ✅ Test user registration and login flow
2. ✅ Test adding products to cart
3. ✅ Test creating orders
4. ✅ Test seller features (creating products)
5. ✅ Test admin features

## 📞 Getting Help

If tests fail:

1. **Check Console Errors**
   - Open DevTools (F12)
   - Check Console tab for error messages
   - Check Network tab for request details

2. **Check Backend Logs**
   - Look at terminal where `python manage.py runserver` is running
   - Check for error traceback
   - Check database connection

3. **Verify Configurations**
   - CORS settings in `ZuntoProject/settings.py`
   - API base URL in `.env.local`
   - Database migrations applied

4. **Common Fixes**
   - Restart both backend and frontend
   - Clear browser cache (Ctrl+Shift+Delete)
   - Clear localStorage: `localStorage.clear()`
   - Reinstall dependencies: `npm install` / `pip install -r requirements.txt`

---

**Last Updated:** January 23, 2026

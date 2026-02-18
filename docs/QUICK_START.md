# ⚡ Quick Reference - Zunto Platform

## 🚀 Start the Platform (2 Terminals)

### Terminal 1: Backend
```powershell
cd c:\Users\DELL USER\Desktop\Zunto\server
python manage.py runserver 0.0.0.0:8000
```

### Terminal 2: Frontend
```powershell
cd c:\Users\DELL USER\Desktop\Zunto\client
npm run dev
```

## 🌐 Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend App** | http://localhost:5173 | Main user interface |
| **Backend API** | http://localhost:8000 | REST API server |
| **Admin Panel** | http://localhost:8000/admin | Django admin (needs superuser) |
| **Health Check** | http://localhost:8000/health/ | Backend status |

## 📄 Main Pages

| Path | Feature |
|------|---------|
| `/` | Home page |
| `/shop` | Browse products |
| `/product/:slug` | Product details |
| `/cart` | Shopping cart |
| `/checkout` | Order checkout |
| `/orders` | View orders |
| `/reviews` | Manage reviews |
| `/chat` | Messaging |
| `/notifications` | Notifications |
| `/profile` | User profile |
| `/login` | Login page |
| `/signup` | Register page |

## 🔧 API Base Endpoints

```
Base URL: http://localhost:8000

/accounts/                   # Authentication
/api/market/                 # Products & categories
/api/cart/                   # Shopping cart
/api/orders/                 # Orders
/api/reviews/                # Reviews & ratings
/chat/                       # Messaging
/api/notifications/          # Notifications
/api/payments/               # Payment processing
```

## 📊 File Locations

```
c:\Users\DELL USER\Desktop\Zunto\
├── client/                          # React Frontend
│   ├── src/pages/                  # Page components
│   │   ├── Orders.jsx              # NEW
│   │   ├── Reviews.jsx             # NEW
│   │   ├── Chat.jsx                # NEW
│   │   └── Notifications.jsx       # NEW
│   ├── src/services/api.js         # API functions (UPDATED)
│   ├── .env                        # Environment config
│   └── package.json
│
└── server/                          # Django Backend
    ├── ZuntoProject/
    │   ├── settings.py             # UPDATED (cache fix)
    │   └── urls.py                 # UPDATED (assistant disabled)
    ├── accounts/                   # User auth
    ├── market/                     # Products
    ├── cart/                       # Shopping cart
    ├── orders/                     # Orders & payments
    ├── reviews/                    # Reviews system
    ├── chat/                       # Messaging (FIXED)
    ├── notifications/              # Notifications
    ├── manage.py                   # Django CLI
    └── requirements.txt
```

## 🔑 Key Configuration

### Frontend (.env)
```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Zunto
```

### Backend (Development)
```
DEBUG=True
SECRET_KEY=dev-secret-key
DATABASE=SQLite (db.sqlite3)
CACHE=LocalMemCache
ALLOWED_HOSTS=*
CORS_ORIGINS=All
```

## ✅ Features Implemented

- ✅ User Authentication (JWT)
- ✅ Product Management (CRUD)
- ✅ Shopping Cart
- ✅ Order Processing
- ✅ Review System
- ✅ Chat/Messaging
- ✅ Notifications
- ✅ Payment Integration (Paystack)
- ✅ Admin Dashboard
- ✅ Seller Dashboard
- ✅ Dark Mode Support

## 🚨 Troubleshooting

### Port Already in Use
```powershell
# Find process on port 8000
netstat -ano | findstr :8000

# Kill it
taskkill /PID <PID> /F
```

### Frontend Won't Connect to Backend
```
1. Verify backend is running at http://localhost:8000/health/
2. Check .env has VITE_API_BASE_URL=http://localhost:8000
3. Clear browser cache
4. Check browser console for CORS errors
```

### Missing Python Packages
```bash
pip install -r requirements.txt
```

### Missing Node Packages
```bash
npm install
```

## 📚 Useful Commands

```bash
# Backend
python manage.py migrate              # Apply database migrations
python manage.py createsuperuser      # Create admin user
python manage.py shell               # Django shell

# Frontend
npm run dev                           # Start dev server
npm run build                         # Production build
npm install [package]                # Add dependency
```

## 🎯 Common Tasks

### Create Admin User
```bash
cd server
python manage.py createsuperuser
# Follow prompts
# Access at http://localhost:8000/admin
```

### Add a Product
1. Go to http://localhost:8000/admin
2. Login with superuser
3. Click "Products" → "Add product"
4. Fill form and save
5. Check http://localhost:5173/shop to see it

### Test API Endpoint
```bash
# Using curl
curl http://localhost:8000/api/market/categories/

# Or from browser console
fetch('http://localhost:8000/api/market/categories/')
  .then(r => r.json())
  .then(d => console.log(d))
```

## 🔐 Security Reminder

⚠️ **Development Only!**
- Don't use in production as-is
- Change SECRET_KEY
- Disable DEBUG mode
- Use environment variables
- Enable HTTPS/SSL
- Use PostgreSQL
- Set proper CORS origins

## 📞 Need Help?

1. **Check terminal output** - Often shows helpful error messages
2. **Browser DevTools** - F12 → Console/Network tabs
3. **Backend logs** - Django terminal window
4. **API documentation** - Code comments in api.js

---

**Status**: ✅ Both servers running and connected!

Happy coding! 🚀

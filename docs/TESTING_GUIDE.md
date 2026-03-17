# Backend-Frontend Integration Testing Guide

## Quick Start

### 1. Start Both Servers
```bash
# Terminal 1 - Backend (Django)
cd c:\Users\DELL USER\Desktop\Zunto\server
source venv/Scripts/activate  # Windows
python manage.py runserver 8000

# Terminal 2 - Frontend (React)
cd c:\Users\DELL USER\Desktop\Zunto\client
npm run dev
```

### 2. Access Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000/api/
- **Django Admin**: http://localhost:8000/admin/

---

## Testing Checklist

### Authentication Flow
```
1. Open http://localhost:5173
2. Click "Sign Up" in navbar
3. Fill form: email, password, first/last name, select role (buyer or seller)
4. Submit → Should see success message
5. Login with same credentials
6. Should see JWT tokens in localStorage
7. Navbar should show logged-in state
```

### Product Browsing
```
1. Navigate to Shop (or homepage)
2. Should see product grid
3. Try filters: category, price range, search
4. Click product card → should show product details
5. Click "Add to Cart" → should add item
6. Click heart icon → should favorite product
7. Scroll to reviews section → should load reviews
8. Try to leave a review if logged in
```

### Shopping Cart
```
1. Add multiple products
2. Click Cart icon
3. Update quantities ±
4. Remove items
5. Check totals calculation
6. Click "Proceed to Checkout"
7. Fill shipping & payment info
8. Click "Place Order"
9. Should redirect to orders page
```

### Orders
```
1. Navigate to Orders page
2. Should see list of orders
3. Click to expand order details
4. Verify items, total, shipping address
5. Try to cancel pending order
6. Check order status filters work
7. Try sorting by date/price
```

### Reviews
```
1. Go to Reviews page
2. Select a product
3. See reviews listed
4. Filter by rating (1-5 stars)
5. Leave a new review (if your own product as seller)
6. Edit/delete your reviews
```

### Chat
```
1. Go to Messages
2. See list of conversations
3. Select a conversation
4. Type and send message
5. Should see message appear
6. Messages should refresh every 3 seconds
7. Search conversations by name
```

### Notifications
```
1. Go to Notifications
2. See notifications list
3. Filter by unread/read
4. Mark individual as read
5. Delete notifications
6. Should auto-poll every 5 seconds
7. Show unread count badge
```

### Dashboard
```
1. Go to Dashboard
2. See appropriate stats for user role:
   - Buyer: Orders, spending, completed count
   - Seller: Revenue, product count, ratings
3. View breakdown charts
4. Data should match orders/sales
```

---

## Verify API Endpoints

### Test in Browser (GET requests)
```
http://localhost:8000/api/market/products/
http://localhost:8000/api/market/categories/
http://localhost:8000/accounts/profile/
```

### Test with Postman/Thunder Client

**Headers needed**:
```
Authorization: Bearer {token_from_localStorage}
Content-Type: application/json
```

**Sample Requests**:

1. **Get Products**
```
GET http://localhost:8000/api/market/products/
```

2. **Create Order**
```
POST http://localhost:8000/api/orders/
Body: {
  "shipping_address": "123 Main St",
  "shipping_city": "Lagos",
  "shipping_state": "Lagos",
  "shipping_phone": "+234123456789",
  "notes": "Optional notes"
}
```

3. **Send Chat Message**
```
POST http://localhost:8000/chat/messages/
Body: {
  "content": "Hello!",
  "session_id": 1
}
```

---

## Troubleshooting

### "Module not found" errors
```bash
# Install dependencies
cd client
npm install
```

### CORS errors
✅ Backend CORS is configured for localhost:5173
- Check `ALLOWED_HOSTS` in `ZuntoProject/settings.py`
- Verify port 8000 is accessible

### "Cannot GET /api/..." 404
- Verify backend is running on port 8000
- Check URL patterns in `server/ZuntoProject/urls.py`
- Ensure API prefix is correct

### JWT token errors
```javascript
// Check token in browser console:
localStorage.getItem('token')
localStorage.getItem('refresh_token')
```

### Network requests failing
1. Open DevTools (F12)
2. Go to Network tab
3. Check request/response details
4. Look for 401 (auth), 404 (not found), 500 (server error)

---

## Common Tasks

### Add Test Product
```bash
curl -X POST http://localhost:8000/api/market/products/ \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Product",
    "description": "Test Description",
    "price": 99.99,
    "stock": 10,
    "category": 1
  }'
```

### Check Available Endpoints
```bash
# Backend will show all endpoints
curl http://localhost:8000/api/
```

### Clear Browser Cache
```
Ctrl+Shift+Delete (Windows)
or
Settings → Privacy → Clear Browsing Data
```

### Reset Database
```bash
cd server
python manage.py flush  # Warning: Deletes all data!
python manage.py migrate
```

---

## Frontend Files Modified

### Pages
- ✅ ProductDetail.jsx - Reviews & favorites
- ✅ Reviews.jsx - Browse & manage reviews
- ✅ Orders.jsx - Order management
- ✅ Chat.jsx - Messaging
- ✅ Notifications.jsx - Notification center
- ✅ Dashboard.jsx - Analytics
- ✅ Cart.jsx - Shopping cart
- ✅ Checkout.jsx - Order creation
- ✅ Profile.jsx - User profile

### Services
- ✅ api.js - All API calls (500+ lines)

### Context
- ✅ AuthContext.jsx - Auth state
- ✅ CartContext.jsx - Cart state

### Components
- ✅ ProtectedRoute.jsx - Route protection
- ✅ Navbar.jsx - Navigation with roles

---

## Expected Working Features

### Immediately After Login
- [ ] See dashboard with your stats
- [ ] Navigate to Shop and see products
- [ ] Add products to cart
- [ ] View cart and checkout
- [ ] Create orders
- [ ] See orders in Orders page
- [ ] View notifications
- [ ] Send/receive messages

### For Sellers
- Additional:
- [ ] Seller Dashboard with sales stats
- [ ] See Admin/Seller links in navbar
- [ ] Create/manage products
- [ ] See reviews on products
- [ ] View seller-specific orders
- [ ] Track revenue

### For Admins
- Additional:
- [ ] Admin links in navbar
- [ ] Admin Dashboard (placeholder)
- [ ] Access admin panel

---

## Performance Notes

### Polling Intervals
- **Chat**: 3 seconds
- **Notifications**: 5 seconds

### Pagination
- Products: 20 per page
- Orders: 10 per page
- Notifications: 15 per page

### Image Handling
- Using inline SVG placeholders
- Image URLs from backend
- Fallback to placeholder.png

---

## Database Checks

### View Data
```bash
cd server
python manage.py dbshell
sqlite> SELECT * FROM accounts_user;
sqlite> SELECT * FROM market_product;
sqlite> SELECT * FROM orders_order;
```

### Unapplied Migrations
```bash
# Check status
python manage.py migrate --plan

# Apply if needed (usually not required for development)
python manage.py migrate
```

---

## Browser DevTools Tips

### Check Network Requests
1. Open DevTools (F12)
2. Go to Network tab
3. Perform an action
4. Watch requests in real-time
5. Click request to see details

### Check Console
1. Open DevTools (F12)
2. Go to Console tab
3. Look for errors (red) or warnings (yellow)
4. Errors will show line numbers

### Check Storage
1. Open DevTools (F12)
2. Go to Application tab
3. Check LocalStorage
4. Should see 'token' and 'refresh_token'

---

## Support Resources

### Backend Documentation
- Django: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Daphne: https://github.com/django/daphne

### Frontend Documentation
- React: https://react.dev/
- Vite: https://vitejs.dev/
- TailwindCSS: https://tailwindcss.com/
- React Router: https://reactrouter.com/

---

## Success Indicators

✅ **Backend working if**:
- No errors in Django console
- API responds to requests
- Status codes are 200, 201, etc.
- Data comes back as JSON

✅ **Frontend working if**:
- No red errors in console
- Pages load and render
- Buttons trigger API calls
- Data displays properly

✅ **Integration working if**:
- Both above ✅
- Frontend calls match backend responses
- Data flows both directions
- No authentication errors

---

## Next Steps

1. **Test thoroughly** using checklist above
2. **Deploy to production** when ready
3. **Add payment processing** (Paystack)
4. **Implement WebSockets** for real-time updates
5. **Add more features** (recommendations, analytics, etc.)

---

**Everything is ready! Start testing and enjoy!** 🚀

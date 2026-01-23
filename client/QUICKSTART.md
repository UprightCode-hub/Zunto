# Quick Setup & Usage Guide

## 🚀 Quick Start

```bash
cd client
npm install
npm run dev
```

The app will be available at `http://localhost:5173`

## 📍 Important Routes to Visit

### 🏠 Homepage
```
http://localhost:5173/
```
- Modern hero section
- Feature highlights
- Product showcase
- Newsletter signup

### 👨‍💼 Admin Dashboard
```
http://localhost:5173/admin
```
**Features:**
- Overview tab with key metrics
- User management (list, view, edit, delete)
- Product management with sales data
- Order tracking (coming soon)
- Real-time statistics

### 🏪 Seller Dashboard
```
http://localhost:5173/seller
```
**Features:**
- Product management table
- Add new products with modal form
- Sales analytics
- Top products chart
- Inventory tracking
- Store settings

### 🌙 Dark Mode Toggle
Look in the navbar for the sun/moon icon to switch between light and dark mode.

## 🎨 What's New

### 1. **Dark/Light Mode**
- Click the sun/moon icon in the top navbar
- Your preference is automatically saved
- All pages support dark mode with smooth transitions

### 2. **Enhanced Navbar**
- Clean, professional design
- Dark mode toggle button
- Search functionality
- User profile dropdown menu
- Links to admin and seller dashboards
- Mobile-responsive menu

### 3. **Beautiful Home Page**
- Eye-catching hero section
- Feature highlights with icons
- Category browsing
- Featured products grid
- Newsletter subscription form
- Responsive design

### 4. **Admin Control Panel**
- View all users and products
- Manage user roles and access
- Monitor sales and inventory
- Track platform statistics
- Professional data tables

### 5. **Seller Portal**
- Manage your products easily
- Create new products with a form modal
- Track sales and ratings
- View analytics and trends
- Edit or delete products
- Customize store settings

### 6. **Improved Footer**
- Multiple information sections
- Contact details
- Social media links
- Quick navigation links
- Dark mode support

## 🎯 Features Checklist

✅ Light/Dark Mode Toggle
✅ Admin Dashboard with User Management
✅ Admin Dashboard with Product Management
✅ Seller Dashboard with Product Creation
✅ Seller Sales Analytics
✅ Beautified UI with Modern Design
✅ Responsive Mobile Design
✅ Smooth Transitions & Animations
✅ Professional Color Scheme
✅ Dark Mode Support Throughout

## 💡 Tips & Tricks

### Adding Products as a Seller
1. Go to `/seller`
2. Click "Add Product" button
3. Fill in the form:
   - Product name
   - Category (Electronics, Fashion, Home, Sports)
   - Price
   - Stock quantity
   - Description
4. Click "Add Product"
5. Your product appears in the table immediately

### Managing Admin Users
1. Go to `/admin`
2. Click "Users" tab
3. View all users with their roles
4. Click action buttons (eye, edit, trash) for each user

### Viewing Product Sales
1. Go to `/seller`
2. Check the "Products" tab for:
   - Sales count for each product
   - Star ratings
   - Stock levels
   - Product prices
3. Click on "Analytics" tab to see:
   - Sales trend chart
   - Top performing products

### Toggling Dark Mode
- Click the sun/moon icon in the navbar (top right on desktop, with menu on mobile)
- Your choice is saved automatically
- All pages update instantly with smooth transitions

## 🎨 Design Highlights

- **Gradient Buttons**: Blue to purple gradient on CTAs
- **Shadow Effects**: Cards have subtle shadows that increase on hover
- **Smooth Animations**: All interactions have smooth transitions
- **Color Palette**:
  - Primary: Blue (#0366d6 - Light, #2c77d1 - Dark)
  - Secondary: Purple (#9426f4)
  - Backgrounds: White/gray (Light), Gray-900/Black (Dark)

## 🔌 Browser DevTools Tips

### Test Dark Mode
Open DevTools Console and run:
```javascript
localStorage.setItem('theme', JSON.stringify(true));  // Dark
localStorage.setItem('theme', JSON.stringify(false)); // Light
```

### Check Theme State
```javascript
console.log(localStorage.getItem('theme'));
console.log(document.documentElement.classList); // Should contain 'dark'
```

## 📱 Mobile Testing

The app is fully responsive:
- **Mobile**: All features work on small screens
- **Tablet**: Optimized layout
- **Desktop**: Full-featured experience

Use browser DevTools (F12) → Device Toggle (Ctrl+Shift+M) to test responsive design.

## 🚨 Common Issues & Solutions

**Problem**: Dark mode not working
- **Solution**: Verify dark: classes are in Tailwind config
- Check that ThemeProvider wraps App component
- Clear browser cache

**Problem**: Pages not showing theme toggle
- **Solution**: Make sure ThemeToggle is imported in Navbar
- Check console for import errors

**Problem**: Admin/Seller pages show blank
- **Solution**: Verify routes are added to App.jsx
- Check browser console for errors

## 📊 Future Enhancements

Ideas for further improvement:
- Real backend integration for products
- User authentication system
- Payment processing
- Email notifications
- Advanced analytics
- Product reviews and ratings
- Wishlist functionality
- Inventory management
- Order tracking
- Customer support chat

## 🎓 Learning Resources

- [Tailwind CSS Dark Mode](https://tailwindcss.com/docs/dark-mode)
- [React Context API](https://react.dev/reference/react/useContext)
- [React Router](https://reactrouter.com/)
- [Lucide React Icons](https://lucide.dev/icons/)

---

**Need help?** Check the FEATURES.md file for detailed documentation!

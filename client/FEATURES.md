# ZUNTO - Premium Ecommerce Platform

A modern, fully-featured ecommerce platform built with React, Vite, and Tailwind CSS with support for light/dark mode, admin dashboard, and seller management.

## ✨ Features

### 🌙 Dark/Light Mode
- **Theme Toggle Button**: Available in the navbar for easy switching between light and dark modes
- **Persistent Storage**: Your theme preference is saved to localStorage and persists across sessions
- **Full App Support**: All pages and components support dark mode with smooth transitions
- **Global Theme Provider**: Using React Context for centralized theme management

### 👨‍💼 Admin Dashboard
- **User Management**: View, edit, and manage all platform users
- **Product Management**: Monitor all products on the platform with sales data
- **Analytics**: Overview of platform statistics and performance metrics
- **Order Management**: Track and manage all orders (coming soon)
- **Key Metrics**: Display total users, products, orders, and revenue

### 🏪 Seller Dashboard
- **Product Management**: Create, edit, and delete products
- **Sales Analytics**: View sales trends and top-performing products
- **Inventory Tracking**: Monitor stock levels for each product
- **Store Settings**: Customize seller profile and store information
- **Product Creation Form**: Modal form to quickly add new products with details like:
  - Product name
  - Category selection
  - Price
  - Stock quantity
  - Description

### 🛍️ Beautiful UI Components
- **Enhanced Navbar**: 
  - Integrated dark mode toggle
  - Search functionality
  - User profile menu (desktop)
  - Mobile-responsive menu
  - Links to admin and seller dashboards
  
- **Modern Home Page**:
  - Hero section with CTA buttons
  - Feature highlights (free shipping, secure payment, 24/7 support, fast delivery)
  - Category browsing
  - Featured products showcase
  - Newsletter subscription

- **Improved Footer**:
  - Multiple sections (Shop, Support, Company, Contact)
  - Social media links
  - Contact information
  - Links to seller portal and admin area

### 🎨 Design Highlights
- **Gradient Accents**: Beautiful blue-to-purple gradients throughout the app
- **Smooth Transitions**: All interactive elements have smooth hover and transition effects
- **Responsive Design**: Mobile-first approach with full responsive support
- **Shadow Effects**: Subtle shadows that enhance depth and hierarchy
- **Color Consistency**: Professional color palette across all pages

## 🚀 Getting Started

### Prerequisites
- Node.js (v14 or higher)
- npm or yarn

### Installation

```bash
# Navigate to client directory
cd client

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## 📁 Project Structure

```
client/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Navbar.jsx          # Navigation with dark mode toggle
│   │   │   ├── Footer.jsx          # Enhanced footer component
│   │   │   └── ThemeToggle.jsx     # Dark/light mode toggle button
│   │   └── [other components]
│   ├── context/
│   │   └── ThemeContext.jsx        # Global theme state management
│   ├── pages/
│   │   ├── Home.jsx                # Beautiful home page
│   │   ├── AdminDashboard.jsx      # Admin control panel
│   │   ├── SellerDashboard.jsx     # Seller management portal
│   │   └── [other pages]
│   ├── App.jsx                     # Main app with theme provider
│   └── main.jsx
├── tailwind.config.js              # Tailwind configuration with dark mode
├── vite.config.js
└── package.json
```

## 🎯 Key Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Home | Landing page with featured products |
| `/shop` | Shop | Product listing and filtering |
| `/product/:id` | ProductDetail | Individual product page |
| `/cart` | Cart | Shopping cart |
| `/checkout` | Checkout | Order checkout |
| `/login` | Login | User authentication |
| `/signup` | Signup | User registration |
| `/profile` | Profile | User profile management |
| **/admin** | **AdminDashboard** | **Admin control panel** |
| **/seller** | **SellerDashboard** | **Seller product management** |

## 🎨 Theme Configuration

The app uses Tailwind's dark mode with class strategy:
- Toggle is saved to localStorage as `theme` key
- Dark mode applied via `dark:` prefix in Tailwind classes
- All components support both light and dark variants

### Dark Mode Classes Example:
```jsx
<div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
  Content adapts to theme
</div>
```

## 📦 Dependencies

- **React**: UI library
- **React Router DOM**: Client-side routing
- **Tailwind CSS**: Utility-first CSS framework
- **Lucide React**: Icon library
- **Vite**: Build tool and dev server

## 🔧 Configuration

### Tailwind Dark Mode
The app uses Tailwind's `class` strategy for dark mode toggling:
```javascript
// tailwind.config.js
export default {
  darkMode: 'class',
  // ...
}
```

### Theme Context
Centralized theme management with React Context:
```jsx
import { useTheme } from './context/ThemeContext';

const MyComponent = () => {
  const { isDark, toggleTheme } = useTheme();
  // Use theme state and toggle function
};
```

## 🎪 UI Improvements Made

✅ Modern gradient backgrounds (blue to purple)
✅ Smooth hover and transition effects
✅ Responsive grid layouts
✅ Professional color palette
✅ Shadow and depth effects
✅ Mobile-first responsive design
✅ Consistent spacing and typography
✅ Interactive buttons with feedback
✅ Clear visual hierarchy
✅ Accessible color contrast

## 📱 Responsive Breakpoints

- **Mobile**: Default (< 768px)
- **Tablet**: md: (768px+)
- **Desktop**: lg: (1024px+)

## 🔐 Admin & Seller Access

### Admin Dashboard (`/admin`)
- Complete platform overview
- User management
- Product moderation
- Sales analytics

### Seller Dashboard (`/seller`)
- Personal product management
- Sales tracking
- Store customization
- Analytics for products

## 🚦 Development Tips

1. **Adding Dark Mode to New Components**:
   - Use `dark:` prefix for dark mode styles
   - Use `transition-colors` for smooth transitions
   - Test both light and dark modes

2. **Color Usage**:
   - Primary: Blue-600 (light), [#2c77d1] (dark)
   - Secondary: Purple-600 (light), [#9426f4] (dark)
   - Backgrounds: White/gray-50 (light), gray-900/black (dark)

3. **Testing Dark Mode**:
   - Toggle the button in navbar
   - Check localStorage for persistence
   - Verify all pages work in both modes

## 🐛 Troubleshooting

**Dark mode not applying?**
- Check that `dark:` prefix is used in Tailwind classes
- Verify ThemeProvider wraps the app in App.jsx
- Check that tailwind.config.js has `darkMode: 'class'`

**Theme not persisting?**
- Verify localStorage is not blocked
- Check browser dev tools console for errors
- Clear cache and reload

## 📄 License

This project is part of the Zunto ecommerce platform.

## 🤝 Contributing

To contribute improvements:
1. Create a feature branch
2. Make your changes with dark mode support
3. Test in both light and dark modes
4. Submit a pull request

---

**Built with ❤️ for the Zunto platform**

# Admin & Seller Dashboards - Complete Guide

## 📊 Admin Dashboard (`/admin`)

### Overview
The admin dashboard is your central hub for managing the entire ecommerce platform. It provides real-time insights into platform performance and user activity.

### Key Statistics
- **Total Users**: Count of all registered users on the platform
- **Total Products**: Number of products listed by all sellers
- **Total Orders**: Complete order history and count
- **Revenue**: Total platform revenue generated

Each stat card shows:
- Icon representing the metric
- Current value
- Percentage change indicator

### Dashboard Tabs

#### 1. **Overview Tab** 📈
- Platform-wide analytics
- Charts and visualizations (coming soon)
- Key performance indicators
- Revenue trends

#### 2. **Users Tab** 👥
Manage all platform users with the following information:
- **Name**: User's full name
- **Email**: Contact email address
- **Role**: Customer or Seller
- **Joined**: Registration date
- **Actions**:
  - 👁️ **View**: See detailed user information
  - ✏️ **Edit**: Modify user details and role
  - 🗑️ **Delete**: Remove user from platform

### Users Management
View all registered users with their roles and joining dates. Easily identify and manage sellers vs. regular customers.

**Color-coded roles:**
- 🔵 Blue: Customer users
- 🟣 Purple: Seller accounts

#### 3. **Products Tab** 📦
Monitor all products listed on the platform:
- **Product Name**: Item title
- **Seller**: Store name selling the product
- **Price**: Product pricing
- **Sales**: Total units sold
- **Status**: Active/Inactive/Draft
- **Actions**:
  - 👁️ **View**: Preview product
  - ✏️ **Edit**: Modify product details
  - 🗑️ **Delete**: Remove from platform

**Status Indicators:**
- 🟢 Green badge: Active products
- 🟡 Yellow badge: Pending approval
- ⚫ Gray badge: Inactive

#### 4. **Orders Tab** 🛒
Track all orders on the platform (coming soon):
- Order ID and dates
- Customer information
- Total amount
- Order status
- Shipping details

## 🏪 Seller Dashboard (`/seller`)

### Overview
The seller dashboard is your personal management center for running your online store. Monitor sales, manage inventory, and grow your business.

### Key Metrics
- **Total Products**: Number of products you've listed
- **Total Sales**: Combined units sold across all products
- **Revenue**: Total earnings from your store
- **Average Rating**: Customer satisfaction metric

Each metric shows current value and growth indicator.

### Dashboard Tabs

#### 1. **Products Tab** 📦 (Active by Default)

Your product management hub with a comprehensive table showing:

**Column Details:**
- **Product Image & Name**: Thumbnail and product title
- **Category**: Product category (Electronics, Accessories, etc.)
- **Price**: Listed price in USD
- **Stock**: Current inventory level
  - 🟢 **Green**: High stock (>100 units)
  - 🟡 **Yellow**: Medium stock (1-100 units)
  - 🔴 **Red**: Low/Out of stock
- **Sales**: Number of units sold
- **Rating**: Customer average rating (e.g., 4.8★)
- **Actions**: 👁️ View | ✏️ Edit | 🗑️ Delete

**Add New Product:**
Click the "➕ Add Product" button in the top right to open the product creation modal.

### Add Product Modal

A convenient form to quickly add products to your store:

```
Product Details Form:
├── Product Name (required)
│   └─ Text input for product title
├── Category (required)
│   └─ Dropdown with options:
│       ├─ Electronics
│       ├─ Accessories
│       ├─ Fashion
│       └─ Home
├── Price (required)
│   └─ Text input with $ placeholder
├── Stock Quantity (required)
│   └─ Number input
├── Description (optional)
│   └─ Textarea for product details
└─ Action Buttons
    ├─ Cancel (closes modal)
    └─ Add Product (creates product)
```

**After submission:**
- Product is immediately added to your table
- Form resets for next entry
- Modal closes automatically
- You can view the new product in the Products tab

#### 2. **Analytics Tab** 📊

View your store's performance metrics:

**Sales Trend Chart**
- Visual representation of sales over time
- 7-day rolling window
- Shows upward/downward trends
- Bar chart for easy interpretation

**Top Products**
- Your 3 best-selling products
- Sales count for each
- Quick reference for popular items
- Helps identify what customers want

**Key Insights:**
- Which products are performing best
- Sales trend direction
- Inventory management priorities

#### 3. **Settings Tab** ⚙️

Customize your store's public appearance:

**Store Configuration:**
- **Store Name**: Your business name (default: "My Store")
- **Description**: Store tagline and about information
- **Contact Info**: (expandable in future)

All settings save with the "Save Settings" button.

### Product Management Best Practices

1. **Stock Management**
   - Keep popular items well-stocked
   - Monitor low-stock warnings
   - Plan reordering based on sales trends

2. **Pricing Strategy**
   - Use analytics to set competitive prices
   - Adjust based on market demand
   - Monitor price changes impact on sales

3. **Product Information**
   - Use clear, descriptive names
   - Accurate categories for discoverability
   - Detailed descriptions help conversions

4. **Category Selection**
   - Electronics: Tech products, gadgets
   - Accessories: Phone cases, cables, etc.
   - Fashion: Clothing, shoes, wearables
   - Home: Furniture, decor, kitchen items

## 🎯 Common Tasks

### How to Add a Product
```
1. Click "Add Product" button
2. Fill in required fields
3. Select appropriate category
4. Enter stock quantity
5. Click "Add Product"
6. See product appear in table immediately
```

### How to Monitor Sales
```
1. Open Seller Dashboard
2. Check Products tab:
   - Sales column shows unit count
   - Rating shows customer satisfaction
3. Click Analytics tab for trends
4. Use insights to adjust inventory
```

### How to Edit Store Info
```
1. Click Settings tab
2. Update Store Name
3. Update Description
4. Click Save Settings
5. Changes reflect immediately
```

### How to Remove a Product
```
1. Find product in Products tab
2. Click trash (🗑️) icon
3. Confirm deletion
4. Product removed from store
```

## 📈 Understanding Your Analytics

### Sales Trend
- **Increasing bars**: Sales momentum growing
- **Decreasing bars**: Sales declining
- **Stable bars**: Consistent performance

### Top Products
- Shows your revenue drivers
- Focus on these for inventory
- Consider creating similar products

### Stock Levels
- Green (>100): Can confidently stock
- Yellow (1-100): Monitor closely
- Red (0): Immediately restock or discontinue

## 💡 Tips for Success

### Inventory Management
- ✅ Restock high-demand items weekly
- ✅ Clear slow-moving inventory with sales
- ✅ Set auto-restock alerts at 20% stock
- ❌ Avoid overstocking niche items

### Pricing Strategy
- ✅ Research competitor pricing
- ✅ Offer bundle deals on popular items
- ✅ Use "Sale" prices strategically
- ❌ Don't undercut sustainable margin

### Product Descriptions
- ✅ Be specific and detailed
- ✅ Highlight unique features
- ✅ Use benefits-focused language
- ✅ Include use cases
- ❌ Avoid misleading claims

### Customer Satisfaction
- ✅ Monitor your average rating
- ✅ Maintain >4.5★ for competitiveness
- ✅ Respond to feedback quickly
- ✅ Keep product quality consistent

## 🔐 Security & Best Practices

- Never share your seller account credentials
- Review analytics regularly (at least weekly)
- Keep product information current
- Respond to customer inquiries promptly
- Maintain accurate inventory counts
- Update prices seasonally

## 📞 Support & Help

For technical support:
- Visit the Support tab
- Contact: support@zunto.com
- Phone: +1 (555) 123-4567

For product policy questions:
- Check company policies
- Review seller guidelines
- Contact support team

## 🎓 Next Steps

After familiarizing yourself with the dashboard:
1. ✅ Add 3-5 test products
2. ✅ Review your analytics
3. ✅ Customize store settings
4. ✅ Start monitoring sales daily
5. ✅ Plan your inventory

---

**Happy selling! 🎉**

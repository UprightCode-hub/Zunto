import React, { Suspense, lazy, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, useLocation } from "react-router-dom";
import { ThemeProvider } from "./context/ThemeContext";
import Navbar from "./components/common/Navbar";
import Footer from "./components/common/Footer";
import ProtectedRoute from "./components/common/ProtectedRoute";
import { getClientContext } from "./utils/clientContext";
const Home = lazy(() => import("./pages/Home"));
const Shop = lazy(() => import("./pages/shop"));
const ProductDetail = lazy(() => import("./pages/ProductDetail"));
const Cart = lazy(() => import("./pages/Cart"));
const Checkout = lazy(() => import("./pages/Checkout"));
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const Profile = lazy(() => import("./pages/Profile"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const SellerDashboard = lazy(() => import("./pages/SellerDashboard"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Orders = lazy(() => import("./pages/Orders"));
const Reviews = lazy(() => import("./pages/Reviews"));
const Notifications = lazy(() => import("./pages/Notifications"));
const Chat = lazy(() => import("./pages/Chat"));
const VerifyRegistration = lazy(() => import("./pages/VerifyRegistration"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const Favorites = lazy(() => import("./pages/Favorites"));
const ShippingAddresses = lazy(() => import("./pages/ShippingAddresses"));
const Refunds = lazy(() => import("./pages/Refunds"));
const OrderDetail = lazy(() => import("./pages/OrderDetail"));
const PaymentVerification = lazy(() => import("./pages/PaymentVerification"));
const NotificationSettings = lazy(() => import("./pages/NotificationSettings"));
const Terms = lazy(() => import("./pages/Terms"));
const Privacy = lazy(() => import("./pages/Privacy"));
const FAQs = lazy(() => import("./pages/FAQs"));
const NotFound = lazy(() => import("./pages/NotFound"));

function AppLayout() {
  const location = useLocation();
  const isDashboard = location.pathname === "/dashboard";

  useEffect(() => {
    const applyClientClass = () => {
      const { viewport, platform } = getClientContext();
      document.body.dataset.viewport = viewport;
      document.body.dataset.platform = platform;
      document.body.classList.toggle('touch-device', platform !== 'laptop-desktop');
    };

    applyClientClass();
    window.addEventListener('resize', applyClientClass);

    return () => {
      window.removeEventListener('resize', applyClientClass);
    };
  }, []);

  return (
    <div className="min-h-screen bg-white dark:bg-[#050d1b] text-gray-900 dark:text-white transition-colors duration-300">
      {!isDashboard && <Navbar />}

      <main className="min-h-[calc(100vh-200px)]">
        <Suspense fallback={<div className="px-4 py-12 text-center text-gray-500 dark:text-gray-400">Loading page...</div>}>
          <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/product/:slug" element={<ProductDetail />} />
          <Route path="/cart" element={<Cart />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/verify-registration" element={<VerifyRegistration />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/favorites" element={<Favorites />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/orders/:orderNumber" element={<OrderDetail />} />
          <Route path="/shipping-addresses" element={<ShippingAddresses />} />
          <Route path="/refunds" element={<Refunds />} />
          <Route path="/payment/verify/:orderNumber" element={<PaymentVerification />} />
          <Route path="/reviews" element={<Reviews />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/notification-settings" element={<NotificationSettings />} />
          <Route path="/terms" element={<Terms />} />
          <Route path="/privacy" element={<Privacy />} />
          <Route path="/faqs" element={<FAQs />} />
          <Route
            path="/chat"
            element={
              <ProtectedRoute>
                <Chat />
              </ProtectedRoute>
            }
          />
          <Route 
            path="/admin" 
            element={
              <ProtectedRoute requiredRole="admin">
                <AdminDashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/seller" 
            element={
              <ProtectedRoute requiredRole="seller">
                <SellerDashboard />
              </ProtectedRoute>
            } 
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute requireVerified>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>

      {!isDashboard && <Footer />}
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <Router>
        <AppLayout />
      </Router>
    </ThemeProvider>
  );
}

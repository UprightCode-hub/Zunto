#server/notifications/management/commands/create_email_templates.py
from django.core.management.base import BaseCommand
from notifications.models import EmailTemplate


class Command(BaseCommand):
    help = 'Create default email templates'
    
    def handle(self, *args, **kwargs):
        templates = [
            {
                'name': 'Welcome Email',
                'template_type': 'welcome',
                'subject': 'Welcome to ZONTO! 🎉',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to ZONTO!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Welcome to ZONTO - Your All-in-One Marketplace! 🎉</p>
            <p>We're excited to have you on board. With ZONTO, you can:</p>
            <ul>
                <li>Buy and sell products</li>
                <li>Find jobs and services</li>
                <li>Rent apartments</li>
                <li>Connect with verified sellers</li>
            </ul>
            <p>Ready to get started?</p>
            <a href="{{frontend_url}}" class="button">Explore ZONTO</a>
            <p>If you have any questions, feel free to reach out to our support team.</p>
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
            <p>Lagos, Nigeria</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Welcome to ZONTO - Your All-in-One Marketplace!

We're excited to have you on board. With ZONTO, you can buy and sell products, find jobs and services, rent apartments, and connect with verified sellers.

Visit us at: {{frontend_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Email Verification',
                'template_type': 'email_verification',
                'subject': 'Verify Your Email - ZONTO',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #667eea; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .code { font-size: 32px; font-weight: bold; color: #667eea; text-align: center; padding: 20px; background: white; border-radius: 5px; letter-spacing: 5px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Verify Your Email</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Thank you for signing up with ZONTO! Please use the verification code below to verify your email address:</p>
            <div class="code">{{verification_code}}</div>
            <p style="text-align: center; color: #666;">This code will expire in 15 minutes.</p>
            <p>If you didn't create an account with ZONTO, please ignore this email.</p>
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Thank you for signing up with ZONTO! Please use the verification code below to verify your email address:

{{verification_code}}

This code will expire in 15 minutes.

If you didn't create an account with ZONTO, please ignore this email.

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Password Reset',
                'template_type': 'password_reset',
                'subject': 'Reset Your Password - ZONTO',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #667eea; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .code { font-size: 32px; font-weight: bold; color: #667eea; text-align: center; padding: 20px; background: white; border-radius: 5px; letter-spacing: 5px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>We received a request to reset your password. Use the code below to reset your password:</p>
            <div class="code">{{reset_code}}</div>
            <p style="text-align: center; color: #666;">This code will expire in 15 minutes.</p>
            <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

We received a request to reset your password. Use the code below to reset your password:

{{reset_code}}

This code will expire in 15 minutes.

If you didn't request a password reset, please ignore this email.

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Order Confirmation',
                'template_type': 'order_confirmation',
                'subject': 'Order Confirmed - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .order-details { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .item { border-bottom: 1px solid #e5e7eb; padding: 15px 0; }
        .button { display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Order Confirmed!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Thank you for your order! Your order has been received and is being processed.</p>
            
            <div class="order-details">
                <h3>Order Details</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Order Date:</strong> {{order_date}}</p>
                <p><strong>Total:</strong> {{total_amount}}</p>
                
                <h4>Items:</h4>
                {% for item in items %}
                <div class="item">
                    <p><strong>{{item.product_name}}</strong></p>
                    <p>Quantity: {{item.quantity}} × ₦{{item.unit_price}}</p>
                </div>
                {% endfor %}
                
                <h4>Shipping Address:</h4>
                <p>{{shipping_address}}</p>
            </div>
            
            <a href="{{order_url}}" class="button">View Order</a>
            
            <p>We'll send you another email when your order ships.</p>
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Thank you for your order! Your order has been received and is being processed.

Order Number: {{order_number}}
Order Date: {{order_date}}
Total: {{total_amount}}

View your order at: {{order_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Payment Success',
                'template_type': 'payment_success',
                'subject': 'Payment Received - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .payment-details { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Payment Successful!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Your payment has been received successfully. Thank you for your purchase!</p>
            
            <div class="payment-details">
                <h3>Payment Details</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Amount Paid:</strong> {{amount_paid}}</p>
                <p><strong>Payment Date:</strong> {{payment_date}}</p>
                <p><strong>Payment Method:</strong> {{payment_method}}</p>
            </div>
            
            <p>Your order is now being processed and will be shipped soon.</p>
            
            <a href="{{order_url}}" class="button">View Order</a>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Your payment has been received successfully. Thank you for your purchase!

Order Number: {{order_number}}
Amount Paid: {{amount_paid}}
Payment Date: {{payment_date}}
Payment Method: {{payment_method}}

View your order at: {{order_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Order Shipped',
                'template_type': 'order_shipped',
                'subject': 'Your Order Has Been Shipped - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #3b82f6; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .tracking-info { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .tracking-number { font-size: 24px; font-weight: bold; color: #3b82f6; text-align: center; padding: 15px; background: #eff6ff; border-radius: 5px; }
        .button { display: inline-block; padding: 12px 30px; background: #3b82f6; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📦 Your Order is on the Way!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Great news! Your order has been shipped and is on its way to you.</p>
            
            <div class="tracking-info">
                <h3>Shipping Information</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Shipped Date:</strong> {{shipped_date}}</p>
                <p><strong>Tracking Number:</strong></p>
                <div class="tracking-number">{{tracking_number}}</div>
            </div>
            
            <p>You can track your package using the tracking number above.</p>
            
            <a href="{{order_url}}" class="button">Track Order</a>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Great news! Your order has been shipped and is on its way to you.

Order Number: {{order_number}}
Shipped Date: {{shipped_date}}
Tracking Number: {{tracking_number}}

Track your order at: {{order_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Order Delivered',
                'template_type': 'order_delivered',
                'subject': 'Your Order Has Been Delivered - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .delivery-info { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 10px 5px; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Order Delivered!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Your order has been successfully delivered! 🎉</p>
            
            <div class="delivery-info">
                <h3>Delivery Information</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Delivered Date:</strong> {{delivered_date}}</p>
            </div>
            
            <p>We hope you love your purchase! If you're satisfied with your order, we'd love to hear about your experience.</p>
            
            <div style="text-align: center;">
                <a href="{{order_url}}" class="button">View Order</a>
                <a href="{{review_url}}" class="button" style="background: #f59e0b;">Leave a Review</a>
            </div>
            
            <p>If you have any issues with your order, please don't hesitate to contact us.</p>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Your order has been successfully delivered!

Order Number: {{order_number}}
Delivered Date: {{delivered_date}}

We hope you love your purchase! Please leave a review at: {{review_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Order Cancelled',
                'template_type': 'order_cancelled',
                'subject': 'Order Cancelled - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #ef4444; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .cancellation-info { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Order Cancelled</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Your order has been cancelled as requested.</p>
            
            <div class="cancellation-info">
                <h3>Cancellation Details</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Cancelled Date:</strong> {{cancelled_date}}</p>
                {% if cancellation_reason %}
                <p><strong>Reason:</strong> {{cancellation_reason}}</p>
                {% endif %}
            </div>
            
            <p>If you paid for this order, a refund will be processed within 5-7 business days.</p>
            
            <a href="{{frontend_url}}" class="button">Continue Shopping</a>
            
            <p>If you have any questions, please contact our support team.</p>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Your order has been cancelled as requested.

Order Number: {{order_number}}
Cancelled Date: {{cancelled_date}}

If you paid for this order, a refund will be processed within 5-7 business days.

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Refund Processed',
                'template_type': 'refund_processed',
                'subject': 'Refund Processed - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .refund-info { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✓ Refund Processed</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>Your refund has been processed successfully.</p>
            
            <div class="refund-info">
                <h3>Refund Details</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Refund Amount:</strong> {{refund_amount}}</p>
                <p><strong>Refund Date:</strong> {{refund_date}}</p>
            </div>
            
            <p>The refund will be credited to your original payment method within 5-7 business days.</p>
            
            <p>If you have any questions about this refund, please contact our support team.</p>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

Your refund has been processed successfully.

Order Number: {{order_number}}
Refund Amount: {{refund_amount}}
Refund Date: {{refund_date}}

The refund will be credited to your original payment method within 5-7 business days.

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Cart Abandonment',
                'template_type': 'cart_abandonment',
                'subject': 'You left items in your cart! 🛒',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .cart-items { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .item { display: flex; padding: 15px 0; border-bottom: 1px solid #e5e7eb; }
        .button { display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛒 Don't Forget Your Cart!</h1>
        </div>
        <div class="content">
            <p>Hi {{user_name}},</p>
            <p>We noticed you left some great items in your cart. Complete your purchase now before they're gone!</p>
            
            <div class="cart-items">
                <h3>Your Cart ({{total_items}} items)</h3>
                {% for item in items %}
                <div class="item">
                    <div>
                        <p><strong>{{item.product.title}}</strong></p>
                        <p>₦{{item.price_at_addition}} × {{item.quantity}}</p>
                    </div>
                </div>
                {% endfor %}
                <p style="margin-top: 20px;"><strong>Subtotal: {{subtotal}}</strong></p>
            </div>
            
            <div style="text-align: center;">
                <a href="{{cart_url}}" class="button">Complete Your Purchase</a>
            </div>
            
            <p>Need help? Our support team is here for you!</p>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{user_name}},

We noticed you left some great items in your cart. Complete your purchase now!

Your Cart ({{total_items}} items)
Subtotal: {{subtotal}}

Complete your purchase at: {{cart_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Seller New Order',
                'template_type': 'seller_new_order',
                'subject': 'New Order Received - {{order_number}}',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #10b981; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .order-info { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .button { display: inline-block; padding: 12px 30px; background: #10b981; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 New Order Received!</h1>
        </div>
        <div class="content">
            <p>Hi {{seller_name}},</p>
            <p>Great news! You've received a new order.</p>
            
            <div class="order-info">
                <h3>Order Details</h3>
                <p><strong>Order Number:</strong> {{order_number}}</p>
                <p><strong>Product:</strong> {{product_name}}</p>
                <p><strong>Quantity:</strong> {{quantity}}</p>
                <p><strong>Amount:</strong> {{amount}}</p>
                <p><strong>Customer:</strong> {{customer_name}}</p>
            </div>
            
            <p>Please process this order as soon as possible and update the order status.</p>
            
            <a href="{{order_url}}" class="button">View Order Details</a>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{seller_name}},

Great news! You've received a new order.

Order Number: {{order_number}}
Product: {{product_name}}
Quantity: {{quantity}}
Amount: {{amount}}
Customer: {{customer_name}}

View order details at: {{order_url}}

Best regards,
The ZONTO Team
                '''
            },
            {
                'name': 'Seller Review',
                'template_type': 'seller_review',
                'subject': 'New Review Received ⭐',
                'html_content': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f59e0b; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .review-info { background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }
        .rating { font-size: 24px; color: #f59e0b; }
        .button { display: inline-block; padding: 12px 30px; background: #f59e0b; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .footer { text-align: center; padding: 20px; color: #666; font-size: 12px; border-radius: 0 0 10px 10px; background: #f9f9f9; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⭐ New Review Received!</h1>
        </div>
        <div class="content">
            <p>Hi {{seller_name}},</p>
            <p>You've received a new review from {{reviewer_name}}!</p>
            
            <div class="review-info">
                <div class="rating">{% for i in "12345" %}{% if forloop.counter <= rating %}★{% else %}☆{% endif %}{% endfor %}</div>
                <h3>{{review_title}}</h3>
                <p>{{review_comment}}</p>
                {% if product_name %}
                <p><strong>Product:</strong> {{product_name}}</p>
                {% endif %}
            </div>
            
            <p>Take a moment to respond to this review and show your customers you care!</p>
            
            <a href="{{frontend_url}}" class="button">Respond to Review</a>
            
            <p>Best regards,<br>The ZONTO Team</p>
        </div>
        <div class="footer">
            <p>&copy; 2025 ZONTO. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
                ''',
                'text_content': '''
Hi {{seller_name}},

You've received a new review from {{reviewer_name}}!

Rating: {{rating}}/5
{{review_title}}
{{review_comment}}

Respond at: {{frontend_url}}

Best regards,
The ZONTO Team
                '''
            },
        ]
        
        for template_data in templates:
            template, created = EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Created: {template.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'⚠ Already exists: {template.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Email templates setup completed!')
        )

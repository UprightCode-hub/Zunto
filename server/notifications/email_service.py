# notifications/email_service.py
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from .models import EmailTemplate, EmailLog
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    @staticmethod
    def send_email(template_type, recipient_email, context_data, recipient_name=''):
        """
        Send email using template
        
        Args:
            template_type: Type of email template to use
            recipient_email: Recipient's email address
            context_data: Dictionary of variables for template
            recipient_name: Recipient's name (optional)
        
        Returns:
            bool: True if email sent successfully
        """
        try:
            # Get template
            template = EmailTemplate.objects.get(
                template_type=template_type,
                is_active=True
            )
            
            # Render subject
            subject_template = Template(template.subject)
            subject = subject_template.render(Context(context_data))
            
            # Render HTML content
            html_template = Template(template.html_content)
            html_content = html_template.render(Context(context_data))
            
            # Render text content
            if template.text_content:
                text_template = Template(template.text_content)
                text_content = text_template.render(Context(context_data))
            else:
                text_content = ''
            
            # Create email log
            email_log = EmailLog.objects.create(
                template=template,
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                status='pending'
            )
            
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, "text/html")
            
            email.send()
            
            # Update log
            email_log.status = 'sent'
            email_log.sent_at = timezone.now()
            email_log.save(update_fields=['status', 'sent_at'])
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True
            
        except EmailTemplate.DoesNotExist:
            logger.error(f"Email template '{template_type}' not found")
            return False
        
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {str(e)}")
            
            # Update log with error
            if 'email_log' in locals():
                email_log.status = 'failed'
                email_log.error_message = str(e)
                email_log.save(update_fields=['status', 'error_message'])
            
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        context = {
            'user_name': user.get_full_name() or user.email,
            'email': user.email,
            'frontend_url': settings.FRONTEND_URL,
        }

        sent = EmailService.send_email(
            'welcome',
            user.email,
            context,
            user.get_full_name()
        )
        if sent:
            return True

        # Fallback if DB template is missing/inactive.
        subject = 'Welcome to Zunto'
        html_content = (
            f"<p>Hello {context['user_name']},</p>"
            "<p>Welcome to Zunto. Your account has been created successfully.</p>"
        )
        text_content = strip_tags(html_content)

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, 'text/html')
            email.send()
            return True
        except Exception as e:
            logger.error(f"Fallback welcome email failed for {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_verification_email(user, code):
        """Send email verification code"""
        recipient_name = user.get_full_name() or user.email
        return EmailService.send_verification_email_to_recipient(
            recipient_email=user.email,
            recipient_name=recipient_name,
            code=code,
        )

    @staticmethod
    def send_verification_email_to_recipient(recipient_email, recipient_name, code):
        """Send email verification code to an arbitrary recipient."""
        context = {
            'user_name': recipient_name or recipient_email,
            'verification_code': code,
            'frontend_url': settings.FRONTEND_URL,
        }

        sent = EmailService.send_email(
            'email_verification',
            recipient_email,
            context,
            recipient_name
        )
        if sent:
            return True

        # Fallback if DB template is missing/inactive.
        subject = 'Your Zunto verification code'
        html_content = (
            f"<p>Hello {context['user_name']},</p>"
            "<p>Use the verification code below to verify your account:</p>"
            f"<h2>{code}</h2>"
            "<p>This code expires in 15 minutes.</p>"
        )
        text_content = strip_tags(html_content)

        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[recipient_email]
            )
            email.attach_alternative(html_content, 'text/html')
            email.send()
            return True
        except Exception as e:
            logger.error(
                f"Fallback verification email failed for {recipient_email}: {str(e)}"
            )
            return False
    
    @staticmethod
    def send_password_reset_email(user, code):
        """Send password reset code"""
        context = {
            'user_name': user.get_full_name() or user.email,
            'reset_code': code,
            'frontend_url': settings.FRONTEND_URL,
        }
        
        return EmailService.send_email(
            'password_reset',
            user.email,
            context,
            user.get_full_name()
        )
    
    @staticmethod
    def send_order_confirmation_email(order):
        """Send order confirmation email"""
        # Check user preferences
        if hasattr(order.customer, 'notification_preferences'):
            if not order.customer.notification_preferences.email_order_updates:
                return False
        
        context = {
            'user_name': order.customer.get_full_name(),
            'order_number': order.order_number,
            'order_date': order.created_at.strftime('%B %d, %Y'),
            'total_amount': f"₦{order.total_amount:,.2f}",
            'items': order.items.all(),
            'shipping_address': order.shipping_address,
            'frontend_url': settings.FRONTEND_URL,
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
        }
        
        return EmailService.send_email(
            'order_confirmation',
            order.customer.email,
            context,
            order.customer.get_full_name()
        )
    
    @staticmethod
    def send_payment_success_email(order):
        """Send payment success email"""
        if hasattr(order.customer, 'notification_preferences'):
            if not order.customer.notification_preferences.email_payment_updates:
                return False
        
        context = {
            'user_name': order.customer.get_full_name(),
            'order_number': order.order_number,
            'amount_paid': f"₦{order.total_amount:,.2f}",
            'payment_date': order.paid_at.strftime('%B %d, %Y at %I:%M %p') if order.paid_at else '',
            'payment_method': order.get_payment_method_display(),
            'frontend_url': settings.FRONTEND_URL,
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
        }
        
        return EmailService.send_email(
            'payment_success',
            order.customer.email,
            context,
            order.customer.get_full_name()
        )
    
    @staticmethod
    def send_order_shipped_email(order):
        """Send order shipped email"""
        if hasattr(order.customer, 'notification_preferences'):
            if not order.customer.notification_preferences.email_shipping_updates:
                return False
        
        context = {
            'user_name': order.customer.get_full_name(),
            'order_number': order.order_number,
            'tracking_number': order.tracking_number or 'N/A',
            'shipped_date': order.shipped_at.strftime('%B %d, %Y') if order.shipped_at else '',
            'frontend_url': settings.FRONTEND_URL,
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
        }
        
        return EmailService.send_email(
            'order_shipped',
            order.customer.email,
            context,
            order.customer.get_full_name()
        )
    
    @staticmethod
    def send_order_delivered_email(order):
        """Send order delivered email"""
        if hasattr(order.customer, 'notification_preferences'):
            if not order.customer.notification_preferences.email_shipping_updates:
                return False
        
        context = {
            'user_name': order.customer.get_full_name(),
            'order_number': order.order_number,
            'delivered_date': order.delivered_at.strftime('%B %d, %Y') if order.delivered_at else '',
            'frontend_url': settings.FRONTEND_URL,
            'order_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}",
            'review_url': f"{settings.FRONTEND_URL}/orders/{order.order_number}/review",
        }
        
        return EmailService.send_email(
            'order_delivered',
            order.customer.email,
            context,
            order.customer.get_full_name()
        )
    
    @staticmethod
    def send_order_cancelled_email(order, reason=''):
        """Send order cancelled email"""
        if hasattr(order.customer, 'notification_preferences'):
            if not order.customer.notification_preferences.email_order_updates:
                return False
        
        context = {
            'user_name': order.customer.get_full_name(),
            'order_number': order.order_number,
            'cancellation_reason': reason,
            'cancelled_date': order.cancelled_at.strftime('%B %d, %Y') if order.cancelled_at else '',
            'frontend_url': settings.FRONTEND_URL,
        }
        
        return EmailService.send_email(
            'order_cancelled',
            order.customer.email,
            context,
            order.customer.get_full_name()
        )
    
    @staticmethod
    def send_refund_processed_email(refund):
        """Send refund processed email"""
        order = refund.order
        
        context = {
            'user_name': order.customer.get_full_name(),
            'order_number': order.order_number,
            'refund_amount': f"₦{refund.amount:,.2f}",
            'refund_date': refund.processed_at.strftime('%B %d, %Y') if refund.processed_at else '',
            'frontend_url': settings.FRONTEND_URL,
        }
        
        return EmailService.send_email(
            'refund_processed',
            order.customer.email,
            context,
            order.customer.get_full_name()
        )
    
    @staticmethod
    def send_cart_abandonment_email(cart):
        """Send cart abandonment reminder"""
        if not cart.user:
            return False
        
        if hasattr(cart.user, 'notification_preferences'):
            if not cart.user.notification_preferences.email_cart_abandonment:
                return False
        
        context = {
            'user_name': cart.user.get_full_name(),
            'items': cart.items.all()[:3],  # Show first 3 items
            'total_items': cart.total_items,
            'subtotal': f"₦{cart.subtotal:,.2f}",
            'frontend_url': settings.FRONTEND_URL,
            'cart_url': f"{settings.FRONTEND_URL}/cart",
        }
        
        return EmailService.send_email(
            'cart_abandonment',
            cart.user.email,
            context,
            cart.user.get_full_name()
        )
    
    @staticmethod
    def send_seller_new_order_email(order_item):
        """Send notification to seller about new order"""
        seller = order_item.seller
        
        if hasattr(seller, 'notification_preferences'):
            if not seller.notification_preferences.email_seller_new_orders:
                return False
        
        context = {
            'seller_name': seller.get_full_name(),
            'order_number': order_item.order.order_number,
            'product_name': order_item.product_name,
            'quantity': order_item.quantity,
            'amount': f"₦{order_item.total_price:,.2f}",
            'customer_name': order_item.order.customer.get_full_name(),
            'frontend_url': settings.FRONTEND_URL,
            'order_url': f"{settings.FRONTEND_URL}/seller/orders/{order_item.order.order_number}",
        }
        
        return EmailService.send_email(
            'seller_new_order',
            seller.email,
            context,
            seller.get_full_name()
        )
    
    @staticmethod
    def send_seller_review_email(review):
        """Send notification to seller about new review"""
        seller = review.product.seller if hasattr(review, 'product') else review.seller
        
        if hasattr(seller, 'notification_preferences'):
            if not seller.notification_preferences.email_seller_reviews:
                return False
        
        context = {
            'seller_name': seller.get_full_name(),
            'rating': review.rating,
            'review_title': review.title,
            'review_comment': review.comment,
            'reviewer_name': review.reviewer.get_full_name(),
            'product_name': review.product.title if hasattr(review, 'product') else '',
            'frontend_url': settings.FRONTEND_URL,
        }
        
        return EmailService.send_email(
            'seller_review',
            seller.email,
            context,
            seller.get_full_name()
        )

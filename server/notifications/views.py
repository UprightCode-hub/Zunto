# notifications/views.py
from rest_framework import generics, status, permissions, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import EmailTemplate, EmailLog, NotificationPreference, Notification
from .serializers import (
    EmailTemplateSerializer, EmailLogSerializer,
    NotificationPreferenceSerializer, NotificationSerializer
)
from .email_service import EmailService


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for user notifications"""
    
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all marked as read'})


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """Get and update notification preferences"""
    
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences


class EmailLogListView(generics.ListAPIView):
    """List email logs for current user"""
    
    serializer_class = EmailLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EmailLog.objects.filter(
            recipient_email=self.request.user.email
        ).select_related('template').order_by('-created_at')


class TestEmailView(APIView):
    """Send test email (for testing purposes)"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        template_type = request.data.get('template_type')
        
        if not template_type:
            return Response({
                'error': 'template_type is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Send test email
        result = EmailService.send_email(
            template_type=template_type,
            recipient_email=request.user.email,
            context_data={
                'user_name': request.user.get_full_name(),
                'email': request.user.email,
                'frontend_url': 'http://localhost:3000',
                'verification_code': '123456',
                'reset_code': '654321',
                'order_number': 'ORD-TEST-1234',
                'order_date': 'January 15, 2025',
                'total_amount': '₦50,000.00',
            },
            recipient_name=request.user.get_full_name()
        )
        
        if result:
            return Response({
                'message': f'Test email sent to {request.user.email}'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Failed to send test email'
            }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def email_templates_list(request):
    """List all email templates (admin only)"""
    
    templates = EmailTemplate.objects.all()
    serializer = EmailTemplateSerializer(templates, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def email_statistics(request):
    """Get email statistics (admin only)"""
    
    from django.db.models import Count
    
    stats = {
        'total_sent': EmailLog.objects.filter(status='sent').count(),
        'total_failed': EmailLog.objects.filter(status='failed').count(),
        'total_pending': EmailLog.objects.filter(status='pending').count(),
        'by_template': EmailLog.objects.values(
            'template__name'
        ).annotate(count=Count('id')).order_by('-count')
    }
    
    return Response(stats)
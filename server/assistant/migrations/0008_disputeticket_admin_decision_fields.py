from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('assistant', '0007_disputeticket_and_communication'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='disputeticket',
            name='admin_decision_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='admin_decision_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='admin_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_tickets_decided', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='disputeticket',
            name='legacy_report',
            field=models.OneToOneField(blank=True, help_text='Legacy Report mapping for backward-compatible dispute flow', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dispute_ticket', to='assistant.report'),
        ),
        migrations.AlterField(
            model_name='disputeticket',
            name='status',
            field=models.CharField(choices=[('OPEN', 'Open'), ('UNDER_REVIEW', 'Under Review'), ('RESOLVED_APPROVED', 'Resolved Approved'), ('RESOLVED_DENIED', 'Resolved Denied'), ('CLOSED', 'Closed')], default='OPEN', max_length=20),
        ),
    ]

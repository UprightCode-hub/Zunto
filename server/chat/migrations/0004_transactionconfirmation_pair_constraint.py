from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_conversation_lock_and_transaction_confirmation'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='transactionconfirmation',
            constraint=models.UniqueConstraint(fields=('buyer', 'seller', 'product'), name='chat_unique_confirmation_pair_per_product'),
        ),
    ]

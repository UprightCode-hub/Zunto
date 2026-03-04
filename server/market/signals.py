from django.db.models.signals import post_save
from django.dispatch import receiver

from assistant.services.demand_matching_service import match_product_to_demand
from market.models import Product


@receiver(post_save, sender=Product)
def match_new_product_to_existing_demand(sender, instance, created, **kwargs):
    """Run buyer-demand matching only for newly created products."""
    if not created:
        return
    match_product_to_demand(instance)

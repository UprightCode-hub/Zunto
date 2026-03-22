import sys

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models import SellerProfile
from assistant.services.demand_matching_service import match_product_to_demand
from market.demand_signals import track_demand_event
from market.models import DemandEvent, Favorite, Product
from market.tasks import schedule_product_embedding_generation

SKIP_MARKET_BACKGROUND_COMMANDS = {'seed_db'}


def _skip_market_background_hooks():
    command = sys.argv[1] if len(sys.argv) > 1 else ''
    return command in SKIP_MARKET_BACKGROUND_COMMANDS




@receiver(pre_save, sender=Product)
def track_previous_product_embedding_source(sender, instance, **kwargs):
    if not instance.pk:
        instance._embedding_source_changed = True
        return

    previous = sender.objects.filter(pk=instance.pk).values('title', 'description', 'category_id').first()
    if not previous:
        instance._embedding_source_changed = True
        return

    instance._embedding_source_changed = (
        (previous.get('title') or '') != (instance.title or '')
        or (previous.get('description') or '') != (instance.description or '')
        or previous.get('category_id') != instance.category_id
    )


@receiver(post_save, sender=Product)
def match_new_product_to_existing_demand(sender, instance, created, **kwargs):
    """Run buyer-demand matching only for newly created products."""
    if _skip_market_background_hooks():
        return

    if created:
        match_product_to_demand(instance)

    embedding_source_changed = getattr(instance, '_embedding_source_changed', created)
    if embedding_source_changed:
        schedule_product_embedding_generation(instance.id)


@receiver(pre_save, sender=SellerProfile)
def track_previous_seller_location(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_active_location_id = None
        return

    previous = sender.objects.filter(pk=instance.pk).values_list('active_location_id', flat=True).first()
    instance._previous_active_location_id = previous


@receiver(post_save, sender=SellerProfile)
def sync_seller_products_location(sender, instance, **kwargs):
    previous_location_id = getattr(instance, '_previous_active_location_id', None)
    if previous_location_id == instance.active_location_id:
        return

    Product.objects.filter(seller=instance.user).exclude(location_id=instance.active_location_id).update(
        location_id=instance.active_location_id
    )


@receiver(post_save, sender=Favorite)
def track_favorite_demand_event(sender, instance, created, **kwargs):
    if _skip_market_background_hooks():
        return

    if not created:
        return

    track_demand_event(
        DemandEvent.EVENT_FAVORITE,
        product=instance.product,
        user=instance.user,
        source='favorite_toggle',
    )

from django.db.models.signals import post_save
from django.dispatch import receiver

from assistant.models import RecommendationDemandGap
from assistant.services.demand_signal_service import (
    notify_sellers_for_hot_cluster,
    update_cluster_from_gap,
)


@receiver(post_save, sender=RecommendationDemandGap)
def update_demand_cluster_on_gap_save(sender, instance, created, **kwargs):
    if not created:
        return

    cluster = update_cluster_from_gap(instance)
    if cluster is None:
        return

    notify_sellers_for_hot_cluster(cluster)

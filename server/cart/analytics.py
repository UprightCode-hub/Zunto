# cart/analytics.py
from django.db.models import Count, Q, Avg
from .models import CartAbandonment, Cart


def get_abandoned_carts_count():
    """Count of unrecovered abandoned carts"""
    return CartAbandonment.objects.filter(recovered=False).count()


def get_recovered_carts_count():
    """Count of recovered abandoned carts"""
    return CartAbandonment.objects.filter(recovered=True).count()


def get_abandonment_rate():
    """Calculate abandonment rate as percentage"""
    total_carts = Cart.objects.filter(items__isnull=False).distinct().count()
    if total_carts == 0:
        return 0.0
    abandoned = get_abandoned_carts_count()
    return round((abandoned / total_carts) * 100, 2)


def get_average_abandoned_value():
    """Average value of abandoned carts"""
    result = CartAbandonment.objects.filter(
        recovered=False
    ).aggregate(avg_value=Avg('total_value'))
    return result['avg_value'] or 0.0


def get_recovery_rate():
    """Calculate recovery rate as percentage"""
    total_abandoned = CartAbandonment.objects.count()
    if total_abandoned == 0:
        return 0.0
    recovered = get_recovered_carts_count()
    return round((recovered / total_abandoned) * 100, 2)


def get_abandonment_summary():
    """Get complete abandonment metrics"""
    return {
        'total_abandoned': get_abandoned_carts_count(),
        'total_recovered': get_recovered_carts_count(),
        'abandonment_rate': get_abandonment_rate(),
        'recovery_rate': get_recovery_rate(),
        'avg_abandoned_value': get_average_abandoned_value(),
    }
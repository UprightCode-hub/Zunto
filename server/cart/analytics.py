#server/cart/analytics.py
from django.db.models import Count, Q, Avg, Sum, Min, Max
from .models import CartAbandonment, Cart, UserScore
from decimal import Decimal


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


def get_score_distribution():
    """Get distribution of users across score tiers"""
    total_scored = UserScore.objects.count()
    
    if total_scored == 0:
        return {
            'high_value': 0,
            'medium_value': 0,
            'low_value': 0,
            'at_risk': 0,
            'total': 0
        }
    
    high = UserScore.objects.filter(composite_score__gte=75).count()
    medium = UserScore.objects.filter(composite_score__gte=50, composite_score__lt=75).count()
    low = UserScore.objects.filter(composite_score__gte=25, composite_score__lt=50).count()
    at_risk = UserScore.objects.filter(composite_score__lt=25).count()
    
    return {
        'high_value': high,
        'medium_value': medium,
        'low_value': low,
        'at_risk': at_risk,
        'total': total_scored,
        'high_value_pct': round((high / total_scored) * 100, 2) if total_scored else 0,
        'medium_value_pct': round((medium / total_scored) * 100, 2) if total_scored else 0,
        'low_value_pct': round((low / total_scored) * 100, 2) if total_scored else 0,
        'at_risk_pct': round((at_risk / total_scored) * 100, 2) if total_scored else 0,
    }


def get_top_users_by_score(limit=10):
    """Get top users by composite score"""
    return UserScore.objects.select_related('user').order_by('-composite_score')[:limit]


def get_recovery_targets(min_score=50, limit=50):
    """Get high-value users with unrecovered abandoned carts"""
    target_users = UserScore.objects.filter(
        composite_score__gte=min_score,
        user__abandoned_carts__recovered=False
    ).select_related('user').distinct().order_by('-composite_score')[:limit]
    
    return target_users


def get_score_analytics_summary():
    """Get comprehensive scoring analytics"""
    score_stats = UserScore.objects.aggregate(
        avg_composite=Avg('composite_score'),
        avg_abandonment=Avg('abandonment_score'),
        avg_value=Avg('value_score'),
        avg_conversion=Avg('conversion_score'),
        avg_hesitation=Avg('hesitation_score'),
        max_composite=Max('composite_score'),
        min_composite=Min('composite_score')
    )
    
    distribution = get_score_distribution()
    
    return {
        'averages': {
            'composite': round(score_stats['avg_composite'] or 0, 2),
            'abandonment': round(score_stats['avg_abandonment'] or 0, 2),
            'value': round(score_stats['avg_value'] or 0, 2),
            'conversion': round(score_stats['avg_conversion'] or 0, 2),
            'hesitation': round(score_stats['avg_hesitation'] or 0, 2),
        },
        'range': {
            'max': round(score_stats['max_composite'] or 0, 2),
            'min': round(score_stats['min_composite'] or 0, 2),
        },
        'distribution': distribution,
        'total_users_scored': distribution['total']
    }


def get_value_by_tier():
    """Get total abandoned cart value by user tier"""
    tiers = {
        'high_value': {'min': 75, 'max': 100},
        'medium_value': {'min': 50, 'max': 75},
        'low_value': {'min': 25, 'max': 50},
        'at_risk': {'min': 0, 'max': 25}
    }
    
    result = {}
    
    for tier_name, score_range in tiers.items():
        users = UserScore.objects.filter(
            composite_score__gte=score_range['min'],
            composite_score__lt=score_range['max']
        ).values_list('user_id', flat=True)
        
        stats = CartAbandonment.objects.filter(
            user_id__in=users,
            recovered=False
        ).aggregate(
            total_value=Sum('total_value'),
            total_carts=Count('id')
        )
        
        result[tier_name] = {
            'total_value': float(stats['total_value'] or 0),
            'total_carts': stats['total_carts'],
            'user_count': len(users)
        }
    
    return result


def get_promo_eligible_users(min_score=40):
    """Get users eligible for promotional campaigns"""
    return UserScore.objects.filter(
        composite_score__gte=min_score
    ).select_related('user').order_by('-composite_score')


def get_abandonment_summary_with_scores():
    """Enhanced abandonment summary with scoring data"""
    base_summary = get_abandonment_summary()
    score_summary = get_score_analytics_summary()
    value_by_tier = get_value_by_tier()
    
    return {
        **base_summary,
        'scoring': score_summary,
        'value_by_tier': value_by_tier,
    }

# cart/scoring.py - Core scoring calculation logic

from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import CartAbandonment, CartEvent, SavedForLater, Cart
import logging

logger = logging.getLogger(__name__)


# Score weights (must sum to 100)
WEIGHTS = {
    'abandonment': 30,
    'value': 25,
    'conversion': 20,
    'hesitation': 15,
    'price_sensitivity': 10,
}


def _clamp_score(value):
    """Clamp score value between 0 and 100."""
    return max(0, min(100, value))


def calculate_abandonment_score(user):
    """Calculate score based on abandonment frequency (0-100)"""
    total_carts = Cart.objects.filter(
        Q(user=user) & ~Q(items__isnull=True)
    ).distinct().count()
    
    if total_carts == 0:
        return Decimal('50.00')  # Neutral score for new users
    
    abandoned_count = CartAbandonment.objects.filter(user=user).count()
    
    if abandoned_count == 0:
        return Decimal('100.00')  # Perfect score
    
    # Lower abandonment rate = higher score
    abandonment_rate = abandoned_count / total_carts
    score = _clamp_score(100 - (abandonment_rate * 100))
    
    return Decimal(str(round(score, 2)))


def calculate_value_score(user):
    """Calculate score based on average abandoned cart value (0-100)"""
    avg_value = CartAbandonment.objects.filter(
        user=user
    ).aggregate(avg=Avg('total_value'))['avg']
    
    if not avg_value:
        return Decimal('50.00')  # Neutral score for no data
    
    # Normalize against benchmarks (adjust based on your product prices)
    # Example: ₦50,000 = 100 score, scales down from there
    benchmark_high = 50000
    benchmark_low = 5000
    
    if avg_value >= benchmark_high:
        score = 100.00
    elif avg_value <= benchmark_low:
        score = 20.00
    else:
        # Linear scale between low and high benchmarks
        score = 20 + ((avg_value - benchmark_low) / (benchmark_high - benchmark_low) * 80)
    
    return Decimal(str(round(score, 2)))


def calculate_conversion_score(user):
    """Calculate score based on recovery/conversion rate (0-100)"""
    total_abandoned = CartAbandonment.objects.filter(user=user).count()
    
    if total_abandoned == 0:
        return Decimal('50.00')  # Neutral for no abandonment history
    
    recovered_count = CartAbandonment.objects.filter(
        user=user,
        recovered=True
    ).count()
    
    # Higher recovery rate = higher score
    recovery_rate = recovered_count / total_abandoned
    score = recovery_rate * 100
    
    return Decimal(str(round(score, 2)))


def calculate_hesitation_score(user):
    """Calculate score based on time-to-abandon and save-for-later behavior (0-100)"""
    # Component 1: Average time to abandon (70% of hesitation score)
    time_score = _calculate_time_to_abandon_score(user)
    
    # Component 2: Save-for-later ratio (30% of hesitation score)
    save_ratio_score = _calculate_save_ratio_score(user)
    
    # Weighted combination
    hesitation_score = (time_score * 0.7) + (save_ratio_score * 0.3)
    
    return Decimal(str(round(hesitation_score, 2)))


def _calculate_time_to_abandon_score(user):
    """Calculate score based on average time between cart creation and abandonment"""
    abandonments = CartAbandonment.objects.filter(
        user=user
    ).select_related('cart')
    
    if not abandonments.exists():
        return 50.00  # Neutral
    
    time_deltas = []
    for abandonment in abandonments:
        time_diff = abs((abandonment.abandoned_at - abandonment.cart.created_at).total_seconds()) / 3600
        time_deltas.append(time_diff)
    
    if not time_deltas:
        return 50.00
    
    avg_hours = sum(time_deltas) / len(time_deltas)
    
    # Shorter time = less hesitation = higher score
    # Example: <1 hour = 100, >48 hours = 20
    if avg_hours <= 1:
        score = 100.00
    elif avg_hours >= 48:
        score = 20.00
    else:
        score = 100 - ((avg_hours - 1) / 47 * 80)
    
    return round(score, 2)


def _calculate_save_ratio_score(user):
    """Calculate score based on save-for-later vs add-to-cart ratio"""
    total_added = CartEvent.objects.filter(
        user=user,
        event_type='cart_item_added'
    ).count()
    
    if total_added == 0:
        return 50.00  # Neutral for no activity
    
    total_saved = CartEvent.objects.filter(
        user=user,
        event_type='cart_item_saved'
    ).count()
    
    # Lower save ratio = less hesitation = higher score
    save_ratio = total_saved / total_added
    score = _clamp_score(100 - (save_ratio * 100))
    
    return round(score, 2)


def calculate_price_sensitivity_score(user):
    """Calculate score based on price sensitivity indicators (0-100)"""
    # For now, use a placeholder that can be enhanced later
    # Future: track if user waits for price drops, uses discount codes, etc.
    
    # Simple heuristic: users with higher value carts are less price sensitive
    avg_value = CartAbandonment.objects.filter(
        user=user
    ).aggregate(avg=Avg('total_value'))['avg']
    
    if not avg_value:
        return Decimal('50.00')
    
    # Higher cart value suggests lower price sensitivity
    benchmark = 30000
    if avg_value >= benchmark:
        score = 80.00
    else:
        score = 50 + (avg_value / benchmark * 30)
    
    return Decimal(str(round(score, 2)))


def calculate_composite_score(user):
    """Calculate weighted composite score (0-100)"""
    abandonment = calculate_abandonment_score(user)
    value = calculate_value_score(user)
    conversion = calculate_conversion_score(user)
    hesitation = calculate_hesitation_score(user)
    price_sensitivity = calculate_price_sensitivity_score(user)
    
    composite = (
        (abandonment * WEIGHTS['abandonment'] / 100) +
        (value * WEIGHTS['value'] / 100) +
        (conversion * WEIGHTS['conversion'] / 100) +
        (hesitation * WEIGHTS['hesitation'] / 100) +
        (price_sensitivity * WEIGHTS['price_sensitivity'] / 100)
    )
    
    return Decimal(str(round(_clamp_score(composite), 2)))


def calculate_all_scores(user):
    """Calculate all component and composite scores for a user"""
    return {
        'abandonment_score': calculate_abandonment_score(user),
        'value_score': calculate_value_score(user),
        'conversion_score': calculate_conversion_score(user),
        'hesitation_score': calculate_hesitation_score(user),
        'price_sensitivity_score': calculate_price_sensitivity_score(user),
        'composite_score': calculate_composite_score(user),
    }
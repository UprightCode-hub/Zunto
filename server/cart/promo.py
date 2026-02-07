# cart/promo.py - In-memory discount calculations (no DB writes)

def calculate_promo_discount(user_score):
    """Calculate recommended discount based on composite score (in-memory only)"""
    if user_score.composite_score >= 80:
        return 10.00  # 10% for top users
    elif user_score.composite_score >= 60:
        return 7.50   # 7.5% for high-value users
    elif user_score.composite_score >= 40:
        return 5.00   # 5% for medium users
    return 0.00


def is_discount_eligible(user_score):
    """Check if user qualifies for discount (in-memory only)"""
    return user_score.composite_score >= 40


def get_promo_tier(user_score):
    """Get promo tier name for user"""
    score = user_score.composite_score
    if score >= 80:
        return 'premium'
    elif score >= 60:
        return 'gold'
    elif score >= 40:
        return 'silver'
    return 'standard'
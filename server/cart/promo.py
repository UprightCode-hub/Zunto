#server/cart/promo.py
def calculate_promo_discount(user_score):
    """Calculate recommended discount based on composite score (in-memory only)"""
    if user_score.composite_score >= 80:
        return 10.00                     
    elif user_score.composite_score >= 60:
        return 7.50                              
    elif user_score.composite_score >= 40:
        return 5.00                        
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

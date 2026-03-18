from accounts.models import SellerProfile


def get_seller_profile(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.seller_profile
    except SellerProfile.DoesNotExist:
        return None


def is_active_seller(user):
    profile = get_seller_profile(user)
    if profile is not None:
        return profile.status == SellerProfile.STATUS_APPROVED
    if getattr(user, 'role', None) == 'seller':
        return True
    return bool(getattr(user, 'is_seller', False))


def is_pending_seller(user):
    profile = get_seller_profile(user)
    if profile is not None:
        return profile.status == SellerProfile.STATUS_PENDING
    return False


def is_verified_seller(user):
    profile = get_seller_profile(user)
    if profile is not None:
        return bool(profile.is_verified_seller)
    return bool(getattr(user, 'is_verified_seller', False))


def get_seller_commerce_mode(user):
    profile = get_seller_profile(user)
    if profile is None:
        return getattr(user, 'seller_commerce_mode', 'direct')
    return profile.seller_commerce_mode

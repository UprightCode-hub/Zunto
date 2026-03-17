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
    return bool(profile is not None and profile.status == SellerProfile.STATUS_APPROVED)


def is_pending_seller(user):
    profile = get_seller_profile(user)
    if profile is not None:
        return profile.status == SellerProfile.STATUS_PENDING
    return False


def is_verified_seller(user):
    profile = get_seller_profile(user)
    return bool(profile is not None and profile.is_verified_seller)


def get_seller_commerce_mode(user):
    profile = get_seller_profile(user)
    if profile is None:
        return 'direct'
    return profile.seller_commerce_mode

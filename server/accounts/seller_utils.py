from accounts.models import SellerApplication, SellerProfile


def get_seller_profile(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None


def get_seller_application(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    try:
        return user.seller_application
    except SellerApplication.DoesNotExist:
        return None


def get_seller_application_status(user):
    application = get_seller_application(user)
    return getattr(application, 'status', None)
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
    application = get_seller_application(user)
    return getattr(application, 'status', None) == SellerApplication.STATUS_PENDING


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

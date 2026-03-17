from dataclasses import dataclass

from django.db.models import Case, IntegerField, Value, When

from market.models import Location


@dataclass(frozen=True)
class BuyerLocation:
    state: str
    area: str = ''


def resolve_buyer_location(request):
    """Resolve buyer location in priority: query override -> authenticated profile -> none."""
    params = request.query_params

    location_id = params.get('location')
    if location_id:
        location = Location.objects.filter(id=location_id).only('state', 'area').first()
        if location:
            return BuyerLocation(state=(location.state or '').strip(), area=(location.area or '').strip())

    override_state = (params.get('state') or '').strip()
    override_area = (params.get('lga') or params.get('area') or '').strip()
    if override_state:
        return BuyerLocation(state=override_state, area=override_area)

    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return None

    seller_profile = getattr(user, 'seller_profile', None)
    if seller_profile and seller_profile.active_location_id:
        location = seller_profile.active_location
        return BuyerLocation(state=(location.state or '').strip(), area=(location.area or '').strip())

    profile_state = (getattr(user, 'state', '') or '').strip()
    profile_area = (getattr(user, 'city', '') or '').strip()
    if profile_state:
        return BuyerLocation(state=profile_state, area=profile_area)

    return None


def apply_location_priority(queryset, buyer_location):
    """Annotate location_priority for downstream ordering in the listing pipeline."""
    if not buyer_location or not buyer_location.state:
        return queryset.annotate(location_priority=Value(2, output_field=IntegerField()))

    state = buyer_location.state
    area = buyer_location.area

    if area:
        priority_case = Case(
            When(location__state__iexact=state, location__area__iexact=area, then=Value(0)),
            When(location__state__iexact=state, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )
    else:
        priority_case = Case(
            When(location__state__iexact=state, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        )

    return queryset.annotate(location_priority=priority_case)

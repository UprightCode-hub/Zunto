from dataclasses import dataclass


@dataclass(frozen=True)
class SearchQuery:
    query_text: str
    category: str
    min_price: str
    max_price: str
    condition: str
    verified_only: str
    seller_type: str
    state: str
    lga: str
    ordering: str


def build_search_query(request):
    params = request.query_params
    return SearchQuery(
        query_text=(params.get('q') or params.get('search') or '').strip(),
        category=(params.get('category') or '').strip(),
        min_price=(params.get('min_price') or '').strip(),
        max_price=(params.get('max_price') or '').strip(),
        condition=(params.get('condition') or '').strip(),
        verified_only=(params.get('verified_only') or '').strip(),
        seller_type=(params.get('seller_type') or '').strip(),
        state=(params.get('state') or '').strip(),
        lga=(params.get('lga') or '').strip(),
        ordering=(params.get('ordering') or '').strip(),
    )

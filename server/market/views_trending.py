from django.db.models import Case, IntegerField, Value, When
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from market.demand_engine import get_trending_products
from market.models import Product
from market.serializers import ProductListSerializer
from market.search import search_products


class TrendingProductsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        product_ids = get_trending_products(limit=20)
        if not product_ids:
            return Response([])

        ordering_case = Case(
            *[When(id=product_id, then=Value(index)) for index, product_id in enumerate(product_ids)],
            default=Value(len(product_ids)),
            output_field=IntegerField(),
        )

        base_queryset = Product.objects.filter(id__in=product_ids, status='active')
        products = search_products(request, base_queryset).annotate(
            _order=ordering_case,
        ).order_by(
            '_order',
            'location_priority',
            '-intent_match_score',
            '-semantic_score',
            '-popularity_score',
            '-created_at',
        )

        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from product_module.models import Product, ProductCategory
from product_module.serializers import ProductSerializer, ProductCategorySerializer


class ProductPaginationViewSet(PageNumberPagination):
    page_size = 4


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.filter(is_active=True)
    serializer_class = ProductSerializer
    pagination_class = ProductPaginationViewSet
    parser_classes = [MultiPartParser, FormParser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['title', 'description', 'categories__title']


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    pagination_class = ProductPaginationViewSet


class GroupedProductListView(APIView):
    def get(self, request):
        data = {}

        categories = ProductCategory.objects.filter(is_active=True)
        for category in categories:
            products = Product.objects.filter(categories=category).order_by('-id')[:5]
            serializer = ProductSerializer(products, many=True)
            data[category.id] = {
                'title': category.title,
                'products': serializer.data
            }

        return Response(data)

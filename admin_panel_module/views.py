from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView, DestroyAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.contrib.auth import get_user_model

from admin_panel_module.serializers import AdminUserListSerializer
from product_module.models import Product, ProductCategory
from product_module.serializers import ProductSerializer, ProductCategorySerializer

User = get_user_model()


class AdminDashboardSummaryView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        total_users = User.objects.count()
        total_products = Product.objects.count()

        return Response({
            "summary": {
                "total_users": total_users,
                "total_products": total_products
            }
        })


class AdminUserListView(ListAPIView):
    queryset = User.objects.all().order_by("-date_joined")
    serializer_class = AdminUserListSerializer
    permission_classes = [IsAdminUser]


class AdminUserDeleteView(DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]

    def perform_destroy(self, instance):
        if instance.is_staff or instance.is_superuser:
            raise PermissionDenied("You cannot remove the admin or superuser.")
        instance.delete()


class ProductListCreateView(generics.ListCreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAdminUser]


class ProductRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAdminUser]


class ProductCategoryListCreateView(generics.ListCreateAPIView):
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAdminUser]


class ProductCategoryRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductCategory.objects.filter(is_active=True)
    serializer_class = ProductCategorySerializer
    permission_classes = [permissions.IsAdminUser]

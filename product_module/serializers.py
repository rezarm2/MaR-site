from rest_framework import serializers

from product_module.models import Product, ProductCategory


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = '__all__'


class ProductSerializer(serializers.ModelSerializer):
    categories = ProductCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=ProductCategory.objects.all(), write_only=True, source='categories'
    )
    is_active = serializers.BooleanField(default=True)

    class Meta:
        model = Product
        fields = ['id', 'title', 'slug', 'price', 'categories', 'description', 'category_ids', 'is_active', 'image']

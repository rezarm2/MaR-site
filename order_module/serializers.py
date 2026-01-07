from rest_framework import serializers
from order_module.models import Order, OrderDetail


class OrderSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'is_paid', 'payment_date', 'total_price']

    def get_total_price(self, obj):
        return obj.total_price


class OrderDetailSerializer(serializers.ModelSerializer):
    total_item_price = serializers.SerializerMethodField()
    final_price = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderDetail
        fields = '__all__'
        extra_kwargs = {'final_price': {'read_only': True}
                        }

    def get_total_item_price(self, obj):
        return (obj.final_price or 0) * obj.quantity

    def validate_quantity(self, value):
        try:
            quantity = int(value)
            if quantity <= 0:
                raise serializers.ValidationError("Quantity must be a positive integer.")
        except (ValueError, TypeError):
            raise serializers.ValidationError("Quantity must be a valid integer.")
        return quantity








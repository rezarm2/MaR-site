from rest_framework import viewsets, status
from rest_framework.response import Response
from product_module.models import Product

from order_module.models import OrderDetail, Order
from order_module.serializers import OrderDetailSerializer, OrderSerializer
# from product_module.views import ProductPaginationViewSet


# Create your views here.
class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    # pagination_class = ProductPaginationViewSet

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)


class OrderDetailViewSet(viewsets.ModelViewSet):
    queryset = OrderDetail.objects.all()
    serializer_class = OrderDetailSerializer
    # pagination_class = ProductPaginationViewSet

    def get_queryset(self):
        return OrderDetail.objects.filter(order__user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        order, _ = Order.objects.get_or_create(user=user, is_paid=False)
        product_id = request.data.get('product')
        quantity_input = request.data.get('quantity', 1)

        # اعتبارسنجی product_id
        if not product_id:
            return Response({'error': 'Product is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return Response({'error': 'Product not found'}, status=status.HTTP_404_NOT_FOUND)

        # اعتبارسنجی quantity
        try:
            quantity = int(quantity_input)
            if quantity <= 0:
                return Response({'error': 'Quantity must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError):
            return Response({'error': 'Invalid quantity value'}, status=status.HTTP_400_BAD_REQUEST)

        # چک وجود OrderDetail
        order_detail, created = OrderDetail.objects.get_or_create(
            order=order,
            product=product,
            defaults={'quantity': quantity, 'final_price': product.get_final_price()}
        )

        if not created:
            # آپدیت تعداد برای محصول موجود
            order_detail.quantity += quantity
            order_detail.save()
            return Response({'message': 'Quantity updated successfully'}, status=status.HTTP_200_OK)
        else:
            # محصول جدید قبلاً با defaults ذخیره شده
            serializer = self.get_serializer(order_detail)
            return Response({
                'message': 'Product added to cart',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
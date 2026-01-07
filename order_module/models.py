from django.conf import settings
from django.db import models
from user_module.models import User
from product_module.models import Product


# Create your models here.

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_paid = models.BooleanField()
    payment_date = models.DateField(null=True, blank=True)

    @property
    def total_price(self):
        return sum([(item.final_price or 0) * item.quantity for item in self.order_details.all()])

    def __str__(self):
        return str(self.user)

    class Meta:
        verbose_name = 'سبد خرید'
        verbose_name_plural = 'سبدهای خرید کاربران'


class OrderDetail(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_details')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    final_price = models.IntegerField(null=True, blank=True)
    quantity = models.IntegerField(verbose_name='تعداد')

    def save(self, *args, **kwargs):
        if self.final_price is None:
            if not self.product:
                raise ValueError("Product is required to calculate final_price.")
            self.final_price = self.product.get_final_price()
        super().save(*args, **kwargs)

    @property
    def total_item_price(self):
        return (self.final_price or 0) * self.quantity

    def __str__(self):
        return f"{self.order.user} - {self.product.title} x {self.quantity}"

    class Meta:
        verbose_name = 'جزییات سبد خرید'
        verbose_name_plural = 'لیست جزییات سبدهای خرید'

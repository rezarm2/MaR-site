from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/summary", views.AdminDashboardSummaryView.as_view()),
    path("users", views.AdminUserListView.as_view()),
    path("users/<int:pk>", views.AdminUserDeleteView.as_view()),
    path('products/', views.ProductListCreateView.as_view()),
    path('products/<int:pk>/', views.ProductRetrieveUpdateDestroyView.as_view()),
    path('products-category/', views.ProductCategoryListCreateView.as_view()),
    path('products-category/<int:pk>/', views.ProductCategoryRetrieveUpdateDestroyView.as_view()),
]

from django.urls import path
from . import views
app_name = 'catalog'



urlpatterns = [
    path('', views.category_list, name='category_list'),
    path('category/<slug:category_slug>/', views.product_list, name='product_list'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/update/<int:product_id>/', views.cart_update, name='cart_update'),
    path('cart/remove/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('checkout/', views.checkout, name='checkout'),  # Новый маршрут
    path('order/success/', views.order_success, name='order_success'),  # Для страницы успеха
]
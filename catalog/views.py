from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from .models import Category, Product, Cart, Order
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Cart, Order, Product
from decimal import Decimal
from datetime import date
from django.core.mail import send_mail
from django.conf import settings 
def category_list(request):
    categories = Category.objects.all()
    return render(request, "catalog/category_list.html", {"categories": categories})

def product_list(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    products = Product.objects.filter(category=category).select_related("category")
    return render(
        request,
        "catalog/product_list.html",
        {"category": category, "products": products},
    )

def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    images = product.images.all()
    return render(
        request, "catalog/product_detail.html", {"product": product, "images": images}
    )

@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity <= 0:
                raise ValueError("Количество должно быть больше 0")
        except (ValueError, TypeError):
            messages.error(request, "Некорректное количество")
            return render(
                request,
                "catalog/product_detail.html",
                {"product": product, "images": product.images.all()},
            )
        if quantity > product.quantity:
            messages.error(request, f"Недостаточно товара. В наличии: {product.quantity} шт.")
            return render(
                request,
                "catalog/product_detail.html",
                {"product": product, "images": product.images.all()},
            )
        cart, created = Cart.objects.get_or_create(user=request.user, product=product)
        cart.quantity += quantity
        cart.save()
        messages.success(request, f"{product.name} ({quantity} шт.) добавлен в корзину")
    return redirect("catalog:cart_detail")

@login_required
def cart_detail(request):
    cart_items = Cart.objects.filter(user=request.user).select_related("product")
    total = sum(item.get_item_total() for item in cart_items)  # Исправлено
    return render(
        request, "catalog/cart_detail.html", {"cart_items": cart_items, "total": total}
    )

@login_required
def cart_update(request, product_id):
    cart = get_object_or_404(Cart, user=request.user, product_id=product_id)
    if request.method == "POST":
        try:
            quantity = int(request.POST.get("quantity", 1))
            if quantity <= 0:
                cart.delete()
                messages.success(request, f"{cart.product.name} удален из корзины")
                return redirect("catalog:cart_detail")
            if quantity > cart.product.quantity:
                messages.error(request, f"Недостаточно товара. В наличии: {cart.product.quantity} шт.")
                return redirect("catalog:cart_detail")
            cart.quantity = quantity
            cart.save()
            messages.success(request, f"Количество {cart.product.name} обновлено")
        except (ValueError, TypeError):
            messages.error(request, "Некорректное количество")
    return redirect("catalog:cart_detail")

@login_required
def cart_remove(request, product_id):
    cart = get_object_or_404(Cart, user=request.user, product_id=product_id)
    product_name = cart.product.name
    cart.delete()
    messages.success(request, f"{product_name} удален из корзины")
    return redirect("catalog:cart_detail")

@login_required

def checkout(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        user = request.user if request.user.is_authenticated else None

        cart_items = Cart.objects.filter(user=request.user)
        if not cart_items.exists():
            messages.error(request, "Ваша корзина пуста.")
            return redirect('catalog:cart_detail')

        for item in cart_items:
            order = Order.objects.create(
                user=user,
                product=item.product,
                quantity=item.quantity,
                start_date=start_date,
                end_date=end_date,
                total_price=item.get_item_total(),
                name=name,
                phone=phone
            )

        # Очистка корзины
        cart_items.delete()

        # === Отправка письма ===
        subject = "Новый заказ"
        message = f"Имя: {name}\nТелефон: {phone}\nДата аренды: с {start_date} по {end_date}\nТовар: {item.product}\nКоличество: {item.quantity}\nОбщая цена: {item.get_item_total()} "
        recipient_list = ["your_email@example.com"]  # адрес получателя

        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

        messages.success(request, "Ваш заказ принят! Мы свяжемся с вами.")
        return redirect('catalog:cart_detail')

    return redirect('catalog:cart_detail')

@login_required
def order_success(request):
    return render(request, "catalog/order_success.html")
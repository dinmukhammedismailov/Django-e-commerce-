from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.utils import timezone

def validate_image(image):
    """Валидация изображений: минимальная проверка."""
    print(f"Validating image: {image.name}, size: {image.size}")
    max_size = 10 * 1024 * 1024  # 10MB
    if image.size > max_size:
        raise ValidationError("Размер изображения не должен превышать 10MB.")

class Category(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название категории")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="URL (slug)")
    image = models.ImageField(
        upload_to="categories/",
        validators=[validate_image],
        blank=True,
        null=True,
        verbose_name="Фото категории",
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        indexes = [models.Index(fields=["slug"])]

    def save(self, *args, **kwargs):
        if not self.slug or self.name != Category.objects.get(pk=self.pk).name if self.pk else True:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self):
        if not self.name.strip():
            raise ValidationError("Название категории не может быть пустым.")

    def __str__(self):
        return self.name

class Product(models.Model):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products", verbose_name="Категория"
    )
    name = models.CharField(max_length=255, verbose_name="Название товара")
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name="URL (slug)")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Цена за аренду (тенге)", validators=[MinValueValidator(0)]
    )
    quantity = models.PositiveIntegerField(default=0, verbose_name="Количество в наличии")
    image = models.ImageField(
        upload_to="products/", validators=[validate_image], blank=True, null=True, verbose_name="Фото"
    )
    status = models.CharField(
        max_length=20,
        choices=[("available", "В наличии"), ("rented", "Арендован"), ("unavailable", "Недоступен")],
        default="available",
        verbose_name="Статус"
    )
    material = models.CharField(max_length=100, blank=True, verbose_name="Материал")
    color = models.CharField(max_length=50, blank=True, verbose_name="Цвет")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        indexes = [models.Index(fields=["slug"]), models.Index(fields=["category"])]

    def save(self, *args, **kwargs):
        if not self.slug or self.name != Product.objects.get(pk=self.pk).name if self.pk else True:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self):
        existing = Product.objects.filter(category=self.category, name=self.name).exclude(pk=self.pk)
        if existing.exists():
            raise ValidationError("Товар с таким названием уже существует в этой категории.")
        if self.quantity == 0 and self.status == "available":
            self.status = "unavailable"

    def __str__(self):
        return f"{self.name} ({self.category.name})"

    def get_reserved_quantity(self, start_date, end_date):
        """Сколько единиц товара зарезервировано на заданный период."""
        overlapping_orders = self.order_set.filter(
            Q(start_date__lte=end_date) & Q(end_date__gte=start_date),
            status__in=["pending", "confirmed"]
        ).aggregate(total_reserved=Sum("quantity"))
        return overlapping_orders["total_reserved"] or 0

    def get_available_quantity(self, start_date, end_date):
        """Доступное количество товара на заданный период."""
        reserved = self.get_reserved_quantity(start_date, end_date)
        return self.quantity - reserved

class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="Товар"
    )
    image = models.ImageField(
        upload_to="product_images/", validators=[validate_image], verbose_name="Дополнительное фото"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")

    class Meta:
        verbose_name = "Дополнительное фото товара"
        verbose_name_plural = "Дополнительные фото товаров"

    def __str__(self):
        return f"Фото для {self.product.name}"

class Cart(models.Model):
    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, verbose_name="Пользователь")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(default=1, verbose_name="Количество")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        unique_together = ("user", "product")
        indexes = [models.Index(fields=["user"])]

    def clean(self):
        if self.quantity > self.product.quantity:
            raise ValidationError(
                f"Нельзя добавить {self.quantity} единиц. В наличии: {self.product.quantity}."
            )

    def get_item_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.user.username} - {self.product.name} ({self.quantity})"

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "В ожидании"),
        ("confirmed", "Подтвержден"),
        ("completed", "Завершен"),
        ("canceled", "Отменен"),
    ]

    user = models.ForeignKey(
        "auth.User", on_delete=models.SET_NULL, null=True, verbose_name="Пользователь"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Товар")
    quantity = models.PositiveIntegerField(verbose_name="Количество")
    start_date = models.DateField(verbose_name="Дата начала аренды")
    end_date = models.DateField(verbose_name="Дата окончания аренды")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="Статус"
    )
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Итоговая цена", validators=[MinValueValidator(0)]
    )
    name = models.CharField(max_length=255, verbose_name="Имя клиента", blank=True)
    phone = models.CharField(max_length=20, verbose_name="Телефон", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Обновлено")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        indexes = [models.Index(fields=["user"]), models.Index(fields=["start_date", "end_date"])]

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("Дата окончания аренды должна быть позже даты начала.")
        if self.quantity > self.product.get_available_quantity(self.start_date, self.end_date):
            available = self.product.get_available_quantity(self.start_date, self.end_date)
            raise ValidationError(
                f"Нельзя заказать {self.quantity} единиц. Доступно: {available}."
            )

    def restore_quantity(self):
        """Возвращает количество товара в инвентарь и завершает заказ."""
        if self.status in ["pending", "confirmed"]:
            self.product.quantity += self.quantity
            self.product.save()
            self.status = "completed"
            self.save()

    def __str__(self):
        return f"Заказ {self.id} - {self.user.username if self.user else 'Гость'}"
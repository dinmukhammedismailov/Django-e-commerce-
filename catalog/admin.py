from django.contrib import admin
from django.utils.html import mark_safe
from django.contrib.admin import DateFieldListFilter
from django.utils import timezone
from .models import Category, Product, ProductImage, Cart, Order
from django import forms

# Форма для действия set_image
class SetImageForm(forms.Form):
    image = forms.ImageField(
        label="Выберите изображение",
        help_text="Выберите JPEG или PNG файл (до 5MB) для установки на выбранные объекты."
    )

# Кастомная форма для Category
class CategoryAdminForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'description', 'image']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"Rendering Category form for: {self.instance.name if self.instance.pk else 'New Category'}")
        print(f"Form files: {self.files}")
        if self.instance and self.instance.image:
            self.fields['image'].help_text = mark_safe(
                f'<img src="{self.instance.image.url}" style="max-width:200px; max-height:200px; margin-top:10px;" /><br>'
                f'Текущее изображение: {self.instance.image.name}<br>'
                'Чтобы заменить, выберите новый файл. Чтобы удалить, отметьте "Clear".'
            )
        self.fields['image'].widget.attrs.update({
            'accept': 'image/jpeg,image/png',
        })

    def save(self, commit=True):
        print(f"Saving Category: {self.instance.name}, Image: {self.cleaned_data.get('image')}, Clear: {self.data.get('image-clear')}")
        instance = super().save(commit=False)
        if self.cleaned_data.get('image') is None and self.data.get('image-clear') == 'on':
            print("Clearing image for Category")
            instance.image = None
        if commit:
            instance.save()
        return instance

# Кастомная форма для Product
class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'slug', 'description', 'price', 'quantity', 'image', 'status', 'material', 'color']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"Rendering Product form for: {self.instance.name if self.instance.pk else 'New Product'}")
        print(f"Form files: {self.files}")
        if self.instance and self.instance.image:
            self.fields['image'].help_text = mark_safe(
                f'<img src="{self.instance.image.url}" style="max-width:200px; max-height:200px; margin-top:10px;" /><br>'
                f'Текущее изображение: {self.instance.image.name}<br>'
                'Чтобы заменить, выберите новый файл. Чтобы удалить, отметьте "Clear".'
            )
        self.fields['image'].widget.attrs.update({
            'accept': 'image/jpeg,image/png',
        })

    def save(self, commit=True):
        print(f"Saving Product: {self.instance.name}, Image: {self.cleaned_data.get('image')}, Clear: {self.data.get('image-clear')}")
        instance = super().save(commit=False)
        if self.cleaned_data.get('image') is None and self.data.get('image-clear') == 'on':
            print("Clearing image for Product")
            instance.image = None
        if commit:
            instance.save()
        return instance

# Фильтр для истекших заказов
class ExpiredOrdersFilter(admin.SimpleListFilter):
    title = "Истекшие заказы"
    parameter_name = "expired"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Истекшие"),
            ("no", "Не истекшие"),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == "yes":
            return queryset.filter(end_date__lt=today, status__in=["pending", "confirmed"])
        if self.value() == "no":
            return queryset.filter(end_date__gte=today)
        return queryset

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    list_display = ('name', 'slug', 'description', 'image_preview', 'created_at')
    list_editable = ('description',)
    list_display_links = ('name',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    fields = ('name', 'slug', 'description', 'image')
    list_filter = ('created_at',)
    actions = ['clear_images', 'set_image']

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        return "-"
    image_preview.short_description = 'Фото категории'

    def clear_images(self, request, queryset):
        updated = queryset.update(image=None)
        self.message_user(request, f"Удалено изображений: {updated}")
    clear_images.short_description = "Удалить фотографии у выбранных категорий"

    def set_image(self, request, queryset):
        print(f"Processing set_image action for {queryset.count()} categories")
        print(f"Request files: {request.FILES}")
        if request.POST.get('post'):
            form = SetImageForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data['image']
                print(f"Received image: {image.name}, size: {image.size}")
                for obj in queryset:
                    obj.image = image
                    obj.save()
                self.message_user(request, f"Изображение установлено для {queryset.count()} категорий")
            else:
                print(f"Form errors: {form.errors}")
                self.message_user(request, "Ошибка: выберите корректное изображение", level='error')
            return
        return self.get_action_form_response(request, SetImageForm())
    set_image.short_description = "Установить изображение для выбранных категорий"

    def get_action_form_response(self, request, form):
        from django.template.response import TemplateResponse
        context = self.admin_site.each_context(request)
        context['form'] = form
        context['queryset'] = self.get_queryset(request)
        context['action'] = 'set_image'
        return TemplateResponse(request, 'admin/set_image_action.html', context)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'category', 'price', 'quantity', 'status', 'image_preview', 'created_at')
    list_editable = ('price', 'quantity', 'status')
    list_display_links = ('name',)
    list_filter = ('category', 'status', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    fields = ('category', 'name', 'slug', 'description', 'price', 'quantity', 'image', 'status', 'material', 'color')
    autocomplete_fields = ['category'] if 'dal' in admin.site._registry else []
    actions = ['clear_images', 'set_image']

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        return "Нет изображения"
    image_preview.short_description = "Превью фото товара"

    def clear_images(self, request, queryset):
        updated = queryset.update(image=None)
        self.message_user(request, f"Удалено изображений: {updated}")
    clear_images.short_description = "Удалить фотографии у выбранных товаров"

    def set_image(self, request, queryset):
        print(f"Processing set_image action for {queryset.count()} products")
        print(f"Request files: {request.FILES}")
        
        if request.POST.get('post'):
            form = SetImageForm(request.POST, request.FILES)
            if form.is_valid():
                image = form.cleaned_data['image']
                print(f"Received image: {image.name}, size: {image.size}")
                for obj in queryset:
                    obj.image = image
                    obj.save()
                self.message_user(request, f"Изображение установлено для {queryset.count()} товаров")
            else:
                print(f"Form errors: {form.errors}")
                self.message_user(request, "Ошибка: выберите корректное изображение", level='error')
            return
        return self.get_action_form_response(request, SetImageForm())
    set_image.short_description = "Установить изображение для выбранных товаров"

    def get_action_form_response(self, request, form):
        from django.template.response import TemplateResponse
        context = self.admin_site.each_context(request)
        context['form'] = form
        context['queryset'] = self.get_queryset(request)
        context['action'] = 'set_image'
        return TemplateResponse(request, 'admin/set_image_action.html', context)

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview', 'created_at')
    search_fields = ('product__name',)
    list_filter = ('created_at',)

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="50" height="50" />')
        return "Нет изображения"
    image_preview.short_description = "Превью фото"

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'quantity', 'get_total_price', 'added_at')
    search_fields = ('user__username', 'product__name')
    list_filter = ('added_at',)

    def get_total_price(self, obj):
        return obj.get_item_total()
    get_total_price.short_description = "Общая стоимость"

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'quantity', 'start_date', 'end_date', 'status', 'total_price', 'created_at')
    list_editable = ('quantity', 'status')
    list_display_links = ('id',)
    search_fields = ('user__username', 'product__name', 'name', 'phone')
    list_filter = ('status', ('start_date', DateFieldListFilter), ('end_date', DateFieldListFilter), ExpiredOrdersFilter)
    actions = ['restore_inventory']
    fields = ('user', 'product', 'quantity', 'start_date', 'end_date', 'status', 'total_price', 'name', 'phone')
    autocomplete_fields = ['product', 'user'] if 'dal' in admin.site._registry else []

    def restore_inventory(self, request, queryset):
        for order in queryset:
            order.restore_quantity()
        self.message_user(request, "Количество товаров возвращено для выбранных заказов.")
    restore_inventory.short_description = "Вернуть количество товаров в инвентарь"
from django.db import models
from django.utils.text import slugify


class ProductSEO(models.Model):
    PRICE_DISPLAY_FORMAT_CHOICES = [
        ('from', 'From KES X'),
        ('starting', 'Starting at KES X'),
        ('plus', 'KES X+'),
        ('range', 'KES X – Y'),
    ]

    STOCK_DISPLAY_CHOICES = [
        ('in-stock-only', 'Show "In Stock" only'),
        ('always', 'Always show stock level'),
        ('low-stock', 'Show when low stock'),
        ('never', 'Never show'),
    ]

    product = models.OneToOneField('clientapp.Product', on_delete=models.CASCADE, related_name='seo')
    meta_title = models.CharField(max_length=60)
    meta_description = models.CharField(max_length=160)
    slug = models.SlugField(max_length=255, unique=True)
    auto_generate_slug = models.BooleanField(default=True)
    focus_keyword = models.CharField(max_length=100, blank=True)
    additional_keywords = models.TextField(blank=True)

    show_price = models.BooleanField(default=True)
    price_display_format = models.CharField(max_length=20, choices=PRICE_DISPLAY_FORMAT_CHOICES, default='from')
    show_stock_status = models.CharField(max_length=20, choices=STOCK_DISPLAY_CHOICES, default='in-stock-only')

    related_products = models.ManyToManyField('clientapp.Product', blank=True, related_name='related_to')
    upsell_products = models.ManyToManyField('clientapp.Product', blank=True, related_name='upsells_for')
    frequently_bought_together = models.ManyToManyField('clientapp.Product', blank=True, related_name='bundles_with')

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Product SEO'
        verbose_name_plural = 'Product SEO'

    def __str__(self):
        return f'SEO – {self.product.name}'

    def save(self, *args, **kwargs):
        if self.auto_generate_slug and not self.slug:
            self.slug = slugify(self.product.name)
        super().save(*args, **kwargs)


class ProductReviewSettings(models.Model):
    REVIEW_REMINDER_CHOICES = [
        ('3', '3 days after delivery'),
        ('7', '7 days after delivery'),
        ('14', '14 days after delivery'),
        ('30', '30 days after delivery'),
        ('never', 'Never'),
    ]

    product = models.OneToOneField('clientapp.Product', on_delete=models.CASCADE, related_name='review_settings')
    enable_reviews = models.BooleanField(default=True)
    require_purchase = models.BooleanField(default=True)
    auto_approve_reviews = models.BooleanField(default=False)
    review_reminder = models.CharField(max_length=10, choices=REVIEW_REMINDER_CHOICES, default='7')

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Product Review Settings'
        verbose_name_plural = 'Product Review Settings'

    def __str__(self):
        return f'Review Settings – {self.product.name}'


class ProductFAQ(models.Model):
    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'display_order']
        verbose_name = 'Product FAQ'
        verbose_name_plural = 'Product FAQs'

    def __str__(self):
        return f'{self.product.name} – FAQ {self.display_order}'


class ProductShipping(models.Model):
    SHIPPING_CLASS_CHOICES = [
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('overnight', 'Overnight'),
        ('fragile', 'Fragile'),
    ]

    HANDLING_TIME_UNIT_CHOICES = [
        ('hours', 'Hours'),
        ('days', 'Business Days'),
        ('weeks', 'Weeks'),
    ]

    product = models.OneToOneField('clientapp.Product', on_delete=models.CASCADE, related_name='shipping')

    shipping_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_weight_unit = models.CharField(max_length=5, default='kg')
    shipping_class = models.CharField(max_length=20, choices=SHIPPING_CLASS_CHOICES, default='standard')

    package_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_dimension_unit = models.CharField(max_length=5, default='cm')

    free_shipping = models.BooleanField(default=False)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    nairobi_only = models.BooleanField(default=False)
    kenya_only = models.BooleanField(default=False)
    no_international = models.BooleanField(default=False)

    handling_time = models.IntegerField(default=1)
    handling_time_unit = models.CharField(max_length=10, choices=HANDLING_TIME_UNIT_CHOICES, default='days')
    pickup_available = models.BooleanField(default=False)
    pickup_location = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Product Shipping'
        verbose_name_plural = 'Product Shipping'

    def __str__(self):
        return f'Shipping – {self.product.name}'


class ProductLegal(models.Model):
    RETURN_POLICY_CHOICES = [
        ('non-refundable', 'Non-refundable (custom items)'),
        ('7-days', '7 days'),
        ('14-days', '14 days'),
        ('30-days', '30 days'),
        ('custom', 'Custom policy'),
    ]

    product = models.OneToOneField('clientapp.Product', on_delete=models.CASCADE, related_name='legal')

    product_terms = models.TextField(blank=True)
    return_policy = models.CharField(max_length=30, choices=RETURN_POLICY_CHOICES, default='non-refundable')
    age_restriction = models.BooleanField(default=False)

    cert_fsc = models.BooleanField(default=False, verbose_name='FSC Certified Paper')
    cert_eco = models.BooleanField(default=False, verbose_name='Eco-Friendly')
    cert_food_safe = models.BooleanField(default=False, verbose_name='Food Safe')

    copyright_notice = models.TextField(blank=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Product Legal'
        verbose_name_plural = 'Product Legal'

    def __str__(self):
        return f'Legal – {self.product.name}'

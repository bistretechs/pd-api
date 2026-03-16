from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = [
        ('physical', 'Physical Product'),
        ('digital', 'Digital Product'),
        ('service', 'Service'),
    ]

    PRICING_MODE_CHOICES = [
        ('auto_calculate', 'Auto Calculate'),
        ('quote_only', 'Quote Only'),
    ]

    VISIBILITY_CHOICES = [
        ('catalog-search', 'Catalog and Search'),
        ('catalog-only', 'Catalog Only'),
        ('search-only', 'Search Only'),
        ('hidden', 'Hidden'),
    ]

    UNIT_CHOICES = [
        ('pieces', 'Pieces'),
        ('packs', 'Packs'),
        ('sets', 'Sets'),
        ('sqm', 'm²'),
        ('cm', 'Centimeters'),
    ]

    WEIGHT_UNIT_CHOICES = [
        ('gsm', 'GSM (g/m²)'),
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
    ]

    DIMENSION_UNIT_CHOICES = [
        ('cm', 'Centimeters'),
        ('mm', 'Millimeters'),
        ('in', 'Inches'),
    ]

    WARRANTY_CHOICES = [
        ('satisfaction-guarantee', 'Satisfaction Guarantee - Reprint if defective'),
        ('no-warranty', 'No Warranty'),
        ('30-days', '30 Days'),
        ('90-days', '90 Days'),
    ]

    COUNTRY_CHOICES = [
        ('kenya', 'Kenya'),
        ('china', 'China'),
        ('india', 'India'),
        ('uae', 'UAE'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    STOCK_STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('made_to_order', 'Made to Order'),
        ('discontinued', 'Discontinued'),
    ]

    # ── Identity ────────────────────────────────────────────────────────────
    name = models.CharField(max_length=255)
    internal_code = models.CharField(max_length=50, unique=True, blank=True)
    auto_generate_code = models.BooleanField(default=True, editable=False)
    short_description = models.CharField(max_length=150)
    long_description = models.TextField()
    maintenance = models.TextField(blank=True)
    technical_specs = models.TextField(blank=True)

    # ── Classification ───────────────────────────────────────────────────────
    print_category = models.ForeignKey(
        'clientapp.PrintCategory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products',
    )
    primary_category = models.ForeignKey(
        'clientapp.ProductCategory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products',
    )
    sub_category = models.ForeignKey(
        'clientapp.ProductSubCategory', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products',
    )
    product_family = models.ForeignKey(
        'clientapp.ProductFamily', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products',
    )
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='physical')
    tags = models.ManyToManyField('clientapp.ProductTag', blank=True, related_name='products')

    # ── Pricing mode ─────────────────────────────────────────────────────────
    pricing_mode = models.CharField(
        max_length=20, choices=PRICING_MODE_CHOICES, default='auto_calculate',
        help_text=(
            'auto_calculate: storefront computes price live from spec groups. '
            'quote_only: Production Team must manually price each request.'
        ),
    )

    # ── Status & Visibility ──────────────────────────────────────────────────
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_visible = models.BooleanField(default=True)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='catalog-search')
    feature_product = models.BooleanField(default=False)
    bestseller_badge = models.BooleanField(default=False)
    new_arrival = models.BooleanField(default=False)
    new_arrival_expires = models.DateField(null=True, blank=True)
    on_sale_badge = models.BooleanField(default=False)

    # ── Physical attributes ──────────────────────────────────────────────────
    unit_of_measure = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pieces')
    unit_of_measure_custom = models.CharField(max_length=50, blank=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight_unit = models.CharField(max_length=5, choices=WEIGHT_UNIT_CHOICES, default='kg')
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dimension_unit = models.CharField(max_length=5, choices=DIMENSION_UNIT_CHOICES, default='cm')
    warranty = models.CharField(max_length=50, choices=WARRANTY_CHOICES, default='satisfaction-guarantee')
    country_of_origin = models.CharField(max_length=50, choices=COUNTRY_CHOICES, default='kenya')

    # ── Inventory ────────────────────────────────────────────────────────────
    stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default='made_to_order')
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    track_inventory = models.BooleanField(default=False)
    allow_backorders = models.BooleanField(default=True)

    # ── Notes ────────────────────────────────────────────────────────────────
    internal_notes = models.TextField(blank=True)
    client_notes = models.TextField(blank=True)

    # ── Audit ────────────────────────────────────────────────────────────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_updated')

    class Meta:
        app_label = 'clientapp'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['internal_code']),
            models.Index(fields=['status', 'is_visible']),
        ]

    def __str__(self):
        return f'{self.internal_code} - {self.name}'

    def can_be_published(self):
        if self.pricing_mode == 'auto_calculate':
            active_groups = self.spec_groups.filter(is_active=True)
            if not active_groups.exists():
                return False, 'Auto-calculate products must have at least one active spec group before publishing.'
            if not active_groups.filter(group_type='quantity_tier').exists():
                return False, 'Auto-calculate products must have a Quantity Tier spec group before publishing.'
        return True, None

    def save(self, *args, **kwargs):
        skip_validation = kwargs.pop('skip_validation', False)

        if not skip_validation and self.status == 'published':
            can_publish, error_msg = self.can_be_published()
            if not can_publish:
                raise ValidationError(error_msg)

        if self.auto_generate_code or not self.internal_code:
            name_words = self.name.split()
            if len(name_words) >= 2:
                prefix = f'PRD-{name_words[0][:2].upper()}{name_words[1][:2].upper()}'
            else:
                prefix = f'PRD-{self.name[:3].upper()}'

            last = Product.objects.filter(internal_code__startswith=prefix).order_by('-internal_code').first()
            if last:
                try:
                    new_num = int(last.internal_code.split('-')[-1]) + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1

            self.internal_code = f'{prefix}-{new_num:03d}'

        super().save(*args, **kwargs)

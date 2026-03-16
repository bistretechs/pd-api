from django.db import models
from django.utils.text import slugify
from django import forms


def _unique_slug(model_class, base_slug: str, exclude_pk=None) -> str:
    slug = base_slug
    counter = 2
    qs = model_class.objects.all()
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def _unique_slug_scoped(model_class, category_id, base_slug: str, exclude_pk=None) -> str:
    slug = base_slug
    counter = 2
    qs = model_class.objects.filter(category_id=category_id)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name_plural = 'Product Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(ProductCategory, slugify(self.name), self.pk)
        super().save(*args, **kwargs)


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'slug', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Category Name'}),
            'slug': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'slug-name'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3}),
        }


class ProductSubCategory(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name_plural = 'Product Sub-Categories'
        ordering = ['category', 'name']
        unique_together = ['category', 'slug']

    def __str__(self):
        return f'{self.category.name} - {self.name}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug_scoped(
                ProductSubCategory, self.category_id, slugify(self.name), self.pk
            )
        super().save(*args, **kwargs)


class ProductFamily(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name_plural = 'Product Families'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(ProductFamily, slugify(self.name), self.pk)
        super().save(*args, **kwargs)


class ProductTag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(ProductTag, slugify(self.name), self.pk)
        super().save(*args, **kwargs)


class PrintCategory(models.Model):
    """
    Controls the frontend configurator type and pre-fills default production
    specs (bleed, DPI, colour profile) when creating a product.
    """
    PRODUCTION_METHOD_CHOICES = [
        ('digital_offset', 'Digital Offset Printing'),
        ('offset', 'Offset Printing'),
        ('screen', 'Screen Printing'),
        ('digital', 'Digital Printing'),
        ('large_format', 'Large Format Printing'),
        ('embroidery', 'Embroidery'),
        ('sublimation', 'Sublimation'),
        ('laser_engraving', 'Laser Engraving'),
        ('uv_printing', 'UV Printing'),
        ('other', 'Other'),
    ]

    COLOR_PROFILE_CHOICES = [
        ('cmyk', 'CMYK (Print Standard)'),
        ('rgb', 'RGB (Digital)'),
        ('pantone', 'Pantone Spot Colors'),
        ('cmyk_pantone', 'CMYK + Pantone'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)

    default_bleed_mm = models.DecimalField(max_digits=5, decimal_places=1, default=3.0)
    default_safe_zone_mm = models.DecimalField(max_digits=5, decimal_places=1, default=5.0)
    default_min_dpi = models.IntegerField(default=300)
    default_color_profile = models.CharField(max_length=20, choices=COLOR_PROFILE_CHOICES, default='cmyk')
    default_production_method = models.CharField(max_length=50, choices=PRODUCTION_METHOD_CHOICES, default='digital_offset')

    # Spec groups suggested when building products of this category
    suggested_library_groups = models.ManyToManyField(
        'clientapp.SpecGroupLibrary',
        blank=True,
        related_name='suggested_for_categories',
    )

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Print Category'
        verbose_name_plural = 'Print Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(PrintCategory, slugify(self.name), self.pk)
        super().save(*args, **kwargs)

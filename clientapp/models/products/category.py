from django.db import models
from django.utils.text import slugify
from django import forms


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
            self.slug = slugify(self.name)
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

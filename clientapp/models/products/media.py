from django.db import models


class ProductImage(models.Model):
    IMAGE_TYPE_CHOICES = [
        ('product-photo', 'Product Photo'),
        ('detail', 'Detail/Close-up'),
        ('mockup', 'Mockup/In-Use'),
        ('size-comparison', 'Size Comparison'),
        ('sample', 'Sample/Example'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/%Y/%m/')
    alt_text = models.CharField(max_length=255)
    caption = models.CharField(max_length=255, blank=True)
    image_type = models.CharField(max_length=30, choices=IMAGE_TYPE_CHOICES, default='product-photo')
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)

    associated_spec_option = models.ForeignKey(
        'clientapp.SpecOption', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='images',
        help_text='Show this image only when the linked spec option is selected.',
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'display_order']
        verbose_name = 'Product Image'

    def __str__(self):
        return f'{self.product.name} – Image {self.display_order}'

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductVideo(models.Model):
    VIDEO_TYPE_CHOICES = [
        ('demo', 'Product Demo'),
        ('tutorial', 'Tutorial'),
        ('review', 'Customer Review'),
        ('unboxing', 'Unboxing'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='videos')
    video_url = models.URLField()
    video_type = models.CharField(max_length=20, choices=VIDEO_TYPE_CHOICES, default='demo')
    thumbnail = models.ImageField(upload_to='products/video_thumbnails/%Y/%m/', blank=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'display_order']
        verbose_name = 'Product Video'

    def __str__(self):
        return f'{self.product.name} – {self.get_video_type_display()}'


class ProductDownloadableFile(models.Model):
    FILE_TYPE_CHOICES = [
        ('illustrator', 'Adobe Illustrator'),
        ('pdf', 'PDF'),
        ('psd', 'Photoshop'),
        ('indd', 'InDesign'),
        ('zip', 'ZIP Archive'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='downloadable_files')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='products/downloads/%Y/%m/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(editable=False, default=0)
    display_order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'display_order']
        verbose_name = 'Downloadable File'

    def __str__(self):
        return f'{self.product.name} – {self.file_name}'

    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class ProductTemplate(models.Model):
    """Design templates available for a product."""

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to='templates/')
    thumbnail = models.ImageField(upload_to='templates/thumbnails/', blank=True)
    category_tags = models.CharField(max_length=500, blank=True, help_text='Comma-separated tags.')
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['-created_at']
        verbose_name = 'Product Template'

    def __str__(self):
        return f'{self.product.name} – {self.name}'

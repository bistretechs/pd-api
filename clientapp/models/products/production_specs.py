from django.db import models


class ProductProduction(models.Model):
    """Production-specific settings and pre-press specs for a product."""

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

    product = models.OneToOneField('clientapp.Product', on_delete=models.CASCADE, related_name='production')

    # ── Production method ────────────────────────────────────────────────────
    production_method_detail = models.CharField(max_length=100, choices=PRODUCTION_METHOD_CHOICES, default='digital_offset')
    machine_equipment = models.CharField(max_length=100, blank=True)

    # ── Pre-press specs ───────────────────────────────────────────────────────
    color_profile = models.CharField(max_length=20, choices=COLOR_PROFILE_CHOICES, default='cmyk')
    bleed_mm = models.DecimalField(max_digits=5, decimal_places=1, default=3.0)
    safe_zone_mm = models.DecimalField(max_digits=5, decimal_places=1, default=5.0)
    min_resolution_dpi = models.IntegerField(default=300)
    max_ink_coverage = models.IntegerField(default=280)
    requires_outlined_fonts = models.BooleanField(default=True)
    accepts_transparency = models.BooleanField(default=False)

    # ── Finishing options ─────────────────────────────────────────────────────
    finish_lamination = models.BooleanField(default=False, verbose_name='Lamination')
    finish_uv_coating = models.BooleanField(default=False, verbose_name='UV Coating')
    finish_embossing = models.BooleanField(default=False, verbose_name='Embossing')
    finish_debossing = models.BooleanField(default=False, verbose_name='Debossing')
    finish_foil_stamping = models.BooleanField(default=False, verbose_name='Foil Stamping')
    finish_die_cutting = models.BooleanField(default=False, verbose_name='Die Cutting')
    finish_folding = models.BooleanField(default=False, verbose_name='Folding')
    finish_binding = models.BooleanField(default=False, verbose_name='Binding')
    finish_perforation = models.BooleanField(default=False, verbose_name='Perforation')
    finish_scoring = models.BooleanField(default=False, verbose_name='Scoring')

    # ── QC requirements ───────────────────────────────────────────────────────
    qc_color_match = models.BooleanField(default=True, verbose_name='Color Match Check')
    qc_registration = models.BooleanField(default=True, verbose_name='Registration Check')
    qc_cutting_accuracy = models.BooleanField(default=True, verbose_name='Cutting Accuracy Check')
    qc_finish_quality = models.BooleanField(default=True, verbose_name='Finish Quality Check')

    # ── Pre-production checklist ──────────────────────────────────────────────
    checklist_artwork = models.BooleanField(default=False, verbose_name='Client artwork approved')
    checklist_preflight = models.BooleanField(default=False, verbose_name='Pre-flight check passed')
    checklist_material = models.BooleanField(default=False, verbose_name='Material in stock')
    checklist_proofs = models.BooleanField(default=False, verbose_name='Color proofs confirmed')

    # ── Bill of materials (simplified flat BOM) ───────────────────────────────
    bom_primary_material = models.CharField(max_length=200, blank=True)
    bom_primary_size = models.CharField(max_length=100, blank=True)
    bom_primary_quantity_per_unit = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    bom_primary_unit = models.CharField(max_length=20, blank=True)

    bom_secondary_material = models.CharField(max_length=200, blank=True)
    bom_secondary_size = models.CharField(max_length=100, blank=True)
    bom_secondary_quantity_per_unit = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    bom_secondary_unit = models.CharField(max_length=20, blank=True)

    bom_ink_coverage_sqm = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    production_notes = models.TextField(blank=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Product Production Settings'
        verbose_name_plural = 'Product Production Settings'

    def __str__(self):
        return f'Production – {self.product.name}'

    def get_finishing_options(self) -> list[str]:
        finish_map = {
            'finish_lamination': 'Lamination',
            'finish_uv_coating': 'UV Coating',
            'finish_embossing': 'Embossing',
            'finish_debossing': 'Debossing',
            'finish_foil_stamping': 'Foil Stamping',
            'finish_die_cutting': 'Die Cutting',
            'finish_folding': 'Folding',
            'finish_binding': 'Binding',
            'finish_perforation': 'Perforation',
            'finish_scoring': 'Scoring',
        }
        return [label for field, label in finish_map.items() if getattr(self, field)]

    def get_qc_requirements(self) -> list[str]:
        qc_map = {
            'qc_color_match': 'Color Match',
            'qc_registration': 'Registration',
            'qc_cutting_accuracy': 'Cutting Accuracy',
            'qc_finish_quality': 'Finish Quality',
        }
        return [label for field, label in qc_map.items() if getattr(self, field)]


class ProductMaterialLink(models.Model):
    """
    Links a finished product to raw materials in inventory.
    Enables automatic stock deduction when products are produced.
    """
    MATERIAL_TYPE_CHOICES = [
        ('primary', 'Primary Material'),
        ('secondary', 'Secondary Material'),
        ('consumable', 'Consumable (Ink, etc.)'),
        ('packaging', 'Packaging'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='material_links')
    material = models.ForeignKey('clientapp.MaterialInventory', on_delete=models.CASCADE, related_name='product_links')
    quantity_per_product = models.DecimalField(max_digits=10, decimal_places=4, default=1.0)
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, default='primary')
    notes = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'material_type']
        unique_together = ['product', 'material']
        verbose_name = 'Product–Material Link'
        verbose_name_plural = 'Product–Material Links'

    def __str__(self):
        return f'{self.product.internal_code} → {self.material.material_name}'

    def calculate_material_needed(self, product_quantity: int):
        return self.quantity_per_product * product_quantity

    def check_material_availability(self, product_quantity: int) -> bool:
        needed = self.calculate_material_needed(product_quantity)
        return self.material.available_stock >= needed

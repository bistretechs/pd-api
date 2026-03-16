from decimal import Decimal

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

SPEC_GROUP_TYPE_CHOICES = [
    ('quantity_tier', 'Quantity Tier'),
    ('single_select_modifier', 'Single Select Modifier'),
    ('multi_select_modifier', 'Multi Select Modifier'),
    ('numeric_input', 'Numeric Input'),
    ('dimension_input', 'Dimension Input (W × H)'),
    ('multiplier', 'Multiplier'),
    ('display_only', 'Display Only'),
]

LIBRARY_STATUS_CHOICES = [
    ('active', 'Active'),
    ('draft', 'Draft'),
    ('archived', 'Archived'),
]


class SpecGroupLibrary(models.Model):
    """
    Reusable spec group definitions shared across products.
    Examples: "Turnaround Time", "Delivery Options", "Paper Side Options".
    Products can attach a library group and either use its library options
    directly or define their own overriding options.
    """
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True)
    group_type = models.CharField(max_length=30, choices=SPEC_GROUP_TYPE_CHOICES)
    display_label = models.CharField(
        max_length=150, blank=True,
        help_text='Customer-facing label. Defaults to name if blank.',
    )
    help_text = models.CharField(max_length=500, blank=True)
    is_required = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=LIBRARY_STATUS_CHOICES, default='active')

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='library_groups_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clientapp'
        verbose_name = 'Spec Group Library'
        verbose_name_plural = 'Spec Group Libraries'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_group_type_display()})'

    def get_display_label(self) -> str:
        return self.display_label or self.name


class SpecGroupLibraryOption(models.Model):
    """Default options bundled with a library spec group."""
    library_group = models.ForeignKey(SpecGroupLibrary, on_delete=models.CASCADE, related_name='library_options')
    name = models.CharField(max_length=200)
    display_order = models.IntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    preview_image = models.ImageField(upload_to='spec_groups/library_options/%Y/%m/', null=True, blank=True, help_text='Swatch or preview image shown on the storefront')

    # Quantity tier
    quantity_value = models.IntegerField(null=True, blank=True)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Modifier types
    selling_price_modifier = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor_cost_modifier = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Multiplier type
    multiplier_value = models.DecimalField(max_digits=6, decimal_places=4, null=True, blank=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['library_group', 'display_order']
        verbose_name = 'Spec Group Library Option'

    def __str__(self):
        return f'{self.library_group.name} › {self.name}'


class ProductSpecGroup(models.Model):
    """
    A spec group attached to a specific product.
    Can be linked to a SpecGroupLibrary group (inheriting its type and defaults)
    or be entirely custom.
    """
    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='spec_groups')
    library_group = models.ForeignKey(
        SpecGroupLibrary, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='product_usages',
        help_text='Link to a library group. Leave blank for a product-custom group.',
    )
    uses_library_options = models.BooleanField(
        default=False,
        help_text='When True, the storefront uses library options instead of product-level SpecOptions.',
    )

    name = models.CharField(max_length=150)
    display_label = models.CharField(max_length=150, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    group_type = models.CharField(max_length=30, choices=SPEC_GROUP_TYPE_CHOICES)
    is_required = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    parent_option = models.ForeignKey(
        'SpecOption', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_spec_groups',
        help_text='Show this group only when the parent option is selected (conditional logic).',
    )
    header_image = models.ImageField(upload_to='spec_groups/headers/%Y/%m/', null=True, blank=True, help_text='Illustrative diagram or image shown above the group on the storefront')

    # ── Dimension-input-specific ─────────────────────────────────────────────
    DIM_UNIT_CHOICES = [('mm', 'mm'), ('cm', 'cm'), ('in', 'inches')]

    dim_unit = models.CharField(max_length=5, choices=DIM_UNIT_CHOICES, default='mm', blank=True)
    dim_width_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dim_width_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dim_height_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dim_height_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    selling_rate_per_sqm = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    vendor_rate_per_sqm = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    min_selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_vendor_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'display_order']
        verbose_name = 'Product Spec Group'

    def __str__(self):
        return f'{self.product.internal_code} › {self.name}'

    def get_display_label(self) -> str:
        return self.display_label or self.name


class SpecOption(models.Model):
    """
    A single selectable option within a ProductSpecGroup.
    Carries the selling price and vendor cost for its contribution to the total.
    """
    spec_group = models.ForeignKey(ProductSpecGroup, on_delete=models.CASCADE, related_name='options')
    library_option = models.ForeignKey(
        SpecGroupLibraryOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='product_option_overrides',
    )
    name = models.CharField(max_length=200)
    display_order = models.IntegerField(default=0)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # ── quantity_tier ─────────────────────────────────────────────────────────
    quantity_value = models.IntegerField(
        null=True, blank=True,
        help_text='The quantity this tier represents (e.g. 100, 500, 1000).',
    )
    selling_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    vendor_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ── single/multi-select modifier ─────────────────────────────────────────
    selling_price_modifier = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Amount added to selling total when this option is selected.',
    )
    vendor_cost_modifier = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Amount added to vendor cost when this option is selected.',
    )

    # ── multiplier ───────────────────────────────────────────────────────────
    multiplier_value = models.DecimalField(
        max_digits=6, decimal_places=4, null=True, blank=True,
        help_text='Multiplied against the current subtotal (e.g. 1.50 = +50%).',
    )
    preview_image = models.ImageField(upload_to='spec_groups/options/%Y/%m/', null=True, blank=True, help_text='Swatch or preview image shown on the storefront for this option')

    class Meta:
        app_label = 'clientapp'
        ordering = ['spec_group', 'display_order']
        verbose_name = 'Spec Option'

    def __str__(self):
        return f'{self.spec_group.name} › {self.name}'


class SpecOptionRange(models.Model):
    """
    Pricing ranges for numeric_input spec groups.
    When a customer types a number (e.g. stitch count, meters), the system
    finds the matching range and calculates:
        price = selling_price_base + (input_value × selling_rate_per_unit)
    """
    spec_group = models.ForeignKey(
        ProductSpecGroup, on_delete=models.CASCADE, related_name='ranges',
    )
    range_from = models.DecimalField(max_digits=12, decimal_places=2)
    range_to = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Leave blank for open-ended upper bound.',
    )
    unit_label = models.CharField(max_length=50, blank=True, help_text='e.g. "stitches", "meters".')

    selling_price_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    selling_rate_per_unit = models.DecimalField(max_digits=12, decimal_places=4, default=0)
    vendor_cost_base = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vendor_rate_per_unit = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    display_order = models.IntegerField(default=0)

    class Meta:
        app_label = 'clientapp'
        ordering = ['spec_group', 'display_order', 'range_from']
        verbose_name = 'Spec Option Range'

    def __str__(self):
        upper = f'–{self.range_to}' if self.range_to is not None else '+'
        return f'{self.spec_group.name} [{self.range_from}{upper}]'

    def contains(self, value: Decimal) -> bool:
        if value < self.range_from:
            return False
        if self.range_to is not None and value > self.range_to:
            return False
        return True


class ProductCompatibilityRule(models.Model):
    """
    Defines conditional constraints between spec options.
    Replaces the old ProductRule model with proper FK-based relationships.

    Examples:
      - "When Paper = 400gsm REQUIRES Lamination = Matt or Gloss"
      - "When Size = A0 EXCLUDES Turnaround = Same Day"
    """
    RULE_TYPE_CHOICES = [
        ('requires', 'Requires'),
        ('excludes', 'Excludes'),
        ('min_value', 'Minimum Value'),
        ('max_value', 'Maximum Value'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='compatibility_rules')
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES)

    condition_spec_group = models.ForeignKey(
        ProductSpecGroup, on_delete=models.CASCADE, related_name='condition_rules',
    )
    condition_option = models.ForeignKey(
        SpecOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='condition_rules',
        help_text='If null, the rule applies when any option in the condition group is selected.',
    )

    target_spec_group = models.ForeignKey(
        ProductSpecGroup, on_delete=models.CASCADE, related_name='target_rules',
    )
    target_option = models.ForeignKey(
        SpecOption, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='target_rules',
        help_text='If null, the rule applies to any option in the target group.',
    )

    error_message = models.CharField(
        max_length=500, blank=True,
        help_text='Message shown to the customer when this rule is violated.',
    )
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['product', 'priority']
        verbose_name = 'Product Compatibility Rule'

    def __str__(self):
        condition = str(self.condition_option or self.condition_spec_group)
        target = str(self.target_option or self.target_spec_group)
        return f'{self.product.internal_code}: {condition} {self.get_rule_type_display()} {target}'


# ── Pricing Calculator ────────────────────────────────────────────────────────

class PriceCalculationResult:
    def __init__(self):
        self.selling_price: Decimal = Decimal('0')
        self.vendor_cost: Decimal = Decimal('0')
        self.multiplier: Decimal = Decimal('1')
        self.line_items: list[dict] = []
        self.errors: list[str] = []

    @property
    def final_selling_price(self) -> Decimal:
        return (self.selling_price * self.multiplier).quantize(Decimal('0.01'))

    @property
    def final_vendor_cost(self) -> Decimal:
        return (self.vendor_cost * self.multiplier).quantize(Decimal('0.01'))

    @property
    def margin_percent(self) -> Decimal:
        if self.final_selling_price == 0:
            return Decimal('0')
        return ((self.final_selling_price - self.final_vendor_cost) / self.final_selling_price * 100).quantize(Decimal('0.01'))


def _is_group_visible(group, selections: dict) -> bool:
    if group.parent_option_id is None:
        return True
    trigger_id = group.parent_option_id
    for value in selections.values():
        if isinstance(value, list):
            if trigger_id in value:
                return True
        elif value == trigger_id:
            return True
    return False


def calculate_product_price(
    product: 'clientapp.Product',
    selections: dict,
) -> PriceCalculationResult:
    """
    Compute the selling price and vendor cost given a dict of customer selections.

    selections format:
        {
            <spec_group_id>: <option_id or list[option_id] or numeric_value or {'width': w, 'height': h}>,
            ...
        }
    """
    result = PriceCalculationResult()

    active_groups = (
        product.spec_groups
        .filter(is_active=True)
        .prefetch_related('options', 'ranges')
        .order_by('display_order')
    )

    for group in active_groups:
        if not _is_group_visible(group, selections):
            continue
        group_selection = selections.get(group.id)
        group_type = group.group_type

        if group_type == 'quantity_tier':
            if group_selection is None:
                result.errors.append(f'No quantity selected for "{group.get_display_label()}".')
                continue
            option = group.options.filter(id=group_selection, is_active=True).first()
            if option is None:
                result.errors.append(f'Invalid quantity option for "{group.get_display_label()}".')
                continue
            sell = option.selling_price or Decimal('0')
            cost = option.vendor_cost or Decimal('0')
            result.selling_price += sell
            result.vendor_cost += cost
            result.line_items.append({
                'description': f'{group.name}: {option.name}',
                'selling_price': str(sell),
                'vendor_cost': str(cost),
            })

        elif group_type in ('single_select_modifier', 'multi_select_modifier'):
            selected_ids = group_selection if isinstance(group_selection, list) else ([group_selection] if group_selection else [])
            if not selected_ids and group.is_required:
                result.errors.append(f'"{group.get_display_label()}" is required.')
                continue
            for option_id in selected_ids:
                option = group.options.filter(id=option_id, is_active=True).first()
                if option is None:
                    result.errors.append(f'Invalid option selected for "{group.get_display_label()}".')
                    continue
                sell = option.selling_price_modifier or Decimal('0')
                cost = option.vendor_cost_modifier or Decimal('0')
                result.selling_price += sell
                result.vendor_cost += cost
                result.line_items.append({
                    'description': f'{group.name}: {option.name}',
                    'selling_price': str(sell),
                    'vendor_cost': str(cost),
                })

        elif group_type == 'numeric_input':
            if group_selection is None:
                if group.is_required:
                    result.errors.append(f'"{group.get_display_label()}" requires a numeric value.')
                continue
            input_value = Decimal(str(group_selection))
            matching_range = next((r for r in group.ranges.all() if r.contains(input_value)), None)
            if matching_range is None:
                result.errors.append(f'Value {input_value} is out of range for "{group.get_display_label()}".')
                continue
            sell = matching_range.selling_price_base + input_value * matching_range.selling_rate_per_unit
            cost = matching_range.vendor_cost_base + input_value * matching_range.vendor_rate_per_unit
            result.selling_price += sell
            result.vendor_cost += cost
            result.line_items.append({
                'description': f'{group.name}: {input_value}',
                'selling_price': str(sell),
                'vendor_cost': str(cost),
            })

        elif group_type == 'dimension_input':
            if group_selection is None:
                if group.is_required:
                    result.errors.append(f'"{group.get_display_label()}" requires dimensions.')
                continue
            width = Decimal(str(group_selection.get('width', 0)))
            height = Decimal(str(group_selection.get('height', 0)))

            sqm_divisor = Decimal('1000000') if group.dim_unit == 'mm' else (Decimal('10000') if group.dim_unit == 'cm' else Decimal('1550'))
            sqm = (width * height / sqm_divisor).quantize(Decimal('0.0001'))

            sell = max(group.min_selling_price or Decimal('0'), sqm * (group.selling_rate_per_sqm or Decimal('0')))
            cost = max(group.min_vendor_cost or Decimal('0'), sqm * (group.vendor_rate_per_sqm or Decimal('0')))
            result.selling_price += sell
            result.vendor_cost += cost
            result.line_items.append({
                'description': f'{group.name}: {width}×{height} {group.dim_unit}',
                'selling_price': str(sell),
                'vendor_cost': str(cost),
            })

        elif group_type == 'multiplier':
            if group_selection is None:
                continue
            option = group.options.filter(id=group_selection, is_active=True).first()
            if option is not None and option.multiplier_value:
                result.multiplier *= option.multiplier_value

    return result

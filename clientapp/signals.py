"""
Django signals for automatic change tracking in Product Catalog
Implements ProductChangeHistory entry creation for ALL product field changes
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.apps import AppConfig
from clientapp.models import Product, ProductChangeHistory, ProductPricing, ProductSEO
import json
from decimal import Decimal

# Track previous values before save
_product_previous_values = {}


# ──────────────────────────────────────────────
# Vendor Performance Score — auto-recalculate
# ──────────────────────────────────────────────

@receiver(post_save, sender='clientapp.PurchaseOrder')
def recalculate_vps_on_purchase_order_save(sender, instance, **kwargs):
    vendor = getattr(instance, 'vendor', None)
    if vendor is not None:
        vendor.update_performance_score()


@receiver(post_save, sender='clientapp.QCInspection')
def recalculate_vps_on_qc_inspection_save(sender, instance, **kwargs):
    vendor = getattr(instance, 'vendor', None)
    if vendor is not None:
        vendor.update_performance_score()

@receiver(pre_save, sender=Product)
def track_product_changes_pre_save(sender, instance, **kwargs):
    """
    Pre-save signal to capture product values before they change
    Stores in module-level dict for comparison in post_save
    """
    if instance.pk:  # Only for updates, not creates
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            _product_previous_values[instance.pk] = {
                'name': old_instance.name,
                'short_description': old_instance.short_description,
                'long_description': old_instance.long_description,
                'technical_specs': old_instance.technical_specs,
                'customization_level': old_instance.customization_level,
                'primary_category': old_instance.primary_category,
                'sub_category': old_instance.sub_category,
                'product_family': old_instance.product_family,
                'visibility': old_instance.visibility,
                'feature_product': old_instance.feature_product,
                'bestseller_badge': old_instance.bestseller_badge,
                'new_arrival': old_instance.new_arrival,
                'base_price': str(old_instance.base_price) if old_instance.base_price else None,
                'status': old_instance.status,
                'internal_code': old_instance.internal_code,
            }
        except Product.DoesNotExist:
            pass

@receiver(post_save, sender=Product)
def create_change_history_for_product(sender, instance, created, **kwargs):
    """
    Post-save signal to create ProductChangeHistory entries
    Tracks changes to all product fields automatically
    """
    from django.utils import timezone
    
    # Skip if this is a create (not an update)
    if created:
        return
    
    # Get changed_by user (set by the view or model)
    changed_by = getattr(instance, '_changed_by', None)
    if not changed_by:
        # Fall back to updated_by or created_by
        changed_by = instance.updated_by or instance.created_by
    
    # Get previous values
    previous_values = _product_previous_values.pop(instance.pk, {})
    if not previous_values:
        return  # No changes tracked
    
    # Check each field for changes
    fields_to_track = [
        'name', 'short_description', 'long_description', 'technical_specs',
        'customization_level', 'primary_category', 'sub_category', 'product_family',
        'visibility', 'feature_product', 'bestseller_badge', 'new_arrival',
        'base_price', 'status', 'internal_code'
    ]
    
    for field in fields_to_track:
        old_value = previous_values.get(field)
        new_value = getattr(instance, field, None)
        
        # Convert to strings for comparison
        old_str = str(old_value) if old_value is not None else ''
        new_str = str(new_value) if new_value is not None else ''
        
        # Skip if no actual change
        if old_str == new_str:
            continue
        
        # Create change history entry
        ProductChangeHistory.objects.create(
            product=instance,
            changed_by=changed_by,
            change_type='update',
            field_changed=field,
            old_value=old_str[:255] if old_str else '',  # Truncate to fit in DB
            new_value=new_str[:255] if new_str else '',
            changed_at=timezone.now()
        )

@receiver(post_save, sender=ProductPricing)
def create_change_history_for_pricing(sender, instance, created, **kwargs):
    """
    Track changes to pricing information
    """
    from django.utils import timezone
    
    # Get the product's user
    changed_by = instance.product.updated_by or instance.product.created_by
    
    if created:
        # Log pricing creation
        ProductChangeHistory.objects.create(
            product=instance.product,
            changed_by=changed_by,
            change_type='update',
            field_changed='pricing_created',
            old_value='',
            new_value='Pricing configuration added',
            changed_at=timezone.now()
        )
    else:
        # Log pricing updates
        fields_to_track = ['base_cost', 'return_margin', 'lead_time_value', 'lead_time_unit']
        for field in fields_to_track:
            # We could enhance this with pre_save signal to get old values
            ProductChangeHistory.objects.create(
                product=instance.product,
                changed_by=changed_by,
                change_type='update',
                field_changed=f'pricing_{field}',
                old_value='',
                new_value=str(getattr(instance, field, '')),
                changed_at=timezone.now()
            )

class ClientAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clientapp'
    
    def ready(self):
        """
        Import signals when app is ready
        This ensures signals are registered when Django starts
        """
        import clientapp.signals  # noqa


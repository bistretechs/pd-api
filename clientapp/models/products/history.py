from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ProductChangeHistory(models.Model):
    """Audit trail for every change made to a product."""

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='change_history')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    change_type = models.CharField(max_length=50)
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['-changed_at']
        verbose_name = 'Product Change History'
        verbose_name_plural = 'Product Change History'

    def __str__(self):
        return f'{self.product.internal_code} – {self.change_type} at {self.changed_at}'


class ProductApprovalRequest(models.Model):
    """Approval workflow for sensitive product changes."""

    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('auto_approved', 'Auto-Approved'),
    ]

    REQUEST_TYPE_CHOICES = [
        ('price_change', 'Price Change'),
        ('margin_change', 'Margin Adjustment'),
        ('category_change', 'Category Change'),
        ('visibility_change', 'Visibility Change'),
        ('publish', 'Publish Product'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='approval_requests')
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='product_approval_requests_made')
    requested_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_approval_requests_assigned')

    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='product_approval_requests_approved')
    approved_at = models.DateTimeField(null=True, blank=True)

    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    reason_for_change = models.TextField(blank=True)
    approval_notes = models.TextField(blank=True)
    is_urgent = models.BooleanField(default=False)

    class Meta:
        app_label = 'clientapp'
        ordering = ['-requested_at']
        verbose_name = 'Product Approval Request'
        verbose_name_plural = 'Product Approval Requests'

    def __str__(self):
        return f'{self.product.internal_code} – {self.request_type} ({self.status})'

    def is_pending(self) -> bool:
        return self.status == 'pending'

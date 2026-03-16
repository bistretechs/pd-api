from django.db import models


class ProductReview(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]

    product = models.ForeignKey('clientapp.Product', on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey('clientapp.Customer', on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey('clientapp.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')

    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    review_text = models.TextField()
    review_photos = models.JSONField(default=list, blank=True)

    is_approved = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'clientapp'
        ordering = ['-created_at']
        unique_together = [['product', 'customer', 'order']]
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['rating']),
        ]
        verbose_name = 'Product Review'

    def __str__(self):
        return f'{self.rating}★ – {self.product.name} by {self.customer.email}'

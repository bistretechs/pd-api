from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from datetime import timedelta
from decimal import Decimal
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django import forms
import json
from datetime import date

# Account manager tables
class Lead(models.Model):
    """Lead model for prospect tracking"""
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Converted', 'Converted'),
        ('Lost', 'Lost'),
    ]
    
    SOURCE_CHOICES = [
        ('Website', 'Website'),
        ('Referral', 'Referral'),
        ('Cold Call', 'Cold Call'),
        ('Social Media', 'Social Media'),
        ('Event', 'Event'),
        ('Other', 'Other'),
    ]
    
    CONTACT_METHOD_CHOICES = [
        ('Email', 'Email'),
        ('Phone', 'Phone'),
        ('WhatsApp', 'WhatsApp'),
    ]
    
    CLIENT_TYPE_CHOICES = [
        ('B2B', 'B2B Business'),
        ('B2C', 'B2C Retail'),
    ]
    
    lead_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, blank=True)
    product_interest = models.CharField(max_length=200, blank=True)
    preferred_contact = models.CharField(max_length=20, choices=CONTACT_METHOD_CHOICES, default='Email')
    preferred_client_type = models.CharField(max_length=10, choices=CLIENT_TYPE_CHOICES, default='B2B', help_text="Client type lead will convert to (B2B/B2C)")
    follow_up_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='New')
    notes = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leads_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_to_client = models.BooleanField(default=False)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.lead_id} - {self.name}"
    
    def check_duplicate(self):
        """Check if lead is duplicate (exists in Lead or Client tables)"""
        # Check in Lead table
        if self.pk:
            duplicate_lead = Lead.objects.filter(
                email=self.email
            ).exclude(pk=self.pk).first()
        else:
            duplicate_lead = Lead.objects.filter(email=self.email).first()
        
        if duplicate_lead:
            return True, f"Email already exists as lead {duplicate_lead.lead_id}"
        
        # Check in Client table to prevent onboarding existing clients as leads
        duplicate_client = Client.objects.filter(email=self.email).first()
        if duplicate_client:
            return True, f"Email already exists as client {duplicate_client.client_id}"
        
        return False, None
    
    def save(self, *args, **kwargs):
        if not self.lead_id:
            # Generate lead ID: format-LD-YYYY-XX
            year = timezone.now().year
            last_lead = Lead.objects.filter(
                lead_id__startswith=f'LD-{year}-'
            ).order_by('lead_id').last()
            
            if last_lead:
                last_number = int(last_lead.lead_id.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.lead_id = f'LD-{year}-{new_number:03d}'
        
        super().save(*args, **kwargs)


class Client(models.Model):
    """Client model for active customers"""
    CLIENT_TYPE_CHOICES = [
        ('B2B', 'B2B Business'),
        ('B2C', 'B2C Retail'),
    ]
    
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Dormant', 'Dormant'),
        ('Inactive', 'Inactive'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('Prepaid', 'Prepaid Before Production'),
        ('Net 7', 'Net 7 Days'),
        ('Net 15', 'Net 15 Days'),
        ('Net 30', 'Net 30 Days'),
        ('Net 60', 'Net 60 Days'),
    ]
    
    RISK_RATING_CHOICES = [
        ('Low', 'Low Risk'),
        ('Medium', 'Medium Risk'),
        ('High', 'High Risk'),
    ]
    
    CHANNEL_CHOICES = [
        ('Email', 'Email'),
        ('Phone', 'Phone'),
        ('WhatsApp', 'WhatsApp'),
        ('In-Person', 'In-Person'),
    ]
    
    # Basic Information
    client_id = models.CharField(max_length=20, unique=True, editable=False)
    client_type = models.CharField(max_length=10, choices=CLIENT_TYPE_CHOICES, default='B2B')
    company = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)  # Optional for B2C, required for B2B (enforced in serializer)
    phone = models.CharField(max_length=20)
    
    # Business Details
    vat_tax_id = models.CharField(max_length=50, blank=True)
    kra_pin = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    
    # Financial
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS_CHOICES, default='Prepaid')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    default_markup = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    risk_rating = models.CharField(max_length=20, choices=RISK_RATING_CHOICES, default='Low')
    is_reseller = models.BooleanField(default=False)

    # Delivery Details
    delivery_address = models.CharField(max_length=200, blank=True, null=True)
    # might use it later
    delivery_instructions = models.TextField(blank=True, help_text="Specific delivery instructions (gate codes, contact person)")
    
    # Communication
    preferred_channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='Email')
    lead_source = models.CharField(max_length=50, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Active')
    
    # Relationships
    account_manager = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='managed_clients'
    )
    converted_from_lead = models.OneToOneField(
        Lead, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='client_profile'
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(auto_now=True)
    onboarded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='clients_onboarded'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['client_type']),
        ]
    
    def __str__(self):
        return f"{self.client_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.client_id:
            # Generate client ID: CL-YYYY-XXX
            year = timezone.now().year
            last_client = Client.objects.filter(
                client_id__startswith=f'CL-{year}-'
            ).order_by('client_id').last()
            
            if last_client:
                last_number = int(last_client.client_id.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.client_id = f'CL-{year}-{new_number:03d}'
        
        # Set payment terms to Prepaid for B2C by default
        if self.client_type == 'B2C' and not self.pk:
            self.payment_terms = 'Prepaid'
        
        # Update status based on activity
        if self.last_activity:
            days_inactive = (timezone.now() - self.last_activity).days
            if days_inactive > 180:
                self.status = 'Dormant'
        
        super().save(*args, **kwargs)
    # for profile
    def get_last_activity_display(self):
        """Get human-readable last activity"""
        if not self.last_activity:
            return "Never"
        
        delta = timezone.now() - self.last_activity
        
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        elif delta.days < 30:
            weeks = delta.days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif delta.days < 365:
            months = delta.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        else:
            years = delta.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
    
    @property
    def total_jobs(self):
        """Count total quotes/jobs"""
        return self.quotes.count()
    
    @property
    def total_revenue(self):
        """Calculate total revenue from approved quotes"""
        from django.db.models import Sum
        total = self.quotes.filter(
            status='Approved'
        ).aggregate(Sum('total_amount'))['total_amount__sum']
        return total or 0
    
    @property
    def conversion_rate(self):
        """Calculate quote to approval conversion rate"""
        total = self.quotes.count()
        if total == 0:
            return 0
        approved = self.quotes.filter(status='Approved').count()
        return round((approved / total) * 100, 1)


class ClientContact(models.Model):
    """Additional contacts for a client"""
    ROLE_CHOICES = [
        ('None', 'None'),
        ('Approve Quotes', 'Approve Quotes'),
        ('Approve Artwork', 'Approve Artwork'),
        ('Billing Contact', 'Billing Contact'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contacts')
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='None')
    is_primary = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', 'full_name']
    
    def __str__(self):
        return f"{self.full_name} - {self.client.name}"


class BrandAsset(models.Model):
    """Brand assets library for clients- B2B"""
    ASSET_TYPE_CHOICES = [
        ('Logo', 'Logo'),
        ('Brand Guide', 'Brand Guidelines'),
        ('Color Palette', 'Color Palette'),
        ('Font', 'Font Files'),
        ('Other', 'Other'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='brand_assets')
    asset_type = models.CharField(max_length=50, choices=ASSET_TYPE_CHOICES)
    file = models.FileField(upload_to='brand_assets/%Y/%m/')
    description = models.CharField(max_length=200, blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.client.name} - {self.asset_type}"


class ComplianceDocument(models.Model):
    """Compliance and legal documents for clients"""
    DOCUMENT_TYPE_CHOICES = [
        ('COI', 'Certificate of Incorporation'),
        ('KRA', 'KRA Pin Certificate'),
        ('PO Terms', 'Purchase Order Terms'),
        ('NDA', 'Non-Disclosure Agreement'),
        ('Other', 'Other Legal Document'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='compliance_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    file = models.FileField(upload_to='compliance/%Y/%m/')
    expiry_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.client.name} - {self.document_type}"
    
    @property
    def is_expired(self):
        """Check if document is expired"""
        if self.expiry_date:
            return timezone.now().date() > self.expiry_date
        return False
    
    @property
    def expires_soon(self):
        """Check if document expires in next 30 days"""
        if self.expiry_date:
            days_until_expiry = (self.expiry_date - timezone.now().date()).days
            return 0 < days_until_expiry <= 30
        return False


User = get_user_model()

# PRODUCTION TEAM - PRODUCT MODELS
class ProductCategory(models.Model):
    """Primary categories for products"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Product Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class ProductCategoryForm(forms.ModelForm):
    """Form for creating/editing product categories"""
    
    class Meta:
        model = ProductCategory
        fields = ['name', 'slug', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'Category Name'}),
            'slug': forms.TextInput(attrs={'class': 'form-input w-full', 'placeholder': 'slug-name'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea w-full', 'rows': 3}),
        }
class ProductSubCategory(models.Model):
    """Sub-categories under primary categories"""
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Product Sub-Categories"
        ordering = ['category', 'name']
        unique_together = ['category', 'slug']
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class ProductFamily(models.Model):
    """Product families for grouping related products"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Product Families"
        ordering = ['name']
    
    def __str__(self):
        return self.name



class Product(models.Model):
    """Main Product Model - General Info Tab"""
    
    # Product Type Choices
    PRODUCT_TYPE_CHOICES = [
        ('physical', 'Physical Product'),
        ('digital', 'Digital Product'),
        ('service', 'Service'),
    ]
    CUSTOMIZATION_LEVELS = [
        ('non_customizable', 'Non-Customizable'),
        ('semi_customizable', 'Semi-Customizable'),
        ('fully_customizable', 'Fully Customizable'),
    ]

    customization_level = models.CharField(
        max_length=30,
        choices=CUSTOMIZATION_LEVELS,
        default='non_customizable',
        help_text="Determines which pricing methods are available"
    )
    
    # Visibility Choices
    VISIBILITY_CHOICES = [
        ('catalog-search', 'Catalog and Search'),
        ('catalog-only', 'Catalog Only'),
        ('search-only', 'Search Only'),
        ('hidden', 'Hidden'),
    ]
    
    # Unit of Measure Choices
    UNIT_CHOICES = [
        ('pieces', 'Pieces'),
        ('packs', 'Packs'),
        ('sets', 'Sets'),
        ('sqm', 'm²'),
        ('cm', 'Centimeters'),
    ]
    
    # Weight Unit Choices
    WEIGHT_UNIT_CHOICES = [
        ('gsm', 'GSM (g/m²)'),
        ('kg', 'Kilograms'),
        ('g', 'Grams'),
    ]
    
    # Dimension Unit Choices
    DIMENSION_UNIT_CHOICES = [
        ('cm', 'Centimeters'),
        ('mm', 'Millimeters'),
        ('in', 'Inches'),
    ]
    
    # Warranty Choices
    WARRANTY_CHOICES = [
        ('satisfaction-guarantee', 'Satisfaction Guarantee - Reprint if defective'),
        ('no-warranty', 'No Warranty'),
        ('30-days', '30 Days'),
        ('90-days', '90 Days'),
    ]
    
    # Country Choices
    COUNTRY_CHOICES = [
        ('kenya', 'Kenya'),
        ('china', 'China'),
        ('india', 'India'),
        ('uae', 'UAE'),
    ]
    
    # Status
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Basic Product Information
    name = models.CharField(max_length=255, help_text="Customer-facing name")
    internal_code = models.CharField(max_length=50, unique=True, blank=True, help_text="Internal SKU/Code (auto-generated)")
    auto_generate_code = models.BooleanField(default=True, editable=False)  
    short_description = models.CharField(max_length=150)
    long_description = models.TextField()
    maintenance = models.TextField(blank=True, help_text="Product maintenance details and care instructions")
    technical_specs = models.TextField(blank=True)
    
    # Classification
    primary_category = models.CharField(max_length=100, blank=True, help_text="Print Products, Signage, Apparel")
    sub_category = models.CharField(max_length=100, blank=True, help_text="Business Cards, Flyers, Brochures")
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES, default='physical')
    product_family = models.CharField(max_length=100, blank=True, help_text="Business Cards Family")

    tags = models.ManyToManyField('ProductTag', blank=True, related_name='products')
    
    # Status & Visibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_visible = models.BooleanField(default=True, help_text="Visible to customers?")
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='catalog-search')
    feature_product = models.BooleanField(default=False)
    bestseller_badge = models.BooleanField(default=False)
    new_arrival = models.BooleanField(default=False)
    new_arrival_expires = models.DateField(null=True, blank=True)
    on_sale_badge = models.BooleanField(default=False)
    
    # Product Attributes
    unit_of_measure = models.CharField(max_length=20, choices=UNIT_CHOICES, default='pieces')
    unit_of_measure_custom = models.CharField(max_length=50, blank=True, help_text="Custom unit if 'Other' is selected")
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight_unit = models.CharField(max_length=5, choices=WEIGHT_UNIT_CHOICES, default='kg')
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    dimension_unit = models.CharField(max_length=5, choices=DIMENSION_UNIT_CHOICES, default='cm')
    warranty = models.CharField(max_length=50, choices=WARRANTY_CHOICES, default='satisfaction-guarantee')
    country_of_origin = models.CharField(max_length=50, choices=COUNTRY_CHOICES, default='kenya')
    
    # Pricing
    base_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Base price for non-customizable products")
    
    # INVENTORY & STOCK TRACKING
    STOCK_STATUS_CHOICES = [
        ('in_stock', 'In Stock'),
        ('low_stock', 'Low Stock'),
        ('out_of_stock', 'Out of Stock'),
        ('made_to_order', 'Made to Order'),
        ('discontinued', 'Discontinued'),
    ]
    stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default='made_to_order', help_text="Current stock availability")
    stock_quantity = models.IntegerField(default=0, help_text="Current stock quantity (for pre-made products)")
    low_stock_threshold = models.IntegerField(default=10, help_text="Alert when stock falls below this")
    track_inventory = models.BooleanField(default=False, help_text="Enable inventory tracking for this product")
    allow_backorders = models.BooleanField(default=True, help_text="Allow orders when out of stock")
    
    # Notes & Comments
    internal_notes = models.TextField(blank=True, help_text="Internal use only")
    client_notes = models.TextField(blank=True, help_text="Visible to clients")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='products_updated')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['internal_code']),
            models.Index(fields=['status', 'is_visible']),
        ]
    
    def __str__(self):
        return f"{self.internal_code} - {self.name}"
    
    def clean(self):
        """Validate product pricing rules based on customization level"""
        super().clean()
        
        # Map customization levels to simpler names for validation
        level_map = {
            'non_customizable': 'non',
            'semi_customizable': 'semi',
            'fully_customizable': 'full'
        }
        level = level_map.get(self.customization_level, 'non')
        
        # Non/Semi products must have base_price
        if level in ['non', 'semi']:
            if self.base_price is None:
                raise ValidationError({
                    'base_price': f'{self.get_customization_level_display()} products must have a base price.'
                })
            if self.base_price <= 0:
                raise ValidationError({
                    'base_price': 'Base price must be greater than zero.'
                })
        
        # Fully customizable products must have base_price as NULL
        if level == 'full':
            if self.base_price is not None:
                raise ValidationError({
                    'base_price': 'Fully customizable products must not have a base price (must be NULL).'
                })
    
    def has_costing_process(self):
        """Check if product has at least one costing process"""
        if hasattr(self, 'pricing'):
            # Check if product has any linked process (main, tier, or formula)
            return (
                self.pricing.process is not None or
                self.pricing.tier_process is not None or
                self.pricing.formula_process is not None
            )
        return False
    
    def can_be_published(self):
        """Check if product can be published based on pricing rules"""
        level_map = {
            'non_customizable': 'non',
            'semi_customizable': 'semi',
            'fully_customizable': 'full'
        }
        level = level_map.get(self.customization_level, 'non')
        
        if level in ['non', 'semi']:
            # Must have base_price
            if self.base_price is None or self.base_price <= 0:
                return False, "Non/Semi-customizable products must have a valid base price."
        
        if level == 'full':
            # Must have costing process
            if not self.has_costing_process():
                return False, "Fully customizable products must have at least one costing process."
        
        return True, None
    
    def save(self, *args, **kwargs):
        # Skip validation if skip_validation is set
        skip_validation = kwargs.pop('skip_validation', False)
        
        if not skip_validation:
            # Validate before saving
            self.clean()
            
            # Prevent publishing invalid products
            if self.status == 'published':
                can_publish, error_msg = self.can_be_published()
                if not can_publish:
                    raise ValidationError(error_msg)
        
        if self.auto_generate_code or not self.internal_code:
            # Generate code based on product name
            name_words = self.name.split()
            if len(name_words) >= 2:
                # Use first letters of first two words
                prefix = f"PRD-{name_words[0][:2].upper()}{name_words[1][:2].upper()}"
            else:
                # Use first 2-3 letters of product name
                prefix = f"PRD-{self.name[:3].upper()}"
            
            # Get last product with this prefix
            last_product = Product.objects.filter(
                internal_code__startswith=prefix
            ).order_by('-internal_code').first()
            
            if last_product:
                try:
                    # Extract last number and increment- FROM product code name
                    last_num = int(last_product.internal_code.split('-')[-1])
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    new_num = 1
            else:
                new_num = 1
            
            self.internal_code = f"{prefix}-{new_num:03d}"
        
        super().save(*args, **kwargs)


class ProductTag(models.Model):
    """Tags for products"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ProductPricing(models.Model):
    """Pricing & Variables Tab"""
    
    PRICING_MODEL_CHOICES = [
        ('variable', 'Variable Pricing (customer selects options)'),
        ('simple', 'Simple/Fixed Pricing (one price)'),
        ('quote', 'Quote-Based (PT must cost)'),
    ]
    
    PRICE_DISPLAY_CHOICES = [
        ('from', 'From KES X'),
        ('starting', 'Starting at KES X'),
        ('plus', 'KES X+'),
    ]
    
    PRODUCTION_METHOD_CHOICES = [
        ('digital-offset', 'Digital Offset Printing'),
        ('offset', 'Offset Printing'),
        ('screen', 'Screen Printing'),
        ('digital', 'Digital Printing'),
    ]
    
    LEAD_TIME_UNIT_CHOICES = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('hours', 'Hours'),
    ]
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='pricing')
    
    # Base Pricing Information
    pricing_model = models.CharField(max_length=20, choices=PRICING_MODEL_CHOICES, default='variable')
    base_cost = models.DecimalField(max_digits=10, decimal_places=2, default=15, help_text="Lowest possible vendor cost per piece (EVP)")
    price_display = models.CharField(max_length=20, choices=PRICE_DISPLAY_CHOICES, default='from')
    default_margin = models.DecimalField(max_digits=5, decimal_places=2, default=30, validators=[MinValueValidator(0), MaxValueValidator(100)])
    minimum_margin = models.DecimalField(max_digits=5, decimal_places=2, default=15, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Below this triggers approval")
    minimum_order_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Process Integration
    process = models.ForeignKey('Process', on_delete=models.SET_NULL, null=True, blank=True, related_name='products', help_text='Select the costing process for this product')
    use_process_costs = models.BooleanField(default=True, help_text='Use costs from linked process, or override with custom values')
    
    # Separate Tier and Formula Process Integration
    tier_process = models.ForeignKey('Process', on_delete=models.SET_NULL, null=True, blank=True, related_name='tier_products', help_text='Tier-based pricing process (quantity discounts)')
    formula_process = models.ForeignKey('Process', on_delete=models.SET_NULL, null=True, blank=True, related_name='formula_products', help_text='Formula-based pricing process (customization pricing)')
    
    # Return margin (explicit field for form compatibility)
    return_margin = models.DecimalField(max_digits=5, decimal_places=2, default=30, validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Margin percentage for this product")
    
    # Production & Vendor Information
    production_method = models.CharField(max_length=50, choices=PRODUCTION_METHOD_CHOICES, default='digital-offset')
    alternative_vendors = models.ManyToManyField('Vendor', related_name='alternative_products', blank=True)
    minimum_quantity = models.IntegerField(default=1)
    
    # Rush Production
    rush_available = models.BooleanField(default=False)
    rush_lead_time_value = models.IntegerField(null=True, blank=True)
    rush_lead_time_unit = models.CharField(max_length=10, choices=LEAD_TIME_UNIT_CHOICES, default='days', blank=True)
    rush_upcharge = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentage upcharge")
    
    # Advanced Settings
    enable_conditional_logic = models.BooleanField(default=False)
    enable_conflict_detection = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Product Pricing"
    
    def __str__(self):
        return f"Pricing for {self.product.name}"


class Process(models.Model):
    """Main Process model - represents a production process with pricing logic"""
    
    PRICING_TYPE_CHOICES = [
        ('tier', 'Tier-Based Pricing'),
        ('formula', 'Formula-Based Pricing'),
    ]
    
    CATEGORY_CHOICES = [
        ('outsourced', 'Outsourced'),
        ('in_house', 'In-house'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    # Basic Information
    process_id = models.CharField(max_length=50, unique=True, db_index=True)
    process_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    standard_lead_time = models.IntegerField(help_text="Days")
    
    # Pricing Configuration
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES)
    unit_of_measure = models.CharField(max_length=50, blank=True, null=True)
    base_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Base cost for formula-based pricing")
    
    # Approval Settings
    approval_type = models.CharField(max_length=50, default='auto_approve')
    approval_margin_threshold = models.DecimalField(
        max_digits=5, decimal_places=2, default=25.00
    )
    
    # Metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                   related_name='processes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Process'
        verbose_name_plural = 'Processes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.process_id} - {self.process_name}"
    
    def generate_process_id(self):
        """Auto-generate process ID from name"""
        words = self.process_name.upper().split()
        if len(words) >= 2:
            code = f"PR-{words[0][:3]}-{words[1][:3]}"
        else:
            code = f"PR-{words[0][:6]}"
        
        # Ensure uniqueness
        counter = 1
        original_code = code
        while Process.objects.filter(process_id=code).exists():
            code = f"{original_code}-{counter}"
            counter += 1
        return code
    
    def save(self, *args, **kwargs):
        if not self.process_id:
            self.process_id = self.generate_process_id()
        super().save(*args, **kwargs)




class ProcessTier(models.Model):
    """Quantity tiers for tier-based pricing"""
    
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='tiers')
    tier_number = models.IntegerField()
    
    # Quantity Range
    quantity_from = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_to = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Auto-calculated fields
    per_unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    margin_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    class Meta:
        ordering = ['tier_number']
        unique_together = ['process', 'tier_number']
    
    def __str__(self):
        return f"{self.process.process_id} - Tier {self.tier_number}"
    
    def calculate_values(self):
        """Calculate per-unit price and margin"""
        if self.quantity_to > 0:
            self.per_unit_price = self.price / self.quantity_to
        self.margin_amount = self.price - self.cost
        if self.price > 0:
            self.margin_percentage = (self.margin_amount / self.price) * 100
    
    def save(self, *args, **kwargs):
        self.calculate_values()
        super().save(*args, **kwargs)


class ProcessVariable(models.Model):
    """Variables for formula-based pricing"""
    
    VARIABLE_TYPE_CHOICES = [
        ('number', 'Number'),
        ('alphanumeric', 'Alphanumeric'),
    ]
    
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='variables')
    variable_name = models.CharField(max_length=100)
    variable_type = models.CharField(max_length=20, choices=VARIABLE_TYPE_CHOICES, default='number') 
    unit = models.CharField(max_length=50, blank=True, help_text="e.g., stitches, m, cm")
    
    # Single value fields -for number type
    variable_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Single value for this variable (only for number type)"
    )
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Price for this variable value (KES)"
    )
    rate = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=1.0,
        help_text="Multiplier rate for this variable"
    )
    
    # Backward compatibility fields - min, max, default
    min_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    default_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.process.process_id} - {self.variable_name} ({self.get_variable_type_display()})"

class ProductVariable(models.Model):
    """Product Variables for configurable products"""
    
    VARIABLE_TYPE_CHOICES = [
        ('required', 'Required'),
        ('conditional', 'Conditional'),
        ('optional', 'Optional'),
    ]
    
    PRICING_TYPE_CHOICES = [
        ('fixed', 'Fixed per tier'),
        ('increment', 'Increment per piece'),
        ('percentage', 'Percentage markup'),
        ('none', 'No price impact'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variables')
    name = models.CharField(max_length=100, help_text="Quantity Options, Paper Weight")
    display_order = models.IntegerField(default=0)
    variable_type = models.CharField(max_length=20, choices=VARIABLE_TYPE_CHOICES, default='required')
    pricing_type = models.CharField(max_length=20, choices=PRICING_TYPE_CHOICES, default='fixed')
    
    # Source tracking
    source_process_variable = models.ForeignKey(
        'ProcessVariable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='product_variables',
        help_text="Source variable from process (if auto-imported)"
    )
   
    
    # Conditional Logic
    show_when_variable = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='dependent_variables')
    show_when_option = models.ForeignKey('ProductVariableOption', on_delete=models.SET_NULL, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'display_order']
        unique_together = ['product', 'name']
    
    def __str__(self):
        return f"{self.product.internal_code} - {self.name}"


class ProductVariableOption(models.Model):
    """Options for each product variable"""
    variable = models.ForeignKey(ProductVariable, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100, help_text="100pcs, 250gsm, Matte")
    display_order = models.IntegerField(default=0)
    is_default = models.BooleanField(default=False)
    
    # Pricing
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount to add/subtract")
    
    # Additional info
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['variable', 'display_order']
        unique_together = ['variable', 'name']
    
    def __str__(self):
        return f"{self.variable.name}: {self.name}"


class ProductImage(models.Model):
    """Product Images - Images & Media Tab"""
    
    IMAGE_TYPE_CHOICES = [
        ('product-photo', 'Product Photo'),
        ('detail', 'Detail/Close-up'),
        ('mockup', 'Mockup/In-Use'),
        ('size-comparison', 'Size Comparison'),
        ('sample', 'Sample/Example'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/images/%Y/%m/')
    alt_text = models.CharField(max_length=255, help_text="For SEO & accessibility")
    caption = models.CharField(max_length=255, blank=True)
    image_type = models.CharField(max_length=30, choices=IMAGE_TYPE_CHOICES, default='product-photo')
    is_primary = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    
    # Association with variable option
    associated_variable = models.ForeignKey(ProductVariable, on_delete=models.SET_NULL, null=True, blank=True)
    associated_option = models.ForeignKey(ProductVariableOption, on_delete=models.SET_NULL, null=True, blank=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'display_order']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.display_order}"
    
    def save(self, *args, **kwargs):
        if self.is_primary:
            # Ensure only one primary image per product
            ProductImage.objects.filter(product=self.product, is_primary=True).update(is_primary=False)
        super().save(*args, **kwargs)


class ProductVideo(models.Model):
    """Product Videos"""
    
    VIDEO_TYPE_CHOICES = [
        ('demo', 'Product Demo'),
        ('tutorial', 'Tutorial'),
        ('review', 'Customer Review'),
        ('unboxing', 'Unboxing'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    video_url = models.URLField(help_text="YouTube, Vimeo, or direct MP4 link")
    video_type = models.CharField(max_length=20, choices=VIDEO_TYPE_CHOICES, default='demo')
    thumbnail = models.ImageField(upload_to='products/video_thumbnails/%Y/%m/', blank=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'display_order']
    
    def __str__(self):
        return f"{self.product.name} - {self.get_video_type_display()}"


class ProductDownloadableFile(models.Model):
    """Downloadable files like templates, specs"""
    
    FILE_TYPE_CHOICES = [
        ('illustrator', 'Adobe Illustrator'),
        ('pdf', 'PDF'),
        ('psd', 'Photoshop'),
        ('indd', 'InDesign'),
        ('zip', 'ZIP Archive'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='downloadable_files')
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='products/downloads/%Y/%m/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPE_CHOICES)
    description = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(help_text="File size in bytes", editable=False)
    display_order = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'display_order']
    
    def __str__(self):
        return f"{self.product.name} - {self.file_name}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class ProductSEO(models.Model):
    """SEO & E-commerce Settings"""
    
    PRICE_DISPLAY_FORMAT_CHOICES = [
        ('from', 'From KES X'),
        ('starting', 'Starting at KES X'),
        ('plus', 'KES X+'),
        ('range', 'KES X - Y'),
    ]
    
    STOCK_STATUS_CHOICES = [
        ('in-stock-only', 'Show "In Stock" only'),
        ('always', 'Always show stock level'),
        ('low-stock', 'Show when low stock'),
        ('never', 'Never show'),
    ]
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='seo')
    
    # SEO
    meta_title = models.CharField(max_length=60)
    meta_description = models.CharField(max_length=160)
    slug = models.SlugField(max_length=255, unique=True)
    auto_generate_slug = models.BooleanField(default=True)
    focus_keyword = models.CharField(max_length=100, blank=True)
    additional_keywords = models.TextField(blank=True, help_text="Comma-separated")
    
    # Display Settings
    show_price = models.BooleanField(default=True, help_text="Display price or 'Request Quote'")
    price_display_format = models.CharField(max_length=20, choices=PRICE_DISPLAY_FORMAT_CHOICES, default='from')
    show_stock_status = models.CharField(max_length=20, choices=STOCK_STATUS_CHOICES, default='in-stock-only')
    
    # Related Products
    related_products = models.ManyToManyField(Product, blank=True, related_name='related_to')
    upsell_products = models.ManyToManyField(Product, blank=True, related_name='upsells_for')
    frequently_bought_together = models.ManyToManyField(Product, blank=True, related_name='bundles_with')
    
    class Meta:
        verbose_name = "Product SEO"
        verbose_name_plural = "Product SEO"
    
    def __str__(self):
        return f"SEO for {self.product.name}"
    
    def save(self, *args, **kwargs):
        if self.auto_generate_slug and not self.slug:
            self.slug = slugify(self.product.name)
        super().save(*args, **kwargs)


class ProductReviewSettings(models.Model):
    """Customer Review Settings"""
    
    REVIEW_REMINDER_CHOICES = [
        ('3', '3 days after delivery'),
        ('7', '7 days after delivery'),
        ('14', '14 days after delivery'),
        ('30', '30 days after delivery'),
        ('never', 'Never'),
    ]
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='review_settings')
    enable_reviews = models.BooleanField(default=True)
    require_purchase = models.BooleanField(default=True, help_text="Only verified buyers can review")
    auto_approve_reviews = models.BooleanField(default=False, help_text="Publish without moderation")
    review_reminder = models.CharField(max_length=10, choices=REVIEW_REMINDER_CHOICES, default='7')
    
    def __str__(self):
        return f"Review Settings for {self.product.name}"


class ProductFAQ(models.Model):
    """Frequently Asked Questions"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=255)
    answer = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['product', 'display_order']
        verbose_name = "Product FAQ"
        verbose_name_plural = "Product FAQs"
    
    def __str__(self):
        return f"{self.product.name} - FAQ {self.display_order}"


class ProductShipping(models.Model):
    """Shipping & Delivery Settings"""
    
    SHIPPING_CLASS_CHOICES = [
        ('standard', 'Standard'),
        ('express', 'Express'),
        ('overnight', 'Overnight'),
        ('fragile', 'Fragile'),
    ]
    
    HANDLING_TIME_UNIT_CHOICES = [
        ('days', 'Business Days'),
        ('weeks', 'Weeks'),
        ('hours', 'Hours'),
    ]
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='shipping')
    
    # Shipping Details
    shipping_weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    shipping_weight_unit = models.CharField(max_length=5, default='kg')
    shipping_class = models.CharField(max_length=20, choices=SHIPPING_CLASS_CHOICES, default='standard')
    
    # Package Dimensions
    package_length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    package_dimension_unit = models.CharField(max_length=5, default='cm')
    
    # Free Shipping
    free_shipping = models.BooleanField(default=False)
    free_shipping_threshold = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Delivery Restrictions
    nairobi_only = models.BooleanField(default=False)
    kenya_only = models.BooleanField(default=False)
    no_international = models.BooleanField(default=False)
    
    # Handling Time
    handling_time = models.IntegerField(default=1)
    handling_time_unit = models.CharField(max_length=10, choices=HANDLING_TIME_UNIT_CHOICES, default='days')
    pickup_available = models.BooleanField(default=False)
    pickup_location = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return f"Shipping for {self.product.name}"


class ProductLegal(models.Model):
    """Legal & Compliance"""
    
    RETURN_POLICY_CHOICES = [
        ('non-refundable', 'Non-refundable (custom items)'),
        ('7-days', '7 days'),
        ('14-days', '14 days'),
        ('30-days', '30 days'),
        ('custom', 'Custom policy'),
    ]
    
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='legal')
    
    # Terms & Policies
    product_terms = models.TextField(blank=True)
    return_policy = models.CharField(max_length=30, choices=RETURN_POLICY_CHOICES, default='non-refundable')
    age_restriction = models.BooleanField(default=False, help_text="Age 18+ required")
    
    # Certifications
    cert_fsc = models.BooleanField(default=False, verbose_name="FSC Certified Paper")
    cert_eco = models.BooleanField(default=False, verbose_name="Eco-Friendly")
    cert_food_safe = models.BooleanField(default=False, verbose_name="Food Safe")
    
    copyright_notice = models.TextField(blank=True)
    
    def __str__(self):
        return f"Legal for {self.product.name}"


class ProductProduction(models.Model):
    """Production-specific settings with structured print specs"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='production')
    
    # ===== PRODUCTION METHOD =====
    # Should be vendor specific
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
    production_method_detail = models.CharField(max_length=100, choices=PRODUCTION_METHOD_CHOICES, default='digital_offset')
    machine_equipment = models.CharField(max_length=100, blank=True, help_text="e.g., HP Indigo 7900, Epson SureColor")
    
    # PRINT-SPECIFIC METADATA
    COLOR_PROFILE_CHOICES = [
        ('cmyk', 'CMYK (Print Standard)'),
        ('rgb', 'RGB (Digital)'),
        ('pantone', 'Pantone Spot Colors'),
        ('cmyk_pantone', 'CMYK + Pantone'),
    ]
    color_profile = models.CharField(max_length=20, choices=COLOR_PROFILE_CHOICES, default='cmyk', help_text="Required color mode for artwork")
    bleed_mm = models.DecimalField(max_digits=5, decimal_places=1, default=3.0, help_text="Bleed requirement in mm")
    safe_zone_mm = models.DecimalField(max_digits=5, decimal_places=1, default=5.0, help_text="Safe zone from edge in mm")
    min_resolution_dpi = models.IntegerField(default=300, help_text="Minimum required DPI for artwork")
    max_ink_coverage = models.IntegerField(default=280, help_text="Maximum ink coverage percentage (usually 280-320%)")
    requires_outlined_fonts = models.BooleanField(default=True, help_text="Fonts must be converted to outlines")
    accepts_transparency = models.BooleanField(default=False, help_text="Artwork can contain transparency")
    
    #FINISHING OPTIONS
    finish_lamination = models.BooleanField(default=False, verbose_name="Lamination")
    finish_uv_coating = models.BooleanField(default=False, verbose_name="UV Coating")
    finish_embossing = models.BooleanField(default=False, verbose_name="Embossing")
    finish_debossing = models.BooleanField(default=False, verbose_name="Debossing")
    finish_foil_stamping = models.BooleanField(default=False, verbose_name="Foil Stamping")
    finish_die_cutting = models.BooleanField(default=False, verbose_name="Die Cutting")
    finish_folding = models.BooleanField(default=False, verbose_name="Folding")
    finish_binding = models.BooleanField(default=False, verbose_name="Binding")
    finish_perforation = models.BooleanField(default=False, verbose_name="Perforation")
    finish_scoring = models.BooleanField(default=False, verbose_name="Scoring")
    
    # ===== QUALITY CONTROL REQUIREMENTS =====
    qc_color_match = models.BooleanField(default=True, verbose_name="Color Match Check")
    qc_registration = models.BooleanField(default=True, verbose_name="Registration Check")
    qc_cutting_accuracy = models.BooleanField(default=True, verbose_name="Cutting Accuracy Check")
    qc_finish_quality = models.BooleanField(default=True, verbose_name="Finish Quality Check")
    
    # Pre-Production Checklist
    checklist_artwork = models.BooleanField(default=False, verbose_name="Client artwork approved")
    checklist_preflight = models.BooleanField(default=False, verbose_name="Pre-flight check passed")
    checklist_material = models.BooleanField(default=False, verbose_name="Material in stock")
    checklist_proofs = models.BooleanField(default=False, verbose_name="Color proofs confirmed")
    
    # BILL OF MATERIALS 
    # Primary Material
    bom_primary_material = models.CharField(max_length=200, blank=True, help_text="e.g., 300gsm Art Card")
    bom_primary_size = models.CharField(max_length=100, blank=True, help_text="e.g., SRA3, A4, Custom")
    bom_primary_quantity_per_unit = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Material qty per product unit")
    bom_primary_unit = models.CharField(max_length=20, blank=True, help_text="e.g., sheets, sqm, meters")
    
    # Secondary Material (if any)
    bom_secondary_material = models.CharField(max_length=200, blank=True)
    bom_secondary_size = models.CharField(max_length=100, blank=True)
    bom_secondary_quantity_per_unit = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    bom_secondary_unit = models.CharField(max_length=20, blank=True)
    
    # Ink/Consumables
    bom_ink_coverage_sqm = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Ink coverage per unit in sqm")
    
    production_notes = models.TextField(blank=True, help_text="Special production instructions")
    
    class Meta:
        verbose_name = "Product Production Settings"
        verbose_name_plural = "Product Production Settings"
    
    def __str__(self):
        return f"Production for {self.product.name}"
    
    def get_finishing_options(self):
        """Return list of enabled finishing options"""
        options = []
        if self.finish_lamination:
            options.append('Lamination')
        if self.finish_uv_coating:
            options.append('UV Coating')
        if self.finish_embossing:
            options.append('Embossing')
        if self.finish_debossing:
            options.append('Debossing')
        if self.finish_foil_stamping:
            options.append('Foil Stamping')
        if self.finish_die_cutting:
            options.append('Die Cutting')
        if self.finish_folding:
            options.append('Folding')
        if self.finish_binding:
            options.append('Binding')
        if self.finish_perforation:
            options.append('Perforation')
        if self.finish_scoring:
            options.append('Scoring')
        return options
    
    def get_qc_requirements(self):
        """Return list of QC checks required"""
        checks = []
        if self.qc_color_match:
            checks.append('Color Match')
        if self.qc_registration:
            checks.append('Registration')
        if self.qc_cutting_accuracy:
            checks.append('Cutting Accuracy')
        if self.qc_finish_quality:
            checks.append('Finish Quality')
        return checks


class ProductChangeHistory(models.Model):
    """Track all changes to products"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='change_history')
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    change_type = models.CharField(max_length=50)  # 'created', 'updated', 'published', 
    field_changed = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        verbose_name_plural = "Product Change History"
    
    def __str__(self):
        return f"{self.product.internal_code} - {self.change_type} at {self.changed_at}"


class ProductApprovalRequest(models.Model):
    """
    Track approval requests for sensitive product changes
    (e.g., price changes below threshold, margin adjustments)
    """
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
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='approval_requests')
    request_type = models.CharField(max_length=50, choices=REQUEST_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Who made the request
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approval_requests_made')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    # Who will approve it
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests_assigned')
    
    # Approval details
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approval_requests_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Change details
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)
    reason_for_change = models.TextField(blank=True, help_text="Why is this change needed?")
    
    # Approval notes
    approval_notes = models.TextField(blank=True, help_text="Approver's notes")
    
    # Is this urgent?
    is_urgent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-requested_at']
        verbose_name_plural = "Product Approval Requests"
    
    def __str__(self):
        return f"{self.product.internal_code} - {self.request_type} ({self.status})"
    
    def is_pending(self):
        """Check if approval is still pending"""
        return self.status == 'pending'
    
    def can_auto_approve(self):
        """Check if this request can be auto-approved based on criteria"""
        # Auto-approve non-critical changes
        auto_approvable_types = ['visibility_change']  # Add more as needed
        return self.request_type in auto_approvable_types


class ProductMaterialLink(models.Model):
    """
    Links a finished product to raw materials in inventory
    Enables automatic stock deduction when products are produced
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='material_links')
    material = models.ForeignKey('MaterialInventory', on_delete=models.CASCADE, related_name='product_links')
    
    # How much of this material is consumed per unit of product
    quantity_per_product = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        default=1.0,
        help_text="Amount of material consumed per product unit"
    )
    
    # Material type
    MATERIAL_TYPE_CHOICES = [
        ('primary', 'Primary Material'),
        ('secondary', 'Secondary Material'),
        ('consumable', 'Consumable (Ink, etc.)'),
        ('packaging', 'Packaging'),
    ]
    material_type = models.CharField(max_length=20, choices=MATERIAL_TYPE_CHOICES, default='primary')
    
    # Notes
    notes = models.CharField(max_length=255, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['product', 'material_type']
        unique_together = ['product', 'material']
        verbose_name = "Product-Material Link"
        verbose_name_plural = "Product-Material Links"
    
    def __str__(self):
        return f"{self.product.internal_code} → {self.material.material_name} ({self.quantity_per_product} {self.material.unit})"
    
    def calculate_material_needed(self, product_quantity):
        """Calculate how much material is needed for a given product quantity"""
        return self.quantity_per_product * product_quantity
    
    def check_material_availability(self, product_quantity):
        """Check if enough material is available for production"""
        needed = self.calculate_material_needed(product_quantity)
        return self.material.available_stock >= needed


class Quote(models.Model):
    """Quote/Proposal model - Tryign"""
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Sent to PT', 'Sent to PT'),
        ('Costed', 'Costed'),
        ('Sent to Customer', 'Sent to Customer'),
        ('Approved', 'Approved'),
        ('Lost', 'Lost'),
    ]

    PRODUCTION_STATUS_CHOICES = [
        ('pending', 'Pending Costing'),
        ('in_progress', 'Costing In Progress'),
        ('costed', 'Costed'),
        ('sent_to_client', 'Sent To Client'),
        ('on_hold', 'On Hold'),
        ('in_production', 'In Production'),
        ('completed', 'Completed'),
    ]
    
    PAYMENT_TERMS_CHOICES = [
        ('Prepaid', 'Prepaid Before Production'),
        ('Net 7', 'Net 7 Days'),
        ('Net 15', 'Net 15 Days'),
        ('Net 30', 'Net 30 Days'),
        ('Net 60', 'Net 60 Days'),
    ]

    CHANNEL_CHOICES = [
        ('portal', 'Internal Portal'),
        ('ecommerce', 'Ecommerce'),
        ('api', 'API Integration'),
    ]

    CHECKOUT_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('cart', 'Cart'),
        ('submitted', 'Submitted'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Basic Info
    quote_id = models.CharField(max_length=20, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='quotes', null=True, blank=True)
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True, related_name='quotes')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='portal', db_index=True)
    checkout_status = models.CharField(max_length=20, choices=CHECKOUT_STATUS_CHOICES, default='draft')
    
    # Product Details
    product_name = models.CharField(max_length=200)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Simplified Pricing - ONLY UNIT PRICE
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    reference_number = models.CharField(max_length=100, blank=True, help_text="Client LPO reference")
    shipping_charges = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Delivery cost")
    adjustment_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Final adjustment (+/-)")
    adjustment_reason = models.CharField(max_length=255, blank=True, help_text="Reason for adjustment")
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=16, help_text="Tax percentage (default 16% VAT)")
    custom_terms = models.TextField(blank=True, help_text="Custom terms & conditions for this quote")
    
    # Calculated Totals 
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Quote Details
    payment_terms = models.CharField(max_length=20, choices=PAYMENT_TERMS_CHOICES, default='Prepaid')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    include_vat = models.BooleanField(default=False)
    production_status = models.CharField(max_length=20, choices=PRODUCTION_STATUS_CHOICES, default='pending')
    production_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    production_notes = models.TextField(blank=True)
    costed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotes_costed'
    )
    
    # Quote Locking & Production Assignment
    is_locked = models.BooleanField(default=False, help_text="When True (after Approval), quote is read-only. Changes require revision.")
    preferred_production_lead = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='preferred_production_quotes',
        help_text="Production Team member to assign job to when quote is approved"
    )
    
    # Dates
    quote_date = models.DateField(default=timezone.now)
    valid_until = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Additional Info
    notes = models.TextField(blank=True)
    terms = models.TextField(blank=True)
    loss_reason = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True, help_text="Notes provided by customer (ecommerce/API)")
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='quotes_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Email Tracking (Mailgun Integration)
    email_sent = models.BooleanField(default=False, help_text="Email sent to client")
    email_sent_at = models.DateTimeField(null=True, blank=True, help_text="When email was sent")
    email_delivered = models.BooleanField(default=False, help_text="Email delivered to recipient")
    email_delivered_at = models.DateTimeField(null=True, blank=True, help_text="When email was delivered")
    email_opened = models.BooleanField(default=False, help_text="Email opened by recipient")
    email_opened_at = models.DateTimeField(null=True, blank=True, help_text="When email was first opened")
    email_opened_by = models.EmailField(blank=True, help_text="Email address that opened the message")
    email_clicked = models.BooleanField(default=False, help_text="Link clicked in email")
    email_clicked_at = models.DateTimeField(null=True, blank=True, help_text="When link was clicked")
    email_clicked_url = models.URLField(blank=True, help_text="Which link was clicked")
    email_failed = models.BooleanField(default=False, help_text="Email delivery failed")
    email_failed_reason = models.TextField(blank=True, help_text="Reason for delivery failure")
    mailgun_message_id = models.CharField(max_length=200, blank=True, help_text="Mailgun message ID for tracking")
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['quote_id']),
            models.Index(fields=['status']),
            models.Index(fields=['client']),
            models.Index(fields=['production_status']),
        ]
    
    def __str__(self):
        return f"{self.quote_id} - {self.product_name}"
    
    def save(self, *args, **kwargs):
        # Generate quote_id if not exists
        if not self.quote_id:
            year = timezone.now().year
            last_quote = Quote.objects.filter(
                quote_id__startswith=f'QT-{year}-'
            ).order_by('quote_id').last()
            
            if last_quote:
                try:
                    last_number = int(last_quote.quote_id.split('-')[-1])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.quote_id = f'QT-{year}-{new_number:03d}'
        
        # Calculate total amount (unit_price * quantity + VAT + shipping + adjustments)
        unit_price = self.unit_price if self.unit_price is not None else Decimal('0')
        subtotal = unit_price * self.quantity
        
        # Calculate VAT if enabled
        vat_amount = Decimal('0')
        if self.include_vat:
            vat_amount = subtotal * Decimal('0.16')
            self.tax_total = vat_amount
        else:
            self.tax_total = Decimal('0')
        
        # Calculate total: subtotal + VAT + shipping + adjustments
        shipping_charges = self.shipping_charges if self.shipping_charges is not None else Decimal('0')
        adjustment_amount = self.adjustment_amount if self.adjustment_amount is not None else Decimal('0')
        
        self.total_amount = subtotal + vat_amount + shipping_charges + adjustment_amount
        self.subtotal = subtotal
        
        # Set valid_until if not set
        if not self.valid_until:
            self.valid_until = timezone.now().date() + timedelta(days=3)

        # Enforce status transitions 
        if not getattr(self, '_skip_status_validation', False):
            self._enforce_status_transitions()
        
        # Update production status transitions automatically
        if self.status == 'Costed' and self.production_status == 'pending':
            self.production_status = 'costed'
        if self.status == 'Sent to Customer':
            self.production_status = 'sent_to_client'
        if self.status == 'Approved' and self.production_status not in ['in_production', 'completed']:
            self.production_status = 'in_production'
        if self.status == 'Lost':
            self.production_status = 'completed'
        
        # Lock quote when approved to prevent accidental edits
        if self.status == 'Approved':
            self.is_locked = True
        
        # Unlock quote if status is reverted (back to Draft or Sent to Customer)
        if self.status in ['Draft', 'Sent to PT', 'Sent to Customer', 'Costed']:
            self.is_locked = False
        
        # Call super().save() to actually save the object to the database
        super().save(*args, **kwargs)
    
    def _enforce_status_transitions(self):
        """Enforce valid status transitions"""
        if not self.pk:  # New quote, no previous status to compare
            return
        
        try:
            old_quote = Quote.objects.get(pk=self.pk)
            old_status = old_quote.status
            new_status = self.status
            
            # Define valid transitions
            valid_transitions = {
                'Draft': ['Sent to PT', 'Sent to Customer'],  # Can skip PT if no fully customizable products
                'Sent to PT': ['Costed', 'Draft'],  # Can go back to draft
                'Costed': ['Sent to Customer', 'Draft', 'Sent to PT'],  # Allow going back to PT for re-costing
                'Sent to Customer': ['Approved', 'Lost', 'Draft'],
                'Approved': ['Lost'],  # Once approved, can only be lost
                'Lost': [],  # Terminal state
            }
            
            # Check if transition is valid
            if old_status != new_status:
                allowed_next = valid_transitions.get(old_status, [])
                # Special case: Allow Draft -> Costed transition when costed_by is set (PT costing workflow)
                if new_status == 'Costed' and old_status == 'Draft' and hasattr(self, 'costed_by') and self.costed_by:
                    
                    #costing of a quote by PT
                    pass
                elif new_status not in allowed_next:
                    raise ValidationError(
                        f"Invalid status transition from '{old_status}' to '{new_status}'. "
                        f"Allowed transitions: {', '.join(allowed_next) if allowed_next else 'None'}"
                    )
        except Quote.DoesNotExist:
            pass  # New quote, no validation needed
        
        # Handle Lead to Client conversion when approved
        if self.status == 'Approved' and self.lead and not self.lead.converted_to_client:
            self.convert_lead_to_client()
    
    def can_be_edited(self):
        """Check if quote can be edited based on lock status"""
        if self.is_locked:
            return False, "Quote is locked. Create a revised quote to make changes."
        return True, None
    
    def create_revised_quote(self, revised_by=None):
        """Create a revised (cloned) quote from a locked quote"""
        if not self.is_locked:
            raise ValidationError("Can only create revisions from locked (approved) quotes.")
        
        # Clone the quote
        revised_quote = Quote.objects.create(
            client=self.client,
            lead=self.lead,
            product=self.product,
            channel=self.channel,
            product_name=self.product_name,
            quantity=self.quantity,
            unit_price=self.unit_price,
            total_amount=self.total_amount,
            reference_number=self.reference_number,
            shipping_charges=self.shipping_charges,
            adjustment_amount=self.adjustment_amount,
            adjustment_reason=self.adjustment_reason,
            tax_rate=self.tax_rate,
            custom_terms=self.custom_terms,
            subtotal=self.subtotal,
            discount_total=self.discount_total,
            tax_total=self.tax_total,
            payment_terms=self.payment_terms,
            status='Draft',
            include_vat=self.include_vat,
            production_cost=self.production_cost,
            production_notes=self.production_notes,
            notes=f"Revised quote based on {self.quote_id}",
            terms=self.terms,
            customer_notes=self.customer_notes,
            created_by=revised_by or self.created_by,
            preferred_production_lead=self.preferred_production_lead,
        )
        
        # Clone line items
        for line_item in self.line_items.all():
            QuoteLineItem.objects.create(
                quote=revised_quote,
                product=line_item.product,
                product_name=line_item.product_name,
                customization_level_snapshot=line_item.customization_level_snapshot,
                base_price_snapshot=line_item.base_price_snapshot,
                quantity=line_item.quantity,
                unit_price=line_item.unit_price,
                line_total=line_item.line_total,
                discount_amount=line_item.discount_amount,
                discount_type=line_item.discount_type,
                variable_amount=line_item.variable_amount,
                order=line_item.order,
            )
        
        return revised_quote
    
    def convert_lead_to_client(self):
        """Convert lead to client when quote is approved"""
        lead = self.lead
        
        # Check if client already exists with this email
        existing_client = Client.objects.filter(email=lead.email).first()
        
        if not existing_client:
            # Get client type from lead's preferred_client_type field (B2B/B2C)
            client_type = lead.preferred_client_type if hasattr(lead, 'preferred_client_type') else 'B2C'
            
            # Create new client from lead
            client = Client.objects.create(
                name=lead.name,
                email=lead.email,
                phone=lead.phone,
                client_type=client_type,
                lead_source=lead.source if hasattr(lead, 'source') else '',
                preferred_channel=lead.preferred_contact if hasattr(lead, 'preferred_contact') else 'Email',
                status='Active',
                converted_from_lead=lead,
                onboarded_by=self.created_by,
                account_manager=self.created_by
            )
            
            # Update lead status
            lead.status = 'Converted'
            lead.converted_to_client = True
            lead.converted_at = timezone.now()
            lead.save()
            
            # Transfer quote to new client
            self.client = client
            self.lead = None  # Remove lead reference
            
            # Log activity
            ActivityLog.objects.create(
                client=client,
                activity_type='Note',
                title=f"Client Converted from Lead {lead.lead_id}",
                description=f"Lead automatically converted to {client_type} client after quote {self.quote_id} was approved.",
                created_by=self.created_by
            )
        else:
            # Use existing client
            self.client = existing_client
            self.lead = None
            lead.status = 'Converted'
            lead.converted_to_client = True
            lead.converted_at = timezone.now()
            lead.save()
    
    @property
    def is_expired(self):
        """Check if quote is expired"""
        return timezone.now().date() > self.valid_until
    
    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        delta = self.valid_until - timezone.now().date()
        return delta.days
    
    def has_fully_customizable_products(self):
        """Check if quote has any fully customizable products"""
        # Check line items first
        if hasattr(self, 'line_items') and self.line_items.exists():
            return self.line_items.filter(
                customization_level_snapshot='fully_customizable'
            ).exists()
        # Fallback to product field-backward compatibility
        if self.product:
            return self.product.customization_level == 'fully_customizable'
        return False
    
    def can_send_to_customer(self):
        """Check if quote can be sent to customer - no costed requirement"""
        # Quotes can be sent to customers
        # Basic validation: quote must have at least one line item or product
        has_items = False
        if hasattr(self, 'line_items') and self.line_items.exists():
            has_items = True
        elif self.product:
            has_items = True
        
        if not has_items:
            return False, "Quote must have at least one item before sending to customer."
        
        return True, None
    
    def has_customizable_products(self):
        """Check if quote has any customizable products (semi or fully)"""
        # Check line items first (preferred method)
        if hasattr(self, 'line_items') and self.line_items.exists():
            return self.line_items.filter(
                customization_level_snapshot__in=['semi_customizable', 'fully_customizable']
            ).exists()
        # Fallback to product field (backward compatibility)
        if self.product:
            return self.product.customization_level in ['semi_customizable', 'fully_customizable']
        return False
    
    def can_send_to_pt(self):
        """Check if quote can be sent to Production Team"""
        # Must have at least one customizable product (semi or fully)
        if not self.has_customizable_products():
            return False, "Only quotes with customizable products (semi or fully) can be sent to Production Team."
        
        return True, None


class QuoteLineItem(models.Model):
    """Line items for quotes - stores product pricing"""
    
    DISCOUNT_TYPE_CHOICES = [
        ('percent', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='line_items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='quote_line_items')
    
    # Product snapshot at time of quote creation
    product_name = models.CharField(max_length=200)
    customization_level_snapshot = models.CharField(max_length=30)
    base_price_snapshot = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Line item details
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Discount fields
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Discount value")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent', help_text="Discount type")
    
    # Variable pricing (for semi-customizable products)
    variable_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Additional cost from variables")
    
    # Ordering
    order = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'created_at']
        indexes = [
            models.Index(fields=['quote']),
        ]
    
    def __str__(self):
        return f"{self.quote.quote_id} - {self.product_name} (x{self.quantity})"
    
    def save(self, *args, **kwargs):
        # Calculate line total with discount
        subtotal = (self.unit_price + self.variable_amount) * self.quantity
        
        # Apply discount
        discount = Decimal('0')
        if self.discount_amount > 0:
            if self.discount_type == 'percent':
                discount = subtotal * (self.discount_amount / Decimal('100'))
            else:  # fixed
                discount = self.discount_amount
        
        self.line_total = subtotal - discount
        super().save(*args, **kwargs)


class QuoteAttachment(models.Model):
    """File attachments for quotes (briefs, artwork, specs)"""
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='quote_attachments/%Y/%m/')
    filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField(help_text="Size in bytes")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.quote.quote_id})"


# Centralized Pricing Resolver Function
def resolve_unit_price(product, variables=None, quantity=1):
    """
    Centralized pricing resolver - single source of truth for product pricing.
    
    Args:
        product: Product instance
        variables: Decimal amount for variable pricing (semi-customizable)
        quantity: Quantity for tier-based pricing (future use)
    
    Returns:
        Decimal: Unit price for the product
    """
    if not product:
        return Decimal('0')
    
    level_map = {
        'non_customizable': 'non',
        'semi_customizable': 'semi',
        'fully_customizable': 'full'
    }
    level = level_map.get(product.customization_level, 'non')
    
    # Non-customizable: return base_price (or fallback to ProductPricing.base_cost with margin)
    if level == 'non':
        if product.base_price is not None and product.base_price > 0:
            return product.base_price
        # Fallback: try to get from ProductPricing.base_cost if available
        # Note: base_cost is vendor cost, so we apply margin to get selling price
        if hasattr(product, 'pricing') and product.pricing.base_cost:
            cost = product.pricing.base_cost
            margin = product.pricing.return_margin if hasattr(product.pricing, 'return_margin') else Decimal('30')
            # Calculate price: cost * (1 + margin%)
            return cost * (Decimal('1') + (margin / Decimal('100')))
        return Decimal('0')
    
    # Semi-customizable: base_price (variables added later in quote line items)
    if level == 'semi':
        base = product.base_price or Decimal('0')
        # Variables are handled separately in QuoteLineItem.variable_amount
        # Initial price is just base_price
        return base
    
    # Fully customizable: return 0 (PT will cost it)
    if level == 'full':
        return Decimal('0')
    
    return Decimal('0')


class ActivityLog(models.Model):
    """Activity log for tracking client interactions"""
    ACTIVITY_TYPE_CHOICES = [
        ('Quote', 'Quote'),
        ('Order', 'Order'),
        ('Payment', 'Payment'),
        ('Meeting', 'Meeting'),
        ('Email', 'Email'),
        ('Call', 'Phone Call'),
        ('Note', 'Note'),
        ('Other', 'Other'),
    ]
    
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    
    related_quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='activities', null=True, blank=True)

    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.activity_type} - {self.client.name} - {self.created_at.strftime('%Y-%m-%d')}"
    

class ProductionUpdate(models.Model):
    """Progress updates submitted by the production team"""

    UPDATE_TYPE_CHOICES = [
        ('quote', 'Quote'),
        ('job', 'Job'),
    ]

    update_type = models.CharField(max_length=10, choices=UPDATE_TYPE_CHOICES)
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name='production_updates',
        null=True,
        blank=True
    )
    job = models.ForeignKey(
        'Job',
        on_delete=models.CASCADE,
        related_name='production_updates',
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20, choices=Quote.PRODUCTION_STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='production_updates_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['update_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        subject = self.quote.quote_id if self.quote else (self.job.job_number if self.job else 'Update')
        return f"{subject} - {self.get_status_display()}"

    def clean(self):
        super().clean()
        if not self.quote and not self.job:
            raise ValidationError('A production update must be linked to a quote or a job.')
        if self.quote and self.job:
            raise ValidationError('A production update can only target a quote or a job, not both.')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.clean()
        target_client = None

        if self.quote and self.status:
            self.quote.production_status = self.status
            if self.status in ['costed', 'sent_to_client'] and self.created_by:
                self.quote.costed_by = self.created_by
            self.quote.save(update_fields=['production_status', 'costed_by', 'updated_at'])
            target_client = self.quote.client
        elif self.job:
            target_client = self.job.client

        super().save(*args, **kwargs)

        # Notify account manager on fresh updates
        if is_new and target_client and target_client.account_manager:
            title = 'Production Update'
            if self.quote:
                title = f"Quote {self.quote.quote_id} Update"
            elif self.job:
                title = f"Job {self.job.job_number} Update"

            Notification.objects.create(
                recipient=target_client.account_manager,
                notification_type='general', 
                title=title,
                message=self.notes or f"Production status changed to {self.get_status_display()}",
                link=self._resolve_notification_link()
            )


    def _resolve_notification_link(self):
        if self.quote:
            return reverse('quote_detail', args=[self.quote.quote_id])
        if self.job:
            return reverse('job_detail', args=[self.job.pk])
        return ''




class Job(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
    ]
    
    PRIORITY_CHOICES = [
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    JOB_TYPE_CHOICES = [
        ('printing', 'Printing'),
        ('design', 'Design'),
        ('branding', 'Branding'),
        ('packaging', 'Packaging'),
        ('signage', 'Signage'),
        ('other', 'Other'),
    ]
    
    DELIVERY_METHOD_CHOICES = [
        ('pickup', 'Pickup'),
        ('delivery', 'Delivery'),
        ('courier', 'Courier'),
    ]

    SOURCE_CHOICES = [
        ('portal', 'Internal Portal'),
        ('ecommerce', 'Ecommerce'),
        ('api', 'API Integration'),
    ]
    
    # Basic Info
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='jobs')
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name='job', null=True, blank=True)
    job_number = models.CharField(max_length=50, editable=False, null=True, blank=True)
    job_name = models.CharField(max_length=255)
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='portal')
    
    # Product Info
    product = models.CharField(max_length=255) 
    quantity = models.PositiveIntegerField()
    
    # Assignment
    person_in_charge = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_jobs',
        help_text="Production Team member assigned to this job"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Dates
    start_date = models.DateField(default=date.today)
    expected_completion = models.DateField(default=date.today)
    delivery_date = models.DateField(null=True, blank=True)
    actual_completion = models.DateField(null=True, blank=True)
    
    # Delivery
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHOD_CHOICES, default='pickup')
    
    # Additional Info
    notes = models.TextField(blank=True)
    
    # Reminder & Notification Fields
    remind_days_before = models.IntegerField(default=2, help_text="Send reminder N days before deadline")
    last_reminder_sent = models.DateTimeField(null=True, blank=True, help_text="When was the last reminder sent")
    reminder_count = models.IntegerField(default=0, help_text="How many reminders have been sent")
    assignment_notes = models.TextField(blank=True, help_text="Notes from AM when assigning job")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='jobs_created'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['client']),
            models.Index(fields=['start_date']),
        ]

    def __str__(self):
        return f"{self.job_number} - {self.job_name}"
    
    def save(self, *args, **kwargs):
        if not self.job_number:
            # Generate job number:
            year = timezone.now().year
            last_job = Job.objects.filter(
                job_number__startswith=f'JOB-{year}-'
            ).order_by('job_number').last()
            
            if last_job:
                last_number = int(last_job.job_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.job_number = f'JOB-{year}-{new_number:03d}'
        
        super().save(*args, **kwargs)


class JobProduct(models.Model):
    """Individual products within a job"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='products')
    product_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    unit = models.CharField(max_length=20, default='pcs')
    specifications = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.product_name} ({self.quantity} {self.unit})"


class JobAttachment(models.Model):
    """File attachments for jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='job_attachments/%Y/%m/')
    file_name = models.CharField(max_length=255)
    file_size = models.IntegerField()  # in bytes
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_name} - {self.job.job_number}"

# PRODUCT MANAGEMENT MODELS 

class PropertyType(models.Model):
    """Types of properties like Size, Finish, Paper Stock, Corners"""
    PROPERTY_TYPE_CHOICES = [
        ('size', 'Size'),
        ('finish', 'Finish'),
        ('paper_stock', 'Paper Stock'),
        ('thickness', 'Thickness'),
        ('corners', 'Corners'),
        ('shape', 'Shape'),
        ('coating', 'Coating'),
        ('color', 'Color'),
        ('orientation', 'Orientation'),
        ('folding', 'Folding Style'),
        ('quantity', 'Quantity'),
        ('special_finish', 'Special Finish'),
        ('material', 'Material'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPE_CHOICES)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(default=False, help_text="Is this property required for the product?")
    affects_price = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name_plural = "Property Types"
    
    def __str__(self):
        return f"{self.name} ({self.get_property_type_display()})"


class PropertyValue(models.Model):
    """Specific values for each property type"""
    property_type = models.ForeignKey(PropertyType, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=200)
    value_code = models.CharField(max_length=50, blank=True, help_text="Short code for internal use")
    description = models.TextField(blank=True)
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['property_type', 'display_order', 'value']
        unique_together = ['property_type', 'value']
    
    def __str__(self):
        return f"{self.property_type.name}: {self.value}"


class ProductProperty(models.Model):
    """Links products to their available property values with pricing"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='properties')
    property_value = models.ForeignKey(PropertyValue, on_delete=models.CASCADE)
    price_modifier = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Additional price for this property (+/-)"
    )
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    stock_quantity = models.IntegerField(default=0, help_text="Stock specific to this property variant")
    
    class Meta:
        unique_together = ['product', 'property_value']
        verbose_name_plural = "Product Properties"
    
    def __str__(self):
        return f"{self.product.name} - {self.property_value}"
    
    def get_total_price(self):
        """Calculate total price including modifier"""
        return self.product.base_price + self.price_modifier




class QuantityPricing(models.Model):
    """Quantity-based pricing tiers"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='quantity_pricing')
    min_quantity = models.IntegerField(validators=[MinValueValidator(1)])
    max_quantity = models.IntegerField(null=True, blank=True, help_text="Leave blank for no upper limit")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    percentage_discount = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Discount percentage (0-100)"
    )
    
    class Meta:
        ordering = ['product', 'min_quantity']
        verbose_name_plural = "Quantity Pricing Tiers"
        unique_together = ['product', 'min_quantity']
    
    def __str__(self):
        if self.max_quantity:
            return f"{self.product.name}: {self.min_quantity}-{self.max_quantity} units @ KES {self.unit_price}"
        return f"{self.product.name}: {self.min_quantity}+ units @ KES {self.unit_price}"


class ProductTemplate(models.Model):
    """Design templates available for products"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='templates')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    template_file = models.FileField(upload_to='templates/')
    thumbnail = models.ImageField(upload_to='templates/thumbnails/', blank=True)
    category_tags = models.CharField(max_length=500, blank=True, help_text="Comma-separated tags")
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"


class TurnAroundTime(models.Model):
    """Production turnaround times with pricing"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='turnaround_times')
    name = models.CharField(max_length=100, help_text="Standard, 2-Day, Next-Day")
    business_days = models.IntegerField(help_text="Number of business days")
    price_modifier = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_default = models.BooleanField(default=False)
    is_available = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['display_order', 'business_days']
        unique_together = ['product', 'name']
    
    def __str__(self):
        return f"{self.product.name} - {self.name} ({self.business_days} days)"


class LPO(models.Model):
    """Local Purchase Order model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('in_production', 'In Production'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    lpo_number = models.CharField(max_length=20, unique=True, editable=False)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='lpos')
    quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name='lpo')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Details
    payment_terms = models.CharField(max_length=20)
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)
    
    # QuickBooks Integration
    quickbooks_invoice_id = models.CharField(max_length=50, null=True, blank=True)
    quickbooks_invoice_number = models.CharField(max_length=50, null=True, blank=True)
    synced_to_quickbooks = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='lpos_created')
    created_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lpos_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lpo_number']),
            models.Index(fields=['client']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.lpo_number} - {self.client.name}"
    
    def save(self, *args, **kwargs):
        if not self.lpo_number:
            # Generate LPO number: LPO-YYYY-XXX
            year = timezone.now().year
            last_lpo = LPO.objects.filter(
                lpo_number__startswith=f'LPO-{year}-'
            ).order_by('lpo_number').last()
            
            if last_lpo:
                try:
                    last_number = int(last_lpo.lpo_number.split('-')[-1])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.lpo_number = f'LPO-{year}-{new_number:03d}'
            
        super().save(*args, **kwargs)
    
    
    def sync_to_quickbooks(self, user=None):
        """Syncing LPO to QuickBooks as an invoice"""
        
        from quickbooks_integration.helpers import get_qb_client
        from quickbooks.objects.invoice import Invoice
        from quickbooks.objects.detailline import DetailLine, SalesItemLineDetail
        from quickbooks.objects.customer import Customer
        
        try:
            
            if not user:
                return {'success': False, 'message': 'User required for QuickBooks sync'}
                
            client = get_qb_client(user)
            
            # 1. Find or Create Customer in QB- based on client info- mostly created clients
            qb_customer = None
            customers = Customer.filter(DisplayName=self.client.name, qb=client)
            
            if customers:
                qb_customer = customers[0]
            else:
                # Create new customer
                qb_customer = Customer()
                qb_customer.DisplayName = self.client.name
                qb_customer.PrimaryEmailAddr = {"Address": self.client.email}
                qb_customer.PrimaryPhone = {"FreeFormNumber": self.client.phone}
                qb_customer.CompanyName = self.client.company or self.client.name
                qb_customer.save(qb=client)
            
            # 2. Create Invoice
            invoice = Invoice()
            invoice.CustomerRef = {"value": qb_customer.Id}
            invoice.DocNumber = self.lpo_number
            
            # Add Line Items
            lines = []
            for item in self.line_items.all():
                line = DetailLine()
                line.Amount = float(item.line_total)
                line.Description = item.product_name
                line.DetailType = "SalesItemLineDetail"
                
                # Create SalesItemLineDetail object or dict
                sales_item = SalesItemLineDetail()
                sales_item.Qty = item.quantity
                sales_item.UnitPrice = float(item.unit_price)
                
                
                line.SalesItemLineDetail = sales_item
                lines.append(line)
            
            invoice.Line = lines
            
            # Save Invoice
            invoice.save(qb=client)
            
            # Update LPO
            self.quickbooks_invoice_id = invoice.Id
            self.quickbooks_invoice_number = invoice.DocNumber
            self.synced_to_quickbooks = True
            self.synced_at = timezone.now()
            self.save()
            
            # Log activity (Ensure ActivityLog is imported or available)
            try:
                from clientapp.models import ActivityLog
                ActivityLog.objects.create(
                    client=self.client,
                    activity_type='Other',
                    title='QuickBooks Sync',
                    description=f"LPO {self.lpo_number} synced to QuickBooks as Invoice #{invoice.DocNumber}",
                    created_by=user
                )
            except ImportError:
                pass 
            
            return {'success': True, 'message': f"Successfully synced to QuickBooks as Invoice #{invoice.DocNumber}"}
            
        except Exception as e:
            return {'success': False, 'message': str(e)}

class LPOLineItem(models.Model):
    """Line items for LPO"""
    lpo = models.ForeignKey(LPO, on_delete=models.CASCADE, related_name='line_items')
    product_name = models.CharField(max_length=200)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    def __str__(self):
        return f"{self.product_name} - {self.lpo.lpo_number}"
    
    def save(self, *args, **kwargs):
        self.line_total = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class QuoteApprovalToken(models.Model):
    """Secure tokens for external quote approval"""
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='approval_tokens')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Token for {self.quote.quote_id}"
    
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()


class SystemAlert(models.Model):
    """System-wide alerts for admin dashboard"""
    ALERT_TYPE_CHOICES = [
        ('low_stock', 'Low Stock Alert'),
        ('urgent_order', 'Urgent Order'),
        ('payment_due', 'Payment Due'),
        ('system_error', 'System Error'),
        ('new_lead', 'New Lead'),
        ('quote_expired', 'Quote Expired'),
        ('info', 'General Information'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=200, blank=True, help_text="URL to related object")
    
    # Who should see this
    visible_to_admins = models.BooleanField(default=True)
    visible_to_production = models.BooleanField(default=False)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='dismissed_alerts')
    dismissed_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects 
    related_client = models.ForeignKey('Client', on_delete=models.CASCADE, null=True, blank=True)
    related_quote = models.ForeignKey('Quote', on_delete=models.CASCADE, null=True, blank=True)
    related_lpo = models.ForeignKey('LPO', on_delete=models.CASCADE, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='alerts_created')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'is_dismissed']),
            models.Index(fields=['severity']),
        ]
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.title}"
    
    def dismiss(self, user):
        """Dismiss this alert"""
        self.is_dismissed = True
        self.dismissed_by = user
        self.dismissed_at = timezone.now()
        self.save()


# JOB VENDOR STAGE - Track job progress through different vendors
class JobVendorStage(models.Model):
    """Track job progress through different vendor stages"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent_to_vendor', 'Sent to Vendor'),
        ('in_production', 'In Production'),
        ('completed', 'Completed'),
        ('issues', 'Issues Reported'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='vendor_stages')
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='job_stages')
    stage_order = models.PositiveIntegerField(default=1)  # 1, 2, 3... for multiple vendors
    stage_name = models.CharField(max_length=100)  # "Printing"
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.PositiveIntegerField(default=0)  # 0-100%
    
    # Dates
    started_at = models.DateTimeField(null=True, blank=True)
    expected_completion = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Cost tracking
    vendor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['stage_order']
    
    def __str__(self):
        return f"{self.job.job_number} - Stage {self.stage_order}: {self.stage_name} ({self.vendor.name})"


class JobNote(models.Model):
    """Notes and updates for jobs"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='job_notes')
    content = models.TextField()
    note_type = models.CharField(max_length=20, default='general', choices=[
        ('general', 'General'),
        ('vendor_update', 'Vendor Update'),
        ('issue', 'Issue'),
        ('resolution', 'Resolution'),
    ])
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Note on {self.job.job_number} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class JobReminder(models.Model):
    """Track reminders sent to job assignees"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('acknowledged', 'Acknowledged'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='reminders')
    sent_to_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='job_reminders_received')
    sent_by_user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='job_reminders_sent')
    reminder_message = models.TextField(help_text="Message with reminder")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    days_until_deadline = models.IntegerField(help_text="How many days until deadline when reminder was sent")
    sent_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Reminder for {self.job.job_number} to {self.sent_to_user.first_name}"


class JobMessage(models.Model):
    """Direct messages/notes between AM and job assignee"""
    MESSAGE_TYPES = [
        ('note', 'Note'),
        ('update', 'Update'),
        ('question', 'Question'),
        ('instruction', 'Instruction'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='job_messages_sent')
    recipient = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='job_messages_received')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='note')
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Message on {self.job.job_number}: {self.sender.first_name} → {self.recipient.first_name}"

class Payment(models.Model):
    """Payment tracking for invoices/LPOs"""
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('credit_card', 'Credit Card'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    lpo = models.ForeignKey('LPO', on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='completed')
    reference_number = models.CharField(max_length=100, blank=True, help_text="Transaction ID, Cheque #, etc.")
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-payment_date']
    
    def __str__(self):
        return f"Payment {self.reference_number} - KES {self.amount}"



class Vendor(models.Model):
    """
    Consolidated Vendor/Supplier model for the portal and production team.
    """
    # Authentication & Basic Info
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='vendor_profile', null=True, blank=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    business_address = models.TextField(blank=True, null=True)
    
    # Business & Compliance
    tax_pin = models.CharField(max_length=50, blank=True, null=True)
    payment_terms = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    
    # Capabilities
    services = models.TextField(blank=True, null=True, help_text="Comma-separated services")
    specialization = models.TextField(blank=True, null=True)
    minimum_order = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    lead_time = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., 5 days")
    rush_capable = models.BooleanField(default=False)
    
    # Performance & Ratings
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    quality_rating = models.CharField(max_length=20, blank=True, null=True)
    reliability_rating = models.CharField(max_length=20, blank=True, null=True)
    vps_score_value = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    performance_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Status & Flags
    is_certified = models.BooleanField(default=False)
    recommended = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    max_concurrent_jobs = models.IntegerField(default=10)
    
    # Internal
    internal_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_active_jobs_count(self):
        return self.purchase_orders.filter(
            status__in=['NEW', 'ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
        ).count()
    
    def update_performance_score(self):
        from django.utils import timezone
        from datetime import timedelta

        completed_jobs = self.purchase_orders.filter(status='COMPLETED')
        total = completed_jobs.count()

        if total == 0:
            self.performance_score = 0
            self.vps_score_value = 0
            self.save(update_fields=['performance_score', 'vps_score_value'])
            return

        # On-time delivery (40% weight)
        on_time = completed_jobs.filter(completed_on_time=True).count()
        on_time_rate = (on_time / total) * 100

        # Issue penalty — each job with issues drags score down (20% weight)
        issues = self.purchase_orders.filter(has_issues=True).count()
        issue_rate = (issues / total) * 100

        # QC pass rate over last 90 days (40% weight)
        qc_inspections = self.qc_inspections.filter(
            created_at__gte=timezone.now() - timedelta(days=90)
        ) if hasattr(self, 'qc_inspections') else []
        qc_total = len(qc_inspections) if hasattr(qc_inspections, '__len__') else qc_inspections.count()
        qc_passed = qc_inspections.filter(status='passed').count() if qc_total > 0 else 0
        qc_rate = (qc_passed / qc_total * 100) if qc_total > 0 else on_time_rate

        score = (on_time_rate * 0.40) + (qc_rate * 0.40) + (max(0, 100 - issue_rate) * 0.20)
        score = round(max(0, min(100, score)), 2)

        self.performance_score = score
        self.vps_score_value = score
        self.save(update_fields=['performance_score', 'vps_score_value'])

    @property
    def vps_score(self) -> str:
        score = float(self.vps_score_value)
        if score >= 90:
            return 'A'
        if score >= 75:
            return 'B'
        if score >= 60:
            return 'C'
        if score >= 45:
            return 'D'
        return 'F'
    
    def get_current_workload(self):
        """Get count of active jobs for vendor"""
        active_statuses = ['sent_to_vendor', 'in_production']
        return self.job_vendor_stages.filter(
            status__in=active_statuses
        ).count()
    
    def is_at_capacity(self):
        """Check if vendor is at maximum concurrent jobs"""
        current = self.get_current_workload()
        return current >= self.max_concurrent_jobs
    
    def get_available_capacity(self):
        """Get remaining capacity slots"""
        current = self.get_current_workload()
        return max(0, self.max_concurrent_jobs - current)
    
    def get_workload_percentage(self):
        """Get workload as percentage"""
        if self.max_concurrent_jobs == 0:
            return 0
        current = self.get_current_workload()
        return int((current / self.max_concurrent_jobs) * 100)






class VendorQuote(models.Model):
    """
    Vendor quote for a specific job.
    Multiple vendors can submit quotes for the same job.
    """
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='vendor_quotes')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='quotes')
    
    # Quote details
    lead_time = models.IntegerField(help_text="Lead time in days")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    selected = models.BooleanField(default=False)
    
    # Special notices or conditions
    notice = models.CharField(max_length=200, blank=True, help_text="e.g., Watch out (2 close misses this month)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['lead_time', 'total_cost']
        unique_together = ['job', 'vendor']
    
    def __str__(self):
        return f"{self.vendor.name} - {self.job.job_number}"



class QCInspection(models.Model):
    """Quality Control Inspection for jobs"""
    INSPECTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('rework', 'Needs Rework'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='qc_inspections')
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name='qc_inspections', null=True, blank=True)
    inspector = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inspections')
    
    status = models.CharField(max_length=20, choices=INSPECTION_STATUS_CHOICES, default='pending')
    inspection_date = models.DateTimeField(auto_now_add=True)
    
    # Inspection checklist
    color_accuracy = models.BooleanField(default=False)
    print_quality = models.BooleanField(default=False)
    cutting_accuracy = models.BooleanField(default=False)
    finishing_quality = models.BooleanField(default=False)
    quantity_verified = models.BooleanField(default=False)
    packaging_checked = models.BooleanField(default=False)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"QC for {self.job.job_number} - {self.get_status_display()}"


#DELIVERY MODEL- for handoff from Production to Account Management
class Delivery(models.Model):
    """Delivery handoff from PT to AM"""
    STATUS_CHOICES = [
        ('staged', 'Staged - Awaiting Pickup'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Delivery Failed'),
    ]
    
    STAGING_LOCATION_CHOICES = [
        ('shelf-a', 'Shelf A - Urgent/Priority'),
        ('shelf-b', 'Shelf B - Standard/Ready Today'),
        ('shelf-c', 'Shelf C - Future Delivery'),
        ('warehouse', 'Warehouse - Overflow'),
    ]
    
    # Identification
    delivery_number = models.CharField(max_length=50, unique=True, editable=False)
    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name='delivery')
    qc_inspection = models.OneToOneField(QCInspection, on_delete=models.CASCADE, related_name='delivery', null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='staged')
    
    # Staging
    staging_location = models.CharField(max_length=20, choices=STAGING_LOCATION_CHOICES, default='shelf-b')
    
    # Packaging verification
    packaging_verified = models.JSONField(default=dict, blank=True)
    # Structure: {
    #   "boxes_sealed": true,
    #   "job_labels": true,
    #   "quantity_marked": true,
    #   "total_quantity": true,
    #   "fragile_stickers": false
    # }
    
    # Photos
    package_photos = models.JSONField(default=list, blank=True)  # List of photo paths
    
    # Notes
    notes_to_am = models.TextField(blank=True)
    
    # Costs
    locked_evp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Handoff confirmation
    handoff_confirmed = models.BooleanField(default=False)
    handoff_confirmed_at = models.DateTimeField(null=True, blank=True)
    handoff_confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='deliveries_confirmed')
    
    # Notifications
    notify_am = models.BooleanField(default=True)
    notify_via_email = models.BooleanField(default=True)
    mark_urgent = models.BooleanField(default=False)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='deliveries_created')
    
    class Meta:
        verbose_name_plural = 'Deliveries'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.delivery_number} - {self.job.job_number}"
    
    def save(self, *args, **kwargs):
        if not self.delivery_number:
            # Generate delivery number: DLV-YYYY-XXX
            year = timezone.now().year
            last_delivery = Delivery.objects.filter(
                delivery_number__startswith=f'DLV-{year}-'
            ).order_by('-delivery_number').first()
            
            if last_delivery:
                try:
                    last_num = int(last_delivery.delivery_number.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            
            self.delivery_number = f'DLV-{year}-{new_num:03d}'
        
        super().save(*args, **kwargs)
    
    @property
    def cost_variance(self):
        """Calculate cost variance"""
        if self.locked_evp and self.actual_cost:
            return self.actual_cost - self.locked_evp
        return Decimal('0')
    
    @property
    def cost_variance_percentage(self):
        """Calculate cost variance percentage"""
        if self.locked_evp and self.locked_evp > 0:
            return (self.cost_variance / self.locked_evp) * 100
        return Decimal('0')



class ProcessVendor(models.Model):
    """Vendors linked to a process"""
    
    PRIORITY_CHOICES = [
        ('preferred', 'Preferred'),
        ('alternative', 'Alternative'),
        ('backup', 'Backup'),
    ]
    
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='process_vendors')
    vendor_name = models.CharField(max_length=200)
    vendor_id = models.CharField(max_length=50)
    vps_score = models.DecimalField(max_digits=5, decimal_places=2, 
                                    help_text="Vendor Performance Score")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='alternative')
    
    # Pricing 
    tier_costs = models.JSONField(null=True, blank=True)
    formula_rates = models.JSONField(null=True, blank=True)
    
    # Rush fees
    rush_enabled = models.BooleanField(default=False)
    rush_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    rush_threshold_days = models.IntegerField(default=3)
    
    # Other settings
    minimum_order = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    standard_lead_time = models.IntegerField(help_text="Days")
    rush_lead_time = models.IntegerField(help_text="Days", null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['priority', '-vps_score']
    
    def __str__(self):
        return f"{self.process.process_id} - {self.vendor_name}"

class PricingTier(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE, related_name='pricing_tiers')
    tier_number = models.IntegerField()
    quantity_from = models.IntegerField(validators=[MinValueValidator(1)])
    quantity_to = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['tier_number']
        unique_together = ['process', 'tier_number']
    
    @property
    def margin_amount(self):
        return self.price - self.cost
    
    @property
    def margin_percentage(self):
        if self.cost > 0:
            return ((self.price - self.cost) / self.cost) * 100
        return 0
    
    @property
    def per_unit_price(self):
        if self.quantity_to > 0:
            return self.price / self.quantity_to
        return 0
    
    def __str__(self):
        return f"Tier {self.tier_number}: {self.quantity_from}-{self.quantity_to}"









# class Vendor(models.Model):
#     vendor_id = models.CharField(max_length=50, unique=True)
#     name = models.CharField(max_length=255)
#     vps_score = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], help_text="Vendor Performance Score")
#     is_active = models.BooleanField(default=True)
    
#     def __str__(self):
#         return f"{self.name} ({self.vps_score}%)"





class VendorTierPricing(models.Model):
    process_vendor = models.ForeignKey(ProcessVendor, on_delete=models.CASCADE, related_name='tier_pricing')
    tier_number = models.IntegerField()
    quantity_from = models.IntegerField()
    quantity_to = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        ordering = ['tier_number']
        unique_together = ['process_vendor', 'tier_number']
    
    def __str__(self):
        return f"{self.process_vendor.vendor.name} - Tier {self.tier_number}"

class Notification(models.Model):
    """Notification system for all users"""
    NOTIFICATION_TYPES = [
        ('lead_created', 'New Lead Created'),
        ('quote_reminder', 'Quote Creation Reminder'),
        ('quote_approved', 'Quote Approved by Client'),
        ('quote_sent_pt', 'Quote Sent to PT for Approval'),
        ('quote_pt_approved', 'Quote Costed by PT'),
        ('quote_discount_request', 'Price Reduction Requested'),
        ('quote_adjustment_request', 'Quote Adjustments Requested'),
        ('convert_lead', 'Convert Lead to Client'),
        ('delivery_ready', 'Delivery Ready for AM'),
        ('job_completed', 'Job Completed'),
        ('general', 'General Notification'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=500, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Related objects
    related_lead = models.ForeignKey('Lead', on_delete=models.CASCADE, null=True, blank=True)
    related_quote_id = models.CharField(max_length=50, null=True, blank=True)
    related_job = models.ForeignKey('Job', on_delete=models.CASCADE, null=True, blank=True)
    
    # Action button data
    action_url = models.CharField(max_length=500, blank=True, null=True)
    action_label = models.CharField(max_length=100, blank=True, null=True)  # "Convert to Client", "Create Quote"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"




class AuditLog(models.Model):
    """Audit log for tracking admin actions"""
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100, null=True, blank=True)
    object_repr = models.CharField(max_length=200, null=True, blank=True)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['action']),
            models.Index(fields=['model_name']),
            models.Index(fields=['timestamp']),
        ]
        
    def __str__(self):
        return f"{self.user} - {self.action} {self.model_name} - {self.timestamp}"


class SystemSetting(models.Model):
    """System-wide settings"""
    key = models.CharField(max_length=50, unique=True)
    value = models.TextField(blank=True)
    description = models.CharField(max_length=200, blank=True)
    is_public = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['key']
    
    def __str__(self):
        return f"{self.key}: {self.value}"


class ProcessVariableRange(models.Model):
    """Ranges for formula-based pricing variables"""
    variable = models.ForeignKey(
        'ProcessVariable',
        on_delete=models.CASCADE,
        related_name='ranges'
    )
    min_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Minimum value for this range"
    )
    max_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Maximum value for this range"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base price for this range (KES)"
    )
    rate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=1.0,
        help_text="Multiplier rate for this range"
    )
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'min_value']
        verbose_name = "Variable Range"
        verbose_name_plural = "Variable Ranges"

    def __str__(self):
        return f"{self.variable.variable_name}: {self.min_value}-{self.max_value}"

    def applies_to(self, value):
        """Check if this range applies to a given value"""
        return self.min_value <= Decimal(str(value)) <= self.max_value



# COSTING PROCESS SYSTEM MODELS


# ============================================================================
# STOREFRONT ECOMMERCE MODELS
# ============================================================================

class Customer(models.Model):
    """
    Storefront Customer Profile - Separate from internal Client model
    Handles identity matching and customer accounts for ecommerce
    """
    # Link to Django User (optional - for authenticated customers)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='customer_profile'
    )
    
    # Identity Information
    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # Account Status
    is_guest = models.BooleanField(default=True, help_text="True if no account created")
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    
    # Preferences
    preferred_currency = models.CharField(max_length=3, default='KES')
    preferred_language = models.CharField(max_length=10, default='en')
    marketing_consent = models.BooleanField(default=False)
    
    # Link to existing Client (if matched)
    matched_client = models.ForeignKey(
        'Client',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_profiles',
        help_text="Auto-matched to existing Client if email/phone matches"
    )
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['is_guest']),
        ]
    
    def __str__(self):
        return f"{self.email} ({'Guest' if self.is_guest else 'Account'})"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    def match_to_existing_client(self):
        """Auto-match customer to existing Client by email or phone"""
        if self.matched_client:
            return self.matched_client
        
        # Try to match by email
        try:
            client = Client.objects.get(email=self.email)
            self.matched_client = client
            self.save(update_fields=['matched_client'])
            return client
        except Client.DoesNotExist:
            pass
        
        # Try to match by phone
        if self.phone:
            try:
                client = Client.objects.get(phone=self.phone)
                self.matched_client = client
                self.save(update_fields=['matched_client'])
                return client
            except Client.DoesNotExist:
                pass
        
        return None


class CustomerAddress(models.Model):
    """Address Book for Customers - Multiple addresses per customer"""
    ADDRESS_TYPE_CHOICES = [
        ('billing', 'Billing Address'),
        ('shipping', 'Shipping Address'),
        ('both', 'Both'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, default='both')
    
    # Address Details
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state_province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default='Kenya')
    
    # Flags
    is_default_billing = models.BooleanField(default=False)
    is_default_shipping = models.BooleanField(default=False)
    
    # Additional Info
    delivery_instructions = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default_shipping', '-is_default_billing', '-created_at']
        verbose_name_plural = "Customer Addresses"
    
    def __str__(self):
        return f"{self.customer.email} - {self.city} ({self.address_type})"


class Cart(models.Model):
    """Shopping Cart for Storefront Customers"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='carts',
        null=True,
        blank=True
    )
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        help_text="For guest carts"
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_abandoned = models.BooleanField(default=False)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['session_key', 'is_active']),
        ]
    
    def __str__(self):
        identifier = self.customer.email if self.customer else f"Guest-{self.session_key[:8]}"
        return f"Cart-{self.id} ({identifier})"
    
    @property
    def item_count(self):
        return self.items.count()
    
    @property
    def subtotal(self):
        return sum(item.line_total for item in self.items.all())
    
    @property
    def total(self):
        # Subtotal + shipping + tax - discounts
        return self.subtotal  # Will be enhanced with tax/shipping/discounts


class CartItem(models.Model):
    """Individual items in a shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    
    # Product Details (snapshot at time of adding to cart)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Customization (for design products)
    design_state_json = models.JSONField(null=True, blank=True, help_text="Stored design configuration")
    design_file_url = models.URLField(blank=True, help_text="Link to uploaded design file")
    
    # Calculated
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        unique_together = [['cart', 'product', 'design_state_json']]
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} in Cart-{self.cart.id}"
    
    def save(self, *args, **kwargs):
        # Auto-calculate line_total
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Order(models.Model):
    """
    Ecommerce Order Model - Separate from Quote
    Orders are created after payment confirmation
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('processing', 'Processing'),
        ('in_production', 'In Production'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Order Identification
    order_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Addresses
    billing_address = models.ForeignKey(
        CustomerAddress,
        on_delete=models.PROTECT,
        related_name='billing_orders',
        null=True
    )
    shipping_address = models.ForeignKey(
        CustomerAddress,
        on_delete=models.PROTECT,
        related_name='shipping_orders',
        null=True
    )
    
    # Payment
    payment_method = models.CharField(max_length=50, blank=True)  # mpesa, stripe, pesapal
    payment_transaction_id = models.CharField(max_length=255, blank=True)
    payment_receipt_url = models.URLField(blank=True)
    
    # Coupon/Discount
    coupon_code = models.CharField(max_length=50, blank=True)
    coupon = models.ForeignKey('Coupon', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Shipping
    shipping_method = models.ForeignKey('ShippingMethod', on_delete=models.SET_NULL, null=True, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    
    # Link to Quote (if converted from quote)
    quote = models.ForeignKey('Quote', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    
    # Link to Job (created after order confirmation)
    job = models.ForeignKey('Job', on_delete=models.SET_NULL, null=True, blank=True, related_name='storefront_orders')
    
    # Customer Notes
    customer_notes = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['payment_status']),
        ]
    
    def __str__(self):
        return f"Order {self.order_number} - {self.customer.email}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            # Generate order number: ORD-YYYY-XXX
            year = timezone.now().year
            last_order = Order.objects.filter(
                order_number__startswith=f'ORD-{year}-'
            ).order_by('order_number').last()
            
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.order_number = f'ORD-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Individual items in an order"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('Product', on_delete=models.PROTECT)
    
    # Product Details (snapshot)
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    
    # Customization
    design_state_json = models.JSONField(null=True, blank=True)
    design_file_url = models.URLField(blank=True)
    
    # Pricing
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        ordering = ['id']
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} in {self.order.order_number}"


class Coupon(models.Model):
    """Coupon/Discount Engine"""
    TYPE_CHOICES = [
        ('percentage', 'Percentage Off'),
        ('fixed', 'Fixed Amount Off'),
        ('free_shipping', 'Free Shipping'),
        ('buy_x_get_y', 'Buy X Get Y'),
    ]
    
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Discount Type
    discount_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Percentage or fixed amount")
    
    # Buy X Get Y (for discount_type='buy_x_get_y')
    buy_quantity = models.IntegerField(null=True, blank=True)
    get_quantity = models.IntegerField(null=True, blank=True)
    
    # Conditions
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    maximum_discount_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    applicable_products = models.ManyToManyField('Product', blank=True, help_text="Leave empty for all products")
    
    # Usage Limits
    usage_limit = models.IntegerField(null=True, blank=True, help_text="Total times coupon can be used")
    usage_count = models.IntegerField(default=0)
    usage_limit_per_customer = models.IntegerField(default=1, help_text="Times per customer")
    
    # Validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def is_valid(self, customer=None, order_amount=0):
        """Check if coupon is valid for use"""
        if not self.is_active:
            return False, "Coupon is not active"
        
        if timezone.now() < self.valid_from or timezone.now() > self.valid_until:
            return False, "Coupon is not valid at this time"
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False, "Coupon usage limit reached"
        
        if order_amount < self.minimum_order_amount:
            return False, f"Minimum order amount of {self.minimum_order_amount} required"
        
        if customer:
            # Check per-customer usage limit
            customer_usage = Order.objects.filter(
                customer=customer,
                coupon=self,
                payment_status='completed'
            ).count()
            if customer_usage >= self.usage_limit_per_customer:
                return False, "You have already used this coupon"
        
        return True, "Valid"
    
    def calculate_discount(self, order_amount, items=None):
        """Calculate discount amount for an order"""
        if self.discount_type == 'percentage':
            discount = order_amount * (self.discount_value / 100)
            if self.maximum_discount_amount:
                discount = min(discount, self.maximum_discount_amount)
            return discount
        elif self.discount_type == 'fixed':
            return min(self.discount_value, order_amount)
        elif self.discount_type == 'free_shipping':
            return Decimal('0')  # Applied separately
        elif self.discount_type == 'buy_x_get_y':
            # Complex logic for BOGO
            return Decimal('0')  # Placeholder
        return Decimal('0')


class TaxConfiguration(models.Model):
    """Tax Engine - Region-based tax calculation"""
    REGION_TYPE_CHOICES = [
        ('country', 'Country'),
        ('state', 'State/Province'),
        ('city', 'City'),
        ('postal_code', 'Postal Code'),
    ]
    
    TAX_TYPE_CHOICES = [
        ('vat', 'VAT'),
        ('gst', 'GST'),
        ('sales_tax', 'Sales Tax'),
        ('exempt', 'Tax Exempt'),
    ]
    
    name = models.CharField(max_length=200)
    tax_type = models.CharField(max_length=20, choices=TAX_TYPE_CHOICES, default='vat')
    rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tax rate percentage")
    
    # Region Targeting
    region_type = models.CharField(max_length=20, choices=REGION_TYPE_CHOICES, default='country')
    country = models.CharField(max_length=100, default='Kenya')
    state_province = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    # Conditions
    is_active = models.BooleanField(default=True)
    applies_to_b2b = models.BooleanField(default=True)
    applies_to_b2c = models.BooleanField(default=True)
    
    # Exemptions
    exempt_product_categories = models.JSONField(default=list, blank=True, help_text="List of category names")
    exempt_business_types = models.JSONField(default=list, blank=True, help_text="List of business types")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['country', 'state_province', 'city']
        verbose_name_plural = "Tax Configurations"
    
    def __str__(self):
        return f"{self.name} ({self.rate}%) - {self.country}"
    
    def applies_to(self, address, customer=None):
        """Check if this tax configuration applies to given address/customer"""
        if not self.is_active:
            return False
        
        if address.country != self.country:
            return False
        
        if self.region_type == 'state' and address.state_province != self.state_province:
            return False
        
        if self.region_type == 'city' and address.city != self.city:
            return False
        
        if self.region_type == 'postal_code' and address.postal_code != self.postal_code:
            return False
        
        # Check customer type
        if customer and customer.matched_client:
            client_type = customer.matched_client.client_type
            if client_type == 'B2B' and not self.applies_to_b2b:
                return False
            if client_type == 'B2C' and not self.applies_to_b2c:
                return False
        
        return True
    
    def calculate_tax(self, subtotal):
        """Calculate tax amount for given subtotal"""
        if self.tax_type == 'exempt':
            return Decimal('0')
        return subtotal * (self.rate / 100)


class DesignTemplate(models.Model):
    """Pre-made Design Templates for Design Studio"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Template Files
    thumbnail_url = models.URLField(blank=True)
    template_file_url = models.URLField(blank=True, help_text="High-res template file")
    preview_url = models.URLField(blank=True)
    
    # Product Association
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='design_templates')
    product_category = models.CharField(max_length=100, blank=True)
    
    # Template Metadata
    template_json = models.JSONField(default=dict, help_text="Template structure/configuration")
    is_premium = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    
    # Usage Stats
    usage_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_featured', '-usage_count', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.product.name})"


class DesignState(models.Model):
    """Stores user's design state (JSON recipe) for custom products"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='design_states', null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, help_text="For guest designs")
    
    # Design Data
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    design_json = models.JSONField(default=dict, help_text="Complete design state/configuration")
    design_preview_url = models.URLField(blank=True)
    
    # Source
    template = models.ForeignKey(DesignTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    is_from_template = models.BooleanField(default=False)
    
    # Status
    is_saved = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_accessed_at']
        indexes = [
            models.Index(fields=['customer', 'is_saved']),
            models.Index(fields=['session_key', 'is_saved']),
        ]
    
    def __str__(self):
        identifier = self.customer.email if self.customer else f"Guest-{self.session_key[:8]}"
        return f"Design-{self.id} ({identifier})"


class ProductReview(models.Model):
    """Product Reviews and Ratings"""
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    
    # Review Content
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    review_text = models.TextField()
    
    # Photos
    review_photos = models.JSONField(default=list, blank=True, help_text="List of photo URLs")
    
    # Moderation
    is_approved = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)
    
    # Helpfulness
    helpful_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['product', 'customer', 'order']]
        indexes = [
            models.Index(fields=['product', 'is_approved']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.rating}★ - {self.product.name} by {self.customer.email}"


class ShippingMethod(models.Model):
    """Shipping Methods and Rates"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Carrier
    carrier = models.CharField(max_length=100, blank=True, help_text="G4S, DHL, Sendy, etc.")
    carrier_api_enabled = models.BooleanField(default=False, help_text="Use carrier API for real-time rates")
    carrier_api_config = models.JSONField(default=dict, blank=True, help_text="API credentials/config")
    
    # Pricing
    pricing_type = models.CharField(
        max_length=20,
        choices=[
            ('flat', 'Flat Rate'),
            ('weight_based', 'Weight Based'),
            ('price_based', 'Price Based'),
            ('api', 'API Calculated'),
        ],
        default='flat'
    )
    flat_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight_rate_per_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_rate_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Coverage
    available_countries = models.JSONField(default=list, blank=True)
    available_regions = models.JSONField(default=list, blank=True)
    
    # Delivery Time
    estimated_days_min = models.IntegerField(default=1)
    estimated_days_max = models.IntegerField(default=3)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['is_default', 'name']
        verbose_name_plural = "Shipping Methods"
    
    def __str__(self):
        return f"{self.name} ({self.carrier or 'Custom'})"
    
    def calculate_shipping_cost(self, weight=None, order_amount=None, destination=None):
        """Calculate shipping cost based on method"""
        if self.pricing_type == 'flat':
            return self.flat_rate or Decimal('0')
        elif self.pricing_type == 'weight_based' and weight:
            return (weight * self.weight_rate_per_kg) if self.weight_rate_per_kg else Decimal('0')
        elif self.pricing_type == 'price_based' and order_amount:
            return order_amount * (self.price_rate_percentage / 100) if self.price_rate_percentage else Decimal('0')
        elif self.pricing_type == 'api':
            # Placeholder - would call carrier API
            return Decimal('0')
        return Decimal('0')


class PaymentTransaction(models.Model):
    """Payment Gateway Transaction Tracking"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('stripe', 'Stripe'),
        ('pesapal', 'Pesapal'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash on Delivery'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payment_transactions')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='payment_transactions')
    
    # Payment Details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    
    # Gateway Response
    transaction_id = models.CharField(max_length=255, unique=True, db_index=True)
    gateway_response = models.JSONField(default=dict, blank=True, help_text="Full gateway response")
    receipt_url = models.URLField(blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    failure_reason = models.TextField(blank=True)
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['order', 'status']),
        ]
    
    def __str__(self):
        return f"{self.payment_method.upper()} - {self.transaction_id} ({self.status})"


# ==================== STOREFRONT BACKEND ENHANCEMENTS ====================

class ProductRule(models.Model):
    """
    Product Configuration Rules Engine
    Vistaprint's secret sauce - validates product variable combinations
    """
    RULE_TYPE_CHOICES = [
        ('requires', 'Requires'),
        ('excludes', 'Excludes'),
        ('range', 'Range (Min/Max)'),
        ('conditional', 'Conditional'),
        ('turnaround_compatibility', 'Turnaround Compatibility'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='rules')
    rule_type = models.CharField(max_length=30, choices=RULE_TYPE_CHOICES)
    condition_json = models.JSONField(
        default=dict,
        help_text="Rule conditions (e.g., {'variable': 'paper', 'value': '300gsm', 'excludes': ['spot_uv']})"
    )
    message = models.CharField(
        max_length=500,
        help_text="Error message shown when rule is violated"
    )
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=0, help_text="Higher priority rules checked first")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-priority', 'rule_type']
        indexes = [
            models.Index(fields=['product', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.product.name} - {self.get_rule_type_display()}"


class TimelineEvent(models.Model):
    """
    Timeline & Event Bus - Append-only event log
    Drives notifications, webhooks, and audit trails
    """
    EVENT_TYPE_CHOICES = [
        # Quote events
        ('quote.created', 'Quote Created'),
        ('quote.sent', 'Quote Sent'),
        ('quote.approved', 'Quote Approved'),
        ('quote.rejected', 'Quote Rejected'),
        ('quote.expired', 'Quote Expired'),
        ('quote.cancelled', 'Quote Cancelled'),
        # Order events
        ('order.created', 'Order Created'),
        ('order.paid', 'Order Paid'),
        ('order.shipped', 'Order Shipped'),
        ('order.delivered', 'Order Delivered'),
        ('order.cancelled', 'Order Cancelled'),
        # Job events
        ('job.created', 'Job Created'),
        ('job.assigned', 'Job Assigned'),
        ('job.in_production', 'Job In Production'),
        ('job.completed', 'Job Completed'),
        # Payment events
        ('payment.received', 'Payment Received'),
        ('payment.refunded', 'Payment Refunded'),
        # Vendor events
        ('vendor.assigned', 'Vendor Assigned'),
        ('vendor.failed', 'Vendor Failed'),
        # SLA events
        ('sla.breached', 'SLA Breached'),
        ('sla.warning', 'SLA Warning'),
        # Other
        ('custom', 'Custom Event'),
    ]
    
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='timeline_events'
    )
    entity_type = models.CharField(max_length=50, db_index=True)  # 'quote', 'order', 'job', etc.
    entity_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=50, choices=EVENT_TYPE_CHOICES, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['event_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.entity_type}#{self.entity_id} at {self.timestamp}"


class DesignSession(models.Model):
    """
    Design Session - Tracks customer design sessions
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('abandoned', 'Abandoned'),
    ]
    
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='design_sessions',
        null=True,
        blank=True
    )
    session_key = models.CharField(max_length=40, null=True, blank=True, help_text="For guest sessions")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    current_version = models.ForeignKey(
        'DesignVersion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_sessions'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_accessed_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-last_accessed_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['session_key', 'status']),
        ]
    
    def __str__(self):
        identifier = self.customer.email if self.customer else f"Guest-{self.session_key[:8]}"
        return f"DesignSession-{self.id} ({identifier})"


class DesignVersion(models.Model):
    """
    Design Version - Every upload = new version
    """
    session = models.ForeignKey(DesignSession, on_delete=models.CASCADE, related_name='versions')
    version_number = models.IntegerField()
    
    # Design files
    design_file_url = models.URLField(help_text="Link to design file")
    preview_url = models.URLField(blank=True)
    thumbnail_url = models.URLField(blank=True)
    
    # Metadata
    file_size = models.BigIntegerField(help_text="File size in bytes")
    file_format = models.CharField(max_length=20, blank=True)  # PDF, PNG, etc.
    design_json = models.JSONField(default=dict, blank=True, help_text="Design configuration/state")
    
    # Status
    is_approved = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False, help_text="Locked after approval")
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-version_number']
        unique_together = [['session', 'version_number']]
    
    def __str__(self):
        return f"{self.session} - v{self.version_number}"


class ProofApproval(models.Model):
    """
    Proof Approval - Customer approval/rejection of design proofs
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('revision_requested', 'Revision Requested'),
    ]
    
    design_version = models.ForeignKey('DesignVersion', on_delete=models.CASCADE, related_name='proof_approvals')
    quote = models.ForeignKey('Quote', on_delete=models.CASCADE, related_name='proof_approvals', null=True, blank=True)
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='proof_approvals', null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    comment = models.TextField(blank=True, help_text="Required for rejections")
    approved_by_email = models.EmailField(blank=True, help_text="Email of approver (customer)")
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"ProofApproval-{self.id} - {self.get_status_display()}"


class Shipment(models.Model):
    """
    Shipment - Multi-carrier logistics with split-shipment support
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('preparing', 'Preparing'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='shipments')
    vendor = models.ForeignKey('Vendor', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Shipment identification
    shipment_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    tracking_id = models.CharField(max_length=100, blank=True, db_index=True)
    carrier = models.CharField(max_length=100, blank=True, help_text="G4S, DHL, Sendy, etc.")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Line items in this shipment (subset of order items)
    line_items = models.ManyToManyField('OrderItem', related_name='shipments')
    
    # Shipping details
    shipping_address = models.ForeignKey(
        'CustomerAddress',
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.SET_NULL, null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Tracking
    estimated_delivery = models.DateField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking updates (normalized from different carriers)
    tracking_updates = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tracking status updates from carrier API"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'status']),
            models.Index(fields=['tracking_id']),
        ]
    
    def __str__(self):
        return f"Shipment-{self.shipment_number} for {self.order.order_number}"
    
    def save(self, *args, **kwargs):
        if not self.shipment_number:
            year = timezone.now().year
            last_shipment = Shipment.objects.filter(
                shipment_number__startswith=f'SHIP-{year}-'
            ).order_by('shipment_number').last()
            
            if last_shipment:
                try:
                    last_num = int(last_shipment.shipment_number.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
            
            self.shipment_number = f'SHIP-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)


class Promotion(models.Model):
    """
    Advanced Promotions & Loyalty Engine
    Beyond simple coupons - BOGO, tiered discounts, customer-segment pricing
    """
    PROMOTION_TYPE_CHOICES = [
        ('bogo', 'Buy One Get One (BOGO)'),
        ('tiered', 'Tiered Discount (Spend X, Get Y Off)'),
        ('segment', 'Customer Segment Pricing'),
        ('loyalty', 'Loyalty Points Discount'),
        ('first_time', 'First-Time Customer Discount'),
    ]
    
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    promotion_type = models.CharField(max_length=20, choices=PROMOTION_TYPE_CHOICES)
    
    # BOGO settings
    buy_quantity = models.IntegerField(null=True, blank=True)
    get_quantity = models.IntegerField(null=True, blank=True)
    get_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bogo_promotions'
    )
    
    # Tiered discount settings
    tier_rules = models.JSONField(
        default=list,
        blank=True,
        help_text="[{'min_spend': 10000, 'discount_amount': 1000}, ...]"
    )
    
    # Segment pricing
    customer_segments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of customer segment IDs or types"
    )
    segment_discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Eligibility
    eligible_products = models.ManyToManyField(Product, blank=True, related_name='promotions')
    eligible_categories = models.ManyToManyField('ProductCategory', blank=True)
    minimum_order_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Validity
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Usage limits
    usage_limit = models.IntegerField(null=True, blank=True)
    usage_limit_per_customer = models.IntegerField(null=True, blank=True, default=1)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-starts_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_promotion_type_display()})"


class MaterialInventory(models.Model):
    """
    Inventory & Material Commitment 
    Virtual stock tracking for raw materials
    """
    # Link to ProductVariableOption ("300gsm Matte Paper")
    product_variable_option = models.ForeignKey(
        'ProductVariableOption',
        on_delete=models.CASCADE,
        related_name='inventory',
        null=True,
        blank=True
    )
    
    # Or direct material specification
    material_name = models.CharField(max_length=200, help_text="e.g., 300gsm Matte Paper")
    material_code = models.CharField(max_length=100, blank=True)
    
    # Stock levels
    virtual_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Available stock (can be negative for backorders)"
    )
    reserved_stock = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Stock reserved by approved quotes/paid orders"
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Alert when stock falls below this"
    )
    
    # Unit
    unit = models.CharField(max_length=20, default='pcs')
    
    # Status
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['material_name']
        indexes = [
            models.Index(fields=['material_name', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.material_name} - Stock: {self.virtual_stock} {self.unit}"
    
    @property
    def available_stock(self):
        """Available stock = virtual_stock - reserved_stock"""
        return self.virtual_stock - self.reserved_stock
    
    @property
    def is_low_stock(self):
        """Check if stock is below threshold"""
        return self.available_stock <= self.low_stock_threshold


class Refund(models.Model):
    """
    Refunds - Immutable payment corrections
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('processed', 'Processed'),
        ('rejected', 'Rejected'),
    ]
    
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.PROTECT,
        related_name='refunds'
    )
    order = models.ForeignKey('Order', on_delete=models.PROTECT, related_name='refunds')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Approval
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    # Processing
    refund_transaction_id = models.CharField(max_length=255, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Refund-{self.id} for {self.order.order_number} - {self.amount}"


class CreditNote(models.Model):
    """
    Credit Notes - Store credit for future purchases
    """
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='credit_notes')
    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='credit_notes', null=True, blank=True)
    refund = models.ForeignKey(Refund, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_notes')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance = models.DecimalField(max_digits=12, decimal_places=2, help_text="Remaining credit")
    reason = models.TextField()
    
    expires_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"CreditNote-{self.id} - {self.amount} for {self.customer.email}"


class Adjustment(models.Model):
    """
    Adjustments - Manual price corrections
    """
    ADJUSTMENT_TYPE_CHOICES = [
        ('discount', 'Discount'),
        ('surcharge', 'Surcharge'),
        ('correction', 'Correction'),
    ]
    
    quote = models.ForeignKey(
        'Quote',
        on_delete=models.CASCADE,
        related_name='adjustments',
        null=True,
        blank=True
    )
    order = models.ForeignKey(
        'Order',
        on_delete=models.CASCADE,
        related_name='adjustments',
        null=True,
        blank=True
    )
    
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    
    # Approval required
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='adjustments_created')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        entity = self.quote.quote_id if self.quote else self.order.order_number
        return f"Adjustment-{self.id} - {self.get_adjustment_type_display()} for {entity}"


class WebhookSubscription(models.Model):
    """
    Webhook Subscriptions - External system integrations
    """
    EVENT_TYPE_CHOICES = [
        ('quote.approved', 'Quote Approved'),
        ('order.created', 'Order Created'),
        ('order.paid', 'Order Paid'),
        ('order.shipped', 'Order Shipped'),
        ('job.completed', 'Job Completed'),
        ('payment.received', 'Payment Received'),
        ('payment.refunded', 'Payment Refunded'),
    ]
    
    name = models.CharField(max_length=200)
    url = models.URLField()
    event_types = models.JSONField(
        default=list,
        help_text="List of event types to subscribe to"
    )
    secret_key = models.CharField(
        max_length=255,
        help_text="Secret key for signing payloads"
    )
    is_active = models.BooleanField(default=True)
    
    # Retry settings
    max_retries = models.IntegerField(default=3)
    retry_delay_seconds = models.IntegerField(default=60)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} - {self.url}"


class WebhookDelivery(models.Model):
    """
    Webhook Delivery Log - Tracks webhook delivery attempts
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    subscription = models.ForeignKey('WebhookSubscription', on_delete=models.CASCADE, related_name='deliveries')
    event = models.ForeignKey('TimelineEvent', on_delete=models.CASCADE, related_name='webhook_deliveries')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payload = models.JSONField(default=dict)
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    
    attempt_number = models.IntegerField(default=1)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"WebhookDelivery-{self.id} - {self.status}"



# ============================================================================
# VENDOR PORTAL MODELS
# ============================================================================

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta



class PurchaseOrder(models.Model):
    """
    Consolidated Purchase Order model.
    """
    STATUS_CHOICES = [
        ('NEW', 'New - Awaiting Acceptance'),
        ('ACCEPTED', 'Accepted'),
        ('IN_PRODUCTION', 'In Production'),
        ('AWAITING_APPROVAL', 'Awaiting Proof Approval'),
        ('BLOCKED', 'Blocked'),
        ('AT_RISK', 'At Risk'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    MILESTONE_CHOICES = [
        ('awaiting_acceptance', 'Awaiting Acceptance'),
        ('in_production', 'In Production'),
        ('quality_check', 'Quality Check'),
        ('completed', 'Completed'),
    ]

    po_number = models.CharField(max_length=50, unique=True, editable=False)
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='purchase_orders')
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='purchase_orders')
    
    product_type = models.CharField(max_length=255)
    product_description = models.TextField(blank=True)
    quantity = models.PositiveIntegerField()
    
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEW')
    milestone = models.CharField(max_length=50, choices=MILESTONE_CHOICES, default='awaiting_acceptance')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    required_by = models.DateField()
    due_date = models.DateTimeField(null=True, blank=True)
    
    vendor_accepted = models.BooleanField(default=False)
    vendor_accepted_at = models.DateTimeField(null=True, blank=True)
    vendor_notes = models.TextField(blank=True)
    
    last_activity_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_on_time = models.BooleanField(default=False)
    has_issues = models.BooleanField(default=False)
    
    is_blocked = models.BooleanField(default=False)
    blocked_reason = models.TextField(blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    
    assets_acknowledged = models.BooleanField(default=False)
    assets_acknowledged_at = models.DateTimeField(null=True, blank=True)
    shipping_method = models.CharField(max_length=20, blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    ready_for_pickup = models.BooleanField(default=False)
    
    invoice_sent = models.BooleanField(default=False)
    invoice_paid = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.po_number} - {self.vendor.name}"

    def save(self, *args, **kwargs):
        if not self.po_number:
            year = timezone.now().year
            last_po = PurchaseOrder.objects.filter(po_number__startswith=f'PO-{year}-').order_by('po_number').last()
            new_number = (int(last_po.po_number.split('-')[-1]) + 1) if last_po else 1
            self.po_number = f'PO-{year}-{new_number:04d}'
        
        if self.unit_cost and self.quantity:
            self.total_cost = self.unit_cost * self.quantity
            
        if self.required_by and not self.due_date:
            self.due_date = timezone.make_aware(timezone.datetime.combine(self.required_by, timezone.datetime.min.time()))
            
        super().save(*args, **kwargs)

    @property
    def days_until_due(self):
        if self.status == 'COMPLETED' or not self.required_by:
            return 0
        delta = self.required_by - timezone.now().date()
        return max(0, delta.days)


class PurchaseOrderNote(models.Model):
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='notes')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=20)
    message = models.TextField()
    file_attachment = models.FileField(upload_to='po_notes/%Y/%m/', null=True, blank=True)
    read_by = models.ManyToManyField(User, related_name='read_po_notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    @property
    def has_attachment(self):
        return bool(self.file_attachment)





class VendorInvoice(models.Model):
    """
    Invoice submitted by vendor for completed work.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    vendor_invoice_ref = models.CharField(max_length=100, blank=True)
    
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='vendor_invoices')
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='vendor_invoices')
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='vendor_invoices')
    
    invoice_date = models.DateField(default=timezone.now)
    due_date = models.DateField()
    
    line_items = models.JSONField(default=list)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    invoice_file = models.FileField(upload_to='vendor_invoices/%Y/%m/', null=True, blank=True)
    
    # Approval fields
    validation_errors = models.JSONField(default=list, blank=True, help_text="Validation errors from invoice validation service")
    validation_warnings = models.JSONField(default=list, blank=True, help_text="Validation warnings")
    is_validated = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices_approved')
    rejection_reason = models.TextField(blank=True, null=True)
    
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Ensure line_items is never NULL (default to empty list)
        if self.line_items is None:
            self.line_items = []
        
        if not self.invoice_number:
            year = timezone.now().year
            last_invoice = VendorInvoice.objects.filter(invoice_number__startswith=f'INV-{year}-').order_by('invoice_number').last()
            new_number = (int(last_invoice.invoice_number.split('-')[-1]) + 1) if last_invoice else 1
            self.invoice_number = f'INV-{year}-{new_number:04d}'
        
        if self.subtotal:
            self.tax_amount = (self.subtotal * self.tax_rate) / 100
            self.total_amount = self.subtotal + self.tax_amount
        
        super().save(*args, **kwargs)


class PurchaseOrderProof(models.Model):
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='proofs')
    proof_image = models.ImageField(upload_to='po_proofs/')
    description = models.TextField(blank=True, help_text="Notes or context about this proof")
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)


class PurchaseOrderIssue(models.Model):
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='issues')
    issue_type = models.CharField(max_length=50)
    description = models.TextField()
    status = models.CharField(max_length=20, default='open')
    created_at = models.DateTimeField(auto_now_add=True)


class MaterialSubstitutionRequest(models.Model):
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='substitution_requests')
    original_material = models.CharField(max_length=200)
    proposed_material = models.CharField(max_length=200)
    match_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    justification = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


class QuickBooksToken(models.Model):
    """Store QuickBooks OAuth tokens for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='quickbooks_token')
    access_token = models.TextField()
    refresh_token = models.TextField()
    realm_id = models.CharField(max_length=100)
    token_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"QB Token - {self.user.username}"
    
    def is_expired(self):
        return timezone.now() > self.token_expires_at


# ============================================================================
# CLIENT PORTAL MODELS
# ============================================================================

class ClientPortalUser(models.Model):
    """
    Client Portal User - Access to client's account/orders/invoices
    Linked to Client (B2B Account)
    """
    CLIENT_ROLES = [
        ('owner', 'Account Owner'),
        ('admin', 'Portal Administrator'),
        ('user', 'Regular User'),
        ('viewer', 'View-Only Access'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_portal_user')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='portal_users')
    role = models.CharField(max_length=20, choices=CLIENT_ROLES, default='user')
    
    # Permissions
    can_view_orders = models.BooleanField(default=True)
    can_place_orders = models.BooleanField(default=True)
    can_view_invoices = models.BooleanField(default=True)
    can_view_payments = models.BooleanField(default=True)
    can_submit_tickets = models.BooleanField(default=True)
    can_access_documents = models.BooleanField(default=True)
    can_manage_users = models.BooleanField(default=False)  # Admin only
    
    # Status
    is_active = models.BooleanField(default=True)
    email_verified = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'client']]
    
    def __str__(self):
        return f"{self.user.username} - {self.client.client_id} ({self.role})"


class ClientOrder(models.Model):
    """
    Client Portal Order - Represents a Quote converted to Order for B2B Clients
    Linked to Quote for tracking purposes
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('acknowledged', 'Acknowledged'),
        ('in_production', 'In Production'),
        ('ready', 'Ready for Shipment'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Identification
    order_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='portal_orders')
    quote = models.ForeignKey(Quote, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_orders')
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_portal_orders')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Delivery Info
    shipping_address = models.TextField()
    delivery_date = models.DateField(null=True, blank=True)
    special_instructions = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='client_orders_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"CO-{self.order_number} - {self.client.client_id}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            year = timezone.now().year
            last_order = ClientOrder.objects.filter(
                order_number__startswith=f'CO-{year}-'
            ).order_by('order_number').last()
            
            if last_order:
                last_num = int(last_order.order_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.order_number = f'CO-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)


class ClientOrderItem(models.Model):
    """Items in a Client Order"""
    order = models.ForeignKey(ClientOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    
    # Details
    product_name = models.CharField(max_length=255)
    product_sku = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Specifications
    specifications = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity}x {self.product_name} - Order {self.order.order_number}"


class ClientInvoice(models.Model):
    """
    Client Portal Invoice - Generated from Orders/Jobs
    Synced with QuickBooks
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('overdue', 'Overdue'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Identification
    invoice_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='portal_invoices')
    order = models.ForeignKey(ClientOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance_due = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Dates
    invoice_date = models.DateField()
    due_date = models.DateField()
    issued_at = models.DateTimeField(null=True, blank=True)
    
    # QB Integration
    qb_invoice_id = models.CharField(max_length=255, blank=True, db_index=True)
    is_synced_to_qb = models.BooleanField(default=False)
    qb_last_sync_at = models.DateTimeField(null=True, blank=True)
    
    # Description
    description = models.TextField(blank=True)
    line_items_json = models.JSONField(default=list, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['invoice_number']),
        ]
    
    def __str__(self):
        return f"INV-{self.invoice_number} - {self.client.client_id}"
    
    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            last_invoice = ClientInvoice.objects.filter(
                invoice_number__startswith=f'INV-{year}-'
            ).order_by('invoice_number').last()
            
            if last_invoice:
                last_num = int(last_invoice.invoice_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.invoice_number = f'INV-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)


class ClientPayment(models.Model):
    """
    Client Portal Payment Record - Track payments from clients
    Synced with QB Payments
    """
    PAYMENT_METHODS = [
        ('credit_card', 'Credit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('mpesa', 'M-Pesa'),
        ('paypal', 'PayPal'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    # Identification
    payment_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='portal_payments')
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    
    # Amount
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # QB Integration
    qb_payment_id = models.CharField(max_length=255, blank=True, db_index=True)
    is_synced_to_qb = models.BooleanField(default=False)
    
    # Reference
    reference_number = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['payment_number']),
        ]
    
    def __str__(self):
        return f"PAY-{self.payment_number} - {self.client.client_id}"
    
    def save(self, *args, **kwargs):
        if not self.payment_number:
            year = timezone.now().year
            month = timezone.now().month
            last_payment = ClientPayment.objects.filter(
                payment_number__startswith=f'PAY-{year}{month:02d}-'
            ).order_by('payment_number').last()
            
            if last_payment:
                last_num = int(last_payment.payment_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.payment_number = f'PAY-{year}{month:02d}-{new_num:04d}'
        
        super().save(*args, **kwargs)


class ClientSupportTicket(models.Model):
    """
    Client Portal Support Ticket - Track client support requests
    """
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('awaiting_client', 'Awaiting Client'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]
    
    CATEGORY_CHOICES = [
        ('order', 'Order Issue'),
        ('invoice', 'Invoice/Billing'),
        ('delivery', 'Delivery'),
        ('quality', 'Quality'),
        ('technical', 'Technical'),
        ('other', 'Other'),
    ]
    
    # Identification
    ticket_number = models.CharField(max_length=50, unique=True, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='support_tickets')
    
    # Content
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    
    # Linked items
    order = models.ForeignKey(ClientOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_tickets')
    
    # Status
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_support_tickets')
    
    # Resolution
    resolution_notes = models.TextField(blank=True)
    
    # Tracking
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_support_tickets')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'status']),
            models.Index(fields=['ticket_number']),
        ]
    
    def __str__(self):
        return f"TKT-{self.ticket_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            year = timezone.now().year
            last_ticket = ClientSupportTicket.objects.filter(
                ticket_number__startswith=f'TKT-{year}-'
            ).order_by('ticket_number').last()
            
            if last_ticket:
                last_num = int(last_ticket.ticket_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.ticket_number = f'TKT-{year}-{new_num:05d}'
        
        super().save(*args, **kwargs)


class ClientTicketReply(models.Model):
    """Replies to support tickets"""
    ticket = models.ForeignKey(ClientSupportTicket, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='ticket_replies')
    
    message = models.TextField()
    attachment_url = models.URLField(blank=True)
    
    is_internal = models.BooleanField(default=False, help_text="Internal note not visible to client")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reply to {self.ticket.ticket_number}"


class ClientDocumentLibrary(models.Model):
    """
    Client Portal Document Library - Store client-accessible documents
    """
    DOC_TYPES = [
        ('invoice', 'Invoice'),
        ('quote', 'Quote'),
        ('specification', 'Specification'),
        ('artwork', 'Artwork'),
        ('proof', 'Proof'),
        ('manual', 'Manual'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]
    
    # Identification
    document_number = models.CharField(max_length=50, editable=False, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='document_library')
    
    # Details
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPES)
    
    # Linked items
    order = models.ForeignKey(ClientOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    
    # File
    file_url = models.URLField()
    file_size = models.IntegerField(help_text="Size in bytes")
    file_format = models.CharField(max_length=10)  # pdf, docx, xlsx, etc
    
    # Access Control
    is_public = models.BooleanField(default=True)
    accessible_by = models.ManyToManyField(ClientPortalUser, blank=True, related_name='accessible_documents')
    
    # Tracking
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', 'doc_type']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.client.client_id}"


class ClientPortalNotification(models.Model):
    """
    Client Portal Notifications - Sent to portal users
    """
    NOTIFICATION_TYPES = [
        ('order_confirmed', 'Order Confirmed'),
        ('order_status_update', 'Order Status Update'),
        ('invoice_issued', 'Invoice Issued'),
        ('payment_received', 'Payment Received'),
        ('delivery_scheduled', 'Delivery Scheduled'),
        ('ticket_reply', 'Support Ticket Reply'),
        ('announcement', 'Announcement'),
        ('reminder', 'Reminder'),
    ]
    
    portal_user = models.ForeignKey(ClientPortalUser, on_delete=models.CASCADE, related_name='notifications')
    
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Links
    order = models.ForeignKey(ClientOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    ticket = models.ForeignKey(ClientSupportTicket, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    # Status
    is_read = models.BooleanField(default=False)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['portal_user', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} - {self.portal_user.user.username}"


class ClientActivityLog(models.Model):
    """
    Client Portal Activity Log - Track user actions
    """
    ACTION_TYPES = [
        ('order_created', 'Order Created'),
        ('order_updated', 'Order Updated'),
        ('order_submitted', 'Order Submitted'),
        ('invoice_viewed', 'Invoice Viewed'),
        ('invoice_downloaded', 'Invoice Downloaded'),
        ('payment_made', 'Payment Made'),
        ('ticket_created', 'Ticket Created'),
        ('document_downloaded', 'Document Downloaded'),
        ('login', 'Login'),
        ('profile_updated', 'Profile Updated'),
    ]
    
    portal_user = models.ForeignKey(ClientPortalUser, on_delete=models.CASCADE, related_name='activity_logs')
    
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    description = models.TextField()
    
    # Context
    order = models.ForeignKey(ClientOrder, on_delete=models.SET_NULL, null=True, blank=True)
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    
    # IP and user agent
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['portal_user', 'action_type']),
        ]
    
    def __str__(self):
        return f"{self.action_type} - {self.portal_user.user.username}"


# ============================================================================
# APPROVAL & AUTHORIZATION MODELS
# ============================================================================

class ApprovalThreshold(models.Model):
    """
    Defines approval thresholds for different user roles.
    Limits spending authority by amount.
    """
    ROLE_CHOICES = [
        ('pt_member', 'Production Team Member'),
        ('pt_manager', 'Production Team Manager'),
        ('director', 'Director'),
        ('ceo', 'CEO'),
    ]
    
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Minimum invoice amount this role can approve")
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Maximum invoice amount this role can approve (0 = unlimited)")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['min_amount']
    
    def __str__(self):
        max_str = f"to {self.max_amount}" if self.max_amount > 0 else "unlimited"
        return f"{self.get_role_display()}: {self.min_amount} {max_str}"
    
    @staticmethod
    def get_user_threshold(user):
        """Get the approval threshold for a specific user based on their role/group"""
        if user.is_superuser:
            return ApprovalThreshold.objects.filter(
                role='ceo',
                is_active=True
            ).first()
        
        if user.groups.filter(name='Production Team Manager').exists():
            return ApprovalThreshold.objects.filter(
                role='pt_manager',
                is_active=True
            ).first()
        
        if user.groups.filter(name='Director').exists():
            return ApprovalThreshold.objects.filter(
                role='director',
                is_active=True
            ).first()
        
        if user.groups.filter(name='Production Team').exists():
            return ApprovalThreshold.objects.filter(
                role='pt_member',
                is_active=True
            ).first()
        
        return None
    
    @staticmethod
    def can_user_approve_amount(user, amount):
        """Check if a user can approve an invoice of a specific amount"""
        threshold = ApprovalThreshold.get_user_threshold(user)
        
        if not threshold:
            return False, f"No approval threshold configured for {user.username}"
        
        if not threshold.is_active:
            return False, f"Approval threshold for {threshold.get_role_display()} is inactive"
        
        if amount < threshold.min_amount:
            return False, f"Amount KES {amount} is below minimum approval amount KES {threshold.min_amount}"
        
        if threshold.max_amount > 0 and amount > threshold.max_amount:
            return False, f"Amount KES {amount} exceeds maximum approval amount KES {threshold.max_amount} for {threshold.get_role_display()}"
        
        return True, f"User can approve this amount"


class InvoiceDispute(models.Model):
    """
    Track disputes on invoices - wrong amount, missing items, etc.
    """
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('vendor_responded', 'Vendor Responded'),
        ('pt_reviewing', 'PT Reviewing'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
    ]
    
    invoice = models.ForeignKey('VendorInvoice', on_delete=models.CASCADE, related_name='disputes')
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='invoice_disputes')
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Resolution
    resolution_notes = models.TextField(blank=True, null=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='disputes_resolved')
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='disputes_created')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dispute on {self.invoice.invoice_number}: {self.title}"


class InvoiceDisputeResponse(models.Model):
    """
    Vendor response to a dispute
    """
    dispute = models.ForeignKey(InvoiceDispute, on_delete=models.CASCADE, related_name='responses')
    
    message = models.TextField()
    attachment = models.FileField(upload_to='dispute_attachments/%Y/%m/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dispute_responses')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Response to {self.dispute.id} - {self.created_at.strftime('%Y-%m-%d')}"


class JobProgressUpdate(models.Model):
    """
    Track vendor progress updates on jobs
    """
    job_vendor_stage = models.ForeignKey('JobVendorStage', on_delete=models.CASCADE, related_name='progress_updates')
    
    progress_percentage = models.PositiveIntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Progress {self.progress_percentage}% - {self.job_vendor_stage.job.job_number}"


class VendorPerformanceMetrics(models.Model):
    """
    Aggregate vendor performance metrics
    """
    vendor = models.OneToOneField('Vendor', on_delete=models.CASCADE, related_name='performance_metrics')
    
    # On-time metrics
    total_jobs = models.IntegerField(default=0)
    on_time_jobs = models.IntegerField(default=0)
    on_time_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Quality metrics
    qc_passed_jobs = models.IntegerField(default=0)
    qc_failed_jobs = models.IntegerField(default=0)
    qc_pass_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Response metrics
    avg_response_time_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Financial metrics
    total_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    approved_invoice_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dispute_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Vendor Performance Metrics"
    
    def __str__(self):
        return f"Metrics for {self.vendor.name}"


class ProfitabilityAnalysis(models.Model):
    """
    Profitability calculations for jobs/vendors/products
    """
    ENTITY_TYPE_CHOICES = [
        ('job', 'Job'),
        ('vendor', 'Vendor'),
        ('product', 'Product'),
        ('process', 'Process'),
    ]
    
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.IntegerField()  # References Job.id, Vendor.id, etc.
    
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    margin = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-period_end', '-margin_percentage']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]
    
    def __str__(self):
        return f"{self.entity_type} {self.entity_id}: {self.margin_percentage}% margin"


# ============================================================================
# STOREFRONT MODELS (Customer-Facing Features)
# ============================================================================

import uuid


class StorefrontProduct(models.Model):
    """
    Public product view for storefront catalog
    Links to existing Product model for storefront visibility
    """
    product_id = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=255)
    description_short = models.CharField(max_length=500, blank=True)
    description_long = models.TextField(blank=True)
    
    # Product category & visibility
    category = models.CharField(max_length=100, db_index=True)
    storefront_visible = models.BooleanField(default=True, db_index=True)
    show_price = models.BooleanField(default=True)
    
    # Pricing
    base_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    price_range_min = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    price_range_max = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Pricing tiers (JSON: [{min_qty, max_qty, price_per_unit}, ...])
    pricing_tiers = models.JSONField(
        default=list,
        help_text="Quantity-based pricing: [{min_qty, max_qty, price_per_unit}]"
    )
    
    # Images
    hero_image = models.URLField(blank=True)
    gallery_images = models.JSONField(default=list, blank=True)
    
    # Customization
    customization_level = models.CharField(
        max_length=50,
        choices=[
            ('non_customizable', 'Non-Customizable'),
            ('semi_customizable', 'Semi-Customizable'),
            ('fully_customizable', 'Fully Customizable'),
        ],
        default='semi_customizable'
    )
    available_customizations = models.JSONField(
        default=dict,
        help_text="Available properties: {size, color, material, finish, ...}"
    )
    
    # Turnaround times
    turnaround_standard_days = models.IntegerField(default=7)
    turnaround_rush_days = models.IntegerField(default=3)
    turnaround_rush_surcharge = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=1000,
        help_text="Additional cost for rush turnaround per item"
    )
    turnaround_expedited_days = models.IntegerField(default=1)
    turnaround_expedited_surcharge = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=2500,
        help_text="Additional cost for expedited turnaround per item"
    )
    
    # Minimum order quantity
    minimum_order_quantity = models.IntegerField(default=1)
    
    # Management
    featured = models.BooleanField(default=False, db_index=True)
    sort_order = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    review_count = models.IntegerField(default=0)
    
    # Dates
    published_at = models.DateTimeField(auto_now_add=True)
    unpublished_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['sort_order', '-featured', 'name']
        indexes = [
            models.Index(fields=['storefront_visible', 'category']),
            models.Index(fields=['featured']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.product_id} - {self.name}"
    
    def get_price_for_quantity(self, quantity):
        """Calculate unit price based on quantity tier"""
        if not self.pricing_tiers:
            return self.base_price
        
        for tier in self.pricing_tiers:
            if tier['min_qty'] <= quantity <= tier.get('max_qty', float('inf')):
                return Decimal(str(tier['price_per_unit']))
        
        return self.base_price


class EstimateQuote(models.Model):
    """
    Draft/Estimate Quote created by customer from storefront
    Not yet in system - anonymous or awaiting AM review
    """
    STATUS_CHOICES = [
        ('draft_unsaved', 'Draft - Not Saved'),
        ('shared_with_am', 'Shared with Account Manager'),
        ('converted_to_quote', 'Converted to Official Quote'),
        ('archived', 'Archived'),
    ]
    
    estimate_id = models.CharField(max_length=20, unique=True, editable=False)
    share_token = models.CharField(
        max_length=100, 
        unique=True, 
        db_index=True,
        help_text="Public share token for viewing estimate"
    )
    
    # Customer information
    customer_name = models.CharField(max_length=255)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20)
    customer_company = models.CharField(max_length=255, blank=True)
    
    # Quote details
    line_items = models.JSONField(
        default=list,
        help_text="Line items: [{product_id, quantity, properties, notes, unit_price, line_total}]"
    )
    subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tax_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    total_amount = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Options
    turnaround_time = models.CharField(
        max_length=50,
        choices=[
            ('standard', 'Standard (7 days)'),
            ('rush', 'Rush (3 days)'),
            ('expedited', 'Expedited (1 day)'),
        ],
        default='standard'
    )
    delivery_method = models.CharField(
        max_length=50,
        choices=[
            ('pickup', 'Pickup'),
            ('courier_nairobi', 'Courier (Nairobi)'),
            ('courier_nationwide', 'Courier (Nationwide)'),
        ],
        blank=True
    )
    payment_terms = models.CharField(
        max_length=50,
        choices=[
            ('prepaid', 'Prepaid (Full payment before production)'),
            ('net7', 'Net 7 Days'),
            ('net15', 'Net 15 Days'),
            ('net30', 'Net 30 Days'),
        ],
        default='prepaid'
    )
    special_notes = models.TextField(blank=True)
    
    # Status & sharing
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='draft_unsaved',
        db_index=True
    )
    shared_via = models.CharField(
        max_length=50,
        choices=[
            ('whatsapp', 'WhatsApp'),
            ('email', 'Email'),
            ('direct_link', 'Direct Link'),
        ],
        blank=True
    )
    share_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Conversion tracking
    converted_quote_id = models.CharField(
        max_length=20,
        blank=True,
        help_text="Quote ID after conversion"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Estimate expires after this date"
    )
    source = models.CharField(
        max_length=50,
        choices=[
            ('storefront_public', 'Storefront - Public'),
            ('storefront_customer', 'Storefront - Registered Customer'),
        ],
        default='storefront_public'
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['share_token']),
            models.Index(fields=['customer_email']),
        ]
    
    def __str__(self):
        return f"{self.estimate_id} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.estimate_id:
            # Generate estimate ID: EST-YYYY-XXXXX
            year = timezone.now().year
            last = EstimateQuote.objects.filter(
                estimate_id__startswith=f'EST-{year}'
            ).order_by('-estimate_id').first()
            
            if last:
                num = int(last.estimate_id.split('-')[-1]) + 1
            else:
                num = 1
            
            self.estimate_id = f'EST-{year}-{str(num).zfill(5)}'
        
        if not self.share_token:
            self.share_token = str(uuid.uuid4())
        
        # Set expiration (7 days from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        
        super().save(*args, **kwargs)


class StorefrontCustomer(models.Model):
    """
    Storefront customer account
    Created when customer registers on storefront
    """
    CUSTOMER_TYPE_CHOICES = [
        ('b2b', 'B2B - Business'),
        ('b2c', 'B2C - Retail'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='storefront_customer_profile')
    customer_id = models.CharField(max_length=20, unique=True, editable=False)
    
    # Contact info
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=255, blank=True)
    
    # Account details
    profile_picture = models.URLField(blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    customer_type = models.CharField(
        max_length=10,
        choices=CUSTOMER_TYPE_CHOICES,
        default='b2b'
    )
    
    # Sales notes
    notes = models.TextField(blank=True)
    
    # Preferences
    communication_channel = models.CharField(
        max_length=50,
        choices=[
            ('email', 'Email'),
            ('whatsapp', 'WhatsApp'),
            ('call', 'Phone Call'),
            ('chat', 'Chat'),
        ],
        default='email'
    )
    language = models.CharField(
        max_length=10,
        choices=[
            ('en', 'English'),
            ('sw', 'Swahili'),
            ('es', 'Spanish'),
        ],
        default='en'
    )
    newsletter_subscribed = models.BooleanField(default=False)
    
    # Relationships
    linked_client = models.OneToOneField(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='storefront_customer_profile'
    )
    linked_lead = models.OneToOneField(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='storefront_customer_profile'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['customer_type']),
        ]
    
    def __str__(self):
        return f"{self.customer_id} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.customer_id:
            # Generate customer ID: CUST-YYYY-XXXXX
            year = timezone.now().year
            last = StorefrontCustomer.objects.filter(
                customer_id__startswith=f'CUST-{year}'
            ).order_by('-customer_id').first()
            
            if last:
                num = int(last.customer_id.split('-')[-1]) + 1
            else:
                num = 1
            
            self.customer_id = f'CUST-{year}-{str(num).zfill(5)}'
        
        super().save(*args, **kwargs)


class StorefrontMessage(models.Model):
    """
    Messages from chatbot, email inquiries, WhatsApp, phone requests
    Tracks all customer communication
    """
    MESSAGE_TYPE_CHOICES = [
        ('chat', 'Chatbot Chat'),
        ('email_inquiry', 'Email Inquiry'),
        ('whatsapp_inquiry', 'WhatsApp Inquiry'),
        ('call_request', 'Call Request'),
        ('contact_form', 'Contact Form'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('archived', 'Archived'),
    ]
    
    message_id = models.CharField(max_length=20, unique=True, editable=False)
    
    # From customer
    customer = models.ForeignKey(
        StorefrontCustomer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages'
    )
    
    # For anonymous users
    customer_name = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    
    # Message details
    message_type = models.CharField(max_length=50, choices=MESSAGE_TYPE_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    message_content = models.TextField()
    attachments = models.JSONField(default=list, blank=True)
    
    # Communication
    channel = models.CharField(
        max_length=50,
        choices=[
            ('whatsapp', 'WhatsApp'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('chat', 'Chat'),
        ]
    )
    
    # Status & assignment
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='new',
        db_index=True
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_storefront_messages',
        help_text="Account Manager assigned to handle"
    )
    
    # Response
    response_message = models.TextField(blank=True)
    response_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    related_estimate_quote = models.ForeignKey(
        EstimateQuote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['message_type']),
            models.Index(fields=['assigned_to']),
        ]
    
    def __str__(self):
        return f"{self.message_id} - {self.message_type}"
    
    def save(self, *args, **kwargs):
        if not self.message_id:
            # Generate message ID: MSG-YYYY-XXXXX
            year = timezone.now().year
            last = StorefrontMessage.objects.filter(
                message_id__startswith=f'MSG-{year}'
            ).order_by('-message_id').first()
            
            if last:
                num = int(last.message_id.split('-')[-1]) + 1
            else:
                num = 1
            
            self.message_id = f'MSG-{year}-{str(num).zfill(5)}'
        
        super().save(*args, **kwargs)


class ChatbotConversation(models.Model):
    """
    Stores chatbot conversation history
    Enables context awareness and conversation tracking
    """
    conversation_id = models.CharField(max_length=100, unique=True, editable=False)
    
    # Participants
    customer = models.ForeignKey(
        StorefrontCustomer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chatbot_conversations'
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Session ID for anonymous users"
    )
    
    # Messages (JSON array)
    messages = models.JSONField(
        default=list,
        help_text="[{timestamp, sender: 'customer'|'bot', text, action, metadata}]"
    )
    
    # Context & state
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Collected info: {name, email, phone, product_interest, ...}"
    )
    
    # Status
    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    resolved = models.BooleanField(default=False)
    
    # Escalation
    escalated_to_human = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_chatbot_conversations'
    )
    
    # Related objects
    related_estimate_quote = models.ForeignKey(
        EstimateQuote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chatbot_conversations'
    )
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['conversation_id']),
            models.Index(fields=['escalated_to_human']),
        ]
    
    def __str__(self):
        return f"{self.conversation_id}"
    
    def save(self, *args, **kwargs):
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())
        super().save(*args, **kwargs)


class QuotePricingSnapshot(models.Model):
    """
    Audit trail for quote pricing changes
    Tracks estimate creation, AM adjustments, approvals
    """
    SNAPSHOT_TYPE_CHOICES = [
        ('estimate_created', 'Estimate Created'),
        ('adjusted_by_am', 'Adjusted by Account Manager'),
        ('approved_by_customer', 'Approved by Customer'),
        ('quote_created', 'Quote Created'),
        ('quote_adjusted', 'Quote Adjusted'),
    ]
    
    snapshot_id = models.CharField(max_length=50, unique=True, editable=False)
    
    # Related quote/estimate
    estimate_quote = models.ForeignKey(
        EstimateQuote,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='pricing_snapshots'
    )
    quote_id = models.CharField(max_length=20, blank=True)  # For quotes in main system
    
    # Pricing data
    snapshot_type = models.CharField(max_length=50, choices=SNAPSHOT_TYPE_CHOICES)
    base_amount = models.DecimalField(max_digits=15, decimal_places=2)
    adjustments = models.JSONField(default=dict, blank=True)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Who made the change
    applied_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_pricing_snapshots'
    )
    reason = models.TextField(blank=True)
    
    # Timestamp
    snapshot_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        ordering = ['-snapshot_at']
        indexes = [
            models.Index(fields=['estimate_quote', 'snapshot_type']),
            models.Index(fields=['snapshot_type']),
        ]
    
    def __str__(self):
        return f"{self.snapshot_id} - {self.snapshot_type}"
    
    def save(self, *args, **kwargs):
        if not self.snapshot_id:
            self.snapshot_id = f"SNAP-{timezone.now().timestamp()}"
        super().save(*args, **kwargs)


class ProductionUnit(models.Model):
    """
    Represents a single task/production unit within a job
    Jobs can be broken down into multiple units sent to different vendors
    """
    UNIT_TYPE_CHOICES = [
        ('material_sourcing', 'Material Sourcing'),
        ('design_preparation', 'Design Preparation'),
        ('production', 'Production'),
        ('quality_check', 'Quality Check'),
        ('packaging', 'Packaging'),
        ('delivery', 'Delivery'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('pending_po', 'Pending PO'),
        ('po_sent', 'PO Sent'),
        ('accepted', 'Accepted by Vendor'),
        ('in_progress', 'In Progress'),
        ('delayed', 'Delayed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    unit_id = models.CharField(max_length=30, unique=True, editable=False)
    
    # Job relationship
    job = models.ForeignKey(
        'Job',
        on_delete=models.CASCADE,
        related_name='production_units'
    )
    
    # Unit details
    unit_sequence = models.IntegerField(
        help_text="Order of execution (1, 2, 3, ...)"
    )
    unit_type = models.CharField(max_length=50, choices=UNIT_TYPE_CHOICES)
    task_description = models.TextField()
    
    # Vendor
    vendor = models.ForeignKey(
        'Vendor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_units'
    )
    
    # Quantities & costs
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    unit_measure = models.CharField(max_length=50, blank=True, default='units')
    estimated_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    actual_cost = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # Timeline
    estimated_timeline_days = models.IntegerField(validators=[MinValueValidator(1)])
    expected_start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    
    # Status & tracking
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending_po',
        db_index=True
    )
    
    # PO relationship
    purchase_order = models.ForeignKey(
        'PurchaseOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='production_units'
    )
    
    # Notes
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['job', 'unit_sequence']
        unique_together = ('job', 'unit_sequence')
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['vendor']),
        ]
    
    def __str__(self):
        return f"{self.unit_id} - {self.job.job_number}"
    
    def save(self, *args, **kwargs):
        if not self.unit_id:
            # Generate: UNIT-JOB-YYYY-SEQ
            if self.job:
                self.unit_id = f"UNIT-{self.job.job_number}-{str(self.unit_sequence).zfill(2)}"
        super().save(*args, **kwargs)


# ==================== PHASE 2 MODELS ====================

class Message(models.Model):
    """Messaging between vendors and production team"""
    SENDER_TYPES = [
        ('PT', 'Production Team'),
        ('Vendor', 'Vendor'),
    ]
    TASK_STATUS = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('escalated', 'Escalated'),
    ]
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
    ]
    
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='phase2_messages')
    sender_type = models.CharField(max_length=20, choices=SENDER_TYPES)
    sender_id = models.IntegerField()  # User ID
    sender_name = models.CharField(max_length=200)
    recipient_type = models.CharField(max_length=20, choices=SENDER_TYPES)
    recipient_id = models.IntegerField()  # User ID
    recipient_name = models.CharField(max_length=200)
    content = models.TextField()
    
    # Task fields
    is_task = models.BooleanField(default=False)
    task_status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending')
    task_priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS, default='normal')
    task_due_date = models.DateTimeField(null=True, blank=True)
    task_acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['recipient_id', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.sender_name} → {self.recipient_name} ({self.job.job_number})"
    
    def acknowledge_task(self):
        """Mark task as acknowledged"""
        if self.is_task:
            self.task_status = 'acknowledged'
            self.task_acknowledged_at = timezone.now()
            self.save()


class MessageAttachment(models.Model):
    """File attachments in messages"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='message_attachments/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)  # 'pdf', 'jpg', 'png', 'doc'
    file_size = models.IntegerField()  # in bytes
    thumbnail = models.ImageField(upload_to='message_thumbnails/%Y/%m/%d/', null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # for videos, in seconds
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.file_name} ({self.message.id})"


class ProgressUpdate(models.Model):
    """Vendor progress updates on jobs"""
    STATUS_CHOICES = [
        ('on_schedule', 'On Schedule'),
        ('behind', 'Behind'),
        ('ahead', 'Ahead'),
    ]
    
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='progress_updates')
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='progress_updates')
    percentage_complete = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True)
    issues = models.TextField(blank=True)  # Any blockers or issues
    eta = models.DateTimeField(null=True, blank=True)  # Estimated completion
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['vendor', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.job.job_number} - {self.percentage_complete}% ({self.status})"


class ProgressUpdatePhoto(models.Model):
    """Photos attached to progress updates"""
    progress_update = models.ForeignKey(ProgressUpdate, on_delete=models.CASCADE, related_name='photos')
    photo = models.ImageField(upload_to='progress_photos/%Y/%m/%d/')
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Photo - {self.progress_update.job.job_number}"


class ProofSubmission(models.Model):
    """Vendor proof submissions (deliverables)"""
    PROOF_TYPES = [
        ('sample', 'Sample'),
        ('final', 'Final'),
        ('before_after', 'Before/After'),
    ]
    REVIEW_STATUS = [
        ('pending_review', 'Pending Review'),
        ('approved', 'Approved'),
        ('revision_requested', 'Revision Requested'),
    ]
    
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='proofs')
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='proofs')
    proof_type = models.CharField(max_length=20, choices=PROOF_TYPES)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=REVIEW_STATUS, default='pending_review')
    
    # Review fields
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_proofs')
    review_notes = models.TextField(blank=True)  # Feedback for revisions or notes
    
    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['vendor', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"{self.job.job_number} - {self.proof_type} ({self.status})"


class VendorPerformanceScore(models.Model):
    """Calculated vendor performance metrics"""
    vendor = models.OneToOneField('Vendor', on_delete=models.CASCADE, related_name='vps_history')
    
    # Scores (0-100)
    on_time_delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    communication_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Job counts
    jobs_completed_90_days = models.IntegerField(default=0)
    on_time_jobs = models.IntegerField(default=0)
    
    # Calculated metrics
    on_time_delivery_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_quality_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    average_communication_rating = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Metadata
    last_recalculated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Vendor Performance Score"
        verbose_name_plural = "Vendor Performance Scores"
    
    def __str__(self):
        return f"{self.vendor.name} - {self.average_score:.1f}"


# ==================== PHASE 3: CLIENT PORTAL MODELS ====================

class ClientNotification(models.Model):
    """Notifications for clients about their orders and system events"""
    NOTIFICATION_TYPES = [
        ('order_update', 'Order Update'),
        ('proof_ready', 'Proof Ready'),
        ('message', 'New Message'),
        ('payment', 'Payment Notice'),
        ('alert', 'Alert'),
        ('system', 'System Notification'),
    ]
    
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    
    # Tracking
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Optional link to related object
    link = models.URLField(blank=True, null=True, help_text="Link to related order or resource")
    
    # Related object references
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    proof = models.ForeignKey(ProofSubmission, on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['client', 'is_read']),
        ]
    
    def __str__(self):
        return f"{self.client.client_id} - {self.title[:50]}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class ClientMessage(models.Model):
    """Real-time messaging between clients and PT team"""
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='client_messages')
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='client_messages_sent')
    sender_type = models.CharField(max_length=10, choices=[('client', 'Client'), ('staff', 'PT Staff')])
    
    message = models.TextField()
    attachment = models.FileField(upload_to='client_messages/%Y/%m/%d/', null=True, blank=True)
    
    # Tracking
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.order.job_number} - {self.sender.username} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"
    
    def mark_as_read(self):
        """Mark message as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


class ClientDashboard(models.Model):
    """Client dashboard metrics aggregated for quick view"""
    client = models.OneToOneField('Client', on_delete=models.CASCADE, related_name='dashboard')
    
    # Order metrics
    total_orders = models.IntegerField(default=0)
    active_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    pending_proofs = models.IntegerField(default=0)
    overdue_orders = models.IntegerField(default=0)
    
    # Financial metrics
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Trends (last 30 days)
    orders_this_month = models.IntegerField(default=0)
    avg_completion_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    on_time_delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Tracking
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Client Dashboards"
    
    def __str__(self):
        return f"{self.client.client_id} - Dashboard"
    
    def refresh_metrics(self):
        """Recalculate dashboard metrics from related orders"""
        from django.db.models import Count, Q
        from datetime import timedelta
        
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)
        
        # Count orders by status
        orders = self.client.orders.all()
        self.total_orders = orders.count()
        self.completed_orders = orders.filter(status='completed').count()
        self.active_orders = orders.filter(status__in=['pending', 'in_progress', 'approved']).count()
        self.overdue_orders = orders.filter(deadline__lt=now, status__in=['pending', 'in_progress']).count()
        
        # Count pending proofs
        self.pending_proofs = orders.filter(
            proofs__status='pending_review'
        ).distinct().count()
        
        # Financial metrics
        self.total_spent = sum([o.total_price for o in orders]) or 0
        self.pending_payment = sum([o.total_price for o in orders.filter(payment_status='pending')]) or 0
        
        # This month metrics
        self.orders_this_month = orders.filter(created_at__gte=thirty_days_ago).count()
        
        # Calculate completion time
        completed = orders.filter(status='completed').exclude(completed_at__isnull=True)
        if completed.exists():
            avg_days = sum([(o.completed_at - o.created_at).days for o in completed]) / completed.count()
            self.avg_completion_days = avg_days
        
        self.save()


class ClientFeedback(models.Model):
    """Feedback from clients about orders and vendors"""
    FEEDBACK_TYPES = [
        ('quality', 'Quality'),
        ('cost', 'Cost/Pricing'),
        ('timeline', 'Timeline/Delivery'),
        ('vendor', 'Vendor Performance'),
        ('general', 'General Feedback'),
    ]
    
    RATINGS = [(i, str(i)) for i in range(1, 6)]  # 1-5 star rating
    
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='client_feedback')
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='feedback_given')
    
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPES)
    rating = models.IntegerField(choices=RATINGS, help_text="1 = Poor, 5 = Excellent")
    comment = models.TextField(blank=True, help_text="Detailed feedback or comments")
    
    # Vendor reference (optional)
    vendor = models.ForeignKey('Vendor', on_delete=models.SET_NULL, null=True, blank=True, related_name='client_feedback')
    
    # Proof reference (optional)
    proof = models.ForeignKey(ProofSubmission, on_delete=models.SET_NULL, null=True, blank=True, related_name='client_feedback')
    
    # Status
    is_addressed = models.BooleanField(default=False, help_text="Whether PT has addressed this feedback")
    response = models.TextField(blank=True, help_text="PT response to feedback")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order', 'created_at']),
            models.Index(fields=['client', 'created_at']),
            models.Index(fields=['vendor', 'rating']),
        ]
    
    def __str__(self):
        return f"{self.order.job_number} - {self.feedback_type} ({self.rating}/5)"


# ==================== PHASE 3: ANALYTICS MODELS ====================

class OrderMetrics(models.Model):
    """Monthly order metrics aggregated by client and time period"""
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='order_metrics')
    month = models.DateField(help_text="First day of month for this metric")
    
    # Order counts
    total_orders = models.IntegerField(default=0)
    completed_orders = models.IntegerField(default=0)
    pending_orders = models.IntegerField(default=0)
    cancelled_orders = models.IntegerField(default=0)
    
    # Financial metrics
    total_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Performance metrics
    avg_turnaround_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    on_time_delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Percentage 0-100")
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Quality metrics
    avg_quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    proofs_approved_first_attempt = models.IntegerField(default=0)
    revision_requests = models.IntegerField(default=0)
    
    # Tracking
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-month']
        unique_together = ['client', 'month']
        indexes = [
            models.Index(fields=['client', 'month']),
            models.Index(fields=['month']),
        ]
        verbose_name_plural = "Order Metrics"
    
    def __str__(self):
        return f"{self.client.client_id} - {self.month.strftime('%B %Y')}"


class VendorComparison(models.Model):
    """Compare vendor performance for client insights"""
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='vendor_comparisons')
    vendor1 = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='comparisons_as_vendor1')
    vendor2 = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='comparisons_as_vendor2')
    
    comparison_date = models.DateField(auto_now_add=True)
    
    # Quality scores
    quality_score_1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quality_score_2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Cost comparison (average cost per unit)
    avg_cost_1 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    avg_cost_2 = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Speed (average turnaround days)
    avg_turnaround_1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_turnaround_2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Reliability (on-time percentage)
    on_time_rate_1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    on_time_rate_2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Overall scores
    overall_score_1 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    overall_score_2 = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Recommendation
    winner = models.CharField(max_length=10, choices=[('vendor1', 'Vendor 1'), ('vendor2', 'Vendor 2'), ('tie', 'Tie')], null=True, blank=True)
    reason = models.TextField(blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-comparison_date']
        indexes = [
            models.Index(fields=['client', 'comparison_date']),
            models.Index(fields=['vendor1', 'vendor2']),
        ]
        verbose_name_plural = "Vendor Comparisons"
    
    def __str__(self):
        return f"{self.client.client_id} - {self.vendor1.name} vs {self.vendor2.name}"


class PerformanceAnalytics(models.Model):
    """Monthly performance analytics for vendors"""
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='performance_analytics')
    month = models.DateField(help_text="First day of month for this metric")
    
    # Order statistics
    orders_completed = models.IntegerField(default=0)
    orders_on_time = models.IntegerField(default=0)
    orders_late = models.IntegerField(default=0)
    
    # Quality metrics
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="0-100 scale")
    proofs_approved_first_attempt = models.IntegerField(default=0)
    revision_requests = models.IntegerField(default=0)
    rejection_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Efficiency metrics
    avg_turnaround_hours = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    on_time_delivery_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Cost efficiency
    avg_cost_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cost_variance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="vs average")
    
    # Communication & reliability
    communication_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    reliability_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Trend
    TREND_CHOICES = [
        ('up', 'Improving ↑'),
        ('down', 'Declining ↓'),
        ('stable', 'Stable →'),
    ]
    overall_trend = models.CharField(max_length=10, choices=TREND_CHOICES, default='stable')
    trend_description = models.CharField(max_length=255, blank=True)
    
    # Ranking
    ranking = models.IntegerField(null=True, blank=True, help_text="Rank among all vendors this month")
    percentile = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Percentile 0-100")
    
    # Tracking
    calculated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-month', '-overall_trend']
        unique_together = ['vendor', 'month']
        indexes = [
            models.Index(fields=['vendor', 'month']),
            models.Index(fields=['month', 'ranking']),
        ]
        verbose_name_plural = "Performance Analytics"
    
    def __str__(self):
        return f"{self.vendor.name} - {self.month.strftime('%B %Y')}"


# ==================== PHASE 3: PAYMENT TRACKING MODELS ====================

class PaymentStatus(models.Model):
    """Track payment status for invoices"""
    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('bank_transfer', 'Bank Transfer'),
        ('mpesa', 'M-Pesa'),
        ('cash', 'Cash'),
        ('check', 'Check'),
        ('credit_card', 'Credit Card'),
    ]
    
    # Reference to ClientInvoice (nullable if invoice gets deleted)
    client_invoice = models.OneToOneField('ClientInvoice', on_delete=models.CASCADE, related_name='payment_status', null=True, blank=True)
    
    # Payment amounts
    amount_due = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_pending = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    
    # Dates
    due_date = models.DateField()
    paid_date = models.DateField(null=True, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, null=True, blank=True)
    
    # Tracking
    days_overdue = models.IntegerField(default=0)
    is_overdue = models.BooleanField(default=False)
    last_payment_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['client_invoice', 'status']),
        ]
    
    def __str__(self):
        invoice_num = self.client_invoice.invoice_number if self.client_invoice else "Unknown"
        return f"{invoice_num} - {self.status}"
    
    def calculate_overdue(self):
        """Calculate if payment is overdue and days overdue"""
        if self.status != 'paid' and self.due_date < timezone.now().date():
            self.is_overdue = True
            self.days_overdue = (timezone.now().date() - self.due_date).days
        else:
            self.is_overdue = False
            self.days_overdue = 0


class PaymentHistory(models.Model):
    """Track individual payment transactions"""
    payment_status = models.ForeignKey(PaymentStatus, on_delete=models.CASCADE, related_name='payment_history')
    
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    
    # Transaction details
    reference_number = models.CharField(max_length=100, help_text="Bank reference, M-Pesa ref, etc")
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentStatus.PAYMENT_METHODS
    )
    
    # Additional info
    bank_account = models.CharField(max_length=50, blank=True, null=True)
    depositor_name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, help_text="Internal notes about this payment")
    
    # Reconciliation
    reconciled = models.BooleanField(default=False)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reconciled_payments')
    reconciled_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='payments_recorded')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['payment_status', 'payment_date']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        invoice_num = self.payment_status.client_invoice.invoice_number if self.payment_status.client_invoice else "Unknown"
        return f"{invoice_num} - {self.payment_amount} ({self.payment_date})"


# =====================================
# NEW: BACKEND GAPS - ALERTING & NOTIFICATIONS
# =====================================

class VendorCapacityAlert(models.Model):
    """Alert system for vendor capacity thresholds"""
    ALERT_TYPES = [
        ('capacity_warning', 'Capacity Warning (80%+)'),
        ('capacity_critical', 'Capacity Critical (100%+)'),
        ('overdue_job', 'Overdue Job'),
        ('sla_breach', 'SLA Breach'),
        ('deadline_approaching', 'Deadline Approaching (3 days)'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ]
    
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='capacity_alerts')
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    severity = models.IntegerField(default=1, help_text="1=info, 2=warning, 3=critical")
    
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['vendor', 'status']),
            models.Index(fields=['alert_type']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.vendor.name}"


class POSMilestone(models.Model):
    """Milestone tracking for Purchase Orders"""
    MILESTONE_TYPES = [
        ('acceptance', 'Awaiting Acceptance'),
        ('production_start', 'Production Start'),
        ('production_mid', 'Production Midpoint'),
        ('quality_check', 'Quality Check'),
        ('final_approval', 'Final Approval'),
        ('delivery', 'Delivery'),
    ]
    
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='milestones')
    milestone_type = models.CharField(max_length=30, choices=MILESTONE_TYPES)
    target_date = models.DateField()
    
    completed = models.BooleanField(default=False)
    completed_on_time = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    alert_sent = models.BooleanField(default=False)
    alert_sent_at = models.DateTimeField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['target_date']
        indexes = [
            models.Index(fields=['purchase_order', 'target_date']),
            models.Index(fields=['completed']),
        ]
    
    def __str__(self):
        return f"{self.get_milestone_type_display()} - {self.purchase_order.po_number}"
    
    @property
    def is_overdue(self):
        if self.completed:
            return False
        return timezone.now().date() > self.target_date
    
    @property
    def days_until_due(self):
        if self.completed:
            return 0
        delta = self.target_date - timezone.now().date()
        return max(0, delta.days)


class MaterialSubstitutionApproval(models.Model):
    """Track approval workflow for material substitutions"""
    APPROVAL_STATUS = [
        ('pending', 'Pending PT Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('customer_notified', 'Customer Notified'),
    ]
    
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='substitutions')
    original_material = models.CharField(max_length=255)
    substitute_material = models.CharField(max_length=255)
    reason = models.TextField()
    
    original_cost = models.DecimalField(max_digits=10, decimal_places=2)
    substitute_cost = models.DecimalField(max_digits=10, decimal_places=2)
    
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS, default='pending')
    approval_notes = models.TextField(blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_substitutions')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    customer_notified = models.BooleanField(default=False)
    customer_notified_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval_status']),
        ]
    
    def __str__(self):
        return f"Sub: {self.original_material} → {self.substitute_material}"
    
    @property
    def cost_difference(self):
        return self.substitute_cost - self.original_cost
    
    @property
    def cost_impact_percentage(self):
        if self.original_cost == 0:
            return 0
        return (self.cost_difference / self.original_cost) * 100


class InvoiceHold(models.Model):
    """Track held invoices and reasons"""
    HOLD_REASONS = [
        ('qc_failed', 'QC Inspection Failed'),
        ('pending_approval', 'Pending PT Approval'),
        ('cost_discrepancy', 'Cost Discrepancy'),
        ('validation_error', 'Validation Error'),
        ('dispute', 'Payment Dispute'),
        ('other', 'Other'),
    ]
    
    invoice = models.OneToOneField('VendorInvoice', on_delete=models.CASCADE, related_name='hold')
    hold_reason = models.CharField(max_length=30, choices=HOLD_REASONS)
    hold_details = models.TextField()
    held_at = models.DateTimeField(auto_now_add=True)
    held_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    released = models.BooleanField(default=False)
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='released_holds')
    
    class Meta:
        ordering = ['-held_at']
    
    def __str__(self):
        return f"Hold: {self.invoice.invoice_number} - {self.get_hold_reason_display()}"


class SLAEscalation(models.Model):
    """Track SLA/deadline escalations for overdue jobs"""
    ESCALATION_LEVEL = [
        ('level_1', 'Level 1 - Vendor Alert'),
        ('level_2', 'Level 2 - PT Review'),
        ('level_3', 'Level 3 - Management Escalation'),
    ]
    
    ESCALATION_STATUS = [
        ('pending', 'Pending'),
        ('notified', 'Notified'),
        ('resolved', 'Resolved'),
        ('overdue', 'Still Overdue'),
    ]
    
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='sla_escalations', null=True, blank=True)
    escalation_level = models.CharField(max_length=20, choices=ESCALATION_LEVEL, default='level_1')
    escalation_status = models.CharField(max_length=20, choices=ESCALATION_STATUS, default='pending')
    
    # SLA/Deadline info
    original_deadline = models.DateField(null=True, blank=True)
    current_deadline = models.DateField(null=True, blank=True)
    days_overdue = models.IntegerField(default=0)
    
    # Escalation details
    escalation_reason = models.TextField(default='')
    escalation_notes = models.TextField(blank=True)
    
    # Tracking
    escalated_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    escalated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalations_created')
    
    # Notification tracking
    vendor_notified = models.BooleanField(default=False)
    vendor_notified_at = models.DateTimeField(null=True, blank=True)
    pt_notified = models.BooleanField(default=False)
    pt_notified_at = models.DateTimeField(null=True, blank=True)
    
    # Resolution
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='escalations_resolved')
    resolution_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-escalated_at']
        indexes = [
            models.Index(fields=['escalation_status']),
            models.Index(fields=['escalation_level']),
            models.Index(fields=['purchase_order']),
        ]
    
    def __str__(self):
        return f"Escalation: {self.purchase_order.po_number} - Level {self.escalation_level}"
    
    def mark_as_notified(self, notify_vendor=False, notify_pt=False):
        """Mark notifications as sent"""
        if notify_vendor:
            self.vendor_notified = True
            self.vendor_notified_at = timezone.now()
        if notify_pt:
            self.pt_notified = True
            self.pt_notified_at = timezone.now()
        
        if notify_vendor and notify_pt:
            self.escalation_status = 'notified'
        
        
        self.save()
    
    def resolve(self, resolution_notes='', resolved_by=None):
        """Mark escalation as resolved"""
        self.escalation_status = 'resolved'
        self.resolved_at = timezone.now()
        self.resolved_by = resolved_by
        self.resolution_notes = resolution_notes
        self.save()


class ProgressUpdateBatch(models.Model):
    """Batch progress updates from vendors"""
    purchase_order = models.ForeignKey('PurchaseOrder', on_delete=models.CASCADE, related_name='progress_batches')
    submission_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Progress details
    percentage_complete = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    status = models.CharField(max_length=50, default='on_track', choices=[
        ('on_track', 'On Track'),
        ('at_risk', 'At Risk'),
        ('behind_schedule', 'Behind Schedule'),
    ])
    description = models.TextField(default='')
    notes = models.TextField(blank=True)
    
    # Milestone tracking
    next_milestone = models.CharField(max_length=200, blank=True)
    next_milestone_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-submission_date']
        indexes = [
            models.Index(fields=['purchase_order', '-submission_date']),
        ]
    
    def __str__(self):
        return f"Update for {self.purchase_order.po_number} - {self.percentage_complete}%"


class QCProofLink(models.Model):
    """Link QC inspection results to purchase order proofs"""
    qc_inspection = models.ForeignKey('QCInspection', on_delete=models.CASCADE, related_name='proof_links')
    proof = models.ForeignKey('PurchaseOrderProof', on_delete=models.CASCADE, related_name='qc_links')
    
    # QC result snapshot
    qc_status = models.CharField(max_length=20, default='passed', choices=[
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('conditional', 'Conditional Pass'),
    ])
    qc_notes = models.TextField(blank=True)
    
    # Impact on invoice
    auto_held_invoice = models.BooleanField(default=False)
    hold_reason = models.CharField(max_length=200, blank=True)
    
    # VPS impact
    vps_impact_calculated = models.BooleanField(default=False)
    vps_score_adjustment = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    linked_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-linked_at']
        unique_together = ('qc_inspection', 'proof')
    
    def __str__(self):
        return f"QC {self.qc_inspection.id} → Proof {self.proof.id}"


class VPSRecalculationLog(models.Model):
    """Log all VPS recalculation events"""
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, related_name='vps_logs')
    trigger_type = models.CharField(max_length=50, choices=[
        ('qc_fail', 'QC Failure'),
        ('late_delivery', 'Late Delivery'),
        ('quality_issue', 'Quality Issue'),
        ('manual', 'Manual Recalculation'),
    ])
    
    previous_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    new_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    score_change = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    reason = models.TextField(default='')
    reference_id = models.CharField(max_length=100, blank=True)  # QC ID, PO ID, etc
    
    recalculated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    recalculated_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-recalculated_at']
        indexes = [
            models.Index(fields=['vendor', '-recalculated_at']),
        ]
    
    def __str__(self):
        return f"VPS adjustment for {self.vendor.name}: {self.score_change:+.2f}"


class CustomerNotification(models.Model):
    """Track customer notifications for substitutions"""
    substitution = models.ForeignKey('MaterialSubstitutionApproval', on_delete=models.CASCADE, related_name='notifications')
    
    NOTIFICATION_STATUS = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('acknowledged', 'Acknowledged'),
    ]
    
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS, default='pending')
    notification_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('portal', 'Portal Message'),
    ], default='email')
    
    recipient_email = models.EmailField(blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(default='')
    
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Notification for {self.substitution.id} - {self.status}"


class DeadlineCalculation(models.Model):
    """Store deadline calculations and logic"""
    purchase_order = models.OneToOneField('PurchaseOrder', on_delete=models.CASCADE, related_name='deadline_calc')
    
    # Base inputs
    job_complexity = models.CharField(max_length=20, default='medium', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ])
    vendor_capacity_available = models.IntegerField(default=5, help_text="Days available considering vendor capacity")
    sla_days = models.IntegerField(default=14, help_text="Standard SLA for this product")
    
    # Calculated values
    base_deadline = models.IntegerField(default=0, help_text="Base days required")
    adjusted_deadline = models.IntegerField(default=0, help_text="Final deadline in days")
    risk_score = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    
    # Reasoning
    calculation_notes = models.TextField(default='')
    
    calculated_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    
    class Meta:
        ordering = ['-calculated_at']
    
    def __str__(self):
        return f"Deadline calc for {self.purchase_order.po_number}"


class DeadlineAlert(models.Model):
    """Deadline alerts and notifications for jobs"""
    ALERT_TYPES = [
        ('approaching', 'Deadline Approaching'),
        ('overdue', 'Overdue'),
        ('due_today', 'Due Today'),
        ('due_tomorrow', 'Due Tomorrow'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ]
    
    URGENCY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='deadline_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='medium')
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Dates
    days_until_deadline = models.IntegerField(help_text="Number of days until deadline (negative = overdue)")
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='deadline_alerts_acknowledged')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'status']),
            models.Index(fields=['urgency']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.job.job_number}"
    
    def get_color_class(self):
        """Return CSS color class based on urgency"""
        colors = {
            'low': 'bg-blue-100 text-blue-800 border-blue-300',
            'medium': 'bg-yellow-100 text-yellow-800 border-yellow-300',
            'high': 'bg-orange-100 text-orange-800 border-orange-300',
            'critical': 'bg-red-100 text-red-800 border-red-300',
        }
        return colors.get(self.urgency, 'bg-gray-100 text-gray-800')


class JobFile(models.Model):
    """File uploads associated with job messages"""
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='files')
    message = models.ForeignKey(JobMessage, on_delete=models.CASCADE, related_name='attachments', null=True, blank=True)
    file = models.FileField(upload_to='job_files/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50, help_text="e.g., pdf, doc, image, video")
    file_size = models.IntegerField(help_text="File size in bytes")
    
    # Metadata
    uploaded_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='uploaded_job_files')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Access Control
    is_shared = models.BooleanField(default=False, help_text="Can be downloaded by other team members")
    shared_with = models.ManyToManyField('auth.User', related_name='shared_job_files', blank=True)
    
    # Tracking
    download_count = models.IntegerField(default=0)
    last_downloaded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['job', 'uploaded_at']),
            models.Index(fields=['is_shared']),
        ]
    
    def __str__(self):
        return f"{self.file_name} - {self.job.job_number}"
    
    def get_file_icon(self):
        """Return icon class based on file type"""
        icons = {
            'pdf': 'fa-file-pdf',
            'doc': 'fa-file-word',
            'docx': 'fa-file-word',
            'xls': 'fa-file-excel',
            'xlsx': 'fa-file-excel',
            'ppt': 'fa-file-powerpoint',
            'pptx': 'fa-file-powerpoint',
            'zip': 'fa-file-archive',
            'image': 'fa-file-image',
            'video': 'fa-file-video',
        }
        for key, icon in icons.items():
            if key in self.file_type.lower():
                return icon
        return 'fa-file'


class DocumentShare(models.Model):
    """Document sharing between teams"""
    SHARE_TYPES = [
        ('team', 'Share with Team'),
        ('vendor', 'Share with Vendor'),
        ('client', 'Share with Client'),
        ('production', 'Share with Production'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]
    
    file = models.ForeignKey(JobFile, on_delete=models.CASCADE, related_name='shares')
    share_type = models.CharField(max_length=20, choices=SHARE_TYPES)
    shared_with_user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null=True, blank=True, related_name='received_document_shares')
    shared_with_group = models.ForeignKey('auth.Group', on_delete=models.CASCADE, null=True, blank=True, related_name='received_document_shares')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    share_date = models.DateTimeField(auto_now_add=True)
    access_count = models.IntegerField(default=0)
    last_accessed = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="When sharing expires")
    
    # Tracking
    shared_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='document_shares_made')
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-share_date']
        indexes = [
            models.Index(fields=['file', 'status']),
            models.Index(fields=['shared_with_user']),
        ]
    
    def __str__(self):
        recipient = self.shared_with_user or self.shared_with_group
        return f"Shared {self.file.file_name} with {recipient}"



from django.contrib import admin
from django.utils.html import format_html
from django.db.models import DecimalField
from django.forms import DecimalField as DecimalFormField
from .models import (
    Lead, Client, ClientContact, BrandAsset, ComplianceDocument,
    Quote, ActivityLog, ProductionUpdate, Notification,
    Job, JobProduct, JobAttachment, Product,
    ProductImage, ProductTemplate,
    ProductCategory, ProductSubCategory, ProductFamily, Vendor,
    ProductTag,
    ProductVideo, ProductDownloadableFile, ProductSEO,
    ProductReviewSettings, ProductFAQ, ProductShipping, ProductLegal,
    ProductProduction, ProductChangeHistory,
    PurchaseOrder,
    PrintCategory, SpecGroupLibrary, SpecGroupLibraryOption,
    ProductSpecGroup, SpecOption, SpecOptionRange, ProductCompatibilityRule,
)

# ---------------------- LEAD ----------------------
@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        'lead_id', 'name', 'email', 'phone', 'status',
        'source', 'preferred_contact', 'created_at', 'converted_to_client'
    )
    search_fields = ('name', 'email', 'phone', 'lead_id')
    list_filter = ('status', 'source', 'preferred_contact', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('lead_id', 'created_at', 'updated_at')


# ---------------------- CLIENT CONTACT INLINE ----------------------
class ClientContactInline(admin.TabularInline):
    model = ClientContact
    extra = 1


# ---------------------- BRAND ASSET INLINE ----------------------
class BrandAssetInline(admin.TabularInline):
    model = BrandAsset
    extra = 1


# ---------------------- COMPLIANCE DOCUMENT INLINE ----------------------
class ComplianceDocumentInline(admin.TabularInline):
    model = ComplianceDocument
    extra = 1


# ---------------------- CLIENT ----------------------
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'client_id', 'name', 'email', 'phone', 'client_type',
        'company', 'status', 'risk_rating', 'payment_terms', 'created_at'
    )
    search_fields = ('client_id', 'name', 'email', 'phone', 'company')
    list_filter = ('status', 'client_type', 'risk_rating', 'payment_terms', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('client_id', 'created_at', 'updated_at', 'last_activity')
    inlines = [ClientContactInline, BrandAssetInline, ComplianceDocumentInline]


# ---------------------- BRAND ASSET ----------------------
@admin.register(BrandAsset)
class BrandAssetAdmin(admin.ModelAdmin):
    list_display = ('client', 'asset_type', 'description', 'uploaded_by', 'uploaded_at')
    list_filter = ('asset_type', 'uploaded_at')
    search_fields = ('client__name', 'asset_type', 'description')
    ordering = ('-uploaded_at',)
    autocomplete_fields = ['client']


# ---------------------- COMPLIANCE DOCUMENT ----------------------
@admin.register(ComplianceDocument)
class ComplianceDocumentAdmin(admin.ModelAdmin):
    list_display = ('client', 'document_type', 'expiry_date', 'is_expired', 'uploaded_by', 'uploaded_at')
    list_filter = ('document_type', 'uploaded_at', 'expiry_date')
    search_fields = ('client__name', 'document_type')
    ordering = ('-uploaded_at',)
    autocomplete_fields = ['client']


# ---------------------- QUOTE ----------------------
@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    """Admin configuration for Quote model"""
    
    list_display = (
        'quote_id', 'product_name', 'client', 'lead',
        'quantity', 'unit_price', 'total_amount', 'production_status',
        'status', 'payment_terms', 'include_vat',
        'quote_date', 'valid_until', 'is_expired', 'days_until_expiry',
        'created_by', 'costed_by', 'created_at',
    )
    list_filter = ('status', 'production_status', 'payment_terms', 'include_vat', 'quote_date', 'valid_until')
    search_fields = ('quote_id', 'product_name', 'client__name', 'lead__name')
    date_hierarchy = 'quote_date'
    ordering = ('-created_at',)
    readonly_fields = ('quote_id', 'total_amount', 'created_at', 'updated_at', 'approved_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('quote_id', 'client', 'lead', 'product_name', 'quantity', 'unit_price', 'total_amount')
        }),
        ('Quote Details', {
            'fields': ('payment_terms', 'status', 'production_status', 'include_vat', 'quote_date', 'valid_until', 'due_date', 'approved_at')
        }),
        ('Additional Information', {
            'fields': ('notes', 'terms', 'loss_reason', 'production_cost', 'production_notes')
        }),
        ('Tracking', {
            'fields': ('created_by', 'costed_by', 'created_at', 'updated_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Auto-assign created_by to the logged-in user"""
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)



@admin.register(ProductionUpdate)
class ProductionUpdateAdmin(admin.ModelAdmin):
    list_display = (
        'update_type', 'quote', 'job', 'status', 'progress', 'created_by', 'created_at'
    )
    search_fields = ('quote__quote_id', 'job__job_number', 'notes')
    list_filter = ('update_type', 'status', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    list_filter = ('is_read', 'created_at')
    ordering = ('-created_at',)



# Add this before ActivityLogAdmin
@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'vendor', 'job', 'status', 'total_cost', 'required_by', 'created_at')
    search_fields = ('po_number', 'vendor__name', 'job__job_number') # Required for autocomplete
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)

# ---------------------- ACTIVITY LOG ----------------------
# In clientapp/admin.py

@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'client', 'activity_type', 'created_by', 'created_at')
    search_fields = ('purchase_order__po_number', 'client__name', 'description')
    list_filter = ('activity_type', 'created_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    # Use only fields that exist
    autocomplete_fields = ['purchase_order', 'client']

# ---------------------- JOB PRODUCT INLINE ----------------------
class JobProductInline(admin.TabularInline):
    model = JobProduct
    extra = 1


# ---------------------- JOB ATTACHMENT INLINE ----------------------
class JobAttachmentInline(admin.TabularInline):
    model = JobAttachment
    extra = 1


# ---------------------- JOB ----------------------
@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        'job_number', 'job_name', 'client', 'job_type', 'priority',
        'status', 'start_date', 'expected_completion', 'created_at'
    )
    search_fields = ('job_number', 'job_name', 'client__name', 'person_in_charge__username')
    list_filter = ('job_type', 'priority', 'status', 'start_date', 'expected_completion')
    ordering = ('-created_at',)
    date_hierarchy = 'start_date'
    readonly_fields = ('job_number', 'created_at', 'updated_at')
    inlines = [JobProductInline, JobAttachmentInline]
    autocomplete_fields = ['client']


# ---------------------- JOB PRODUCT ----------------------
@admin.register(JobProduct)
class JobProductAdmin(admin.ModelAdmin):
    list_display = ('job', 'product_name', 'quantity', 'unit', 'created_at')
    search_fields = ('product_name', 'job__job_number')
    ordering = ('-created_at',)
    autocomplete_fields = ['job']


# ---------------------- JOB ATTACHMENT ----------------------
@admin.register(JobAttachment)
class JobAttachmentAdmin(admin.ModelAdmin):
    list_display = ('job', 'file_name', 'file_size', 'uploaded_by', 'uploaded_at')
    search_fields = ('job__job_number', 'file_name')
    ordering = ('-uploaded_at',)
    autocomplete_fields = ['job']


# ==================== PRODUCT CATALOG SECTION ====================

@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'subcategory_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def subcategory_count(self, obj):
        return obj.subcategories.count()
    subcategory_count.short_description = 'Sub-Categories'


@admin.register(ProductSubCategory)
class ProductSubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'product_count']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(ProductFamily)
class ProductFamilyAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'contact_person', 'email', 'phone', 'active']
    list_filter = ['active']
    search_fields = ['name', 'contact_person', 'email', 'user__username']


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'


# ==================== INLINE ADMINS - MUST BE DEFINED BEFORE USE ====================

# Inline admins for related models
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_primary', 'display_order']
    ordering = ['display_order']


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 0
    fields = ['video_url', 'video_type', 'thumbnail', 'display_order']
    ordering = ['display_order']


class ProductDownloadableFileInline(admin.TabularInline):
    model = ProductDownloadableFile
    extra = 0
    fields = ['file_name', 'file', 'file_type', 'description', 'display_order']
    ordering = ['display_order']


class ProductSEOInline(admin.StackedInline):
    model = ProductSEO
    extra = 0
    fieldsets = (
        ('SEO Basics', {
            'fields': (
                'meta_title', 'meta_description', 'slug', 'auto_generate_slug',
                'focus_keyword', 'additional_keywords'
            )
        }),
        ('Display Settings', {
            'fields': (
                'show_price', 'price_display_format', 'show_stock_status'
            )
        }),
        ('Related Products', {
            'fields': (
                'related_products', 'upsell_products', 'frequently_bought_together'
            ),
            'classes': ('collapse',)
        }),
    )
    filter_horizontal = ['related_products', 'upsell_products', 'frequently_bought_together']
    prepopulated_fields = {'slug': ('meta_title',)}


class ProductReviewSettingsInline(admin.StackedInline):
    model = ProductReviewSettings
    extra = 0


class ProductFAQInline(admin.TabularInline):
    model = ProductFAQ
    extra = 1
    fields = ['question', 'answer', 'display_order', 'is_active']
    ordering = ['display_order']


class ProductShippingInline(admin.StackedInline):
    model = ProductShipping
    extra = 0
    fieldsets = (
        ('Shipping Details', {
            'fields': (
                ('shipping_weight', 'shipping_weight_unit'),
                'shipping_class',
            )
        }),
        ('Package Dimensions', {
            'fields': (
                ('package_length', 'package_width', 'package_height'),
                'package_dimension_unit'
            )
        }),
        ('Free Shipping', {
            'fields': ('free_shipping', 'free_shipping_threshold')
        }),
        ('Restrictions', {
            'fields': ('nairobi_only', 'kenya_only', 'no_international')
        }),
        ('Handling', {
            'fields': (
                ('handling_time', 'handling_time_unit'),
                'pickup_available', 'pickup_location'
            )
        }),
    )


class ProductLegalInline(admin.StackedInline):
    model = ProductLegal
    extra = 0
    fieldsets = (
        ('Terms & Policies', {
            'fields': ('product_terms', 'return_policy', 'age_restriction')
        }),
        ('Certifications', {
            'fields': ('cert_fsc', 'cert_eco', 'cert_food_safe')
        }),
        ('Copyright', {
            'fields': ('copyright_notice',)
        }),
    )


class ProductProductionInline(admin.StackedInline):
    model = ProductProduction
    extra = 0
    fieldsets = (
        ('Production Details', {
            'fields': ('production_method_detail', 'machine_equipment')
        }),
        ('Pre-Production Checklist', {
            'fields': (
                'checklist_artwork', 'checklist_preflight',
                'checklist_material', 'checklist_proofs'
            )
        }),
        ('Notes', {
            'fields': ('production_notes',)
        }),
    )


class ProductChangeHistoryInline(admin.TabularInline):
    model = ProductChangeHistory
    extra = 0
    fields = ['changed_at', 'changed_by', 'change_type', 'field_changed']
    readonly_fields = ['changed_at', 'changed_by', 'change_type', 'field_changed', 'old_value', 'new_value']
    can_delete = False
    max_num = 0
    ordering = ['-changed_at']


# ==================== MAIN PRODUCT ADMIN ====================

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'internal_code', 'name', 'status_badge', 'primary_category',
        'sub_category', 'product_type', 'is_visible', 'created_at'
    ]
    list_filter = [
        'status', 'is_visible', 'product_type', 'primary_category',
        'feature_product', 'bestseller_badge', 'new_arrival'
    ]
    search_fields = ['name', 'internal_code', 'short_description']
    filter_horizontal = ['tags']
    readonly_fields = ['created_at', 'updated_at', 'created_by', 'updated_by']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'name', 'internal_code',
                'short_description', 'long_description', 'maintenance', 'technical_specs'
            )
        }),
        ('Classification', {
            'fields': (
                ('primary_category', 'sub_category'),
                'product_type', 'product_family', 'tags'
            )
        }),
        ('Status & Visibility', {
            'fields': (
                'status', 'is_visible', 'visibility',
                ('feature_product', 'bestseller_badge'),
                ('new_arrival', 'new_arrival_expires'),
                'on_sale_badge'
            )
        }),
        ('Product Attributes', {
            'fields': (
                'unit_of_measure',
                ('weight', 'weight_unit'),
                ('length', 'width', 'height', 'dimension_unit'),
                'warranty', 'country_of_origin'
            ),
            'classes': ('collapse',)
        }),
        ('Notes & Comments', {
            'fields': ('internal_notes', 'client_notes'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                ('created_at', 'updated_at'),
                ('created_by', 'updated_by')
            ),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [
        ProductImageInline,
        ProductVideoInline,
        ProductDownloadableFileInline,
        ProductSEOInline,
        ProductReviewSettingsInline,
        ProductFAQInline,
        ProductShippingInline,
        ProductLegalInline,
        ProductProductionInline,
        ProductChangeHistoryInline,
    ]
    
    def status_badge(self, obj):
        colors = {
            'draft': 'gray',
            'published': 'green',
            'archived': 'red'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, 'gray'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
        
        # Create change history
        ProductChangeHistory.objects.create(
            product=obj,
            changed_by=request.user,
            change_type='created' if not change else 'updated',
            notes=f"Product {'created' if not change else 'updated'} via admin"
        )


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['thumbnail_preview', 'product', 'is_primary', 'display_order']
    list_filter = ['is_primary', 'product__primary_category']
    search_fields = ['product__name', 'alt_text']
    list_editable = ['display_order']
    ordering = ['product', 'display_order']
    
    def thumbnail_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover;" />', obj.image.url)
        return '-'
    thumbnail_preview.short_description = 'Preview'


@admin.register(ProductVideo)
class ProductVideoAdmin(admin.ModelAdmin):
    list_display = ['product', 'video_type', 'video_url', 'display_order', 'created_at']
    list_filter = ['video_type', 'product__primary_category']
    search_fields = ['product__name', 'video_url']
    ordering = ['product', 'display_order']


@admin.register(ProductDownloadableFile)
class ProductDownloadableFileAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'product', 'file_type', 'file_size_display', 'display_order', 'uploaded_at']
    list_filter = ['file_type', 'product__primary_category']
    search_fields = ['file_name', 'product__name', 'description']
    ordering = ['product', 'display_order']
    
    def file_size_display(self, obj):
        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"
    file_size_display.short_description = 'File Size'


@admin.register(ProductFAQ)
class ProductFAQAdmin(admin.ModelAdmin):
    list_display = ['question_preview', 'product', 'display_order', 'is_active', 'created_at']
    list_filter = ['is_active', 'product__primary_category']
    search_fields = ['question', 'answer', 'product__name']
    list_editable = ['display_order', 'is_active']
    ordering = ['product', 'display_order']
    
    def question_preview(self, obj):
        return obj.question[:100] + '...' if len(obj.question) > 100 else obj.question
    question_preview.short_description = 'Question'


@admin.register(ProductChangeHistory)
class ProductChangeHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'change_type', 'changed_by', 'changed_at', 'field_changed']
    list_filter = ['change_type', 'changed_at', 'product__primary_category']
    search_fields = ['product__name', 'product__internal_code', 'field_changed', 'notes']
    readonly_fields = ['product', 'changed_by', 'changed_at', 'change_type', 'field_changed', 'old_value', 'new_value', 'notes']
    date_hierarchy = 'changed_at'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


# ==================== LPO (ORDER MANAGEMENT) ADMIN ====================

from .models import LPO

@admin.register(LPO)
class LPOAdmin(admin.ModelAdmin):
    """Admin for Order Management (LPO)"""
    list_display = [
        'lpo_number', 'client', 'total_amount', 'status_badge',
        'payment_terms', 'delivery_date', 'quickbooks_sync_status',
        'created_at', 'created_by'
    ]
    list_filter = ['status', 'synced_to_quickbooks', 'payment_terms', 'created_at']
    search_fields = ['lpo_number', 'client__name', 'notes']
    readonly_fields = [
        'lpo_number', 'created_at', 'approved_at', 'synced_at',
        'quickbooks_invoice_id', 'quickbooks_invoice_number'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 25
    
    fieldsets = (
        ('Order Information', {
            'fields': ('lpo_number', 'client', 'quote', 'status')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'vat_amount', 'total_amount', 'payment_terms')
        }),
        ('Delivery & Notes', {
            'fields': ('delivery_date', 'notes', 'terms_and_conditions')
        }),
        ('QuickBooks Integration', {
            'fields': (
                'synced_to_quickbooks', 'quickbooks_invoice_id',
                'quickbooks_invoice_number', 'synced_at'
            ),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': (
                'created_by', 'created_at',
                'approved_by', 'approved_at'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['sync_to_quickbooks_action', 'mark_as_approved', 'export_orders']
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'approved': '#0066CC',
            'in_production': '#FFD700',
            'completed': '#28A745',
            'cancelled': '#DC3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            colors.get(obj.status, '#6C757D'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def quickbooks_sync_status(self, obj):
        if obj.synced_to_quickbooks:
            return format_html(
                '<span style="color: green;">✓ Synced</span>'
            )
        return format_html(
            '<span style="color: gray;">○ Not Synced</span>'
        )
    quickbooks_sync_status.short_description = 'QB Status'
    
    def sync_to_quickbooks_action(self, request, queryset):
        """Bulk action to sync orders to QuickBooks"""
        synced_count = 0
        for lpo in queryset:
            try:
                lpo.sync_to_quickbooks(user=request.user)
                synced_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error syncing {lpo.lpo_number}: {str(e)}",
                    level='error'
                )
        
        self.message_user(
            request,
            f"Successfully synced {synced_count} order(s) to QuickBooks.",
            level='success'
        )
    sync_to_quickbooks_action.short_description = "Sync selected to QuickBooks"
    
    def mark_as_approved(self, request, queryset):
        updated = queryset.update(status='approved')
        self.message_user(request, f"{updated} order(s) marked as approved.")
    mark_as_approved.short_description = "Mark as Approved"
    
    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        if obj.status == 'approved' and not obj.approved_by:
            obj.approved_by = request.user
            obj.approved_at = timezone.now()
        super().save_model(request, obj, form, change)


# ==================== PRODUCT TEMPLATE ADMIN ====================

from .models import ProductTemplate

@admin.register(ProductTemplate)
class ProductTemplateAdmin(admin.ModelAdmin):
    """Admin for Product Template Management"""
    list_display = [
        'template_thumbnail', 'name', 'product', 'is_premium',
        'is_active', 'usage_count', 'created_at'
    ]
    list_filter = ['is_premium', 'is_active', 'product__primary_category', 'created_at']
    search_fields = ['name', 'product__name', 'description', 'category_tags']
    list_editable = ['is_active']
    readonly_fields = ['created_at', 'template_thumbnail_large']
    
    fieldsets = (
        ('Template Information', {
            'fields': ('product', 'name', 'description')
        }),
        ('Files', {
            'fields': ('template_file', 'thumbnail', 'template_thumbnail_large')
        }),
        ('Settings', {
            'fields': ('category_tags', 'is_premium', 'is_active')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def template_thumbnail(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="60" height="60" style="object-fit: cover; border-radius: 4px;" />',
                obj.thumbnail.url
            )
        return '-'
    template_thumbnail.short_description = 'Preview'
    
    def template_thumbnail_large(self, obj):
        if obj.thumbnail:
            return format_html(
                '<img src="{}" width="300" style="border-radius: 8px;" />',
                obj.thumbnail.url
            )
        return 'No thumbnail available'
    template_thumbnail_large.short_description = 'Template Preview'
    
    def usage_count(self, obj):
        # You can track usage if you have a relationship
        # For now, return a placeholder
        return f"-"
    usage_count.short_description = 'Uses'


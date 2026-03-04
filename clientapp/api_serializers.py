from rest_framework import serializers
from django.contrib.auth.models import User, Group, Permission

from .models import (
    Lead,
    Client,
    ClientContact,
    BrandAsset,
    ComplianceDocument,
    Product,
    Quote,
    QuoteLineItem,
    Job,
    Vendor,
    LPO,
    Payment,
    Notification,
    ActivityLog,
    PropertyType,
    PropertyValue,
    ProductProperty,
    QuantityPricing,
    TurnAroundTime,
    SystemSetting,
    # Costing / process models
    Process,
    ProcessTier,
    ProcessVariable,
    ProductVariable,
    ProductVariableOption,
    ProcessVendor,
    PricingTier,
    VendorTierPricing,
    ProcessVariableRange,
    # Product metadata
    ProductImage,
    ProductVideo,
    ProductDownloadableFile,
    ProductSEO,
    ProductPricing,
    ProductReviewSettings,
    ProductFAQ,
    ProductShipping,
    ProductLegal,
    ProductProduction,
    ProductChangeHistory,
    ProductApprovalRequest,
    ProductTemplate,
    # Operations / QC / delivery / attachments
    JobVendorStage,
    JobNote,
    JobAttachment,
    VendorQuote,
    QCInspection,
    Delivery,
    QuoteAttachment,
    LPOLineItem,
    SystemAlert,
    ProductionUpdate,
    # Storefront models
    Customer,
    CustomerAddress,
    Cart,
    CartItem,
    Order,
    OrderItem,
    Coupon,
    TaxConfiguration,
    DesignTemplate,
    DesignState,
    ProductReview,
    ShippingMethod,
    PaymentTransaction,
    #webhook and other models
    ProductRule,
    TimelineEvent,
    DesignSession,
    DesignVersion,
    ProofApproval,
    Shipment,
    Promotion,
    MaterialInventory,
    Refund,
    CreditNote,
    Adjustment,
    WebhookSubscription,
    WebhookDelivery,
    # Vendor Portal models
    PurchaseOrder,
    VendorInvoice,
    PurchaseOrderProof,
    PurchaseOrderIssue,
    PurchaseOrderNote,
    MaterialSubstitutionRequest,
    # Client Portal models
    ClientPortalUser,
    ClientOrder,
    ClientOrderItem,
    ClientInvoice,
    ClientPayment,
    ClientSupportTicket,
    ClientTicketReply,
    ClientDocumentLibrary,
    ClientPortalNotification,
    ClientActivityLog,
    # Phase 2 models
    Message,
    MessageAttachment,
    ProgressUpdate,
    ProgressUpdatePhoto,
    ProofSubmission,
    VendorPerformanceScore,
    # Phase 3 models
    ClientNotification,
    ClientMessage,
    ClientDashboard,
    ClientFeedback,
    OrderMetrics,
    VendorComparison,
    PerformanceAnalytics,
    PaymentStatus,
    PaymentHistory,
    # Backend Gap models
    VendorCapacityAlert,
    POSMilestone,
    MaterialSubstitutionApproval,
    InvoiceHold,
    SLAEscalation,
    # Phase 2 additional models
    ProgressUpdateBatch,
    QCProofLink,
    VPSRecalculationLog,
    CustomerNotification,
    DeadlineCalculation,
    # Task 8 & 9 models
    DeadlineAlert,
    JobFile,
    DocumentShare,
    JobMessage,
)


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = "__all__"


class ClientContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientContact
        fields = "__all__"


class ClientSerializer(serializers.ModelSerializer):
    contacts = ClientContactSerializer(many=True, read_only=True)

    class Meta:
        model = Client
        fields = "__all__"

    def validate(self, attrs):
        """
        Enforce different field rules for B2B vs B2C clients.
        """
        client_type = attrs.get("client_type")
        if self.instance and not client_type:
            client_type = self.instance.client_type

        # Email is required for B2B, optional for B2C
        if client_type == "B2B" and not attrs.get("email"):
            raise serializers.ValidationError(
                {"email": "Email is required for B2B clients."}
            )

        if client_type == "B2C":
            # Fields that should not be set for B2C clients
            b2b_only_fields = [
                "company",
                "vat_tax_id",
                "kra_pin",
                "industry",
                "credit_limit",
                "default_markup",
                "risk_rating",
                "is_reseller",
            ]
            invalid_fields = [f for f in b2b_only_fields if attrs.get(f)]
            if invalid_fields:
                raise serializers.ValidationError(
                    {"detail": f"Fields {', '.join(invalid_fields)} are only allowed for B2B clients."}
                )

        return super().validate(attrs)

    def to_representation(self, instance):
        """
        Remove B2B-specific fields from the response if the client is B2C.
        This keeps the API response clean and only shows relevant fields.
        """
        ret = super().to_representation(instance)
        
        if instance.client_type == 'B2C':
            # B2B-specific fields to hide for B2C clients
            b2b_fields = [
                'company',
                'vat_tax_id',
                'kra_pin',
                'industry',
                'payment_terms',
                'credit_limit',
                'default_markup',
                'risk_rating',
                'is_reseller',
            ]
            for field in b2b_fields:
                ret.pop(field, None)
        
        return ret


class BrandAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = BrandAsset
        fields = "__all__"


class ComplianceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplianceDocument
        fields = "__all__"


import json
from django.utils import timezone

class ProductPricingSerializer(serializers.ModelSerializer):
    """Serializer for ProductPricing with nested write support"""
    class Meta:
        model = ProductPricing
        fields = [
            'id', 'pricing_model', 'base_cost', 'price_display', 'default_margin',
            'minimum_margin', 'minimum_order_value', 'tier_process', 'formula_process',
            'return_margin', 'production_method', 'rush_lead_time_value', 'rush_lead_time_unit'
        ]
        read_only_fields = ['id']


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for ProductImage"""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'display_order', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']


class ProductVideoSerializer(serializers.ModelSerializer):
    """Serializer for ProductVideo"""
    class Meta:
        model = ProductVideo
        fields = ['id', 'video_url', 'video_type', 'display_order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductSEOSerializer(serializers.ModelSerializer):
    """Serializer for ProductSEO with validation"""
    class Meta:
        model = ProductSEO
        fields = [
            'id', 'meta_title', 'meta_description', 'slug', 'auto_generate_slug',
            'focus_keyword', 'additional_keywords', 'show_price', 
            'price_display_format', 'show_stock_status'
        ]
        read_only_fields = ['id', 'slug']
    
    def validate_meta_title(self, value):
        """Meta title must be max 60 characters"""
        if value and len(value) > 60:
            raise serializers.ValidationError(
                "Meta title must be 60 characters or less (currently {})".format(len(value))
            )
        return value
    
    def validate_meta_description(self, value):
        """Meta description must be max 160 characters"""
        if value and len(value) > 160:
            raise serializers.ValidationError(
                "Meta description must be 160 characters or less (currently {})".format(len(value))
            )
        return value


class ProductChangeHistorySerializer(serializers.ModelSerializer):
    """Serializer for ProductChangeHistory"""
    changed_by_name = serializers.CharField(source='changed_by.get_full_name', read_only=True)
    before_data_parsed = serializers.SerializerMethodField()
    after_data_parsed = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductChangeHistory
        fields = [
            'id', 'changed_by', 'changed_by_name', 'change_type',
            'before_data', 'after_data', 'before_data_parsed', 'after_data_parsed',
            'changed_at'
        ]
        read_only_fields = fields
    
    def get_before_data_parsed(self, obj):
        try:
            return json.loads(obj.before_data) if obj.before_data else {}
        except:
            return {}
    
    def get_after_data_parsed(self, obj):
        try:
            return json.loads(obj.after_data) if obj.after_data else {}
        except:
            return {}


class ProductApprovalRequestSerializer(serializers.ModelSerializer):
    """Serializer for ProductApprovalRequest"""
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, allow_null=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_code = serializers.CharField(source='product.internal_code', read_only=True)
    
    class Meta:
        model = ProductApprovalRequest
        fields = [
            'id', 'product', 'product_name', 'product_code',
            'request_type', 'status', 'is_urgent',
            'requested_by', 'requested_by_name', 'requested_at',
            'assigned_to', 'assigned_to_name',
            'approved_by', 'approved_by_name', 'approved_at',
            'old_value', 'new_value', 'reason_for_change',
            'approval_notes'
        ]
        read_only_fields = [
            'id', 'requested_by', 'requested_at', 'product_name', 'product_code',
            'approved_by', 'approved_at'
        ]



class ProductSerializer(serializers.ModelSerializer):
    """Complete Product serializer with nested relationships"""
    pricing = ProductPricingSerializer(read_only=True)
    seo = ProductSEOSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    videos = ProductVideoSerializer(many=True, read_only=True)
    
    # Computed fields
    can_be_published = serializers.SerializerMethodField()
    has_pricing = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()
    primary_image_url = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.get_full_name', read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'internal_code', 'short_description', 'long_description', 'maintenance',
            'technical_specs', 'primary_category', 'sub_category', 'product_family',
            'visibility', 'feature_product', 'bestseller_badge', 'new_arrival',
            'new_arrival_expires', 'status', 'is_visible', 'customization_level',
            'unit_of_measure', 'unit_of_measure_custom', 'weight', 'weight_unit',
            'length', 'width', 'height', 'dimension_unit', 'warranty',
            'country_of_origin', 'base_price', 'stock_status', 'stock_quantity',
            'track_inventory', 'allow_backorders', 'internal_notes', 'client_notes',
            'product_type',
            'pricing', 'seo', 'images', 'videos',
            'can_be_published', 'has_pricing', 'image_count', 'primary_image_url',
            'completion_percentage', 'created_at', 'updated_at',
            'created_by', 'created_by_name', 'updated_by', 'updated_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'created_by_name', 'updated_by', 'updated_by_name']
    
    def validate(self, data):
        """Validate product pricing rules"""
        # Get current instance status if updating
        instance_status = None
        if self.instance:
            instance_status = self.instance.status
        
        # Allow lenient validation for draft products
        request_status = data.get('status') or instance_status
        is_draft = request_status == 'draft'
        
        customization_level = data.get('customization_level') or (self.instance.customization_level if self.instance else None)
        base_price = data.get('base_price') or (self.instance.base_price if self.instance else None)
        
        # Skip base_price validation for draft mode - only enforce on publish
        if not is_draft:
            if customization_level in ['non_customizable', 'semi_customizable']:
                if base_price is None or base_price <= 0:
                    raise serializers.ValidationError({
                        'base_price': 'Non/Semi-customizable products must have a base price > 0'
                    })
            
            if customization_level == 'fully_customizable':
                if base_price is not None:
                    raise serializers.ValidationError({
                        'base_price': 'Fully customizable products must not have a base price'
                    })
        
        return data
    
    def create(self, validated_data):
        """Create product with nested relationships"""
        pricing_data = validated_data.pop('pricing', {})
        seo_data = validated_data.pop('seo', {})
        
        # Create product
        product = Product.objects.create(**validated_data)
        
        # Create pricing if provided
        if pricing_data:
            ProductPricing.objects.create(product=product, **pricing_data)
        
        # Create SEO if provided
        if seo_data:
            ProductSEO.objects.create(product=product, **seo_data)
        
        return product
    
    def update(self, instance, validated_data):
        """Update product with nested relationships"""
        pricing_data = validated_data.pop('pricing', None)
        seo_data = validated_data.pop('seo', None)
        
        # Update product fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Validate before saving
        instance.full_clean()
        instance.save()
        
        # Update or create pricing
        if pricing_data:
            pricing, _ = ProductPricing.objects.get_or_create(product=instance)
            for attr, value in pricing_data.items():
                setattr(pricing, attr, value)
            pricing.save()
        
        # Update or create SEO
        if seo_data:
            seo, _ = ProductSEO.objects.get_or_create(product=instance)
            for attr, value in seo_data.items():
                setattr(seo, attr, value)
            seo.save()
        
        return instance
    
    def get_can_be_published(self, obj):
        """Check if product can be published"""
        can_publish, _ = obj.can_be_published()
        return can_publish
    
    def get_has_pricing(self, obj):
        """Check if product has pricing configured"""
        return obj.has_costing_process()
    
    def get_image_count(self, obj):
        """Get number of product images"""
        return obj.images.count()
    
    def get_primary_image_url(self, obj):
        """Get primary image URL"""
        primary = obj.images.filter(is_primary=True).first()
        return primary.image.url if primary else None
    
    def get_completion_percentage(self, obj):
        """Calculate product completion percentage"""
        completed_fields = 0
        total_fields = 12
        
        # Check required fields
        if obj.name: completed_fields += 1
        if obj.short_description: completed_fields += 1
        if obj.long_description: completed_fields += 1
        if obj.primary_category: completed_fields += 1
        if obj.base_price and obj.customization_level != 'fully_customizable': completed_fields += 1
        if hasattr(obj, 'images') and obj.images.count() > 0: completed_fields += 1
        if hasattr(obj, 'seo') and obj.seo: completed_fields += 1
        if obj.status == 'published': completed_fields += 1
        
        return int((completed_fields / total_fields) * 100)


class PropertyTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyType
        fields = "__all__"


class PropertyValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyValue
        fields = "__all__"


class ProductPropertySerializer(serializers.ModelSerializer):
    property_value = PropertyValueSerializer(read_only=True)

    class Meta:
        model = ProductProperty
        fields = "__all__"


class QuantityPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuantityPricing
        fields = "__all__"


class TurnAroundTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TurnAroundTime
        fields = "__all__"


class QuoteLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteLineItem
        fields = "__all__"


class QuoteSerializer(serializers.ModelSerializer):
    line_items = QuoteLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Quote
        fields = "__all__"


class JobSerializer(serializers.ModelSerializer):
    person_in_charge_name = serializers.CharField(source='person_in_charge.get_full_name', read_only=True)
    person_in_charge_email = serializers.EmailField(source='person_in_charge.email', read_only=True)
    # Nested serializers for related objects
    client = serializers.SerializerMethodField()
    person_in_charge = serializers.SerializerMethodField()
    
    def get_client(self, obj):
        if obj.client:
            return {
                'id': obj.client.id,
                'name': obj.client.name,
                'email': obj.client.email if hasattr(obj.client, 'email') else None,
            }
        return None
    
    def get_person_in_charge(self, obj):
        if obj.person_in_charge:
            return {
                'id': obj.person_in_charge.id,
                'first_name': obj.person_in_charge.first_name,
                'last_name': obj.person_in_charge.last_name,
                'username': obj.person_in_charge.username,
            }
        return None
    
    class Meta:
        model = Job
        fields = "__all__"


class VendorSerializer(serializers.ModelSerializer):
    user_is_active = serializers.SerializerMethodField()

    def get_user_is_active(self, obj):
        if obj.user:
            return obj.user.is_active
        return None

    class Meta:
        model = Vendor
        fields = "__all__"


class LPOSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True, allow_null=True)
    quote_id = serializers.CharField(source="quote.quote_id", read_only=True, allow_null=True)
    class Meta:
        model = LPO
        fields = "__all__"


class PaymentSerializer(serializers.ModelSerializer):
    lpo_number = serializers.CharField(source="lpo.lpo_number", read_only=True, allow_null=True)
    client_name = serializers.CharField(source="lpo.client.name", read_only=True, allow_null=True)
    class Meta:
        model = Payment
        fields = "__all__"


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"


class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = "__all__"


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = "__all__"


# ===== Costing / Process Serializers =====

class ProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Process
        fields = "__all__"


class ProcessTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessTier
        fields = "__all__"


class ProcessVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessVariable
        fields = "__all__"


class ProductVariableOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariableOption
        fields = "__all__"


class ProductVariableSerializer(serializers.ModelSerializer):
    options = ProductVariableOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ProductVariable
        fields = "__all__"


class ProcessVendorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessVendor
        fields = "__all__"


class PricingTierSerializer(serializers.ModelSerializer):
    class Meta:
        model = PricingTier
        fields = "__all__"


class VendorTierPricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorTierPricing
        fields = "__all__"


class ProcessVariableRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessVariableRange
        fields = "__all__"


# ===== Product Metadata Serializers =====

class ProductImageMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductVideoMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVideo
        fields = "__all__"


class ProductDownloadableFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDownloadableFile
        fields = "__all__"


class ProductReviewSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReviewSettings
        fields = "__all__"


class ProductFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFAQ
        fields = "__all__"


class ProductShippingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductShipping
        fields = "__all__"


class ProductLegalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductLegal
        fields = "__all__"


class ProductProductionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductProduction
        fields = "__all__"


class ProductChangeHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductChangeHistory
        fields = "__all__"


class ProductTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductTemplate
        fields = "__all__"


# ===== QC, Delivery, Attachments, Notes =====

class JobVendorStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobVendorStage
        fields = "__all__"


class JobNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobNote
        fields = "__all__"


class JobAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAttachment
        fields = "__all__"


class VendorQuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorQuote
        fields = "__all__"


class QCInspectionSerializer(serializers.ModelSerializer):
    job_number = serializers.CharField(source="job.job_number", read_only=True, allow_null=True)
    client_name = serializers.CharField(source="job.client.name", read_only=True, allow_null=True)
    quote_id = serializers.CharField(source="job.quote.quote_id", read_only=True, allow_null=True)
    vendor_name = serializers.CharField(source="vendor.name", read_only=True, allow_null=True)
    inspector_name = serializers.CharField(source="inspector.get_full_name", read_only=True, allow_null=True)

    class Meta:
        model = QCInspection
        fields = "__all__"


class DeliverySerializer(serializers.ModelSerializer):
    job_number = serializers.CharField(source="job.job_number", read_only=True, allow_null=True)
    client_name = serializers.CharField(source="job.client.name", read_only=True, allow_null=True)
    quote_id = serializers.CharField(source="job.quote.quote_id", read_only=True, allow_null=True)
    delivery_method = serializers.CharField(source="job.delivery_method", read_only=True, allow_null=True)
    scheduled_delivery_date = serializers.DateField(source="job.delivery_date", read_only=True, allow_null=True)
    class Meta:
        model = Delivery
        fields = "__all__"


class QuoteAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuoteAttachment
        fields = "__all__"


class LPOLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LPOLineItem
        fields = "__all__"


class SystemAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAlert
        fields = "__all__"


class ProductionUpdateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    quote_id = serializers.CharField(source='quote.quote_id', read_only=True)
    
    class Meta:
        model = ProductionUpdate
        fields = "__all__"
    
    def validate(self, attrs):
        """Ensure either job or quote is provided"""
        job = attrs.get('job') or (self.instance.job if self.instance else None)
        quote = attrs.get('quote') or (self.instance.quote if self.instance else None)
        
        if not job and not quote:
            raise serializers.ValidationError("Either job or quote must be provided.")
        
        if job and quote:
            raise serializers.ValidationError("Cannot provide both job and quote.")
        
        return attrs


# ===== User / Group Serializers =====

class PermissionSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Permission
        fields = ["id", "name", "codename", "content_type"]
    
    def get_content_type(self, obj):
        return {
            "app_label": obj.content_type.app_label,
            "model": obj.content_type.model
        }


class GroupSerializer(serializers.ModelSerializer):
    user_count = serializers.IntegerField(read_only=True, required=False)
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Permission.objects.all(),
        source='permissions',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Group
        fields = ["id", "name", "user_count", "permissions", "permission_ids"]


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Group.objects.all(), 
        source='groups', 
        write_only=True,
        required=False
    )
    
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name", "is_active", "is_superuser", "groups", "group_ids", "date_joined", "last_login"]


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ["key", "value", "description", "is_public"]


# ============================================================================
# STOREFRONT ECOMMERCE SERIALIZERS
# ============================================================================

class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    matched_client_name = serializers.CharField(source='matched_client.name', read_only=True)
    
    class Meta:
        model = Customer
        fields = "__all__"
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = "__all__"


class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = "__all__"
    
    def get_product_image(self, obj):
        # Get first product image if available
        first_image = obj.product.product_images.first()
        if first_image:
            return first_image.image.url if hasattr(first_image.image, 'url') else ''
        return ''


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    item_count = serializers.IntegerField(read_only=True)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    
    class Meta:
        model = Cart
        fields = "__all__"


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = OrderItem
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ['order_number', 'created_at', 'updated_at']


class CouponSerializer(serializers.ModelSerializer):
    class Meta:
        model = Coupon
        fields = "__all__"


class TaxConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxConfiguration
        fields = "__all__"


class DesignTemplateSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = DesignTemplate
        fields = "__all__"


class DesignStateSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    
    class Meta:
        model = DesignState
        fields = "__all__"


class ProductReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.get_full_name', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    rating_display = serializers.CharField(source='get_rating_display', read_only=True)
    
    class Meta:
        model = ProductReview
        fields = "__all__"
        read_only_fields = ['created_at', 'updated_at', 'helpful_count']


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = "__all__"


class PaymentTransactionSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    customer_email = serializers.CharField(source='customer.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = "__all__"
        read_only_fields = ['created_at', 'updated_at', 'initiated_at']



class ProductRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductRule
        fields = "__all__"

class TimelineEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)
    class Meta:
        model = TimelineEvent
        fields = "__all__"

class DesignVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignVersion
        fields = "__all__"

class DesignSessionSerializer(serializers.ModelSerializer):
    versions = DesignVersionSerializer(many=True, read_only=True)
    class Meta:
        model = DesignSession
        fields = "__all__"

class ProofApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProofApproval
        fields = "__all__"

class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = "__all__"

class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = "__all__"

class MaterialInventorySerializer(serializers.ModelSerializer):
    available_stock = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    class Meta:
        model = MaterialInventory
        fields = "__all__"

class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = "__all__"

class CreditNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditNote
        fields = "__all__"

class AdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Adjustment
        fields = "__all__"

class WebhookSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookSubscription
        fields = "__all__"

class WebhookDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookDelivery
        fields = "__all__"


# Vendor Portal Serializers

class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializer for Purchase Orders"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    client_name = serializers.CharField(source='job.client.name', read_only=True)
    is_delayed = serializers.BooleanField(read_only=True)
    days_until_due = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'job', 'job_number', 'vendor', 'vendor_name',
            'client_name', 'product_type', 'product_description', 'quantity',
            'unit_cost', 'total_cost', 'required_by', 'estimated_completion',
            'actual_completion', 'status', 'milestone', 'vendor_accepted',
            'vendor_accepted_at', 'vendor_notes', 'special_instructions',
            'assets_acknowledged', 'assets_acknowledged_at', 'shipping_method',
            'tracking_number', 'carrier', 'ready_for_pickup', 'coordination_group',
            'internal_notes', 'is_delayed', 'days_until_due', 'created_at', 'updated_at'
        ]
        read_only_fields = ['po_number', 'created_at', 'updated_at', 'is_delayed', 'days_until_due']


class VendorInvoiceSerializer(serializers.ModelSerializer):
    """Serializer for Vendor Invoices"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    
    class Meta:
        model = VendorInvoice
        fields = [
            'id', 'invoice_number', 'vendor_invoice_ref', 'purchase_order',
            'po_number', 'vendor', 'vendor_name', 'job', 'job_number',
            'invoice_date', 'due_date', 'line_items', 'subtotal', 'tax_rate',
            'tax_amount', 'total_amount', 'payment_terms', 'payment_method',
            'status', 'invoice_file', 'supporting_documents', 'vendor_notes',
            'internal_notes', 'rejection_reason', 'submitted_at', 'approved_at', 
            'approved_by', 'paid_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['invoice_number', 'tax_amount', 'total_amount', 
                           'submitted_at', 'approved_at', 'paid_at', 'created_at', 'updated_at']
        ref_name = 'VendorInvoiceAPI'


class PurchaseOrderProofSerializer(serializers.ModelSerializer):
    """Serializer for Purchase Order Proofs"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True)
    
    class Meta:
        model = PurchaseOrderProof
        fields = [
            'id', 'purchase_order', 'po_number', 'proof_image',
            'submitted_at', 'status', 'reviewed_by',
            'reviewed_by_name', 'reviewed_at'
        ]
        read_only_fields = ['submitted_at']
        ref_name = 'PurchaseOrderProofAPI'


class PurchaseOrderIssueSerializer(serializers.ModelSerializer):
    """Serializer for Purchase Order Issues"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    
    class Meta:
        model = PurchaseOrderIssue
        fields = [
            'id', 'purchase_order', 'po_number', 'issue_type', 'description',
            'status', 'created_at'
        ]
        read_only_fields = ['created_at']
        ref_name = 'PurchaseOrderIssueAPI'


class PurchaseOrderNoteSerializer(serializers.ModelSerializer):
    """Serializer for Purchase Order Notes"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True)
    
    class Meta:
        model = PurchaseOrderNote
        fields = [
            'id', 'purchase_order', 'po_number', 'sender', 'sender_name',
            'category', 'message', 'created_at'
        ]
        ref_name = 'PurchaseOrderNoteAPI'
        read_only_fields = ['created_at']


class MaterialSubstitutionRequestSerializer(serializers.ModelSerializer):
    """Serializer for Material Substitution Requests"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    
    class Meta:
        model = MaterialSubstitutionRequest
        fields = [
            'id', 'purchase_order', 'po_number', 'original_material',
            'proposed_material', 'match_percentage',
            'justification', 'status', 'created_at'
        ]
        read_only_fields = ['created_at']
        ref_name = 'MaterialSubstitutionRequestAPI'


class VendorPerformanceSerializer(serializers.Serializer):
    """Serializer for Vendor Performance Metrics"""
    overall_score = serializers.IntegerField()
    vps_grade = serializers.CharField()
    tax_status = serializers.CharField()
    certifications = serializers.ListField(child=serializers.CharField())
    
    # Performance metrics
    on_time_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    quality_score = serializers.DecimalField(max_digits=5, decimal_places=2)
    avg_turnaround = serializers.DecimalField(max_digits=5, decimal_places=2)
    defect_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    cost_per_job = serializers.DecimalField(max_digits=10, decimal_places=2)
    acceptance_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    response_time = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    ghosting_incidents = serializers.IntegerField(required=False)
    decline_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    
    # Performance insights
    insights = serializers.ListField(child=serializers.DictField())


class PurchaseOrderDetailedSerializer(serializers.ModelSerializer):
    """Detailed serializer for Purchase Orders with nested data"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    vendor_email = serializers.CharField(source='vendor.email', read_only=True)
    vendor_phone = serializers.CharField(source='vendor.phone', read_only=True)
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    job_name = serializers.CharField(source='job.job_name', read_only=True)
    client_name = serializers.CharField(source='job.client.name', read_only=True)
    days_until_due = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'job', 'job_number', 'job_name',
            'vendor', 'vendor_name', 'vendor_email', 'vendor_phone',
            'product_type', 'product_description', 'quantity',
            'unit_cost', 'total_cost', 'status', 'milestone',
            'created_at', 'updated_at', 'required_by', 'due_date',
            'vendor_accepted', 'vendor_accepted_at', 'vendor_notes',
            'completed_at', 'completed_on_time', 'has_issues',
            'is_blocked', 'blocked_reason', 'blocked_at',
            'shipping_method', 'tracking_number', 'ready_for_pickup',
            'invoice_sent', 'invoice_paid', 'days_until_due',
            'client_name', 'assets_acknowledged', 'last_activity_at'
        ]
        read_only_fields = [
            'po_number', 'created_at', 'updated_at', 'days_until_due',
            'vendor_name', 'vendor_email', 'vendor_phone', 'job_number',
            'job_name', 'client_name'
        ]
    
    def get_days_until_due(self, obj):
        return obj.days_until_due


class VendorInvoiceDetailedSerializer(serializers.ModelSerializer):
    """Detailed serializer for Vendor Invoices"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    client_name = serializers.CharField(source='job.client.name', read_only=True)
    
    # Make line_items optional with default empty list
    line_items = serializers.JSONField(required=False, allow_null=False, default=list)
    # Make optional fields not required
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=0)
    
    class Meta:
        model = VendorInvoice
        fields = [
            'id', 'invoice_number', 'vendor_invoice_ref', 'purchase_order',
            'po_number', 'vendor', 'vendor_name', 'job', 'job_number',
            'client_name', 'invoice_date', 'due_date', 'line_items',
            'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'status',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'invoice_number', 'created_at', 'updated_at', 'vendor_name',
            'po_number', 'job_number', 'client_name'
        ]


# ============================================================================
# CLIENT PORTAL SERIALIZERS
# ============================================================================

class ClientPortalUserSerializer(serializers.ModelSerializer):
    """Client Portal User"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = ClientPortalUser
        fields = [
            'id', 'user', 'user_email', 'client', 'client_name', 'role',
            'can_view_orders', 'can_place_orders', 'can_view_invoices',
            'can_view_payments', 'can_submit_tickets', 'can_access_documents',
            'can_manage_users', 'is_active', 'email_verified', 'last_login',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user_email', 'client_name', 'created_at', 'updated_at', 'last_login']


class ClientOrderItemSerializer(serializers.ModelSerializer):
    """Client Order Item"""
    product_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = ClientOrderItem
        fields = [
            'id', 'product', 'product_name', 'product_sku', 'quantity',
            'unit_price', 'line_total', 'specifications', 'created_at'
        ]
        read_only_fields = ['line_total', 'created_at']


class ClientOrderSerializer(serializers.ModelSerializer):
    """Client Order"""
    items = ClientOrderItemSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    quote_number = serializers.CharField(source='quote.quote_number', read_only=True, allow_null=True)
    
    class Meta:
        model = ClientOrder
        fields = [
            'id', 'order_number', 'client', 'client_name', 'quote', 'quote_number',
            'job', 'status', 'subtotal', 'tax_amount', 'shipping_cost', 'total_amount',
            'shipping_address', 'delivery_date', 'special_instructions', 'items',
            'created_by', 'created_at', 'updated_at', 'submitted_at'
        ]
        read_only_fields = [
            'order_number', 'client_name', 'quote_number', 'created_at', 'updated_at', 'submitted_at'
        ]


class ClientInvoiceSerializer(serializers.ModelSerializer):
    """Client Invoice"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True, allow_null=True)
    
    class Meta:
        model = ClientInvoice
        fields = [
            'id', 'invoice_number', 'client', 'client_name', 'order', 'order_number',
            'subtotal', 'tax_amount', 'total_amount', 'amount_paid', 'balance_due',
            'status', 'invoice_date', 'due_date', 'issued_at', 'qb_invoice_id',
            'is_synced_to_qb', 'qb_last_sync_at', 'description', 'line_items_json',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'invoice_number', 'client_name', 'order_number', 'qb_invoice_id',
            'is_synced_to_qb', 'qb_last_sync_at', 'created_at', 'updated_at'
        ]


class ClientPaymentSerializer(serializers.ModelSerializer):
    """Client Payment"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True, allow_null=True)
    
    class Meta:
        model = ClientPayment
        fields = [
            'id', 'payment_number', 'client', 'client_name', 'invoice', 'invoice_number',
            'amount', 'payment_method', 'status', 'qb_payment_id', 'is_synced_to_qb',
            'reference_number', 'notes', 'created_at', 'updated_at', 'processed_at'
        ]
        read_only_fields = [
            'payment_number', 'client_name', 'invoice_number', 'qb_payment_id',
            'is_synced_to_qb', 'created_at', 'updated_at', 'processed_at'
        ]


class ClientTicketReplySerializer(serializers.ModelSerializer):
    """Support Ticket Reply"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ClientTicketReply
        fields = [
            'id', 'ticket', 'user', 'user_name', 'message', 'attachment_url',
            'is_internal', 'created_at'
        ]
        read_only_fields = ['user_name', 'created_at']


class ClientSupportTicketSerializer(serializers.ModelSerializer):
    """Client Support Ticket"""
    replies = ClientTicketReplySerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = ClientSupportTicket
        fields = [
            'id', 'ticket_number', 'client', 'client_name', 'title', 'description',
            'category', 'order', 'invoice', 'priority', 'status', 'assigned_to',
            'assigned_to_name', 'resolution_notes', 'replies', 'created_by',
            'created_by_name', 'created_at', 'updated_at', 'resolved_at'
        ]
        read_only_fields = [
            'ticket_number', 'client_name', 'created_by_name', 'assigned_to_name',
            'created_at', 'updated_at', 'resolved_at'
        ]


class ClientDocumentLibrarySerializer(serializers.ModelSerializer):
    """Client Document"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    
    class Meta:
        model = ClientDocumentLibrary
        fields = [
            'id', 'document_number', 'client', 'client_name', 'title', 'description',
            'doc_type', 'order', 'invoice', 'file_url', 'file_size', 'file_format',
            'is_public', 'uploaded_by', 'uploaded_by_name', 'created_at', 'expires_at'
        ]
        read_only_fields = [
            'document_number', 'client_name', 'uploaded_by_name', 'created_at'
        ]


class ClientPortalNotificationSerializer(serializers.ModelSerializer):
    """Client Portal Notification"""
    
    class Meta:
        model = ClientPortalNotification
        fields = [
            'id', 'portal_user', 'notification_type', 'title', 'message',
            'order', 'invoice', 'ticket', 'is_read', 'created_at', 'read_at'
        ]
        read_only_fields = ['portal_user', 'created_at', 'read_at']


class ClientActivityLogSerializer(serializers.ModelSerializer):
    """Client Activity Log"""
    portal_user_name = serializers.CharField(source='portal_user.user.get_full_name', read_only=True)
    
    class Meta:
        model = ClientActivityLog
        fields = [
            'id', 'portal_user', 'portal_user_name', 'action_type', 'description',
            'order', 'invoice', 'ip_address', 'user_agent', 'created_at'
        ]
        read_only_fields = ['portal_user_name', 'created_at']


# ==================== PHASE 2 SERIALIZERS ====================

class MessageAttachmentSerializer(serializers.ModelSerializer):
    """Serializer for message file attachments"""
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file', 'file_name', 'file_type', 'file_size', 'thumbnail', 'duration', 'created_at']
        read_only_fields = ['id', 'created_at', 'thumbnail']


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for messages with attachments"""
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'job', 'sender_type', 'sender_id', 'sender_name', 
            'recipient_type', 'recipient_id', 'recipient_name', 'content',
            'is_task', 'task_status', 'task_priority', 'task_due_date', 'task_acknowledged_at',
            'is_read', 'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'task_acknowledged_at', 'created_at', 'updated_at']


class ProgressUpdatePhotoSerializer(serializers.ModelSerializer):
    """Serializer for progress update photos"""
    class Meta:
        model = ProgressUpdatePhoto
        fields = ['id', 'photo', 'caption', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProgressUpdateSerializer(serializers.ModelSerializer):
    """Serializer for progress updates with photos"""
    photos = ProgressUpdatePhotoSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProgressUpdate
        fields = [
            'id', 'job', 'vendor', 'percentage_complete', 'status', 
            'notes', 'issues', 'eta', 'photos', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProofSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for proof submissions"""
    reviewed_by_name = serializers.CharField(source='reviewed_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = ProofSubmission
        fields = [
            'id', 'job', 'vendor', 'proof_type', 'description', 'status',
            'submitted_at', 'reviewed_at', 'reviewed_by', 'reviewed_by_name', 'review_notes'
        ]
        read_only_fields = ['id', 'submitted_at', 'reviewed_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'notification_type', 'title', 'message',
            'link', 'is_read', 'action_url', 'action_label', 'related_lead',
            'related_quote_id', 'related_job', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class VendorPerformanceSerializer(serializers.ModelSerializer):
    """Serializer for vendor performance scores"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    
    class Meta:
        model = VendorPerformanceScore
        fields = [
            'id', 'vendor', 'vendor_name', 'on_time_delivery_rate', 'quality_score',
            'communication_score', 'average_score', 'jobs_completed_90_days',
            'on_time_jobs', 'on_time_delivery_percentage', 'average_quality_rating',
            'average_communication_rating', 'last_recalculated', 'created_at'
        ]
        read_only_fields = ['id', 'last_recalculated', 'created_at']


# ==================== PHASE 3: CLIENT PORTAL SERIALIZERS ====================

class ClientNotificationSerializer(serializers.ModelSerializer):
    """Serializer for client notifications"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    order_number = serializers.CharField(source='order.job_number', read_only=True, allow_null=True)
    
    class Meta:
        model = ClientNotification
        fields = [
            'id', 'client', 'client_name', 'title', 'message', 'notification_type',
            'is_read', 'read_at', 'created_at', 'link', 'order', 'order_number', 'proof'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']


class ClientMessageSerializer(serializers.ModelSerializer):
    """Serializer for client messages"""
    sender_name = serializers.CharField(source='sender.get_full_name', read_only=True, allow_null=True)
    order_number = serializers.CharField(source='order.job_number', read_only=True)
    
    class Meta:
        model = ClientMessage
        fields = [
            'id', 'order', 'order_number', 'sender', 'sender_name', 'sender_type',
            'message', 'attachment', 'is_read', 'read_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at']


class ClientDashboardSerializer(serializers.ModelSerializer):
    """Serializer for client dashboard metrics"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = ClientDashboard
        fields = [
            'id', 'client', 'client_name', 'total_orders', 'active_orders',
            'completed_orders', 'pending_proofs', 'overdue_orders',
            'total_spent', 'pending_payment', 'orders_this_month',
            'avg_completion_days', 'on_time_delivery_rate', 'last_updated', 'created_at'
        ]
        read_only_fields = [
            'id', 'total_orders', 'active_orders', 'completed_orders',
            'pending_proofs', 'overdue_orders', 'total_spent', 'pending_payment',
            'orders_this_month', 'avg_completion_days', 'on_time_delivery_rate',
            'last_updated', 'created_at'
        ]


class ClientFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for client feedback"""
    order_number = serializers.CharField(source='order.job_number', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    vendor_name = serializers.CharField(source='vendor.name', read_only=True, allow_null=True)
    
    class Meta:
        model = ClientFeedback
        fields = [
            'id', 'order', 'order_number', 'client', 'client_name',
            'feedback_type', 'rating', 'comment', 'vendor', 'vendor_name',
            'proof', 'is_addressed', 'response', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


# ==================== PHASE 3: ANALYTICS SERIALIZERS ====================

class OrderMetricsSerializer(serializers.ModelSerializer):
    """Serializer for order metrics"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    month_display = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderMetrics
        fields = [
            'id', 'client', 'client_name', 'month', 'month_display',
            'total_orders', 'completed_orders', 'pending_orders', 'cancelled_orders',
            'total_value', 'avg_order_value', 'total_revenue',
            'avg_turnaround_days', 'on_time_delivery_rate', 'completion_rate',
            'avg_quality_score', 'proofs_approved_first_attempt', 'revision_requests',
            'calculated_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'total_orders', 'completed_orders', 'pending_orders', 'cancelled_orders',
            'total_value', 'avg_order_value', 'total_revenue', 'avg_turnaround_days',
            'on_time_delivery_rate', 'completion_rate', 'avg_quality_score',
            'proofs_approved_first_attempt', 'revision_requests', 'calculated_at', 'created_at'
        ]
    
    def get_month_display(self, obj):
        return obj.month.strftime('%B %Y')


class VendorComparisonSerializer(serializers.ModelSerializer):
    """Serializer for vendor comparison"""
    client_name = serializers.CharField(source='client.name', read_only=True)
    vendor1_name = serializers.CharField(source='vendor1.name', read_only=True)
    vendor2_name = serializers.CharField(source='vendor2.name', read_only=True)
    
    class Meta:
        model = VendorComparison
        fields = [
            'id', 'client', 'client_name', 'vendor1', 'vendor1_name', 'vendor2', 'vendor2_name',
            'comparison_date', 'quality_score_1', 'quality_score_2',
            'avg_cost_1', 'avg_cost_2', 'avg_turnaround_1', 'avg_turnaround_2',
            'on_time_rate_1', 'on_time_rate_2', 'overall_score_1', 'overall_score_2',
            'winner', 'reason', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for performance analytics"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    month_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PerformanceAnalytics
        fields = [
            'id', 'vendor', 'vendor_name', 'month', 'month_display',
            'orders_completed', 'orders_on_time', 'orders_late',
            'quality_score', 'proofs_approved_first_attempt', 'revision_requests', 'rejection_rate',
            'avg_turnaround_hours', 'on_time_delivery_percentage', 'avg_cost_per_unit',
            'cost_variance_percentage', 'communication_score', 'reliability_score',
            'overall_trend', 'trend_description', 'ranking', 'percentile',
            'calculated_at', 'created_at'
        ]
        read_only_fields = [
            'id', 'orders_completed', 'orders_on_time', 'orders_late', 'quality_score',
            'proofs_approved_first_attempt', 'revision_requests', 'rejection_rate',
            'avg_turnaround_hours', 'on_time_delivery_percentage', 'avg_cost_per_unit',
            'cost_variance_percentage', 'communication_score', 'reliability_score',
            'overall_trend', 'ranking', 'percentile', 'calculated_at', 'created_at'
        ]
    
    def get_month_display(self, obj):
        return obj.month.strftime('%B %Y')


# ==================== PHASE 3: PAYMENT TRACKING SERIALIZERS ====================

class PaymentStatusSerializer(serializers.ModelSerializer):
    """Serializer for payment status"""
    invoice_number = serializers.CharField(source='client_invoice.invoice_number', read_only=True, allow_null=True)
    
    class Meta:
        model = PaymentStatus
        fields = [
            'id', 'client_invoice', 'invoice_number', 'amount_due', 'amount_paid',
            'amount_pending', 'status', 'due_date', 'paid_date', 'payment_method',
            'days_overdue', 'is_overdue', 'last_payment_date', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'amount_pending', 'days_overdue', 'is_overdue', 'last_payment_date',
            'created_at', 'updated_at'
        ]


class PaymentHistorySerializer(serializers.ModelSerializer):
    """Serializer for payment history"""
    invoice_number = serializers.CharField(source='payment_status.client_invoice.invoice_number', read_only=True, allow_null=True)
    reconciled_by_name = serializers.CharField(source='reconciled_by.get_full_name', read_only=True, allow_null=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = PaymentHistory
        fields = [
            'id', 'payment_status', 'invoice_number', 'payment_amount', 'payment_date',
            'reference_number', 'payment_method', 'bank_account', 'depositor_name',
            'notes', 'reconciled', 'reconciled_by', 'reconciled_by_name', 'reconciled_at',
            'created_at', 'created_by', 'created_by_name', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'reconciled_at']


# Backend Gap Serializers

class VendorCapacityAlertSerializer(serializers.ModelSerializer):
    """Serializer for vendor capacity alerts"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True, allow_null=True)
    acknowledged_by_name = serializers.CharField(source='acknowledged_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = VendorCapacityAlert
        fields = [
            'id', 'vendor', 'vendor_name', 'alert_type', 'status', 'purchase_order',
            'purchase_order_number', 'message', 'severity', 'acknowledged_by',
            'acknowledged_by_name', 'acknowledged_at', 'resolved_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class POSMilestoneSerializer(serializers.ModelSerializer):
    """Serializer for purchase order milestones"""
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    days_until_due = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    
    class Meta:
        model = POSMilestone
        fields = [
            'id', 'purchase_order', 'purchase_order_number', 'milestone_type',
            'target_date', 'completed', 'completed_at', 'completed_on_time',
            'alert_sent', 'alert_sent_at', 'notes', 'days_until_due', 'is_overdue',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'completed_at', 'alert_sent_at', 'created_at', 'updated_at']
    
    def get_days_until_due(self, obj):
        """Calculate days until milestone is due"""
        return obj.days_until_due
    
    def get_is_overdue(self, obj):
        """Check if milestone is overdue"""
        return obj.is_overdue


class MaterialSubstitutionApprovalSerializer(serializers.ModelSerializer):
    """Serializer for material substitution approvals"""
    purchase_order_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True, allow_null=True)
    cost_impact_percentage = serializers.SerializerMethodField()
    cost_difference = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialSubstitutionApproval
        fields = [
            'id', 'purchase_order', 'purchase_order_number', 'original_material',
            'substitute_material', 'reason', 'original_cost', 'substitute_cost',
            'cost_difference', 'cost_impact_percentage', 'approval_status',
            'approval_notes', 'approved_by', 'approved_by_name', 'approved_at',
            'customer_notified', 'customer_notified_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'approved_at', 'created_at', 'updated_at']
    
    def get_cost_impact_percentage(self, obj):
        """Calculate cost impact percentage"""
        return round(obj.cost_impact_percentage, 2)
    
    def get_cost_difference(self, obj):
        """Return cost difference"""
        return str(obj.cost_difference)


class InvoiceHoldSerializer(serializers.ModelSerializer):
    """Serializer for invoice holds"""
    invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
    vendor_name = serializers.CharField(source='invoice.vendor.name', read_only=True)
    held_by_name = serializers.CharField(source='held_by.get_full_name', read_only=True, allow_null=True)
    released_by_name = serializers.CharField(source='released_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = InvoiceHold
        fields = [
            'id', 'invoice', 'invoice_number', 'vendor_name', 'hold_reason',
            'hold_details', 'held_by', 'held_by_name', 'held_at', 'released',
            'released_by', 'released_by_name', 'released_at'
        ]
        read_only_fields = ['id', 'held_at']


class SLAEscalationSerializer(serializers.ModelSerializer):
    """Serializer for SLA escalations"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    vendor_name = serializers.CharField(source='purchase_order.vendor.name', read_only=True)
    escalated_by_name = serializers.CharField(source='escalated_by.get_full_name', read_only=True, allow_null=True)
    resolved_by_name = serializers.CharField(source='resolved_by.get_full_name', read_only=True, allow_null=True)
    time_since_escalation = serializers.SerializerMethodField()
    is_critical = serializers.SerializerMethodField()
    
    class Meta:
        model = SLAEscalation
        fields = [
            'id', 'purchase_order', 'po_number', 'vendor_name', 'escalation_level',
            'escalation_status', 'original_deadline', 'current_deadline', 'days_overdue',
            'escalation_reason', 'escalation_notes', 'escalated_at', 'escalated_by',
            'escalated_by_name', 'vendor_notified', 'vendor_notified_at', 'pt_notified',
            'pt_notified_at', 'resolved_at', 'resolved_by', 'resolved_by_name',
            'resolution_notes', 'created_at', 'updated_at', 'time_since_escalation',
            'is_critical'
        ]
        read_only_fields = ['id', 'escalated_at', 'vendor_notified_at', 'pt_notified_at', 'resolved_at', 'created_at', 'updated_at']
    
    def get_time_since_escalation(self, obj):
        """Calculate hours since escalation"""
        from django.utils import timezone
        from datetime import timedelta
        delta = timezone.now() - obj.escalated_at
        return delta.total_seconds() / 3600
    
    def get_is_critical(self, obj):
        """Check if escalation is critical (level 3 or overdue > 7 days)"""
        return obj.escalation_level == 'level_3' or obj.days_overdue > 7


class ProgressUpdateBatchSerializer(serializers.ModelSerializer):
    """Serializer for progress update batches"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    submitted_by_name = serializers.CharField(source='submitted_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = ProgressUpdateBatch
        fields = [
            'id', 'purchase_order', 'po_number', 'submission_date', 'submitted_by',
            'submitted_by_name', 'percentage_complete', 'status', 'description',
            'notes', 'next_milestone', 'next_milestone_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'submission_date', 'created_at', 'updated_at']


class QCProofLinkSerializer(serializers.ModelSerializer):
    """Serializer for QC-Proof links"""
    qc_id = serializers.IntegerField(source='qc_inspection.id', read_only=True)
    proof_id = serializers.IntegerField(source='proof.id', read_only=True)
    
    class Meta:
        model = QCProofLink
        fields = [
            'id', 'qc_inspection', 'qc_id', 'proof', 'proof_id', 'qc_status',
            'qc_notes', 'auto_held_invoice', 'hold_reason', 'vps_impact_calculated',
            'vps_score_adjustment', 'linked_at', 'updated_at'
        ]
        read_only_fields = ['id', 'linked_at', 'updated_at']


class VPSRecalculationLogSerializer(serializers.ModelSerializer):
    """Serializer for VPS recalculation logs"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    recalculated_by_name = serializers.CharField(source='recalculated_by.get_full_name', read_only=True, allow_null=True)
    
    class Meta:
        model = VPSRecalculationLog
        fields = [
            'id', 'vendor', 'vendor_name', 'trigger_type', 'previous_score',
            'new_score', 'score_change', 'reason', 'reference_id', 'recalculated_by',
            'recalculated_by_name', 'recalculated_at'
        ]
        read_only_fields = ['id', 'recalculated_at']


class CustomerNotificationSerializer(serializers.ModelSerializer):
    """Serializer for customer notifications"""
    substitution_id = serializers.IntegerField(source='substitution.id', read_only=True)
    
    class Meta:
        model = CustomerNotification
        fields = [
            'id', 'substitution', 'substitution_id', 'status', 'notification_method',
            'recipient_email', 'recipient_phone', 'subject', 'message', 'sent_at',
            'acknowledged_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'sent_at', 'created_at', 'updated_at']


class DeadlineCalculationSerializer(serializers.ModelSerializer):
    """Serializer for deadline calculations"""
    po_number = serializers.CharField(source='purchase_order.po_number', read_only=True)
    
    class Meta:
        model = DeadlineCalculation
        fields = [
            'id', 'purchase_order', 'po_number', 'job_complexity',
            'vendor_capacity_available', 'sla_days', 'base_deadline',
            'adjusted_deadline', 'risk_score', 'calculation_notes', 'calculated_at'
        ]
        read_only_fields = ['id', 'calculated_at']


# Task 8: Deadline Alerts
class DeadlineAlertSerializer(serializers.ModelSerializer):
    """Serializer for deadline alerts"""
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    job_name = serializers.CharField(source='job.job_name', read_only=True)
    job_deadline = serializers.DateField(source='job.expected_completion', read_only=True)
    assigned_to = serializers.CharField(source='job.person_in_charge.first_name', read_only=True)
    color_class = serializers.SerializerMethodField()
    
    class Meta:
        model = DeadlineAlert
        fields = [
            'id', 'job', 'job_number', 'job_name', 'job_deadline',
            'alert_type', 'urgency', 'message', 'status',
            'days_until_deadline', 'color_class',
            'created_at', 'acknowledged_at', 'acknowledged_by', 'assigned_to'
        ]
        read_only_fields = ['id', 'created_at', 'acknowledged_at']
    
    def get_color_class(self, obj):
        return obj.get_color_class()


# Task 9: Job Files & Document Sharing
class JobFileSerializer(serializers.ModelSerializer):
    """Serializer for job files"""
    file_icon = serializers.SerializerMethodField()
    uploader_name = serializers.CharField(source='uploaded_by.first_name', read_only=True)
    job_number = serializers.CharField(source='job.job_number', read_only=True)
    
    class Meta:
        model = JobFile
        fields = [
            'id', 'job', 'job_number', 'message', 'file',
            'file_name', 'file_type', 'file_size', 'file_icon',
            'uploaded_by', 'uploader_name', 'uploaded_at',
            'is_shared', 'shared_with', 'download_count', 'last_downloaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at', 'download_count', 'last_downloaded_at']


class DocumentShareSerializer(serializers.ModelSerializer):
    """Serializer for document sharing"""
    file_name = serializers.CharField(source='file.file_name', read_only=True)
    shared_with_name = serializers.SerializerMethodField()
    
    class Meta:
        model = DocumentShare
        fields = [
            'id', 'file', 'file_name', 'share_type', 'shared_with_user',
            'shared_with_name', 'shared_with_group', 'status', 'share_date',
            'access_count', 'last_accessed', 'expires_at', 'shared_by', 'notes'
        ]
        read_only_fields = ['id', 'share_date', 'access_count', 'last_accessed']
    
    def get_shared_with_name(self, obj):
        if obj.shared_with_user:
            return f"{obj.shared_with_user.first_name} {obj.shared_with_user.last_name}"
        elif obj.shared_with_group:
            return obj.shared_with_group.name
        return None




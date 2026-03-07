from django.utils import timezone
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q, F
from django.core.cache import cache
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from rest_framework import viewsets, status, decorators, serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from decimal import Decimal
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from .quickbooks_services import QuickBooksService, QuickBooksAuthService
import logging
import json
import secrets

logger = logging.getLogger(__name__)


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
    PurchaseOrder,
    VendorInvoice,
    PurchaseOrderProof,
    PurchaseOrderIssue,
    PurchaseOrderNote,
    MaterialSubstitutionRequest,
    QuickBooksToken,
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
    resolve_unit_price,
    # Storefront models
    Customer,
    CustomerAddress,
    Cart,
    CartItem,
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
    Order,
    OrderItem,
    Coupon,
    TaxConfiguration,
    DesignTemplate,
    DesignState,
    ProductReview,
    ShippingMethod,
    PaymentTransaction,
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
    # Production Team Portal models
    ApprovalThreshold,
    InvoiceDispute,
    InvoiceDisputeResponse,
    JobProgressUpdate,
    SLAEscalation,
    VendorPerformanceMetrics,
    ProfitabilityAnalysis,
    WebhookDelivery,
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
    # Task 8 & 9 models
    DeadlineAlert,
    JobFile,
    DocumentShare,
    JobMessage,
)
from .api_serializers import (
    LeadSerializer,
    ClientSerializer,
    ClientContactSerializer,
    BrandAssetSerializer,
    ComplianceDocumentSerializer,
    ProductSerializer,
    QuoteSerializer,
    QuoteLineItemSerializer,
    JobSerializer,
    VendorSerializer,
    LPOSerializer,
    PaymentSerializer,
    PurchaseOrderDetailedSerializer,
    VendorInvoiceDetailedSerializer,
    PurchaseOrderProofSerializer,
    PurchaseOrderIssueSerializer,
    PurchaseOrderNoteSerializer,
    MaterialSubstitutionRequestSerializer,
    NotificationSerializer,
    ActivityLogSerializer,
    PropertyTypeSerializer,
    PropertyValueSerializer,
    ProductPropertySerializer,
    QuantityPricingSerializer,
    TurnAroundTimeSerializer,
    SystemSettingSerializer,
    ProcessSerializer,
    ProcessTierSerializer,
    ProcessVariableSerializer,
    ProductVariableSerializer,
    ProductVariableOptionSerializer,
    ProcessVendorSerializer,
    PricingTierSerializer,
    VendorTierPricingSerializer,
    ProcessVariableRangeSerializer,
    ProductImageMetadataSerializer,
    ProductVideoMetadataSerializer,
    ProductDownloadableFileSerializer,
    ProductSEOSerializer,
    ProductReviewSettingsSerializer,
    ProductFAQSerializer,
    # Storefront serializers
    CustomerSerializer,
    CustomerAddressSerializer,
    CartSerializer,
    CartItemSerializer,
    OrderSerializer,
    OrderItemSerializer,
    CouponSerializer,
    TaxConfigurationSerializer,
    DesignTemplateSerializer,
    DesignStateSerializer,
    ProductReviewSerializer,
    ShippingMethodSerializer,
    PaymentTransactionSerializer,
    ProductShippingSerializer,
    ProductLegalSerializer,
    ProductProductionSerializer,
    ProductChangeHistorySerializer,
    ProductApprovalRequestSerializer,
    ProductTemplateSerializer,
    # Client Portal serializers
    ClientPortalUserSerializer,
    ClientOrderSerializer,
    ClientOrderItemSerializer,
    ClientInvoiceSerializer,
    ClientPaymentSerializer,
    ClientSupportTicketSerializer,
    ClientTicketReplySerializer,
    ClientDocumentLibrarySerializer,
    ClientPortalNotificationSerializer,
    ClientActivityLogSerializer,
    JobVendorStageSerializer,
    JobNoteSerializer,
    JobAttachmentSerializer,
    VendorQuoteSerializer,
    QCInspectionSerializer,
    DeliverySerializer,
    QuoteAttachmentSerializer,
    LPOLineItemSerializer,
    SystemAlertSerializer,
    ProductionUpdateSerializer,
    UserSerializer,
    GroupSerializer,
    PermissionSerializer,

    ProductRuleSerializer,
    TimelineEventSerializer,
    DesignSessionSerializer,
    DesignVersionSerializer,
    ProofApprovalSerializer,
    ShipmentSerializer,
    PromotionSerializer,
    MaterialInventorySerializer,
    RefundSerializer,
    CreditNoteSerializer,
    AdjustmentSerializer,
    WebhookSubscriptionSerializer,
    WebhookDeliverySerializer,
    # Phase 2 serializers
    MessageSerializer,
    MessageAttachmentSerializer,
    ProgressUpdateSerializer,
    ProgressUpdatePhotoSerializer,
    ProofSubmissionSerializer,
    VendorPerformanceSerializer,
    NotificationSerializer,
    # Phase 3 serializers
    ClientNotificationSerializer,
    ClientMessageSerializer,
    ClientDashboardSerializer,
    ClientFeedbackSerializer,
    OrderMetricsSerializer,
    VendorComparisonSerializer,
    PerformanceAnalyticsSerializer,
    PaymentStatusSerializer,
    PaymentHistorySerializer,
)
from .permissions import (
    IsAdmin,
    IsAccountManager,
    IsProductionTeam,
    IsOwnerOrAdmin,
    IsClient,
    IsClientOwner,
    IsVendor,
)

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class LeadViewSet(viewsets.ModelViewSet):
    queryset = Lead.objects.select_related("created_by").all()
    serializer_class = LeadSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["status", "source", "created_by"]
    search_fields = ["lead_id", "name", "email", "phone"]
    ordering_fields = ["created_at", "status"]
    
    def perform_create(self, serializer):
        """Set the creator of the lead"""
        serializer.save(created_by=self.request.user)

    
    def get_queryset(self):
        """Restrict AMs to their own leads unless they're Admin"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Admin can see all leads
        if user.groups.filter(name="Admin").exists():
            return queryset
        
        # Account Manager can only see leads they created
        if user.groups.filter(name="Account Manager").exists():
            return queryset.filter(created_by=user)
        
        return queryset

    @decorators.action(detail=True, methods=["post"])
    def qualify(self, request, pk=None):
        """
        Move a lead from 'New' to 'Qualified' status.
        AM can use this as a quick action to mark lead as ready for quote creation.
        """
        lead = self.get_object()
        
        if lead.status != 'New':
            return Response(
                {"detail": f"Lead can only be qualified from 'New' status. Current status: {lead.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        lead.status = 'Qualified'
        lead.save(update_fields=['status', 'updated_at'])
        
        # Create notification for AM to create quote
        Notification.objects.create(
            recipient=request.user,
            notification_type='lead_qualified',
            title=f"Lead {lead.lead_id} Qualified",
            message=f"{lead.name} is ready for quote creation.",
            link=f"/leads/{lead.pk}/",
        )
        
        # Create activity log
        ActivityLog.objects.create(
            client=None,
            activity_type='Note',
            title=f"Lead {lead.lead_id} Qualified",
            description=f"Lead moved to Qualified status by {request.user.username}.",
            created_by=request.user,
        )
        
        serializer = self.get_serializer(lead)
        return Response({
            "detail": "Lead qualified successfully",
            "lead": serializer.data
        })

    @decorators.action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        """
        Convert a lead to a client with full B2B onboarding support.
        Supports:
        - B2B client creation with company details
        - Multiple contacts (contacts array in request data)
        - Compliance documents (compliance_documents array)
        - Brand assets (brand_assets array)
        
        Request body example:
        {
            "client_type": "B2B",  // or "B2C"
            "company": "Company Name",
            "vat_tax_id": "VAT123",
            "kra_pin": "PIN123",
            "industry": "Printing",
            "contacts": [
                {"full_name":"Test User", "email": "test@example.com", "phone": "123", "role": "Manager", "is_primary": true}
            ],
            "compliance_documents": [
                {"document_type": "Certificate", "notes": "Business registration"}
            ],
            "brand_assets": [
                {"asset_type": "Logo", "description": "Company logo"}
            ]
        }
        """
        lead = self.get_object()
        if lead.converted_to_client:
            return Response({"detail": "Lead already converted."}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce rule: Lead converts only after an approved quote
        has_approved_quote = Quote.objects.filter(lead=lead, status="Approved").exists()
        if not has_approved_quote:
            return Response(
                {"detail": "Lead can only be converted after at least one approved quote."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_client = Client.objects.filter(email=lead.email).first()
        if existing_client:
            lead.converted_to_client = True
            lead.converted_at = timezone.now()
            lead.status = "Converted"
            lead.save(update_fields=["converted_to_client", "converted_at", "status", "updated_at"])
            return Response({"detail": "Lead marked converted; client already exists.", "client_id": existing_client.id})

        # Get client type from request (default to B2C)
        client_type = request.data.get("client_type", "B2C")
        
        # Create client
        client_data = {
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "client_type": client_type,
            "lead_source": lead.source if hasattr(lead, "source") else "",
            "preferred_channel": lead.preferred_contact if hasattr(lead, "preferred_contact") else "Email",
            "status": "Active",
            "converted_from_lead": lead,
            "onboarded_by": request.user,
            "account_manager": request.user,
        }
        
        # Add B2B-specific fields if provided
        if client_type == "B2B":
            if "company" in request.data:
                client_data["company"] = request.data["company"]
            if "vat_tax_id" in request.data:
                client_data["vat_tax_id"] = request.data["vat_tax_id"]
            if "kra_pin" in request.data:
                client_data["kra_pin"] = request.data["kra_pin"]
            if "industry" in request.data:
                client_data["industry"] = request.data["industry"]
            if "credit_limit" in request.data:
                client_data["credit_limit"] = request.data["credit_limit"]
        
        client = Client.objects.create(**client_data)
        
        # Create contacts if provided (B2B)
        if client_type == "B2B" and "contacts" in request.data:
            for contact_data in request.data["contacts"]:
                ClientContact.objects.create(
                    client=client,
                    full_name=contact_data.get("full_name", ""),
                    email=contact_data.get("email", ""),
                    phone=contact_data.get("phone", ""),
                    role=contact_data.get("role", ""),
                    is_primary=contact_data.get("is_primary", False),
                )
        
        # Create compliance documents if provided (B2B)
        if client_type == "B2B" and "compliance_documents" in request.data:
            for doc_data in request.data["compliance_documents"]:
                ComplianceDocument.objects.create(
                    client=client,
                    document_type=doc_data.get("document_type", "Other"),
                    notes=doc_data.get("notes", ""),
                    uploaded_by=request.user,
                )
        
        # Create brand assets if provided (B2B)
        if client_type == "B2B" and "brand_assets" in request.data:
            for asset_data in request.data["brand_assets"]:
                BrandAsset.objects.create(
                    client=client,
                    asset_type=asset_data.get("asset_type", "Other"),
                    description=asset_data.get("description", ""),
                    uploaded_by=request.user,
                )
        
        # Update lead
        lead.converted_to_client = True
        lead.converted_at = timezone.now()
        lead.status = "Converted"
        lead.save(update_fields=["converted_to_client", "converted_at", "status", "updated_at"])
        
        # Create activity log
        ActivityLog.objects.create(
            client=client,
            activity_type="Note",
            title=f"Client Converted from Lead {lead.lead_id}",
            description=f"Lead converted to {client_type} client with full onboarding.",
            created_by=request.user,
        )
        
        serializer = ClientSerializer(client)
        return Response({
            "detail": "Lead converted successfully",
            "client": serializer.data
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class ClientContactViewSet(viewsets.ModelViewSet):
    queryset = ClientContact.objects.select_related("client").all()
    serializer_class = ClientContactSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["client", "role", "is_primary"]
    search_fields = ["full_name", "email", "phone"]

    def _ensure_b2b(self, client):
        if client.client_type != "B2B":
            raise serializers.ValidationError("Additional contacts are only allowed for B2B clients.")

    def perform_create(self, serializer):
        client = serializer.validated_data.get("client")
        if client:
            self._ensure_b2b(client)
        serializer.save()

    def perform_update(self, serializer):
        client = serializer.validated_data.get("client") or serializer.instance.client
        if client:
            self._ensure_b2b(client)
        serializer.save()


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.select_related("account_manager", "converted_from_lead").all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["client_type", "status", "account_manager"]
    search_fields = ["client_id", "name", "email", "phone", "company"]
    ordering_fields = ["created_at", "last_activity"]
    
    def perform_create(self, serializer):
        """Set the account manager and onboarder of the client"""
        serializer.save(
            account_manager=self.request.user,
            onboarded_by=self.request.user
        )

    
    def get_queryset(self):
        """Restrict AMs to their own clients unless they're Admin"""
        queryset = super().get_queryset()
        user = self.request.user
        
        # Admin can see all clients
        if user.groups.filter(name="Admin").exists():
            return queryset
        
        # Account Manager can only see clients they manage
        if user.groups.filter(name="Account Manager").exists():
            return queryset.filter(account_manager=user)
        
        return queryset


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class BrandAssetViewSet(viewsets.ModelViewSet):
    queryset = BrandAsset.objects.select_related("client", "uploaded_by").all()
    serializer_class = BrandAssetSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["client", "asset_type"]
    search_fields = ["description"]

    def _ensure_b2b(self, client):
        if client.client_type != "B2B":
            raise serializers.ValidationError("Brand assets are only allowed for B2B clients.")

    def perform_create(self, serializer):
        client = serializer.validated_data.get("client")
        if client:
            self._ensure_b2b(client)
        serializer.save(uploaded_by=self.request.user)

    def perform_update(self, serializer):
        client = serializer.validated_data.get("client") or serializer.instance.client
        if client:
            self._ensure_b2b(client)
        serializer.save()


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class ComplianceDocumentViewSet(viewsets.ModelViewSet):
    queryset = ComplianceDocument.objects.select_related("client", "uploaded_by").all()
    serializer_class = ComplianceDocumentSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["client", "document_type"]
    search_fields = ["notes"]

    def _ensure_b2b(self, client):
        if client.client_type != "B2B":
            raise serializers.ValidationError("Compliance documents are only allowed for B2B clients.")

    def perform_create(self, serializer):
        client = serializer.validated_data.get("client")
        if client:
            self._ensure_b2b(client)
        serializer.save(uploaded_by=self.request.user)

    def perform_update(self, serializer):
        client = serializer.validated_data.get("client") or serializer.instance.client
        if client:
            self._ensure_b2b(client)
        serializer.save()


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductViewSet(viewsets.ModelViewSet):
    """
    Production Team product management viewset.
    
    Supports create, retrieve, update, delete, and publish/archive workflows.
    Handles nested pricing, media uploads, and pricing calculations.
    
    Endpoints:
    - GET /api/v1/products/ - List products with filters
    - POST /api/v1/products/ - Create product
    - GET /api/v1/products/{id}/ - Retrieve product
    - PATCH /api/v1/products/{id}/ - Update product
    - DELETE /api/v1/products/{id}/ - Delete product
    - POST /api/v1/products/{id}/upload-primary-image/ - Upload primary image
    - POST /api/v1/products/{id}/upload-gallery-images/ - Upload gallery images
    - POST /api/v1/products/{id}/add-video/ - Add video
    - POST /api/v1/products/{id}/calculate-price/ - Calculate price
    - POST /api/v1/products/{id}/publish/ - Publish product
    - POST /api/v1/products/{id}/archive/ - Archive product
    - POST /api/v1/products/{id}/save-draft/ - Save as draft
    - GET /api/v1/products/{id}/change-history/ - Get change history
    """
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    filterset_fields = ["customization_level", "status", "is_visible", "primary_category", "sub_category"]
    search_fields = ["name", "internal_code"]
    ordering_fields = ["created_at", "updated_at", "base_price"]
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Optimize queries based on action"""
        queryset = Product.objects.all()
        
        if self.action == 'list':
            # Optimize for list view
            queryset = queryset.select_related(
                'created_by', 'updated_by'
            ).prefetch_related(
                'images', 'videos', 'tags'
            )
        
        if self.action == 'retrieve':
            # Include all relationships for detail view
            queryset = queryset.prefetch_related(
                'images', 'videos', 'tags', 'change_history'
            ).select_related(
                'created_by', 'updated_by'
            )
        
        return queryset
    
    @action(detail=True, methods=['post'], parser_classes=(MultiPartParser, FormParser), permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def upload_primary_image(self, request, pk=None):
        """Upload or replace primary product image"""
        product = self.get_object()
        image_file = request.FILES.get('image')
        
        if not image_file:
            return Response({'error': 'No image provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Validate image
            self._validate_image_file(image_file)
            
            # Remove old primary images
            product.images.filter(is_primary=True).delete()
            
            # Create new primary image
            image = ProductImage.objects.create(
                product=product,
                image=image_file,
                is_primary=True,
                alt_text=request.data.get('alt_text', product.name)
            )
            
            return Response({
                'id': image.id,
                'url': image.image.url,
                'is_primary': True,
                'message': 'Primary image uploaded successfully'
            }, status=status.HTTP_201_CREATED)
        
        except serializers.ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], parser_classes=(MultiPartParser, FormParser), permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def upload_gallery_images(self, request, pk=None):
        """Upload gallery images (bulk upload, max 10)"""
        product = self.get_object()
        files = request.FILES.getlist('images')
        
        if not files:
            return Response({'error': 'No images provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        created_images = []
        errors = []
        
        for idx, file in enumerate(files[:10]):  # Max 10 images
            try:
                self._validate_image_file(file)
                
                image = ProductImage.objects.create(
                    product=product,
                    image=file,
                    is_primary=False,
                    alt_text=request.data.get('alt_text', f"{product.name} - {idx+1}"),
                    display_order=idx
                )
                
                created_images.append({
                    'id': image.id,
                    'url': image.image.url,
                    'order': image.display_order
                })
            
            except serializers.ValidationError as e:
                errors.append({'file': file.name, 'error': str(e)})
        
        return Response({
            'count': len(created_images),
            'images': created_images,
            'errors': errors,
            'message': f'Uploaded {len(created_images)} images'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def add_video(self, request, pk=None):
        """Add product video from URL"""
        product = self.get_object()
        video_url = request.data.get('video_url')
        
        if not video_url:
            return Response({'error': 'No video URL provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Detect video type and validate
            video_type = self._detect_video_type(video_url)
            
            video = ProductVideo.objects.create(
                product=product,
                video_url=video_url,
                video_type=video_type
            )
            
            return Response({
                'id': video.id,
                'url': video.video_url,
                'type': video.video_type,
                'message': 'Video added successfully'
            }, status=status.HTTP_201_CREATED)
        
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def calculate_price(self, request, pk=None):
        """
        Calculate product price for given quantity and variables.
        
        Request body:
        {
            "quantity": 100,
            "variables": {"size": "A4", "finish": "glossy"},
            "include_breakdown": true
        }
        """
        product = self.get_object()
        quantity = request.data.get('quantity', 1)
        variables = request.data.get('variables', {})
        include_breakdown = request.data.get('include_breakdown', False)
        
        if quantity < 1:
            return Response({'error': 'Quantity must be at least 1'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Get pricing info
            if not hasattr(product, 'pricing'):
                return Response({
                    'quantity': quantity,
                    'unit_cost': str(product.base_price or 0),
                    'total_cost': str((product.base_price or 0) * quantity),
                    'unit_price': str(product.base_price or 0),
                    'total_price': str((product.base_price or 0) * quantity),
                    'margin_percentage': 0,
                }, status=status.HTTP_200_OK)
            
            pricing = product.pricing
            
            # Simple pricing calculation
            base_cost = pricing.base_cost or Decimal('0.00')
            base_price = product.base_price or Decimal('0.00')
            
            if product.customization_level == 'fully_customizable':
                # For fully customizable, use base cost + margin
                margin_multiplier = (pricing.return_margin or Decimal('30')) / Decimal('100')
                unit_price = base_cost * (1 + margin_multiplier)
            else:
                unit_price = base_price
            
            total_cost = base_cost * quantity
            total_price = unit_price * quantity
            
            margin = ((unit_price - base_cost) / unit_price * 100) if unit_price > 0 else Decimal('0')
            
            response_data = {
                'quantity': quantity,
                'unit_cost': str(base_cost),
                'total_cost': str(total_cost),
                'unit_price': str(unit_price),
                'total_price': str(total_price),
                'margin_percentage': str(margin),
            }
            
            if include_breakdown:
                response_data['breakdown'] = {
                    'base_cost': str(base_cost),
                    'margin_multiplier': str(pricing.return_margin or 0),
                    'unit_price': str(unit_price),
                    'quantity': quantity,
                    'total_cost': str(total_cost),
                    'total_price': str(total_price),
                }
            
            return Response(response_data)
        
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def publish(self, request, pk=None):
        """Publish product (make visible and available)"""
        product = self.get_object()
        
        # Check if product can be published
        can_publish, error_msg = product.can_be_published()
        if not can_publish:
            return Response({'detail': error_msg}, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = product.status
        product.status = 'published'
        product.updated_by = request.user
        product.save()
        
        # Record change
        ProductChangeHistory.objects.create(
            product=product,
            changed_by=request.user,
            change_type='status_change',
            field_changed='status',
            old_value=old_status,
            new_value='published',
        )
        
        return Response({
            'id': product.id,
            'status': 'published',
            'message': f'Product "{product.name}" published successfully',
            'published_at': timezone.now().isoformat()
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def archive(self, request, pk=None):
        """Archive product (hide from catalog)"""
        product = self.get_object()
        
        old_status = product.status
        product.status = 'archived'
        product.updated_by = request.user
        product.save()
        
        # Record change
        ProductChangeHistory.objects.create(
            product=product,
            changed_by=request.user,
            change_type='status_change',
            field_changed='status',
            old_value=old_status,
            new_value='archived',
        )
        
        return Response({
            'id': product.id,
            'status': 'archived',
            'message': f'Product "{product.name}" archived successfully'
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def save_draft(self, request, pk=None):
        """Save product as draft without publishing"""
        product = self.get_object()
        
        serializer = self.get_serializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            old_status = product.status
            product = serializer.save(status='draft', updated_by=request.user)
            
            # Record change
            ProductChangeHistory.objects.create(
                product=product,
                changed_by=request.user,
                change_type='draft_save',
                field_changed='status',
                old_value=old_status,
                new_value='draft',
            )
            
            return Response({
                'id': product.id,
                'status': 'draft',
                'message': 'Product saved as draft',
                'saved_at': timezone.now().isoformat()
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def change_history(self, request, pk=None):
        """Get product change history (audit trail)"""
        from .api_serializers import ProductChangeHistorySerializer
        
        product = self.get_object()
        
        changes = ProductChangeHistory.objects.filter(
            product=product
        ).order_by('-changed_at')[:50]  # Last 50 changes
        
        serializer = ProductChangeHistorySerializer(changes, many=True)
        
        return Response({
            'product_id': product.id,
            'product_name': product.name,
            'total_changes': ProductChangeHistory.objects.filter(product=product).count(),
            'changes': serializer.data
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin | IsAccountManager)])
    def update_inventory(self, request, pk=None):
        """Update product inventory levels and settings"""
        product = self.get_object()
        
        try:
            # Extract inventory fields from request
            stock_quantity = request.data.get('stock_quantity')
            low_stock_threshold = request.data.get('low_stock_threshold')
            track_inventory = request.data.get('track_inventory')
            allow_backorders = request.data.get('allow_backorders')
            
            # Validate and update fields
            updated_fields = {}
            
            if stock_quantity is not None:
                stock_quantity = int(stock_quantity)
                if stock_quantity < 0:
                    return Response(
                        {'detail': 'Stock quantity cannot be negative'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.stock_quantity = stock_quantity
                updated_fields['stock_quantity'] = stock_quantity
            
            if low_stock_threshold is not None:
                low_stock_threshold = int(low_stock_threshold)
                if low_stock_threshold < 0:
                    return Response(
                        {'detail': 'Low stock threshold cannot be negative'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                product.low_stock_threshold = low_stock_threshold
                updated_fields['low_stock_threshold'] = low_stock_threshold
            
            if track_inventory is not None:
                product.track_inventory = track_inventory in [True, 'true', 'True', 1, '1']
                updated_fields['track_inventory'] = product.track_inventory
            
            if allow_backorders is not None:
                product.allow_backorders = allow_backorders in [True, 'true', 'True', 1, '1']
                updated_fields['allow_backorders'] = product.allow_backorders
            
            # Save product
            product.updated_by = request.user
            product.save()
            
            # Record changes in history
            for field_name, new_value in updated_fields.items():
                old_value = getattr(product, f'_meta').get_field(field_name).get_default() if hasattr(product, f'_meta') else None
                ProductChangeHistory.objects.create(
                    product=product,
                    changed_by=request.user,
                    change_type='field_update',
                    field_changed=field_name,
                    old_value=old_value,
                    new_value=new_value,
                    notes=f'Updated via inventory management form'
                )
            
            return Response({
                'id': product.id,
                'stock_quantity': product.stock_quantity,
                'low_stock_threshold': product.low_stock_threshold,
                'track_inventory': product.track_inventory,
                'allow_backorders': product.allow_backorders,
                'message': 'Inventory updated successfully',
                'updated_fields': updated_fields,
                'updated_at': timezone.now().isoformat()
            }, status=status.HTTP_200_OK)
        
        except (ValueError, TypeError) as e:
            return Response(
                {'detail': f'Invalid input: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f'Error updating inventory for product {pk}: {str(e)}')
            return Response(
                {'detail': f'Error updating inventory: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def perform_create(self, serializer):
        """Set created_by when creating product"""
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        """Set updated_by when updating product"""
        serializer.save(updated_by=self.request.user)
    
    @staticmethod
    def _validate_image_file(image_file):
        """Validate image file"""
        MAX_SIZE = 2 * 1024 * 1024  # 2MB
        ALLOWED_FORMATS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        
        # Check size
        if image_file.size > MAX_SIZE:
            raise serializers.ValidationError(f"Image exceeds 2MB limit ({image_file.size / 1024 / 1024:.1f}MB)")
        
        # Check format
        ext = image_file.name.split('.')[-1].lower()
        if ext not in ALLOWED_FORMATS:
            raise serializers.ValidationError(f"Invalid format. Allowed: {', '.join(ALLOWED_FORMATS)}")
        
        # Check dimensions with PIL
        try:
            from PIL import Image
            from django.core.files.uploadedfile import InMemoryUploadedFile
            
            if isinstance(image_file, InMemoryUploadedFile):
                image_file.seek(0)
            
            img = Image.open(image_file)
            if img.width < 300 or img.height < 300:
                raise serializers.ValidationError(
                    f"Image too small. Minimum 300x300px (yours: {img.width}x{img.height}px)"
                )
        except serializers.ValidationError:
            raise
        except Exception as e:
            raise serializers.ValidationError(f"Invalid image file: {str(e)}")
    
    @staticmethod
    def _detect_video_type(url):
        """Detect video type from URL"""
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        else:
            raise ValueError("Only YouTube and Vimeo URLs are supported")


class ProductApprovalRequestViewSet(viewsets.ModelViewSet):
    """
    API endpoints for product approval requests
    Manages approval workflow for sensitive product changes
    """
    queryset = ProductApprovalRequest.objects.select_related(
        'product', 'requested_by', 'approved_by', 'assigned_to'
    ).order_by('-requested_at')
    serializer_class = ProductApprovalRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['status', 'request_type', 'product', 'is_urgent']
    search_fields = ['product__name', 'product__internal_code', 'reason_for_change']
    ordering_fields = ['requested_at', 'status', 'is_urgent']
    
    def get_queryset(self):
        """Filter approval requests based on user role"""
        if getattr(self, 'swagger_fake_view', False):
            return ProductApprovalRequest.objects.none()
        
        user = self.request.user
        queryset = ProductApprovalRequest.objects.all()
        
        # Admins see all
        if user.groups.filter(name='Admin').exists():
            return queryset
        
        # Production Team sees their own and assigned to them
        if user.groups.filter(name='Production Team').exists():
            return queryset.filter(
                models.Q(requested_by=user) | models.Q(assigned_to=user)
            )
        
        # Others see only their own requests
        return queryset.filter(requested_by=user)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def approve(self, request, pk=None):
        """Approve a pending request"""
        approval = self.get_object()
        
        if approval.status != 'pending':
            return Response(
                {'error': f'Cannot approve {approval.status} request'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update approval
        approval.status = 'approved'
        approval.approved_by = request.user
        approval.approved_at = timezone.now()
        approval.save()
        
        # Create change history entry
        ProductChangeHistory.objects.create(
            product=approval.product,
            changed_by=request.user,
            change_type='approved',
            field_changed=approval.request_type,
            old_value=approval.old_value,
            new_value=approval.new_value,
            notes=f'Approval request {approval.id} approved'
        )
        
        serializer = self.get_serializer(approval)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def reject(self, request, pk=None):
        """Reject a pending request"""
        approval = self.get_object()
        reason = request.data.get('reason', '')
        
        if approval.status != 'pending':
            return Response(
                {'error': f'Cannot reject {approval.status} request'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update approval
        approval.status = 'rejected'
        approval.approved_by = request.user
        approval.approved_at = timezone.now()
        approval.approval_notes = reason
        approval.save()
        
        serializer = self.get_serializer(approval)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending approval requests"""
        pending_requests = self.get_queryset().filter(status='pending')
        
        # Apply sorting
        ordering = request.query_params.get('ordering', '-requested_at')
        pending_requests = pending_requests.order_by(ordering)
        
        # Paginate
        page = self.paginate_queryset(pending_requests)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(pending_requests, many=True)
        return Response(serializer.data)


#storefront- for later use
@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
class StorefrontProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public storefront-safe product listing for ecommerce/landing pages.
    Only returns visible, published products.
    """

    queryset = Product.objects.filter(status="published", is_visible=True)
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["primary_category", "sub_category", "customization_level"]
    search_fields = ["name", "short_description", "primary_category", "sub_category"]
    ordering_fields = ["created_at", "base_price"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client", "lead", "created_by").prefetch_related("line_items")
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin | IsProductionTeam]
    filterset_fields = ["status", "production_status", "client", "lead", "channel", "checkout_status"]
    search_fields = ["quote_id", "product_name", "reference_number"]
    ordering_fields = ["created_at", "quote_date", "valid_until"]

    def get_serializer_class(self):
        """Use MultiProductQuoteListSerializer for list view, QuoteSerializer for detail/create/update"""
        if self.action == 'list':
            from clientapp.api_serializers import MultiProductQuoteListSerializer
            return MultiProductQuoteListSerializer
        return QuoteSerializer

    def create(self, request, *args, **kwargs):
        """
        Override create to support nested line_items for bulk quote creation.
        Request body can include 'line_items' array for atomic creation.
        """
        line_items_data = request.data.pop('line_items', [])
        
        # Create the quote
        response = super().create(request, *args, **kwargs)
        
        # Create associated line items if provided
        if line_items_data and response.status_code == 201:
            quote_id = response.data['id']
            quote = Quote.objects.get(id=quote_id)
            
            for idx, line_item_data in enumerate(line_items_data):
                line_item_data['quote'] = quote_id
                line_item_data['order'] = idx
                QuoteLineItem.objects.create(
                    quote=quote,
                    product_id=line_item_data.get('product'),
                    product_name=line_item_data.get('product_name', ''),
                    customization_level_snapshot=line_item_data.get('customization_level_snapshot', ''),
                    base_price_snapshot=line_item_data.get('base_price_snapshot'),
                    quantity=line_item_data.get('quantity', 1),
                    unit_price=line_item_data.get('unit_price', 0),
                    discount_amount=line_item_data.get('discount_amount', 0),
                    discount_type=line_item_data.get('discount_type', 'percent'),
                    variable_amount=line_item_data.get('variable_amount', 0),
                    order=idx,
                )
            
            # Refresh the response with updated quote data
            quote.refresh_from_db()
            response.data = QuoteSerializer(quote).data
        
        return response

    @decorators.action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def ecommerce_create(self, request):
        """
        Lightweight public endpoint for ecommerce/landing-page checkout.
        Creates a Lead + single-product Quote tagged as channel='ecommerce'.
        """
        data = request.data or {}
        customer = data.get("customer", {})
        product_id = data.get("product_id")
        quantity = data.get("quantity") or 1
        notes = data.get("notes", "")

        if not product_id:
            return Response({"detail": "product_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found"}, status=status.HTTP_404_NOT_FOUND)

        name = customer.get("name") or "Online Customer"
        email = customer.get("email", "")
        phone = customer.get("phone", "")

        # Create a simple lead for tracking
        lead = None
        if email or phone:
            lead = Lead.objects.create(
                name=name,
                email=email or "",
                phone=phone or "",
                source="Website",
                product_interest=product.name,
                preferred_contact="Email",
                created_by=None,
            )

        unit_price = resolve_unit_price(product, quantity=quantity)

        quote = Quote.objects.create(
            client=None,
            lead=lead,
            product=product,
            product_name=product.name,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=unit_price * int(quantity),
            include_vat=True,
            payment_terms="Prepaid",
            status="Draft",
            channel="ecommerce",
            checkout_status="cart",
            customer_notes=notes,
        )

        serializer = self.get_serializer(quote)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def create_from_lead(self, request):
        """
        Create a draft quote from a lead, pre-filling product_name from product_interest.
        """
        lead_id = request.data.get("lead_id")
        quantity = int(request.data.get("quantity") or 1)
        if not lead_id:
            return Response({"detail": "lead_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lead = Lead.objects.get(pk=lead_id)
        except Lead.DoesNotExist:
            return Response({"detail": "Lead not found"}, status=status.HTTP_404_NOT_FOUND)

        product_name = lead.product_interest or "Custom Print Job"

        quote = Quote.objects.create(
            client=None,
            lead=lead,
            product=None,
            product_name=product_name,
            quantity=quantity,
            unit_price=0,
            total_amount=0,
            include_vat=False,
            payment_terms="Prepaid",
            status="Draft",
            channel="portal",
            checkout_status="draft",
            created_by=request.user,
        )

        serializer = self.get_serializer(quote)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def send_to_pt_for_review(self, request, pk=None):
        """
        Send quote to Production Team for costing review.
        Quote status: Draft → Sent to PT
        Optional: assigned_to (user_id) to assign to specific PT member
        """
        quote = self.get_object()
        
        if quote.status != "Draft":
            return Response(
                {"detail": f"Can only send Draft quotes to PT. Current status: {quote.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quote.status = "Sent to PT"
        quote.production_status = "pending"
        quote.save()
        
        # Handle assignment to specific PT member
        assigned_user = None
        assigned_to_id = request.data.get('assigned_to')
        
        if assigned_to_id:
            try:
                assigned_user = User.objects.get(pk=assigned_to_id)
                # Verify user is in Production Team
                if not assigned_user.groups.filter(name="Production Team").exists():
                    return Response(
                        {"detail": "Assigned user must be in Production Team group"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Store assignment (if there's an assigned_to field on quote)
                if hasattr(quote, 'assigned_to'):
                    quote.assigned_to = assigned_user
                    quote.save()
            except User.DoesNotExist:
                return Response(
                    {"detail": "Assigned user not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Notify PT team (or just the assigned user)
        if assigned_user:
            # Notify only the assigned user
            Notification.objects.create(
                recipient=assigned_user,
                notification_type='quote_sent_to_pt',
                title=f'Quote {quote.quote_id} Assigned to You',
                message=f'Quote {quote.quote_id} for {quote.client.name or "Lead"} has been assigned to you for costing review',
                link=f'/quotes/{quote.id}/',
            )
        else:
            # Notify all PT team members
            pt_group = Group.objects.filter(name="Production Team").first()
            if pt_group:
                for user in pt_group.user_set.all():
                    Notification.objects.create(
                        recipient=user,
                        notification_type='quote_sent_to_pt',
                        title=f'Quote {quote.quote_id} Requires Costing',
                        message=f'Quote {quote.quote_id} for {quote.client.name or "Lead"} is ready for costing review',
                        link=f'/quotes/{quote.id}/',
                    )
        
        # Log activity
        if quote.client:
            assigned_text = f" (assigned to {assigned_user.get_full_name() or assigned_user.username})" if assigned_user else ""
            ActivityLog.objects.create(
                client=quote.client,
                activity_type='Quote',
                title=f'Quote {quote.quote_id} Sent to PT{assigned_text}',
                description=f'Quote sent to Production Team for costing review{assigned_text}',
                related_quote=quote,
                created_by=request.user,
            )
        
        serializer = self.get_serializer(quote)
        return Response({
            'detail': 'Quote sent to PT for review',
            'quote': serializer.data
        })
    
    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def cost(self, request, pk=None):
        """
        PT reviews and costs the quote.
        Updates production_cost and moves to Costed status.
        """
        quote = self.get_object()
        
        if quote.status != "Sent to PT":
            return Response(
                {"detail": f"Can only cost quotes in 'Sent to PT' status. Current: {quote.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        production_cost = request.data.get('production_cost')
        notes = request.data.get('notes', '')
        
        if production_cost is None:
            return Response(
                {"detail": "production_cost is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quote.production_cost = float(production_cost)
            quote.production_notes = notes
            quote.production_status = "costed"
            quote.status = "Costed"
            quote.costed_by = request.user
            quote.save()
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid production_cost value"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Notify AM
        if quote.created_by:
            Notification.objects.create(
                recipient=quote.created_by,
                notification_type='quote_costed',
                title=f'Quote {quote.quote_id} Costed',
                message=f'Quote {quote.quote_id} has been costed by PT. Cost: {quote.production_cost}',
                link=f'/quotes/{quote.id}/',
            )
        
        # Log activity
        if quote.client:
            ActivityLog.objects.create(
                client=quote.client,
                activity_type='Quote',
                title=f'Quote {quote.quote_id} Costed',
                description=f'Production cost: {quote.production_cost}. Notes: {notes}',
                related_quote=quote,
                created_by=request.user,
            )
        
        serializer = self.get_serializer(quote)
        return Response({
            'detail': 'Quote costed successfully',
            'quote': serializer.data
        })
    
    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def send_to_customer(self, request, pk=None):
        """
        Send costed/draft quote to customer for approval.
        Quote can be sent from either Costed or Draft status.
        """
        quote = self.get_object()
        
        if quote.status not in ["Costed", "Draft", "Sent to PT"]:
            return Response(
                {"detail": f"Cannot send quote in {quote.status} status to customer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If PT costing is enabled and quote was sent to PT but not costed, reject
        if quote.status == "Sent to PT":
            return Response(
                {"detail": "Quote must be costed by PT before sending to customer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quote.status = "Sent to Customer"
        quote.production_status = "sent_to_client"
        quote.save()
        
        # Send email via service
        from .quote_approval_services import QuoteApprovalService
        result = QuoteApprovalService.send_quote_via_email(quote, request)
        
        if not result['success']:
            return Response(
                {"detail": f"Failed to send quote email: {result['message']}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log activity
        if quote.client:
            ActivityLog.objects.create(
                client=quote.client,
                activity_type='Quote',
                title=f'Quote {quote.quote_id} Sent to Customer',
                description='Quote sent to customer for approval',
                related_quote=quote,
                created_by=request.user,
            )
        
        serializer = self.get_serializer(quote)
        return Response({
            'detail': 'Quote sent to customer successfully',
            'quote': serializer.data,
            'email_result': result
        })

    @decorators.action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """
        Approve a quote, automatically generating LPO and Job.
        Uses quote.preferred_production_lead if set, otherwise accepts user_id in request.
        """
        quote = self.get_object()
        
        # Check if already approved
        if quote.status == "Approved":
            existing_lpo = LPO.objects.filter(quote=quote).first()
            existing_job = Job.objects.filter(quote=quote).first()
            return Response({
                "detail": "Quote already approved",
                "lpo_id": existing_lpo.id if existing_lpo else None,
                "job_id": existing_job.id if existing_job else None,
            })
        
        # Approve quote
        quote.status = "Approved"
        quote.approved_at = timezone.now()
        quote.production_status = "in_production"
        try:
            quote.save()
        except DjangoValidationError as exc:
            return Response({"detail": exc.message}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate LPO using QuoteApprovalService
        from .quote_approval_services import QuoteApprovalService
        lpo = QuoteApprovalService.generate_lpo(quote)
        
        # Determine person_in_charge:
        # 1. Use preferred_production_lead if set on quote
        # 2. Otherwise use user_id from request
        # 3. Otherwise leave unassigned
        person_in_charge = None
        
        if quote.preferred_production_lead:
            person_in_charge = quote.preferred_production_lead
        else:
            user_id = request.data.get("user_id")
            if user_id:
                try:
                    assigned_user = User.objects.get(pk=user_id)
                    # Verify user is in Production Team
                    if not assigned_user.groups.filter(name="Production Team").exists():
                        return Response(
                            {"detail": "User must be in Production Team group"}, 
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    person_in_charge = assigned_user
                except User.DoesNotExist:
                    return Response(
                        {"detail": "User not found"}, 
                        status=status.HTTP_404_NOT_FOUND
                    )
        
        # Create Job with assigned person_in_charge
        job = Job.objects.create(
            client=quote.client,
            quote=quote,
            job_name=f"Job for {quote.product_name}",
            job_type="printing",
            product=quote.product_name,
            quantity=quote.quantity or 1,
            person_in_charge=person_in_charge,
            status="pending",
            expected_completion=quote.valid_until,
            created_by=quote.created_by,
        )
        
        # Send notifications
        QuoteApprovalService.send_approval_notifications(quote, lpo, job)
        
        # Create activity log
        if quote.client:
            ActivityLog.objects.create(
                client=quote.client,
                activity_type="Quote",
                title=f"Quote {quote.quote_id} Approved",
                description=f"Quote approved. LPO {lpo.lpo_number} and Job {job.job_number} created.",
                related_quote=quote,
                created_by=request.user,
            )
        
        return Response({
            "detail": "Quote approved, LPO and Job created",
            "lpo_id": lpo.id,
            "lpo_number": lpo.lpo_number,
            "job_id": job.id,
            "job_number": job.job_number,
        })

    @decorators.action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        """
        Get the activity history for a specific quote.
        Shows when quote was sent, viewed by customer, approved, etc.
        """
        quote = self.get_object()
        
        # Get all activity logs related to this quote
        activities = ActivityLog.objects.filter(related_quote=quote).order_by('-created_at')
        serializer = ActivityLogSerializer(activities, many=True)
        
        return Response({
            "quote_id": quote.quote_id,
            "status": quote.status,
            "history": serializer.data,
        })

    @decorators.action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        """
        Clone an approved (locked) quote to create a revision.
        Returns new quote in Draft status.
        """
        quote = self.get_object()
        
        if not quote.is_locked:
            return Response(
                {"detail": "Can only clone locked/approved quotes. Use direct edit for draft quotes."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            revised_quote = quote.create_revised_quote(revised_by=request.user)
            serializer = self.get_serializer(revised_quote)
            return Response({
                "detail": f"Quote cloned successfully. Original: {quote.quote_id}, Revision: {revised_quote.quote_id}",
                "revised_quote": serializer.data
            })
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @decorators.action(detail=True, methods=["post"])
    def send_to_production(self, request, pk=None):
        """
        Send quote to production by creating a job.
        Optional: user_id to assign a specific Production Team member.
        """
        quote = self.get_object()
        if hasattr(quote, "job"):
            return Response({"detail": "Job already exists", "job_id": quote.job.id})
        
        # Get optional person_in_charge from request
        person_in_charge = None
        user_id = request.data.get("user_id")
        if user_id:
            try:
                assigned_user = User.objects.get(pk=user_id)
                # Verify user is in Production Team
                if not assigned_user.groups.filter(name="Production Team").exists():
                    return Response(
                        {"detail": "User must be in Production Team group"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                person_in_charge = assigned_user
            except User.DoesNotExist:
                return Response(
                    {"detail": "User not found"}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        job = Job.objects.create(
            client=quote.client,
            quote=quote,
            job_name=quote.product_name,
            job_type="printing",
            priority="normal",
            product=quote.product_name,
            quantity=quote.quantity or 1,
            person_in_charge=person_in_charge,
            source=quote.channel,
            created_by=request.user,
        )
        
        # Create notification if user is assigned
        if person_in_charge:
            Notification.objects.create(
                recipient=person_in_charge,
                notification_type="job_assigned",
                title=f"New Job {job.job_number} Assigned",
                message=f"You have been assigned to job {job.job_number}: {job.job_name}",
                link=f"/job/{job.pk}/",
            )
        
        serializer = JobSerializer(job)
        return Response({"detail": "Job created", "job": serializer.data})

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin], url_path="mark-lost")
    def mark_lost(self, request, pk=None):
        """
        Mark a quote as lost with reason.
        """
        quote = self.get_object()
        
        if quote.status == "Approved":
            return Response(
                {"detail": "Cannot mark approved quotes as lost"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get("reason", "")
        if not reason:
            return Response(
                {"detail": "Loss reason is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        quote.status = "Lost"
        quote.loss_reason = reason
        quote.production_status = "cancelled"
        quote.save()
        
        # Log activity
        if quote.client:
            ActivityLog.objects.create(
                client=quote.client,
                activity_type='Quote',
                title=f'Quote {quote.quote_id} Marked as Lost',
                description=f'Reason: {reason}',
                related_quote=quote,
                created_by=request.user,
            )
        
        serializer = self.get_serializer(quote)
        return Response({
            'detail': 'Quote marked as lost',
            'quote': serializer.data
        })

    @decorators.action(detail=True, methods=["get"], url_path="download-pdf")
    def download_pdf(self, request, pk=None):
        """
        Generate and download quote as PDF.
        """
        from django.http import HttpResponse
        from .pdf_utils import generate_quote_pdf
        
        quote = self.get_object()
        
        try:
            pdf_buffer = generate_quote_pdf(quote)
            response = HttpResponse(pdf_buffer, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="quote_{quote.quote_id}.pdf"'
            return response
        except Exception as e:
            return Response(
                {"detail": f"Failed to generate PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_update(self, serializer):
        """
        Override perform_update to enforce quote locking.
        Prevents editing of locked/approved quotes via API.
        """
        if serializer.instance.is_locked:
            raise serializers.ValidationError(
                "This quote is locked (Approved). Please create a revised quote (clone) to make changes."
            )
        serializer.save()


from rest_framework.views import APIView

class PublicQuoteDetailView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request, token):
        from .models import QuoteApprovalToken
        
        try:
            approval_token = QuoteApprovalToken.objects.select_related('quote').get(
                token=token,
                expires_at__gt=timezone.now()
            )
            quote = approval_token.quote
            
            serializer = QuoteSerializer(quote)
            return Response(serializer.data)
            
        except QuoteApprovalToken.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_404_NOT_FOUND
            )


class PublicQuoteAcceptView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, token):
        from .models import QuoteApprovalToken, Notification, ActivityLog
        from django.contrib.auth.models import Group
        
        try:
            approval_token = QuoteApprovalToken.objects.select_related('quote').get(
                token=token,
                expires_at__gt=timezone.now(),
                used=False
            )
            quote = approval_token.quote
            
            if quote.status == "Approved":
                return Response(
                    {"detail": "Quote has already been accepted"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            quote.status = "Approved"
            quote.save()
            
            approval_token.used = True
            approval_token.used_at = timezone.now()
            approval_token.save()
            
            am_group = Group.objects.filter(name="Account Manager").first()
            if am_group and quote.created_by:
                Notification.objects.create(
                    recipient=quote.created_by,
                    notification_type='quote_approved',
                    title=f'Quote {quote.quote_id} Accepted',
                    message=f'Customer has accepted quote {quote.quote_id}',
                    link=f'/quotes/{quote.id}/',
                )
            
            if quote.client:
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='Quote',
                    title=f'Quote {quote.quote_id} Approved by Customer',
                    description='Customer accepted the quote via email link',
                    related_quote=quote,
                )
            
            return Response({
                "detail": "Quote accepted successfully",
                "quote_id": quote.quote_id,
                "status": quote.status
            })
            
        except QuoteApprovalToken.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_404_NOT_FOUND
            )


class PublicQuoteRejectView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, token):
        from .models import QuoteApprovalToken, Notification, ActivityLog
        
        try:
            approval_token = QuoteApprovalToken.objects.select_related('quote').get(
                token=token,
                expires_at__gt=timezone.now(),
                used=False
            )
            quote = approval_token.quote
            
            if quote.status == "Lost":
                return Response(
                    {"detail": "Quote has already been rejected"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reason = request.data.get('reason', 'Customer declined')
            
            quote.status = "Lost"
            quote.lost_reason = reason
            quote.save()
            
            approval_token.used = True
            approval_token.used_at = timezone.now()
            approval_token.save()
            
            if quote.created_by:
                Notification.objects.create(
                    recipient=quote.created_by,
                    notification_type='quote_rejected',
                    title=f'Quote {quote.quote_id} Declined',
                    message=f'Customer declined quote {quote.quote_id}. Reason: {reason}',
                    link=f'/quotes/{quote.id}/',
                )
            
            if quote.client:
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='Quote',
                    title=f'Quote {quote.quote_id} Rejected by Customer',
                    description=f'Customer declined the quote via email link. Reason: {reason}',
                    related_quote=quote,
                )
            
            return Response({
                "detail": "Quote rejected successfully",
                "quote_id": quote.quote_id,
                "status": quote.status
            })
            
        except QuoteApprovalToken.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired token"},
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))
class QuoteLineItemViewSet(viewsets.ModelViewSet):
    queryset = QuoteLineItem.objects.select_related("quote", "product").all()
    serializer_class = QuoteLineItemSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["quote", "product"]
    search_fields = ["product_name"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.select_related("client", "quote", "created_by", "person_in_charge").all()
    serializer_class = JobSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["status", "client", "quote", "person_in_charge"]
    search_fields = ["job_number", "job_name", "product"]
    ordering_fields = ["created_at", "start_date", "expected_completion"]

    def get_queryset(self):
        """Add deadline filtering support"""
        queryset = super().get_queryset()
        
        # Filter by deadline status
        deadline_filter = self.request.query_params.get('deadline_status', None)
        if deadline_filter:
            from datetime import date
            today = date.today()
            
            if deadline_filter == 'overdue':
                queryset = queryset.filter(
                    expected_completion__lt=today,
                    status__in=['pending', 'in_progress']
                )
            elif deadline_filter == 'approaching':
                # Jobs due in next 3 days
                from datetime import timedelta
                three_days_later = today + timedelta(days=3)
                queryset = queryset.filter(
                    expected_completion__gte=today,
                    expected_completion__lte=three_days_later,
                    status__in=['pending', 'in_progress']
                )
        
        return queryset

    @decorators.action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        job = self.get_object()
        next_status = request.data.get("status")
        if next_status not in dict(Job.STATUS_CHOICES):
            return Response({"detail": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)
        job.status = next_status
        job.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Status updated", "status": job.status})

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def assign(self, request, pk=None):
        """
        Assign or reassign a job to a specific Production Team member.
        Requires: user_id in request data
        """
        job = self.get_object()
        user_id = request.data.get("user_id")
        
        if not user_id:
            return Response(
                {"detail": "user_id is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            assigned_user = User.objects.get(pk=user_id)
            # Verify user is in Production Team
            if not assigned_user.groups.filter(name="Production Team").exists():
                return Response(
                    {"detail": "User must be in Production Team group"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            job.person_in_charge = assigned_user
            job.save(update_fields=["person_in_charge", "updated_at"])
            
            # Create notification for assigned user
            Notification.objects.create(
                recipient=assigned_user,
                notification_type="job_assigned",
                title=f"Job {job.job_number} Assigned",
                message=f"You have been assigned to job {job.job_number}: {job.job_name}",
                link=f"/job/{job.pk}/",
            )
            
            # Log activity
            ActivityLog.objects.create(
                client=job.client,
                activity_type="Job",
                title=f"Job {job.job_number} Assigned",
                description=f"Job assigned to {assigned_user.get_full_name() or assigned_user.username}",
                created_by=request.user,
            )
            
            serializer = self.get_serializer(job)
            return Response({
                "detail": "Job assigned successfully",
                "job": serializer.data
            })
            
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

    @decorators.action(detail=True, methods=["get"], url_path='production-units', permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def production_units(self, request, pk=None):
        """
        List production units for a specific job.
        URL: GET /api/v1/jobs/{job_id}/production-units/
        """
        try:
            job = self.get_object()
        except Exception:
            return Response({"detail": "Job not found"}, status=status.HTTP_404_NOT_FOUND)

        # Filter units by job
        units_qs = ProductionUnit.objects.filter(job=job)

        # Import storefront serializer to avoid circular imports at module level
        try:
            from clientapp.storefront_serializers import ProductionUnitSerializer
        except Exception:
            # Fallback to a simple serializer representation
            data = [
                {
                    'unit_id': u.id,
                    'unit_type': u.unit_type,
                    'status': u.status,
                    'vendor': getattr(u.vendor, 'id', None),
                    'estimated_start': u.expected_start_date,
                    'estimated_end': u.expected_end_date,
                }
                for u in units_qs
            ]
            return Response({'job_id': job.id, 'production_units': data})

        serializer = ProductionUnitSerializer(units_qs, many=True, context={'request': request})
        return Response({'job_id': job.id, 'production_units': serializer.data})

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def remind(self, request, pk=None):
        """
        Send a reminder notification to the assigned Production Team member.
        4 Hour cool-down period to prevent spam
        """
        from datetime import timedelta
        
        job = self.get_object()
        
        if not job.person_in_charge:
            return Response(
                {"detail": "No user assigned to this job"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check cooldown: get last reminder from activity log
        last_reminder = ActivityLog.objects.filter(
            client=job.client,
            activity_type="Job",
            title__contains=f"Reminder Sent for Job {job.job_number}",
        ).order_by('-created_at').first()
        
        if last_reminder:
            time_since_last = timezone.now() - last_reminder.created_at
            cooldown_period = timedelta(hours=4)
            
            if time_since_last < cooldown_period:
                remaining_minutes = int((cooldown_period - time_since_last).total_seconds() / 60)
                return Response(
                    {
                        "detail": f"Reminder cooldown active. Please wait {remaining_minutes} minutes before sending another reminder.",
                        "retry_after_minutes": remaining_minutes
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
        
        # Create notification for assigned user
        Notification.objects.create(
            recipient=job.person_in_charge,
            notification_type="job_reminder",
            title=f"Reminder: {job.job_name}",
            message=f"Reminder for job {job.job_number} ({job.client.name}). Due date: {job.expected_completion}. Please update status.",
            link=f"/job/{job.pk}/",
        )
        
        # Send Email Reminder
        if job.person_in_charge.email:
            try:
                from django.core.mail import send_mail
                from django.template.loader import render_to_string
                
                context = {
                    'user_first_name': job.person_in_charge.first_name or 'Team Member',
                    'job_number': job.job_number or job.pk,
                    'job_name': job.job_name,
                    'client_name': (job.client.company or job.client.name) if job.client else 'Unknown Client',
                    'due_date': job.expected_completion.strftime('%B %d, %Y') if job.expected_completion else 'TBD',
                    'priority': job.get_priority_display().upper() if hasattr(job, 'get_priority_display') else 'NORMAL',
                    'job_url': f"{settings.SITE_URL}/job/{job.id}/" if hasattr(settings, 'SITE_URL') else f"http://localhost:8000/job/{job.id}/",
                    'product_summary': job.product or 'Production Required',
                    'reminder_by': request.user.get_full_name() or request.user.username,
                }
                
                subject = f"⏰ Reminder: Job {job.job_number} - {job.job_name}"
                
                try:
                    html_message = render_to_string('emails/job_reminder_notification.html', context)
                except Exception:
                    html_message = f"""
                    <html>
                        <body>
                            <h2>Job Reminder</h2>
                            <p>Hi {context['user_first_name']},</p>
                            <p>This is a reminder about your assigned job:</p>
                            <ul>
                                <li><strong>Job Number:</strong> {context['job_number']}</li>
                                <li><strong>Job Name:</strong> {context['job_name']}</li>
                                <li><strong>Client:</strong> {context['client_name']}</li>
                                <li><strong>Due Date:</strong> {context['due_date']}</li>
                                <li><strong>Priority:</strong> {context['priority']}</li>
                            </ul>
                            <p>Please update the job status or contact the account manager if you need assistance.</p>
                            <p><a href="{context['job_url']}">View Job Details</a></p>
                            <p><small>Reminder sent by: {context['reminder_by']}</small></p>
                        </body>
                    </html>
                    """
                
                send_mail(
                    subject,
                    f"Reminder: Job {job.job_number} needs your attention. Due: {context['due_date']}. View details: {context['job_url']}",
                    settings.DEFAULT_FROM_EMAIL,
                    [job.person_in_charge.email],
                    html_message=html_message,
                    fail_silently=True,
                )
                
                logger.info(f"Job reminder email sent to {job.person_in_charge.email} for job {job.job_number}")
            except Exception as e:
                logger.error(f"Error sending job reminder email: {str(e)}")
        
        # Log activity with timestamp for cooldown tracking
        ActivityLog.objects.create(
            client=job.client,
            activity_type="Job",
            title=f"Reminder Sent for Job {job.job_number}",
            description=f"Reminder sent to {job.person_in_charge.get_full_name() or job.person_in_charge.username}",
            created_by=request.user,
        )
        
        return Response({
            "detail": "Reminder sent successfully (notification + email)",
            "recipient": job.person_in_charge.get_full_name() or job.person_in_charge.username,
            "next_reminder_allowed": (timezone.now() + timedelta(hours=4)).isoformat()
        })

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def send_to_vendor(self, request, pk=None):
        """
        Send job specifications to a vendor.
        Packages job attachments and specs into a vendor-ready format.
        
        ✅ NEW: Includes vendor capacity checking
        """
        job = self.get_object()
        vendor_id = request.data.get("vendor_id")
        stage_name = request.data.get("stage_name", "Production")
        expected_days = int(request.data.get("expected_days", 3))
        total_cost = request.data.get("total_cost", 0)
        
        if not vendor_id:
            return Response(
                {"detail": "vendor_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            vendor = Vendor.objects.get(pk=vendor_id, active=True)
        except Vendor.DoesNotExist:
            return Response(
                {"detail": "Vendor not found or inactive"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # ✅ NEW: Check vendor capacity
        if vendor.is_at_capacity():
            return Response({
                'detail': f'Vendor {vendor.name} is at capacity',
                'error': 'VENDOR_AT_CAPACITY',
                'vendor': {
                    'id': vendor.id,
                    'name': vendor.name,
                    'workload': {
                        'current_jobs': vendor.get_current_workload(),
                        'max_capacity': vendor.max_concurrent_jobs,
                        'available_capacity': vendor.get_available_capacity(),
                        'utilization_percent': vendor.get_workload_percentage(),
                    }
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create vendor stage
        last_stage = job.vendor_stages.order_by('-stage_order').first()
        next_order = (last_stage.stage_order + 1) if last_stage else 1
        
        from datetime import timedelta
        vendor_stage = JobVendorStage.objects.create(
            job=job,
            vendor=vendor,
            stage_order=next_order,
            stage_name=stage_name,
            expected_completion=timezone.now() + timedelta(days=expected_days),
            status='sent_to_vendor',
        )
        
        # Create Purchase Order for this job-vendor assignment
        try:
            from decimal import Decimal
            po = PurchaseOrder.objects.create(
                job=job,
                vendor=vendor,
                product_type=job.product_type if hasattr(job, 'product_type') else stage_name,
                product_description=job.description if hasattr(job, 'description') else f'{stage_name} - {job.job_number}',
                quantity=1,
                total_cost=Decimal(str(float(total_cost))) if total_cost else Decimal('0'),
                status='NEW',
                milestone='awaiting_acceptance',
                required_by=timezone.now().date() + timedelta(days=expected_days),
            )
        except Exception as e:
            # If PurchaseOrder creation fails, still continue with JobVendorStage
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create PurchaseOrder for job {job.id}: {str(e)}", exc_info=True)
            po = None
        
        # Get job attachments
        attachments = job.attachments.all()
        attachment_list = [{
            "file_name": att.file_name,
            "file_size": att.file_size,
            "uploaded_at": att.uploaded_at,
        } for att in attachments]
        
        # Send vendor notification
        from .vendor_notifications import VendorNotificationService
        VendorNotificationService.notify_job_assignment(vendor_stage, vendor)
        
        # Create activity log
        ActivityLog.objects.create(
            client=job.client,
            activity_type="Job",
            title=f"Job {job.job_number} Sent to Vendor",
            description=f"Job sent to {vendor.name} for {stage_name}. Expected completion: {vendor_stage.expected_completion.date()}",
            created_by=request.user,
        )
        
        # Update job status if first stage
        if next_order == 1:
            job.status = 'in_progress'
            job.save()
        
        # ✅ NEW: Include vendor workload in response
        return Response({
            "detail": "Job sent to vendor successfully",
            "vendor_stage_id": vendor_stage.id,
            "vendor_name": vendor.name,
            "expected_completion": vendor_stage.expected_completion,
            "attachments_count": len(attachment_list),
            "attachments": attachment_list,
            "po_id": po.id if po else None,
            "vendor_workload": {
                'current_jobs': vendor.get_current_workload(),
                'max_capacity': vendor.max_concurrent_jobs,
                'available_capacity': vendor.get_available_capacity(),
                'utilization_percent': vendor.get_workload_percentage(),
            }
        })

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def upload_attachments(self, request, pk=None):
        """
        Upload file attachments to a job.
        Accepts multipart form data with 'files' field
        """
        job = self.get_object()
        
        if 'files' not in request.FILES:
            return Response(
                {"detail": "No files provided"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        files = request.FILES.getlist('files')
        if not files:
            return Response(
                {"detail": "No files in request"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from clientapp.models import JobAttachment
        uploaded_files = []
        
        try:
            for file in files:
                attachment = JobAttachment.objects.create(
                    job=job,
                    file=file,
                    file_name=file.name,
                    file_size=file.size,
                    uploaded_by=request.user,
                )
                uploaded_files.append({
                    "id": attachment.id,
                    "file_name": attachment.file_name,
                    "file_size": attachment.file_size,
                    "uploaded_at": attachment.uploaded_at.isoformat(),
                })
            
            # Create activity log
            from clientapp.models import ActivityLog
            ActivityLog.objects.create(
                client=job.client,
                activity_type="Job",
                title=f"Files Uploaded to Job {job.job_number}",
                description=f"Production Team uploaded {len(uploaded_files)} file(s)",
                created_by=request.user,
            )
            
            return Response({
                "detail": f"Successfully uploaded {len(uploaded_files)} file(s)",
                "uploaded_files": uploaded_files,
                "total_attachments": job.attachments.count(),
            })
            
        except Exception as e:
            return Response(
                {"detail": f"Error uploading files: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def update_progress(self, request, pk=None):
        """
        Vendor updates job progress
        Required: progress (0-100), status
        Optional: notes
        """
        from .vendor_notifications import PTNotificationService
        
        job = self.get_object()
        
        # Get vendor stages for this job
        vendor_stage = job.vendor_stages.filter(vendor__user=request.user).first()
        
        if not vendor_stage:
            return Response(
                {"detail": "You are not assigned to this job"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        progress = int(request.data.get("progress", 0))
        status_update = request.data.get("status", "in_production")
        notes = request.data.get("notes", "")
        
        # Validate progress
        if not (0 <= progress <= 100):
            return Response(
                {"detail": "Progress must be between 0 and 100"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update vendor stage
        vendor_stage.progress = progress
        vendor_stage.status = status_update
        vendor_stage.notes = notes
        vendor_stage.save()
        
        # Check if overdue
        if vendor_stage.expected_completion and timezone.now() > vendor_stage.expected_completion:
            days_overdue = (timezone.now() - vendor_stage.expected_completion).days
            # Notify PT team if overdue
            if days_overdue > 0:
                PTNotificationService.notify_pt_job_overdue(vendor_stage)
        
        # Log activity
        ActivityLog.objects.create(
            client=job.client,
            activity_type="Job",
            title=f"Progress Update: Job {job.job_number}",
            description=f"{vendor_stage.vendor.name} updated progress to {progress}%. Status: {status_update}.",
            created_by=request.user,
        )
        
        return Response({
            "detail": "Progress updated successfully",
            "job_number": job.job_number,
            "progress": progress,
            "status": status_update,
            "notes": notes,
            "is_overdue": timezone.now() > vendor_stage.expected_completion if vendor_stage.expected_completion else False,
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class VendorViewSet(viewsets.ModelViewSet):
    queryset = Vendor.objects.all()
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["vps_score_value", "active"]
    search_fields = ["name", "email", "phone", "services"]

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def recalculate_vps(self, request, pk=None):
        """
        Recalculate Vendor Performance Score based on QC and Delivery data.
        """
        vendor = self.get_object()
        result = vendor.calculate_vps()
        
        serializer = self.get_serializer(vendor)
        return Response({
            "detail": "VPS recalculated successfully",
            "vendor": serializer.data,
            "calculation_details": result,
        })
    
    @decorators.action(detail=True, methods=["get"])
    def workload(self, request, pk=None):
        """
        Get vendor workload and capacity information.
        
        Returns:
        - current_jobs: Number of active jobs
        - max_capacity: Maximum concurrent jobs allowed
        - available_capacity: Number of available slots
        - utilization_percent: Workload as percentage (0-100)
        - is_at_capacity: Boolean flag
        - active_stages: List of active job stages
        """
        vendor = self.get_object()
        
        # Get active job vendor stages
        from clientapp.api_serializers import JobVendorStageSerializer
        active_stages = vendor.job_vendor_stages.filter(
            status__in=['sent_to_vendor', 'in_production']
        ).select_related('job').order_by('-created_at')[:10]
        
        return Response({
            'vendor_id': vendor.id,
            'vendor_name': vendor.name,
            'workload': {
                'current_jobs': vendor.get_current_workload(),
                'max_capacity': vendor.max_concurrent_jobs,
                'available_capacity': vendor.get_available_capacity(),
                'utilization_percent': vendor.get_workload_percentage(),
                'is_at_capacity': vendor.is_at_capacity(),
            },
            'active_stages': JobVendorStageSerializer(active_stages, many=True).data,
            'status': 'OK',
        })

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager])
    def invite(self, request, pk=None):
        """Create/resend vendor portal invite for a vendor contact."""
        vendor = self.get_object()

        if not vendor.email:
            return Response(
                {"detail": "Vendor email is required before sending an invite."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = vendor.user
        user_created = False

        if user is None:
            username_base = vendor.email.split("@")[0] if "@" in vendor.email else f"vendor{vendor.id}"
            username = username_base
            counter = 1

            while User.objects.filter(username=username).exists():
                username = f"{username_base}{counter}"
                counter += 1

            first_name = (vendor.contact_person or "").strip().split(" ")[0] if vendor.contact_person else vendor.name[:50]
            user = User.objects.create(
                username=username,
                email=vendor.email,
                first_name=first_name,
                is_active=False,
                is_staff=False,
            )
            vendor.user = user
            vendor.save(update_fields=["user", "updated_at"])
            user_created = True
        else:
            user.email = vendor.email
            user.is_active = False
            user.is_staff = False
            user.save(update_fields=["email", "is_active", "is_staff"])

        invite_token = secrets.token_urlsafe(32)
        cache.set(f"vendor_invite_{invite_token}", user.id, 172800)

        invite_url = request.build_absolute_uri(f"/vendor/invite/{invite_token}/")
        send_invite = request.data.get("send_invite", True)
        email_sent = False

        if send_invite:
            try:
                contact = vendor.contact_person or vendor.name
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "PrintDuka <dev@printduka.co.ke>")
                plain_body = (
                    f"Hello {contact},\n\n"
                    f"You have been invited to the PrintDuka Vendor Portal.\n\n"
                    f"Set your password and activate your account here:\n{invite_url}\n\n"
                    "This link expires in 48 hours.\n\n"
                    "PrintDuka Team"
                )
                html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Vendor Portal Invitation</title></head>
<body style="margin:0;padding:0;background-color:#f0f4f8;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f0f4f8;padding:40px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
        <tr><td style="background-color:#093756;border-radius:8px 8px 0 0;padding:32px 40px;text-align:center;">
          <h1 style="margin:0;color:#f6b619;font-size:24px;font-weight:800;letter-spacing:1px;">PRINT<span style="color:#ffffff;">DUKA</span></h1>
          <p style="margin:8px 0 0;color:#a8c4d8;font-size:12px;letter-spacing:2px;text-transform:uppercase;">Vendor Portal</p>
        </td></tr>
        <tr><td style="background-color:#ffffff;padding:40px;">
          <h2 style="margin:0 0 16px;color:#093756;font-size:20px;font-weight:700;">You&rsquo;re invited, {contact}</h2>
          <p style="margin:0 0 24px;color:#444444;font-size:15px;line-height:1.6;">
            You have been registered as a supplier on the <strong>PrintDuka Vendor Portal</strong>.
            Click the button below to set your password and activate your account.
          </p>
          <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #e8ecf0;border-radius:6px;overflow:hidden;margin-bottom:28px;">
            <tr><td colspan="2" style="background-color:#093756;padding:12px 16px;"><span style="color:#f6b619;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Your Account Details</span></td></tr>
            <tr style="background-color:#f8fafc;"><td style="padding:10px 16px;color:#555555;font-size:14px;width:40%;border-bottom:1px solid #e8ecf0;">Company</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:700;border-bottom:1px solid #e8ecf0;">{vendor.name}</td></tr>
            <tr><td style="padding:10px 16px;color:#555555;font-size:14px;border-bottom:1px solid #e8ecf0;">Login Email</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:600;border-bottom:1px solid #e8ecf0;">{vendor.email}</td></tr>
            <tr style="background-color:#f8fafc;"><td style="padding:10px 16px;color:#555555;font-size:14px;">Link Expires</td><td style="padding:10px 16px;color:#093756;font-size:14px;font-weight:600;">48 hours</td></tr>
          </table>
          <div style="text-align:center;margin-bottom:28px;">
            <a href="{invite_url}" style="display:inline-block;background-color:#f6b619;color:#093756;font-size:15px;font-weight:800;text-decoration:none;padding:14px 36px;border-radius:6px;letter-spacing:0.5px;">Activate My Account &rarr;</a>
          </div>
          <p style="margin:0;color:#888888;font-size:12px;line-height:1.6;">
            If the button doesn&rsquo;t work, copy and paste this link into your browser:<br>
            <a href="{invite_url}" style="color:#093756;word-break:break-all;">{invite_url}</a>
          </p>
        </td></tr>
        <tr><td style="background-color:#093756;border-radius:0 0 8px 8px;padding:24px 40px;text-align:center;">
          <p style="margin:0 0 4px;color:#a8c4d8;font-size:12px;">This is an automated notification from PrintDuka.</p>
          <p style="margin:0;color:#6b8fa8;font-size:11px;">&copy; 2026 PrintDuka. All rights reserved.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""
                msg = EmailMultiAlternatives(
                    subject=f"[PrintDuka] Vendor Portal Invitation — {vendor.name}",
                    body=plain_body,
                    from_email=from_email,
                    to=[vendor.email],
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)
                email_sent = True
            except Exception as exc:
                logger.warning("Vendor invite email failed for vendor %s: %s", vendor.id, exc)

        # Log notification for all Admin + Production Team staff so they can track invites
        staff_users = User.objects.filter(
            is_active=True,
            groups__name__in=["Admin", "Production Team"],
        ).distinct()
        for staff_user in staff_users:
            try:
                Notification.objects.create(
                    recipient=staff_user,
                    notification_type="vendor_portal_invite_sent",
                    title=f"Vendor Invite {'Sent' if email_sent else 'Prepared'} — {vendor.name}",
                    message=(
                        f"Portal invite {'sent to' if email_sent else 'prepared for'} "
                        f"{vendor.name} ({vendor.email}). "
                        f"{'Link delivered by email.' if email_sent else 'Email delivery failed — share the link manually.'}"
                    ),
                    action_url="/production-team/vendors",
                )
            except Exception as notif_exc:
                logger.warning("Could not create invite Notification for staff %s: %s", staff_user.pk, notif_exc)

        return Response(
            {
                "detail": "Vendor invite prepared successfully.",
                "vendor_id": vendor.id,
                "user_created": user_created,
                "email_sent": email_sent,
                "invite_url": invite_url,
            },
            status=status.HTTP_200_OK,
        )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class LPOViewSet(viewsets.ModelViewSet):
    queryset = LPO.objects.select_related("client", "quote", "created_by").all()
    serializer_class = LPOSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsAccountManager]
    filterset_fields = ["status", "client", "quote"]
    search_fields = ["lpo_number", "terms_and_conditions"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("lpo", "recorded_by").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsAccountManager]
    filterset_fields = ["status", "payment_method", "lpo"]
    search_fields = ["reference_number"]
    ordering_fields = ["payment_date", "amount"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    Purchase Order ViewSet - Manages POs created from approved quotes/jobs.
    Vendors can view and accept their POs.
    PT can manage, update, and block POs.
    """
    queryset = PurchaseOrder.objects.select_related('job', 'vendor', 'job__client').all()
    serializer_class = PurchaseOrderDetailedSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager | IsVendor]
    filterset_fields = ['vendor', 'status', 'milestone', 'job']
    search_fields = ['po_number', 'product_type', 'job__job_number']
    ordering_fields = ['created_at', 'required_by', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter POs based on user role"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        # Vendors can only see their own POs
        try:
            vendor = Vendor.objects.get(user=user, active=True)
            queryset = queryset.filter(vendor=vendor)
            return queryset
        except Vendor.DoesNotExist:
            pass  # User is not a vendor, continue with other filtering
        
        # Filter by vendor_id if specified in query params
        vendor_id = self.request.query_params.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        return queryset
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin) | IsVendor])
    def accept(self, request, pk=None):
        """Vendor accepts the purchase order"""
        po = self.get_object()
        
        if po.vendor_accepted:
            return Response(
                {'detail': 'Purchase order already accepted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        po.vendor_accepted = True
        po.vendor_accepted_at = timezone.now()
        po.status = 'ACCEPTED'
        po.milestone = 'in_production'
        po.save()
        
        # Create notification
        if po.job.person_in_charge:
            Notification.objects.create(
                recipient=po.job.person_in_charge,
                notification_type='po_accepted',
                title=f'PO {po.po_number} Accepted',
                message=f'{po.vendor.name} accepted PO {po.po_number}',
                link=f'/purchase-orders/{po.id}/',
            )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Purchase Order',
            title=f'PO {po.po_number} Accepted',
            description=f'{po.vendor.name} accepted the purchase order',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(po)
        return Response({'detail': 'Purchase order accepted', 'po': serializer.data})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, (IsProductionTeam | IsAdmin) | IsVendor])
    def update_milestone(self, request, pk=None):
        """Update PO milestone (production stage)"""
        po = self.get_object()
        milestone = request.data.get('milestone')
        notes = request.data.get('notes', '')
        
        if milestone not in dict(PurchaseOrder.MILESTONE_CHOICES):
            return Response({'error': 'Invalid milestone'}, status=status.HTTP_400_BAD_REQUEST)
        
        old_milestone = po.milestone
        po.milestone = milestone
        
        milestone_status_map = {
            'awaiting_acceptance': 'NEW',
            'in_production': 'IN_PRODUCTION',
            'quality_check': 'AWAITING_APPROVAL',
            'completed': 'COMPLETED',
        }
        
        po.status = milestone_status_map.get(milestone, po.status)
        
        if notes:
            po.vendor_notes = notes
        
        if milestone == 'completed':
            po.completed_at = timezone.now()
            po.completed_on_time = po.required_by >= timezone.now().date()
        
        po.save()
        
        # Notify PT
        if po.job.person_in_charge:
            Notification.objects.create(
                recipient=po.job.person_in_charge,
                notification_type='po_milestone_update',
                title=f'PO {po.po_number} Progress Update',
                message=f'{po.vendor.name} updated PO to: {milestone.replace("_", " ").title()}',
                link=f'/purchase-orders/{po.id}/',
            )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Purchase Order',
            title=f'PO {po.po_number} Milestone Updated',
            description=f'Milestone: {old_milestone} → {milestone}. Notes: {notes}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(po)
        return Response({'detail': 'Milestone updated', 'po': serializer.data})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def block(self, request, pk=None):
        """Block PO due to issues"""
        po = self.get_object()
        reason = request.data.get('reason', '')
        
        po.is_blocked = True
        po.blocked_reason = reason
        po.blocked_at = timezone.now()
        po.status = 'BLOCKED'
        po.has_issues = True
        po.save()
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Purchase Order',
            title=f'PO {po.po_number} Blocked',
            description=f'Reason: {reason}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(po)
        return Response({'detail': 'Purchase order blocked', 'po': serializer.data})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def complete(self, request, pk=None):
        """Mark PO as completed"""
        po = self.get_object()
        
        po.status = 'COMPLETED'
        po.milestone = 'completed'
        po.completed_at = timezone.now()
        po.completed_on_time = po.required_by >= timezone.now().date()
        po.save()
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Purchase Order',
            title=f'PO {po.po_number} Completed',
            description=f'Completed on time: {po.completed_on_time}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(po)
        return Response({'detail': 'Purchase order completed', 'po': serializer.data})
    
    @decorators.action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsVendor | IsProductionTeam | IsAdmin])
    def vendor_dashboard(self, request):
        """Get vendor dashboard statistics"""
        vendor_id = request.query_params.get('vendor_id')
        if not vendor_id:
            return Response(
                {'error': 'vendor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from django.db.models import Sum, Count
        
        pos = PurchaseOrder.objects.filter(vendor_id=vendor_id)
        
        stats = {
            'total_pos': pos.count(),
            'active_pos': pos.exclude(status__in=['completed', 'cancelled']).count(),
            'completed_pos': pos.filter(status='completed').count(),
            'delayed_pos': pos.filter(
                status__in=['in_production', 'quality_check'],
                required_by__lt=timezone.now().date()
            ).count(),
            'total_value': pos.aggregate(Sum('total_cost'))['total_cost__sum'] or 0,
            'pending_approval': pos.filter(status='awaiting_approval').count(),
            'on_time_delivery': pos.filter(completed_on_time=True).count() if pos.filter(status='completed').exists() else 0,
        }
        
        return Response(stats)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class VendorInvoiceViewSet(viewsets.ModelViewSet):
    """
    Vendor Invoice ViewSet - Vendors submit invoices, PT approves/rejects.
    """
    queryset = VendorInvoice.objects.select_related('purchase_order', 'vendor', 'job', 'job__client').all()
    serializer_class = VendorInvoiceDetailedSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager | IsVendor]
    filterset_fields = ['vendor', 'purchase_order', 'job', 'status']
    search_fields = ['invoice_number', 'vendor_invoice_ref', 'job__job_number']
    ordering_fields = ['created_at', 'invoice_date', 'due_date', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter invoices based on user role"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        # If user is a vendor, filter to their invoices only
        try:
            vendor = Vendor.objects.get(user=user, active=True)
            queryset = queryset.filter(vendor=vendor)
            return queryset
        except Vendor.DoesNotExist:
            pass  # Not a vendor, continue with PT logic
        
        # PT/Admin can view all, but can filter by vendor_id param
        vendor_id = self.request.query_params.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create invoice and notify PT team"""
        from .vendor_notifications import PTNotificationService
        
        response = super().create(request, *args, **kwargs)
        
        # Get the created invoice
        if response.status_code == 201:
            try:
                invoice_id = response.data.get('id')
                invoice = VendorInvoice.objects.get(pk=invoice_id)
                invoice.submitted_at = timezone.now()
                invoice.save()
                
                # Notify PT team about pending invoice
                PTNotificationService.notify_pt_invoice_submitted(invoice)
            except Exception as e:
                logger.error(f"Error notifying PT team about invoice: {str(e)}")
        
        return response
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def approve(self, request, pk=None):
        """PT approves vendor invoice"""
        from .invoice_validation import InvoiceValidationService
        from .vendor_notifications import VendorNotificationService
        
        invoice = self.get_object()
        
        if invoice.status == 'approved':
            return Response({'detail': 'Invoice already approved'}, status=status.HTTP_400_BAD_REQUEST)
        
        if invoice.status == 'paid':
            return Response({'detail': 'Cannot approve paid invoice'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate invoice before approval
        validation = InvoiceValidationService.validate(invoice)
        invoice.is_validated = validation['is_valid']
        invoice.validation_errors = validation.get('errors', [])
        invoice.validation_warnings = validation.get('warnings', [])
        
        if not validation['is_valid']:
            invoice.save()
            return Response({
                'detail': 'Invoice validation failed',
                'errors': validation['errors'],
                'warnings': validation['warnings']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.status = 'approved'
        invoice.approved_by = request.user
        invoice.approved_at = timezone.now()
        invoice.save()
        
        # Send notification to vendor
        VendorNotificationService.notify_invoice_approved(invoice)
        
        # Log activity
        ActivityLog.objects.create(
            client=invoice.job.client,
            activity_type='Vendor Invoice',
            title=f'Invoice {invoice.invoice_number} Approved',
            description=f'{invoice.vendor.name} invoice approved. Amount: {invoice.total_amount}. Validated: {validation["is_valid"]}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(invoice)
        return Response({
            'detail': 'Invoice approved',
            'invoice': serializer.data,
            'validation_summary': validation
        })
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def reject(self, request, pk=None):
        """PT rejects vendor invoice"""
        from .vendor_notifications import VendorNotificationService
        
        invoice = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        if invoice.status in ['approved', 'paid']:
            return Response({'detail': f'Cannot reject {invoice.status} invoice'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.status = 'rejected'
        invoice.rejection_reason = reason
        invoice.save()
        
        # Send notification to vendor
        VendorNotificationService.notify_invoice_rejected(invoice, reason)
        
        # Log activity
        ActivityLog.objects.create(
            client=invoice.job.client,
            activity_type='Vendor Invoice',
            title=f'Invoice {invoice.invoice_number} Rejected',
            description=f'Reason: {reason}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(invoice)
        return Response({'detail': 'Invoice rejected', 'invoice': serializer.data, 'reason': reason})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def mark_paid(self, request, pk=None):
        """Mark invoice as paid"""
        invoice = self.get_object()
        payment_date = request.data.get('payment_date', timezone.now().date())
        payment_method = request.data.get('payment_method', '')
        
        if invoice.status != 'approved':
            return Response({'detail': 'Can only mark approved invoices as paid'}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.status = 'paid'
        invoice.save()
        
        # Update PO
        po = invoice.purchase_order
        po.invoice_paid = True
        po.save()
        
        # Log activity
        ActivityLog.objects.create(
            client=invoice.job.client,
            activity_type='Vendor Invoice',
            title=f'Invoice {invoice.invoice_number} Paid',
            description=f'Payment method: {payment_method}. Amount: {invoice.total_amount}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(invoice)
        return Response({'detail': 'Invoice marked as paid', 'invoice': serializer.data})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
class PropertyTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PropertyType.objects.all()
    serializer_class = PropertyTypeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["property_type", "affects_price"]
    search_fields = ["name", "description"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
class PropertyValueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PropertyValue.objects.select_related("property_type").all()
    serializer_class = PropertyValueSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["property_type", "is_active"]
    search_fields = ["value", "description"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
class ProductPropertyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductProperty.objects.select_related("product", "property_value", "property_value__property_type").all()
    serializer_class = ProductPropertySerializer
    permission_classes = [AllowAny]
    filterset_fields = ["product", "property_value__property_type", "is_available"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['API']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['API']))
class QuantityPricingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QuantityPricing.objects.select_related("product").all()
    serializer_class = QuantityPricingSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["product"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
class TurnAroundTimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TurnAroundTime.objects.select_related("product").all()
    serializer_class = TurnAroundTimeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["product", "is_available", "is_default"]


# costing process viewsets

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProcessViewSet(viewsets.ModelViewSet):
    queryset = Process.objects.all()
    serializer_class = ProcessSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["pricing_type", "category", "status"]
    search_fields = ["process_id", "process_name", "description"]

    @decorators.action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def bulk_update_pricing(self, request):
        """
        Bulk update pricing for processes.
        
        Request body:
        {
            "process_ids": [1, 2, 3],  # Optional: specific processes
            "category": "printing",  # Optional: filter by category
            "adjustment_type": "percentage",  # "percentage" or "fixed"
            "adjustment_value": 10,  # 10% increase or fixed amount
            "apply_to": "tiers"  # "tiers", "base_cost", or "both"
        }
        """
        from decimal import Decimal
        
        process_ids = request.data.get("process_ids", [])
        category = request.data.get("category")
        adjustment_type = request.data.get("adjustment_type", "percentage")
        adjustment_value = Decimal(str(request.data.get("adjustment_value", 0)))
        apply_to = request.data.get("apply_to", "tiers")
        
        # Build queryset
        queryset = Process.objects.all()
        if process_ids:
            queryset = queryset.filter(id__in=process_ids)
        if category:
            queryset = queryset.filter(category=category)
        
        updated_count = 0
        
        for process in queryset:
            if apply_to in ["tiers", "both"]:
                # Update tiers
                for tier in process.tiers.all():
                    if adjustment_type == "percentage":
                        tier.cost = tier.cost * (1 + adjustment_value / 100)
                    else:
                        tier.cost = tier.cost + adjustment_value
                    tier.save()
            
            if apply_to in ["base_cost", "both"] and hasattr(process, 'base_cost'):
                # Update base cost
                if adjustment_type == "percentage":
                    process.base_cost = process.base_cost * (1 + adjustment_value / 100)
                else:
                    process.base_cost = process.base_cost + adjustment_value
                process.save()
            
            updated_count += 1
        
        return Response({
            "detail": f"Updated pricing for {updated_count} process(es)",
            "updated_count": updated_count,
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProcessTierViewSet(viewsets.ModelViewSet):
    queryset = ProcessTier.objects.select_related("process").all()
    serializer_class = ProcessTierSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["process", "tier_number"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProcessVariableViewSet(viewsets.ModelViewSet):
    queryset = ProcessVariable.objects.select_related("process").all()
    serializer_class = ProcessVariableSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["process", "variable_type"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProductVariableViewSet(viewsets.ModelViewSet):
    queryset = ProductVariable.objects.select_related("product").all()
    serializer_class = ProductVariableSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["product", "variable_type", "pricing_type", "is_active"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProductVariableOptionViewSet(viewsets.ModelViewSet):
    queryset = ProductVariableOption.objects.select_related("variable").all()
    serializer_class = ProductVariableOptionSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["variable", "is_active", "is_default"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProcessVendorViewSet(viewsets.ModelViewSet):
    queryset = ProcessVendor.objects.select_related("process").all()
    serializer_class = ProcessVendorSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["process", "priority"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class PricingTierViewSet(viewsets.ModelViewSet):
    queryset = PricingTier.objects.select_related("process").all()
    serializer_class = PricingTierSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["process"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class VendorTierPricingViewSet(viewsets.ModelViewSet):
    queryset = VendorTierPricing.objects.select_related("process_vendor").all()
    serializer_class = VendorTierPricingSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["process_vendor"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
class ProcessVariableRangeViewSet(viewsets.ModelViewSet):
    queryset = ProcessVariableRange.objects.select_related("variable").all()
    serializer_class = ProcessVariableRangeSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["variable"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.select_related("recipient").all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["recipient", "is_read", "notification_type"]
    search_fields = ["title", "message"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        # Only return notifications for the current user by default
        qs = super().get_queryset()
        if self.request.user.is_superuser or self.request.user.groups.filter(name="Admin").exists():
            return qs
        return qs.filter(recipient=self.request.user)

    @decorators.action(detail=True, methods=["post"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response({"detail": "Marked read"})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.select_related("client", "created_by").all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]
    filterset_fields = ["client", "activity_type"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at"]


class SystemSettingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(tags=['System & Configuration'])
    def list(self, request):
        """Get all system settings as a flat dictionary"""
        settings = SystemSetting.objects.all()
        result = {}
        for setting in settings:
            # Convert string values to proper types
            value = setting.value
            if setting.key.startswith('email_') or setting.key in ['maintenance_mode', 'allow_registration', 'daily_digest']:
                # Boolean settings
                result[setting.key] = value.lower() in ['true', '1', 'yes']
            elif setting.key == 'session_timeout':
                # Numeric setting
                try:
                    result[setting.key] = int(value)
                except (ValueError, TypeError):
                    result[setting.key] = 60  # default
            else:
                # String settings
                result[setting.key] = value
        return Response(result)
    
    @swagger_auto_schema(tags=['System & Configuration'])
    @action(detail=False, methods=['patch'])
    def bulk_update(self, request):
        """Update multiple settings at once"""
        updates = request.data
        for key, value in updates.items():
            # Convert boolean/int to string for storage
            if isinstance(value, bool):
                str_value = 'true' if value else 'false'
            elif isinstance(value, (int, float)):
                str_value = str(value)
            else:
                str_value = str(value)
            
            SystemSetting.objects.update_or_create(
                key=key,
                defaults={'value': str_value}
            )
        
        # Return updated settings
        settings = SystemSetting.objects.all()
        result = {}
        for setting in settings:
            value = setting.value
            if setting.key.startswith('email_') or setting.key in ['maintenance_mode', 'allow_registration', 'daily_digest']:
                result[setting.key] = value.lower() in ['true', '1', 'yes']
            elif setting.key == 'session_timeout':
                try:
                    result[setting.key] = int(value)
                except (ValueError, TypeError):
                    result[setting.key] = 60
            else:
                result[setting.key] = value
        return Response(result)


# Product metadata viewsets

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.select_related("product").all()
    serializer_class = ProductImageMetadataSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["product", "image_type", "is_primary"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductVideoViewSet(viewsets.ModelViewSet):
    queryset = ProductVideo.objects.select_related("product").all()
    serializer_class = ProductVideoMetadataSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["product", "video_type"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductDownloadableFileViewSet(viewsets.ModelViewSet):
    queryset = ProductDownloadableFile.objects.select_related("product").all()
    serializer_class = ProductDownloadableFileSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["product", "file_type"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductSEOViewSet(viewsets.ModelViewSet):
    queryset = ProductSEO.objects.select_related("product").all()
    serializer_class = ProductSEOSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductReviewSettingsViewSet(viewsets.ModelViewSet):
    queryset = ProductReviewSettings.objects.select_related("product").all()
    serializer_class = ProductReviewSettingsSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductFAQViewSet(viewsets.ModelViewSet):
    queryset = ProductFAQ.objects.select_related("product").all()
    serializer_class = ProductFAQSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["product", "is_active"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductShippingViewSet(viewsets.ModelViewSet):
    queryset = ProductShipping.objects.select_related("product").all()
    serializer_class = ProductShippingSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductLegalViewSet(viewsets.ModelViewSet):
    queryset = ProductLegal.objects.select_related("product").all()
    serializer_class = ProductLegalSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductProductionViewSet(viewsets.ModelViewSet):
    queryset = ProductProduction.objects.select_related("product").all()
    serializer_class = ProductProductionSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductChangeHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductChangeHistory.objects.select_related("product", "changed_by").all()
    serializer_class = ProductChangeHistorySerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]
    filterset_fields = ["product", "change_type"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductTemplateViewSet(viewsets.ModelViewSet):
    queryset = ProductTemplate.objects.select_related("product").all()
    serializer_class = ProductTemplateSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]


class QuickBooksSyncViewSet(viewsets.ViewSet):
    """
    QuickBooks Online synchronization endpoints.
    Manages authentication, invoice sync, and status tracking.
    """
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]

    def list(self, request):
        """Get QuickBooks connection status"""
        try:
            from .quickbooks_services import QuickBooksService
            service = QuickBooksService(request.user)
            status_info = service.get_sync_status()
            return Response(status_info)
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['get'])
    def auth_url(self, request):
        """Get QuickBooks OAuth authorization URL"""
        try:
            from .quickbooks_services import QuickBooksAuthService
            result = QuickBooksAuthService.get_auth_url(request)
            return Response(result)
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'])
    def connect(self, request):
        """Complete QuickBooks OAuth connection"""
        try:
            from .quickbooks_services import QuickBooksAuthService
            
            auth_code = request.data.get('auth_code')
            realm_id = request.data.get('realm_id')
            
            if not auth_code or not realm_id:
                return Response(
                    {'error': 'auth_code and realm_id are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = QuickBooksAuthService.handle_oauth_callback(request, auth_code, realm_id)
            return Response(result)
        
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'])
    def disconnect(self, request):
        """Disconnect QuickBooks account"""
        try:
            from .quickbooks_services import QuickBooksAuthService
            result = QuickBooksAuthService.disconnect(request.user)
            return Response(result)
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'])
    def sync_vendor_invoice(self, request):
        """Sync VendorInvoice to QuickBooks"""
        try:
            from .quickbooks_services import QuickBooksService
            from .models import VendorInvoice
            
            invoice_id = request.data.get('invoice_id')
            if not invoice_id:
                return Response({'error': 'invoice_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                vendor_invoice = VendorInvoice.objects.get(pk=invoice_id)
            except VendorInvoice.DoesNotExist:
                return Response({'error': 'Vendor invoice not found'}, status=status.HTTP_404_NOT_FOUND)
            
            service = QuickBooksService(request.user)
            result = service.create_invoice_from_vendor_invoice(vendor_invoice)
            
            if result['status'] == 'success':
                # Log activity
                ActivityLog.objects.create(
                    client=vendor_invoice.job.client,
                    activity_type='QuickBooks',
                    title=f'Invoice {vendor_invoice.invoice_number} Synced to QB',
                    description=f'QB Invoice ID: {result["qb_invoice_id"]}',
                    created_by=request.user,
                )
            
            return Response(result)
        
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'])
    def sync_purchase_order(self, request):
        """Sync PurchaseOrder to QuickBooks"""
        try:
            from .quickbooks_services import QuickBooksService
            from .models import PurchaseOrder
            
            po_id = request.data.get('po_id')
            if not po_id:
                return Response({'error': 'po_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                po = PurchaseOrder.objects.get(pk=po_id)
            except PurchaseOrder.DoesNotExist:
                return Response({'error': 'Purchase order not found'}, status=status.HTTP_404_NOT_FOUND)
            
            service = QuickBooksService(request.user)
            result = service.sync_purchase_order_as_purchase(po)
            
            if result['status'] == 'success':
                ActivityLog.objects.create(
                    client=po.job.client,
                    activity_type='QuickBooks',
                    title=f'PO {po.po_number} Synced to QB',
                    description=f'QB Purchase ID: {result["qb_purchase_id"]}',
                    created_by=request.user,
                )
            
            return Response(result)
        
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'])
    def sync_quote(self, request):
        """Sync Quote to QuickBooks as Estimate"""
        try:
            from .quickbooks_services import QuickBooksService
            from .models import Quote
            
            quote_id = request.data.get('quote_id')
            if not quote_id:
                return Response({'error': 'quote_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                quote = Quote.objects.get(pk=quote_id)
            except Quote.DoesNotExist:
                return Response({'error': 'Quote not found'}, status=status.HTTP_404_NOT_FOUND)
            
            service = QuickBooksService(request.user)
            result = service.sync_quote_as_estimate(quote)
            
            if result['status'] == 'success':
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='QuickBooks',
                    title=f'Quote {quote.quote_id} Synced to QB',
                    description=f'QB Estimate ID: {result["qb_estimate_id"]}',
                    created_by=request.user,
                ) if quote.client else None
            
            return Response(result)
        
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'])
    def sync_customer(self, request):
        """Sync Client to QuickBooks Customer"""
        try:
            from .quickbooks_services import QuickBooksService
            from .models import Client
            
            client_id = request.data.get('client_id')
            if not client_id:
                return Response({'error': 'client_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                client = Client.objects.get(pk=client_id)
            except Client.DoesNotExist:
                return Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)
            
            service = QuickBooksService(request.user)
            qb_customer = service.find_or_create_customer(client)
            
            ActivityLog.objects.create(
                client=client,
                activity_type='QuickBooks',
                title=f'Client {client.name} Synced to QB',
                description=f'QB Customer ID: {qb_customer.id}',
                created_by=request.user,
            )
            
            return Response({
                'status': 'success',
                'qb_customer_id': qb_customer.id,
                'qb_customer_name': qb_customer.DisplayName,
                'message': 'Customer synced to QuickBooks'
            })
        
        except Exception as e:
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # ===== PHASE 3: COMPLETE QUICKBOOKS SYNC ENDPOINTS =====
    
    @decorators.action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin | IsProductionTeam])
    def sync_lpo_to_invoice(self, request):
        """
        PHASE 3: Sync Local Purchase Order (LPO) to QuickBooks Invoice.
        This is the primary customer-facing invoice in QB.
        """
        try:
            from .quickbooks_services import QuickBooksFullSyncService
            from .models import LPO
            
            lpo_id = request.data.get('lpo_id')
            if not lpo_id:
                return Response({'error': 'lpo_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                lpo = LPO.objects.get(pk=lpo_id)
            except LPO.DoesNotExist:
                return Response({'error': 'LPO not found'}, status=status.HTTP_404_NOT_FOUND)
            
            sync_service = QuickBooksFullSyncService(request.user)
            result = sync_service.sync_lpo_to_invoice(lpo)
            
            if result['status'] == 'success':
                ActivityLog.objects.create(
                    client=lpo.client,
                    activity_type='QuickBooks Sync - Phase 3',
                    title=f'LPO {lpo.lpo_number} → QB Invoice',
                    description=f'QB Invoice ID: {result["qb_invoice_id"]}. Amount: {result["amount"]}',
                    created_by=request.user,
                )
            
            return Response(result)
        
        except Exception as e:
            logger.error(f"Error syncing LPO to QB: {e}")
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin | IsProductionTeam])
    def sync_vendor_invoice_to_bill(self, request):
        """
        PHASE 3: Sync Vendor Invoice to QuickBooks Bill (Accounts Payable).
        This creates vendor payables in QB accounting.
        """
        try:
            from .quickbooks_services import QuickBooksFullSyncService
            from .models import VendorInvoice
            
            invoice_id = request.data.get('invoice_id')
            if not invoice_id:
                return Response({'error': 'invoice_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                vendor_invoice = VendorInvoice.objects.get(pk=invoice_id)
            except VendorInvoice.DoesNotExist:
                return Response({'error': 'Vendor invoice not found'}, status=status.HTTP_404_NOT_FOUND)
            
            sync_service = QuickBooksFullSyncService(request.user)
            result = sync_service.sync_vendor_invoice_to_bill(vendor_invoice)
            
            if result['status'] == 'success':
                ActivityLog.objects.create(
                    client=vendor_invoice.job.client,
                    activity_type='QuickBooks Sync - Phase 3',
                    title=f'Vendor Invoice {vendor_invoice.invoice_number} → QB Bill',
                    description=f'QB Bill ID: {result["qb_bill_id"]}. Amount: {result["amount"]}',
                    created_by=request.user,
                )
            
            return Response(result)
        
        except Exception as e:
            logger.error(f"Error syncing vendor invoice to QB: {e}")
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin | IsProductionTeam])
    def sync_payment_to_qb(self, request):
        """
        PHASE 3: Sync Payment to QuickBooks Payment record.
        Records customer payments in QB.
        """
        try:
            from .quickbooks_services import QuickBooksFullSyncService
            from .models import Payment
            
            payment_id = request.data.get('payment_id')
            if not payment_id:
                return Response({'error': 'payment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                payment = Payment.objects.get(pk=payment_id)
            except Payment.DoesNotExist:
                return Response({'error': 'Payment not found'}, status=status.HTTP_404_NOT_FOUND)
            
            sync_service = QuickBooksFullSyncService(request.user)
            result = sync_service.sync_payment_to_qb(payment)
            
            if result['status'] == 'success':
                ActivityLog.objects.create(
                    client=payment.client,
                    activity_type='QuickBooks Sync - Phase 3',
                    title=f'Payment {payment.payment_reference} Synced to QB',
                    description=f'QB Payment ID: {result["qb_payment_id"]}. Amount: {result["amount"]}',
                    created_by=request.user,
                )
            
            return Response(result)
        
        except Exception as e:
            logger.error(f"Error syncing payment to QB: {e}")
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin | IsProductionTeam])
    def batch_sync_lpos(self, request):
        """
        PHASE 3: Batch sync pending LPOs to QuickBooks Invoices.
        Efficiently syncs multiple LPOs at once.
        """
        try:
            from .quickbooks_services import QuickBooksFullSyncService
            
            limit = request.data.get('limit', 10)
            sync_service = QuickBooksFullSyncService(request.user)
            results = sync_service.batch_sync_lpos(limit=limit)
            
            if results.get('successful', 0) > 0:
                ActivityLog.objects.create(
                    activity_type='QuickBooks Batch Sync',
                    title=f'Batch LPO Sync - {results["successful"]} Successful',
                    description=f'Synced {results["successful"]} LPOs. Failed: {results["failed"]}',
                    created_by=request.user,
                )
            
            return Response(results)
        
        except Exception as e:
            logger.error(f"Error in batch LPO sync: {e}")
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin | IsProductionTeam])
    def batch_sync_vendor_invoices(self, request):
        """
        PHASE 3: Batch sync pending vendor invoices to QuickBooks Bills.
        Efficiently syncs multiple vendor invoices at once.
        """
        try:
            from .quickbooks_services import QuickBooksFullSyncService
            
            limit = request.data.get('limit', 10)
            sync_service = QuickBooksFullSyncService(request.user)
            results = sync_service.batch_sync_vendor_invoices(limit=limit)
            
            if results.get('successful', 0) > 0:
                ActivityLog.objects.create(
                    activity_type='QuickBooks Batch Sync',
                    title=f'Batch Vendor Invoice Sync - {results["successful"]} Successful',
                    description=f'Synced {results["successful"]} invoices. Failed: {results["failed"]}',
                    created_by=request.user,
                )
            
            return Response(results)
        
        except Exception as e:
            logger.error(f"Error in batch vendor invoice sync: {e}")
            return Response({'status': 'error', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @decorators.action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin | IsProductionTeam])
    def sync_status(self, request):
        """
        PHASE 3: Get QuickBooks sync status and statistics.
        Shows pending items, synced items, and sync history.
        """
        try:
            from .quickbooks_services import QuickBooksFullSyncService
            
            sync_service = QuickBooksFullSyncService(request.user)
            status_data = sync_service.get_sync_status()
            
            return Response({
                'status': 'success',
                'sync_status': status_data,
                'last_sync': timezone.now().isoformat(),
                'qb_connected': True
            })
        
        except Exception as e:
            logger.error(f"Error getting QB sync status: {e}")
            return Response({
                'status': 'error',
                'qb_connected': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


# ===== QC, Delivery, Attachments, Notes, Alerts =====

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class JobVendorStageViewSet(viewsets.ModelViewSet):
    queryset = JobVendorStage.objects.select_related("job", "vendor").all()
    serializer_class = JobVendorStageSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["job", "vendor", "status"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class JobNoteViewSet(viewsets.ModelViewSet):
    queryset = JobNote.objects.select_related("job", "created_by").all()
    serializer_class = JobNoteSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["job", "note_type"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class JobAttachmentViewSet(viewsets.ModelViewSet):
    queryset = JobAttachment.objects.select_related("job", "uploaded_by").all()
    serializer_class = JobAttachmentSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["job"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class VendorQuoteViewSet(viewsets.ModelViewSet):
    queryset = VendorQuote.objects.select_related("job", "vendor").all()
    serializer_class = VendorQuoteSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["job", "vendor", "selected"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class QCInspectionViewSet(viewsets.ModelViewSet):
    queryset = QCInspection.objects.select_related("job", "vendor", "inspector").all()
    serializer_class = QCInspectionSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["job", "vendor", "status"]
    
    def perform_update(self, serializer):
        """Auto-recalculate VPS when QC status changes"""
        instance = serializer.save()
        
        # If QC is completed and has a vendor, recalculate VPS
        if instance.vendor and instance.status in ['passed', 'failed']:
            instance.vendor.calculate_vps()


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related("job", "qc_inspection", "handoff_confirmed_by", "created_by").all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["job", "status", "staging_location"]
    
    def perform_update(self, serializer):
        """Auto-recalculate VPS when delivery is completed"""
        instance = serializer.save()
        
        # If delivery is completed, check vendor stages and recalculate VPS
        if instance.status == 'completed' and instance.job:
            # Get vendor stages for this job
            vendor_stages = JobVendorStage.objects.filter(
                job=instance.job,
                status='completed'
            )
            # Recalculate VPS for all vendors involved
            vendors_updated = set()
            for stage in vendor_stages:
                if stage.vendor and stage.vendor.id not in vendors_updated:
                    stage.vendor.calculate_vps()
                    vendors_updated.add(stage.vendor.id)


class QuoteAttachmentViewSet(viewsets.ModelViewSet):
    queryset = QuoteAttachment.objects.select_related("quote", "uploaded_by").all()
    serializer_class = QuoteAttachmentSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["quote"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class LPOLineItemViewSet(viewsets.ModelViewSet):
    queryset = LPOLineItem.objects.select_related("lpo").all()
    serializer_class = LPOLineItemSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsAccountManager]
    filterset_fields = ["lpo"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))
class SystemAlertViewSet(viewsets.ModelViewSet):
    queryset = SystemAlert.objects.all()
    serializer_class = SystemAlertSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["alert_type", "severity", "is_active", "is_dismissed"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]
        else:
            permission_classes = [IsAuthenticated, IsAdmin]

        return [permission() for permission in permission_classes]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class ProductionUpdateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Production Team to post granular progress updates.
    Allows tracking detailed progress (e.g., "Printing 50% complete", "Waiting for material").
    """
    queryset = ProductionUpdate.objects.select_related('job', 'quote', 'created_by').all()
    serializer_class = ProductionUpdateSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ["update_type", "status", "job", "quote", "created_by"]
    ordering_fields = ["created_at", "progress"]
    search_fields = ["notes", "job__job_number", "quote__quote_id"]
    
    def perform_create(self, serializer):
        """Set created_by to current user"""
        serializer.save(created_by=self.request.user)
        
        # Create notification if job update
        instance = serializer.instance
        if instance.job and instance.job.client:
            # Notify Account Manager
            if instance.job.client.account_manager:
                Notification.objects.create(
                    recipient=instance.job.client.account_manager,
                    notification_type="job_update",
                    title=f"Job {instance.job.job_number} Update",
                    message=f"Progress: {instance.progress}% - {instance.notes[:50]}",
                    link=f"/job/{instance.job.pk}/",
                )


# ===== User / Group Management =====

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["is_active", "is_superuser"]
    search_fields = ["username", "email", "first_name", "last_name"]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        if 'group_ids' in request.data:
            groups = serializer.validated_data.get('groups')
            instance.groups.set(groups)
        
        serializer.save()
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["get", "patch"], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Get or update the authenticated user's basic profile fields."""
        user = request.user

        if request.method == "GET":
            serializer = self.get_serializer(user)
            return Response(serializer.data)

        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        update_fields = []

        if first_name is not None:
            if not isinstance(first_name, str):
                return Response(
                    {"detail": "first_name must be a string"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.first_name = first_name.strip()
            update_fields.append("first_name")

        if last_name is not None:
            if not isinstance(last_name, str):
                return Response(
                    {"detail": "last_name must be a string"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.last_name = last_name.strip()
            update_fields.append("last_name")

        if not update_fields:
            return Response(
                {"detail": "No updatable fields provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.save(update_fields=update_fields)
        serializer = self.get_serializer(user)
        return Response(serializer.data)

    @decorators.action(detail=False, methods=["post"], permission_classes=[IsAuthenticated, IsAdmin])
    def invite(self, request):
        """
        Invite a new staff user via email. Creates an inactive user and sends invitation link.
        """
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")
        email = request.data.get("email")
        group_ids = request.data.get("group_ids", [])
        send_invite = request.data.get("send_invite", True)

        if not all([first_name, last_name, email]):
            return Response(
                {"detail": "first_name, last_name, and email are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"detail": "A user with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST
            )

        username = email.split('@')[0]
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1

        user = User.objects.create(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
            is_staff=True
        )

        if group_ids:
            groups = Group.objects.filter(id__in=group_ids)
            user.groups.set(groups)

        invite_token = secrets.token_urlsafe(32)
        cache.set(f'staff_invite_{invite_token}', user.id, 172800)

        if send_invite:
            try:
                admin_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
                group_names = ", ".join([g.name for g in user.groups.all()]) if user.groups.exists() else "None"
                
                activation_link = f"{settings.STAFF_PORTAL_URL}/activate?token={invite_token}"
                
                context = {
                    'first_name': user.first_name,
                    'admin_name': admin_name,
                    'activation_link': activation_link,
                    'group_names': group_names,
                    'company_name': getattr(settings, 'COMPANY_NAME', 'PrintDuka'),
                }
                
                html_message = render_to_string('emails/staff_invite.html', context)
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject=f"You've been invited to join {context['company_name']} Staff Portal",
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
                
                logger.info(f"Staff invite sent to {user.email} by {request.user.username}")
            except Exception as e:
                logger.error(f"Failed to send staff invite email: {str(e)}")
                return Response(
                    {"detail": "User created but failed to send invitation email", "user_id": user.id},
                    status=status.HTTP_201_CREATED
                )

        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @decorators.action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def validate_invite(self, request):
        """
        Validate an invitation token without activating it.
        """
        token = request.data.get("token")
        
        if not token:
            return Response(
                {"detail": "Token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = cache.get(f'staff_invite_{token}')
        
        if not user_id:
            return Response(
                {"detail": "Invalid or expired invitation link"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({"valid": True})

    @decorators.action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def activate_invite(self, request):
        """
        Activate a user account using an invitation token and set password.
        """
        token = request.data.get("token")
        password = request.data.get("password")
        
        if not token or not password:
            return Response(
                {"detail": "Token and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_id = cache.get(f'staff_invite_{token}')
        
        if not user_id:
            return Response(
                {"detail": "Invalid or expired invitation link"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            
            if user.is_active:
                return Response(
                    {"detail": "This account has already been activated"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(password)
            user.is_active = True
            user.save()
            
            cache.delete(f'staff_invite_{token}')
            
            logger.info(f"User {user.username} activated account via invite link")
            
            return Response({
                "detail": "Account activated successfully",
                "username": user.username
            })
            
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

    @decorators.action(detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def production_team(self, request):
        """
        List all users in the Production Team group.
        Available to Account Managers for job assignment.
        """
        production_group = Group.objects.filter(name="Production Team").first()
        if not production_group:
            return Response({"detail": "Production Team group not found"}, status=status.HTTP_404_NOT_FOUND)
        
        users = production_group.user_set.filter(is_active=True).order_by("first_name", "last_name", "username")
        serializer = self.get_serializer(users, many=True)
        return Response({
            "results": serializer.data,
            "count": users.count()
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))
class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        from django.db.models import Count
        return Group.objects.annotate(user_count=Count('user')).order_by('name')
    
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        if 'permission_ids' in request.data:
            permissions = serializer.validated_data.get('permissions')
            instance.permissions.set(permissions)
        
        serializer.save()
        
        from django.db.models import Count
        instance = Group.objects.annotate(user_count=Count('user')).get(pk=instance.pk)
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'content_type__model', 'codename')
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = None
    filterset_fields = ['content_type__app_label']


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not password:
            return Response({"detail": "username and password are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"detail": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=username, email=email, password=password)
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            return Response({"detail": "old_password and new_password are required"}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({"detail": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({"detail": "Password changed successfully"}, status=status.HTTP_200_OK)


# ===== Client Portal Profile (Me) =====

class ClientPortalMeView(APIView):
    permission_classes = [IsAuthenticated, IsClient]

    def get(self, request):
        try:
            portal_user = ClientPortalUser.objects.select_related('user', 'client').get(
                user=request.user, is_active=True
            )
        except ClientPortalUser.DoesNotExist:
            return Response({'detail': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

        user = portal_user.user
        client = portal_user.client
        return Response({
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': client.phone,
            'company': client.company,
            'industry': client.industry,
            'address': client.address,
            'vat_tax_id': client.vat_tax_id,
            'kra_pin': client.kra_pin,
            'preferred_channel': client.preferred_channel,
            'delivery_instructions': client.delivery_instructions or '',
            'role': portal_user.role,
            'client_id': client.client_id,
        })

    def patch(self, request):
        try:
            portal_user = ClientPortalUser.objects.select_related('user', 'client').get(
                user=request.user, is_active=True
            )
        except ClientPortalUser.DoesNotExist:
            return Response({'detail': 'Profile not found'}, status=status.HTTP_404_NOT_FOUND)

        user = portal_user.user
        client = portal_user.client

        user_fields = ['first_name', 'last_name', 'email']
        updated_user_fields = [f for f in user_fields if f in request.data]
        for field in updated_user_fields:
            setattr(user, field, request.data[field])
        if updated_user_fields:
            user.save(update_fields=updated_user_fields)

        client_editable_fields = [
            'phone', 'company', 'industry', 'address',
            'vat_tax_id', 'kra_pin', 'preferred_channel', 'delivery_instructions',
        ]
        updated_client_fields = [f for f in client_editable_fields if f in request.data]
        for field in updated_client_fields:
            setattr(client, field, request.data[field])
        if updated_client_fields:
            client.save(update_fields=updated_client_fields)

        return self.get(request)


# ===== Dashboard / Analytics =====

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdmin | IsAccountManager | IsProductionTeam]

    def list(self, request):
        """Return high-level metrics for dashboards."""
        data = {
            "leads": {
                "total": Lead.objects.count(),
                "new": Lead.objects.filter(status="New").count(),
                "converted": Lead.objects.filter(status="Converted").count(),
            },
            "clients": {
                "total": Client.objects.count(),
                "b2b": Client.objects.filter(client_type="B2B").count(),
                "b2c": Client.objects.filter(client_type="B2C").count(),
            },
            "quotes": {
                "total": Quote.objects.count(),
                "draft": Quote.objects.filter(status="Draft").count(),
                "sent_to_customer": Quote.objects.filter(status="Sent to Customer").count(),
                "approved": Quote.objects.filter(status="Approved").count(),
                "lost": Quote.objects.filter(status="Lost").count(),
                "ecommerce": Quote.objects.filter(channel="ecommerce").count(),
            },
            "jobs": {
                "total": Job.objects.count(),
                "pending": Job.objects.filter(status="pending").count(),
                "in_progress": Job.objects.filter(status="in_progress").count(),
                "on_hold": Job.objects.filter(status="on_hold").count(),
                "completed": Job.objects.filter(status="completed").count(),
            },
            "lpos": {
                "total": LPO.objects.count(),
                "pending": LPO.objects.filter(status="pending").count(),
                "approved": LPO.objects.filter(status="approved").count(),
                "completed": LPO.objects.filter(status="completed").count(),
            },
        }
        return Response(data, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["get"], url_path="account-manager")
    def account_manager_dashboard(self, request):
        """Return personalized dashboard data for the logged-in account manager."""
        from datetime import timedelta
        from django.db.models import Sum, Count, Q
        from decimal import Decimal
        
        user = request.user
        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        six_months_ago = today - timedelta(days=180)
        
        # KPIs
        my_revenue_this_month = Quote.objects.filter(
            created_by=user,
            created_at__gte=this_month_start
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
        
        my_quotes_this_month = Quote.objects.filter(
            created_by=user,
            created_at__gte=this_month_start
        ).values('quote_id').distinct().count()
        
        active_jobs_count = Job.objects.filter(
            created_by=user,
            status__in=['pending', 'in_progress']
        ).count()
        
        client_ids_from_quotes = Quote.objects.filter(
            created_by=user,
            client__isnull=False,
            created_at__gte=this_month_start
        ).values_list('client_id', flat=True).distinct()
        
        new_clients_this_month = len(set(client_ids_from_quotes))
        
        # Lead Funnel
        lead_funnel = {
            "new": Lead.objects.filter(created_by=user, status="New").count(),
            "contacted": Lead.objects.filter(created_by=user, status="Contacted").count(),
            "qualified": Lead.objects.filter(created_by=user, status="Qualified").count(),
            "converted": Lead.objects.filter(created_by=user, status="Converted").count(),
        }
        
        # Revenue Trend (last 6 months)
        revenue_trend = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            revenue = Quote.objects.filter(
                created_by=user,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            revenue_trend.append({
                "month": month_start.strftime("%b"),
                "revenue": float(revenue)
            })
        
        # Client Growth (last 6 months)
        client_growth = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=i*30)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            client_ids_in_month = Quote.objects.filter(
                created_by=user,
                client__isnull=False,
                created_at__gte=month_start,
                created_at__lte=month_end
            ).values_list('client_id', flat=True).distinct()
            
            client_ids_set = set(client_ids_in_month)
            
            b2b_count = Client.objects.filter(
                id__in=client_ids_set,
                client_type='B2B'
            ).count()
            
            b2c_count = Client.objects.filter(
                id__in=client_ids_set,
                client_type='B2C'
            ).count()
            
            client_growth.append({
                "month": month_start.strftime("%b"),
                "b2b": b2b_count,
                "b2c": b2c_count
            })
        
        # Jobs Status Distribution
        jobs_status = {
            "pending": Job.objects.filter(created_by=user, status="pending").count(),
            "in_progress": Job.objects.filter(created_by=user, status="in_progress").count(),
            "on_hold": Job.objects.filter(created_by=user, status="on_hold").count(),
            "completed": Job.objects.filter(created_by=user, status="completed").count(),
        }
        
        # Recent Quotes
        recent_quotes_qs = Quote.objects.filter(
            created_by=user
        ).select_related('client', 'lead').order_by('-created_at')[:5]
        
        recent_quotes = []
        for quote in recent_quotes_qs:
            recent_quotes.append({
                "id": quote.id,
                "quote_id": quote.quote_id,
                "client_name": quote.client.name if quote.client else None,
                "lead_name": quote.lead.name if quote.lead else None,
                "product_name": quote.product_name,
                "quantity": quote.quantity,
                "total_amount": float(quote.total_amount),
                "status": quote.status,
                "created_at": quote.created_at.isoformat(),
            })
        
        # Upcoming Actions (quotes needing follow-up)
        upcoming_actions = []
        follow_up_quotes = Quote.objects.filter(
            created_by=user,
            status='Quoted',
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('client', 'lead')[:5]
        
        for quote in follow_up_quotes:
            client_name = quote.client.name if quote.client else (quote.lead.name if quote.lead else 'Unknown')
            upcoming_actions.append({
                "type": "quote",
                "id": quote.id,
                "title": f"Follow Up Quote {quote.quote_id}",
                "description": quote.product_name,
                "client_name": client_name,
                "due_date": (quote.created_at + timedelta(days=3)).isoformat(),
                "priority": "medium"
            })
        
        data = {
            "kpis": {
                "my_revenue_this_month": float(my_revenue_this_month),
                "my_quotes_this_month": my_quotes_this_month,
                "active_jobs_count": active_jobs_count,
                "new_clients_this_month": new_clients_this_month,
            },
            "lead_funnel": lead_funnel,
            "revenue_trend": revenue_trend,
            "client_growth": client_growth,
            "jobs_status": jobs_status,
            "recent_quotes": recent_quotes,
            "upcoming_actions": upcoming_actions,
        }
        
        return Response(data, status=status.HTTP_200_OK)


class SearchViewSet(viewsets.ViewSet):
    """
    Unified search endpoint for searching across Leads, Clients, Quotes, and Jobs.
    """
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]

    def list(self, request):
        """Search across multiple models."""
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response(
                {"detail": "Query parameter 'q' is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.db.models import Q

        results = {
            "leads": [],
            "clients": [],
            "quotes": [],
            "jobs": [],
        }

        # Search Leads
        leads = Lead.objects.filter(
            Q(lead_id__icontains=query)
            | Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )[:25]
        results["leads"] = LeadSerializer(leads, many=True).data

        # Search Clients
        clients = Client.objects.filter(
            Q(client_id__icontains=query)
            | Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(company__icontains=query)
        )[:25]
        results["clients"] = ClientSerializer(clients, many=True).data

        # Search Quotes
        quotes = Quote.objects.filter(
            Q(quote_id__icontains=query)
            | Q(product_name__icontains=query)
            | Q(reference_number__icontains=query)
        ).select_related("client", "lead")[:25]
        results["quotes"] = QuoteSerializer(quotes, many=True).data

        # Search Jobs
        jobs = Job.objects.filter(
            Q(job_number__icontains=query)
            | Q(job_name__icontains=query)
            | Q(product__icontains=query)
        ).select_related("client", "quote")[:25]
        results["jobs"] = JobSerializer(jobs, many=True).data

        # Summary
        total_results = sum(len(v) for v in results.values())

        return Response(
            {
                "query": query,
                "total_results": total_results,
                "results": results,
            },
            status=status.HTTP_200_OK,
        )


# ===== Production Team APIs =====

class CostingEngineViewSet(viewsets.ViewSet):
    """
    Automated costing calculation engine.
    Takes product properties and returns calculated production cost.
    """
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]

    @decorators.action(detail=False, methods=["post"])
    def calculate_cost(self, request):
        """
        Calculate production cost for a quote line item or product.
        
        Request body:
        {
            "product_id": 123,
            "quantity": 100,
            "process_id": 5,  # Optional: specific process
            "variables": {  # For formula-based processes
                "square_footage": 50,
                "paper_weight": 300
            }
        }
        
        Returns:
        {
            "suggested_cost": 5000.00,
            "process_id": 5,
            "process_name": "Offset Printing",
            "cost_breakdown": {...},
            "vendor_suggestions": [...]
        }
        """
        from decimal import Decimal
        from django.db.models import Q
        
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        process_id = request.data.get("process_id")
        variables = request.data.get("variables", {})
        
        if not product_id:
            return Response(
                {"detail": "product_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return Response(
                {"detail": "Product not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Try to find linked process
        suggested_process = None
        if process_id:
            try:
                suggested_process = Process.objects.get(pk=process_id, status='active')
            except Process.DoesNotExist:
                pass
        
        # If no process specified, try to find by product
        if not suggested_process:
            # Check if product has linked process via ProductProduction
            if hasattr(product, 'production') and hasattr(product.production, 'process'):
                suggested_process = product.production.process
            else:
                # Search by product name similarity
                product_name_lower = product.name.lower()
                for process in Process.objects.filter(status='active'):
                    if product_name_lower in process.process_name.lower() or \
                       process.process_name.lower() in product_name_lower:
                        suggested_process = process
                        break
        
        if not suggested_process:
            return Response({
                "detail": "No matching process found for this product",
                "suggested_cost": None,
            }, status=status.HTTP_200_OK)
        
        # Calculate cost based on process type
        cost_breakdown = {
            "process_id": suggested_process.id,
            "process_name": suggested_process.process_name,
            "pricing_type": suggested_process.pricing_type,
        }
        
        suggested_cost = Decimal('0')
        
        if suggested_process.pricing_type == 'tier':
            # Find matching tier
            tier = ProcessTier.objects.filter(
                process=suggested_process,
                quantity_from__lte=quantity,
                quantity_to__gte=quantity
            ).first()
            
            if tier:
                suggested_cost = tier.cost * quantity
                cost_breakdown.update({
                    "tier_number": tier.tier_number,
                    "quantity_range": f"{tier.quantity_from}-{tier.quantity_to}",
                    "cost_per_unit": float(tier.cost),
                    "total_quantity": quantity,
                })
            else:
                # Use base cost if no tier matches
                suggested_cost = suggested_process.base_cost * quantity if hasattr(suggested_process, 'base_cost') else Decimal('0')
        
        elif suggested_process.pricing_type == 'formula':
            # Formula-based calculation
            base_cost = suggested_process.base_cost if hasattr(suggested_process, 'base_cost') else Decimal('0')
            variable_cost = Decimal('0')
            
            for var_name, var_value in variables.items():
                try:
                    process_var = ProcessVariable.objects.get(
                        process=suggested_process,
                        variable_name=var_name
                    )
                    # Simple calculation: variable_value * variable_cost_per_unit
                    if process_var.cost_per_unit:
                        variable_cost += Decimal(str(var_value)) * process_var.cost_per_unit
                except ProcessVariable.DoesNotExist:
                    pass
            
            suggested_cost = base_cost + variable_cost
            cost_breakdown.update({
                "base_cost": float(base_cost),
                "variable_cost": float(variable_cost),
                "variables_used": variables,
            })
        
        # Get vendor suggestions
        vendor_suggestions = []
        process_vendors = ProcessVendor.objects.filter(
            process=suggested_process,
            vendor__active=True
        ).select_related('vendor').order_by('-vendor__vps_score_value')[:5]
        
        for pv in process_vendors:
            vendor_suggestions.append({
                "vendor_id": pv.vendor.id,
                "vendor_name": pv.vendor.name,
                "vps_score_value": float(pv.vendor.vps_score_value),
                "priority": pv.priority,
            })
        
        return Response({
            "suggested_cost": float(suggested_cost),
            "process_id": suggested_process.id,
            "process_name": suggested_process.process_name,
            "cost_breakdown": cost_breakdown,
            "vendor_suggestions": vendor_suggestions,
        })


class WorkloadViewSet(viewsets.ViewSet):
    """
    Workload management API for Production Team.
    Shows team capacity and job distribution.
    """
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]

    @decorators.action(detail=False, methods=["get"])
    def team_workload(self, request):
        """
        Get workload distribution across Production Team.
        Returns: user, active_jobs, overdue_jobs, capacity
        """
        from datetime import date
        from django.db.models import Count, Q
        
        production_group = Group.objects.filter(name="Production Team").first()
        if not production_group:
            return Response(
                {"detail": "Production Team group not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        team_members = production_group.user_set.filter(is_active=True)
        today = date.today()
        
        workload_data = []
        for member in team_members:
            # Get assigned jobs
            assigned_jobs = Job.objects.filter(person_in_charge=member)
            active_jobs = assigned_jobs.filter(status__in=['pending', 'in_progress']).count()
            overdue_jobs = assigned_jobs.filter(
                status__in=['pending', 'in_progress'],
                expected_completion__lt=today
            ).count()
            completed_jobs = assigned_jobs.filter(status='completed').count()
            
            # Calculate capacity (assuming max 10 active jobs per person)
            max_capacity = 10
            capacity_percentage = (active_jobs / max_capacity * 100) if max_capacity > 0 else 0
            
            workload_data.append({
                "user_id": member.id,
                "user_name": member.get_full_name() or member.username,
                "active_jobs": active_jobs,
                "overdue_jobs": overdue_jobs,
                "completed_jobs": completed_jobs,
                "capacity_percentage": round(capacity_percentage, 1),
                "is_overloaded": active_jobs >= max_capacity,
            })
        
        # Sort by active jobs (descending)
        workload_data.sort(key=lambda x: x['active_jobs'], reverse=True)
        
        return Response({
            "team_workload": workload_data,
            "total_active_jobs": sum(w['active_jobs'] for w in workload_data),
            "total_overdue_jobs": sum(w['overdue_jobs'] for w in workload_data),
        })


class ProductionAnalyticsViewSet(viewsets.ViewSet):
    """
    Production-specific analytics for PT dashboard.
    """
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]

    def list(self, request):
        """
        Get production analytics including:
        - Average turnaround time
        - QC rejection rate
        - Vendor reliability
        - Team performance
        """
        from datetime import timedelta
        from django.db.models import Avg, Count, Q, Sum
        from decimal import Decimal
        
        # Time range (last 90 days)
        ninety_days_ago = timezone.now() - timedelta(days=90)
        
        # Average Turnaround Time
        completed_jobs = Job.objects.filter(
            status='completed',
            actual_completion__isnull=False,
            created_at__gte=ninety_days_ago
        )
        
        avg_turnaround_days = 0
        if completed_jobs.exists():
            turnaround_times = []
            for job in completed_jobs:
                if job.actual_completion and job.created_at:
                    delta = job.actual_completion - job.created_at.date()
                    turnaround_times.append(delta.days)
            if turnaround_times:
                avg_turnaround_days = sum(turnaround_times) / len(turnaround_times)
        
        # QC Rejection Rate
        total_qc = QCInspection.objects.filter(created_at__gte=ninety_days_ago).count()
        failed_qc = QCInspection.objects.filter(
            created_at__gte=ninety_days_ago,
            status='failed'
        ).count()
        qc_rejection_rate = (failed_qc / total_qc * 100) if total_qc > 0 else 0
        
        # Vendor Reliability (on-time delivery)
        vendor_stages = JobVendorStage.objects.filter(
            completed_at__gte=ninety_days_ago,
            status='completed',
            expected_completion__isnull=False,
            completed_at__isnull=False
        )
        
        on_time_count = 0
        late_count = 0
        for stage in vendor_stages:
            if stage.completed_at <= stage.expected_completion:
                on_time_count += 1
            else:
                late_count += 1
        
        total_vendor_stages = on_time_count + late_count
        vendor_on_time_rate = (on_time_count / total_vendor_stages * 100) if total_vendor_stages > 0 else 0
        
        # Team Performance
        production_group = Group.objects.filter(name="Production Team").first()
        team_performance = []
        if production_group:
            for member in production_group.user_set.filter(is_active=True):
                member_jobs = Job.objects.filter(
                    person_in_charge=member,
                    created_at__gte=ninety_days_ago
                )
                completed = member_jobs.filter(status='completed').count()
                total = member_jobs.count()
                completion_rate = (completed / total * 100) if total > 0 else 0
                
                team_performance.append({
                    "user_id": member.id,
                    "user_name": member.get_full_name() or member.username,
                    "total_jobs": total,
                    "completed_jobs": completed,
                    "completion_rate": round(completion_rate, 1),
                })
        
        # Job Status Distribution
        job_status_dist = Job.objects.filter(
            created_at__gte=ninety_days_ago
        ).values('status').annotate(count=Count('id'))
        
        return Response({
            "average_turnaround_days": round(avg_turnaround_days, 1),
            "qc_rejection_rate": round(qc_rejection_rate, 1),
            "vendor_on_time_rate": round(vendor_on_time_rate, 1),
            "team_performance": team_performance,
            "job_status_distribution": list(job_status_dist),
        })


# ============================================================================
# STOREFRONT ECOMMERCE VIEWSETS
# ============================================================================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class CustomerViewSet(viewsets.ModelViewSet):
    """
    Customer Management for Storefront
    Handles identity matching and customer accounts
    """
    queryset = Customer.objects.select_related('user', 'matched_client').all()
    serializer_class = CustomerSerializer
    permission_classes = [AllowAny]  # Public registration
    
    filterset_fields = ['email', 'phone', 'is_guest', 'is_active']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    
    def perform_create(self, serializer):
        """Auto-match to existing Client on creation"""
        customer = serializer.save()
        # Auto-match to existing Client
        customer.match_to_existing_client()
    
    @decorators.action(detail=False, methods=['post'])
    def match_identity(self, request):
        """Match customer to existing Client by email/phone"""
        email = request.data.get('email')
        phone = request.data.get('phone')
        
        if not email and not phone:
            return Response(
                {'error': 'Email or phone required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            customer = Customer.objects.get(email=email) if email else Customer.objects.get(phone=phone)
            matched_client = customer.match_to_existing_client()
            
            return Response({
                'customer_id': customer.id,
                'matched': matched_client is not None,
                'client_id': matched_client.id if matched_client else None,
            })
        except Customer.DoesNotExist:
            return Response(
                {'error': 'Customer not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class CustomerAddressViewSet(viewsets.ModelViewSet):
    """Customer Address Book"""
    queryset = CustomerAddress.objects.select_related('customer').all()
    serializer_class = CustomerAddressSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['customer', 'address_type', 'is_default_billing', 'is_default_shipping']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class CartViewSet(viewsets.ModelViewSet):
    """
    Shopping Cart Management
    Supports both authenticated customers and guest sessions
    """
    queryset = Cart.objects.prefetch_related('items', 'items__product').all()
    serializer_class = CartSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['customer', 'session_key', 'is_active', 'is_abandoned']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filter by customer or session
        customer_id = self.request.query_params.get('customer_id')
        session_key = self.request.query_params.get('session_key')
        
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id, is_active=True)
        elif session_key:
            queryset = queryset.filter(session_key=session_key, is_active=True)
        
        return queryset
    
    @decorators.action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        """Add item to cart"""
        cart = self.get_object()
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))
        design_state_json = request.data.get('design_state_json')
        design_file_url = request.data.get('design_file_url', '')
        
        try:
            product = Product.objects.get(id=product_id)
            unit_price = resolve_unit_price(product, quantity) if hasattr(product, 'base_price') else product.base_price
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                design_state_json=design_state_json,
                defaults={
                    'product_name': product.name,
                    'product_sku': product.internal_code or '',
                    'unit_price': unit_price,
                    'quantity': quantity,
                    'design_file_url': design_file_url,
                }
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            return Response(CartItemSerializer(cart_item).data)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Product not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @decorators.action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        """Remove item from cart"""
        cart = self.get_object()
        item_id = request.data.get('item_id')
        
        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
            item.delete()
            return Response({'success': True})
        except CartItem.DoesNotExist:
            return Response(
                {'error': 'Item not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @decorators.action(detail=True, methods=['post'])
    def apply_coupon(self, request, pk=None):
        """Apply coupon to cart"""
        cart = self.get_object()
        coupon_code = request.data.get('coupon_code')
        
        try:
            coupon = Coupon.objects.get(code=coupon_code, is_active=True)
            is_valid, message = coupon.is_valid(
                customer=cart.customer,
                order_amount=cart.subtotal
            )
            
            if not is_valid:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response({
                'coupon_code': coupon.code,
                'discount_type': coupon.discount_type,
                'discount_value': coupon.discount_value,
                'message': 'Coupon applied successfully'
            })
        except Coupon.DoesNotExist:
            return Response(
                {'error': 'Invalid coupon code'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @decorators.action(detail=True, methods=['post'])
    def checkout(self, request, pk=None):
        """Convert cart to order"""
        cart = self.get_object()
        
        if cart.items.count() == 0:
            return Response(
                {'error': 'Cart is empty'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get addresses
        billing_address_id = request.data.get('billing_address_id')
        shipping_address_id = request.data.get('shipping_address_id')
        
        try:
            billing_address = CustomerAddress.objects.get(id=billing_address_id) if billing_address_id else None
            shipping_address = CustomerAddress.objects.get(id=shipping_address_id) if shipping_address_id else None
            
            # Calculate totals
            subtotal = cart.subtotal
            shipping_cost = Decimal('0')  #Calculated by shipping method
            tax_amount = Decimal('0')  # Calculated by tax engine
            discount_amount = Decimal('0')  # From coupon 
            total_amount = subtotal + shipping_cost + tax_amount - discount_amount
            
            # Create order
            order = Order.objects.create(
                customer=cart.customer,
                subtotal=subtotal,
                shipping_cost=shipping_cost,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                billing_address=billing_address,
                shipping_address=shipping_address,
                status='pending',
                payment_status='pending',
            )
            
            # Create order items
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    product_name=cart_item.product_name,
                    product_sku=cart_item.product_sku,
                    unit_price=cart_item.unit_price,
                    quantity=cart_item.quantity,
                    design_state_json=cart_item.design_state_json,
                    design_file_url=cart_item.design_file_url,
                    line_total=cart_item.line_total,
                )
            
            # Deactivate cart
            cart.is_active = False
            cart.save()
            
            return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)
        except CustomerAddress.DoesNotExist:
            return Response(
                {'error': 'Address not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class OrderViewSet(viewsets.ModelViewSet):
    """Order Management"""
    queryset = Order.objects.prefetch_related('items', 'items__product').select_related('customer').all()
    serializer_class = OrderSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['customer', 'status', 'payment_status', 'order_number']
    search_fields = ['order_number', 'customer__email']
    ordering_fields = ['created_at', 'total_amount']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset
    
    @decorators.action(detail=True, methods=['post'])
    def calculate_shipping(self, request, pk=None):
        """Calculate shipping cost for order"""
        order = self.get_object()
        shipping_method_id = request.data.get('shipping_method_id')
        
        try:
            shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
            
            # Calculate total weight (placeholder - would need product weight)
            total_weight = Decimal('1.0')  # Placeholder
            
            shipping_cost = shipping_method.calculate_shipping_cost(
                weight=total_weight,
                order_amount=order.subtotal,
                destination=order.shipping_address
            )
            
            order.shipping_cost = shipping_cost
            order.shipping_method = shipping_method
            order.total_amount = order.subtotal + order.shipping_cost + order.tax_amount - order.discount_amount
            order.save()
            
            return Response({
                'shipping_cost': float(shipping_cost),
                'total_amount': float(order.total_amount),
            })
        except ShippingMethod.DoesNotExist:
            return Response(
                {'error': 'Shipping method not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @decorators.action(detail=True, methods=['post'])
    def calculate_tax(self, request, pk=None):
        """Calculate tax for order"""
        order = self.get_object()
        
        if not order.shipping_address:
            return Response(
                {'error': 'Shipping address required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Find applicable tax configuration
        tax_config = None
        for config in TaxConfiguration.objects.filter(is_active=True):
            if config.applies_to(order.shipping_address, order.customer):
                tax_config = config
                break
        
        if tax_config:
            tax_amount = tax_config.calculate_tax(order.subtotal)
            order.tax_amount = tax_amount
            order.total_amount = order.subtotal + order.shipping_cost + tax_amount - order.discount_amount
            order.save()
            
            return Response({
                'tax_amount': float(tax_amount),
                'tax_rate': float(tax_config.rate),
                'total_amount': float(order.total_amount),
            })
        else:
            return Response({
                'tax_amount': 0,
                'tax_rate': 0,
                'total_amount': float(order.total_amount),
            })
    
    @decorators.action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """Process payment for order"""
        order = self.get_object()
        payment_method = request.data.get('payment_method')
        transaction_id = request.data.get('transaction_id')
        gateway_response = request.data.get('gateway_response', {})
        
        # Create payment transaction
        payment_transaction = PaymentTransaction.objects.create(
            order=order,
            customer=order.customer,
            payment_method=payment_method,
            amount=order.total_amount,
            transaction_id=transaction_id,
            gateway_response=gateway_response,
            status='processing',
        )
        
        # Update order payment status
        order.payment_method = payment_method
        order.payment_transaction_id = transaction_id
        order.payment_status = 'processing'
        order.save()
        
        return Response({
            'transaction_id': payment_transaction.transaction_id,
            'status': payment_transaction.status,
        })
    
    @decorators.action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """Confirm payment completion"""
        order = self.get_object()
        transaction_id = request.data.get('transaction_id')
        
        try:
            payment_transaction = PaymentTransaction.objects.get(
                transaction_id=transaction_id,
                order=order
            )
            
            payment_transaction.status = 'completed'
            payment_transaction.completed_at = timezone.now()
            payment_transaction.save()
            
            order.payment_status = 'completed'
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save()
            
            # TODO: Create Job from Order
            # TODO: Send confirmation email
            
            return Response({
                'success': True,
                'order_number': order.order_number,
                'status': order.status,
            })
        except PaymentTransaction.DoesNotExist:
            return Response(
                {'error': 'Payment transaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    """Coupon/Discount Engine"""
    queryset = Coupon.objects.filter(is_active=True)
    serializer_class = CouponSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['code', 'discount_type', 'is_active']
    search_fields = ['code', 'name']
    
    @decorators.action(detail=False, methods=['get'])
    def validate(self, request):
        """Validate a coupon code"""
        code = request.query_params.get('code')
        customer_id = request.query_params.get('customer_id')
        order_amount = Decimal(request.query_params.get('order_amount', 0))
        
        if not code:
            return Response(
                {'error': 'Coupon code required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
            customer = Customer.objects.get(id=customer_id) if customer_id else None
            
            is_valid, message = coupon.is_valid(customer=customer, order_amount=order_amount)
            
            if is_valid:
                discount_amount = coupon.calculate_discount(order_amount)
                return Response({
                    'valid': True,
                    'coupon': CouponSerializer(coupon).data,
                    'discount_amount': float(discount_amount),
                    'message': message,
                })
            else:
                return Response({
                    'valid': False,
                    'message': message,
                }, status=status.HTTP_400_BAD_REQUEST)
        except Coupon.DoesNotExist:
            return Response(
                {'valid': False, 'message': 'Invalid coupon code'},
                status=status.HTTP_404_NOT_FOUND
            )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class DesignTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """Design Templates for Design Studio"""
    queryset = DesignTemplate.objects.filter(is_active=True)
    serializer_class = DesignTemplateSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['product', 'product_category', 'is_featured', 'is_premium']
    search_fields = ['name', 'description']
    ordering_fields = ['usage_count', 'created_at']


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class DesignStateViewSet(viewsets.ModelViewSet):
    """Design State Storage"""
    queryset = DesignState.objects.select_related('product', 'template', 'customer').all()
    serializer_class = DesignStateSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['customer', 'product', 'is_saved', 'is_archived']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer_id')
        session_key = self.request.query_params.get('session_key')
        
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        elif session_key:
            queryset = queryset.filter(session_key=session_key)
        
        return queryset


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class ProductReviewViewSet(viewsets.ModelViewSet):
    """Product Reviews and Ratings"""
    queryset = ProductReview.objects.filter(is_approved=True).select_related('product', 'customer', 'order')
    serializer_class = ProductReviewSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['product', 'customer', 'rating', 'is_approved', 'is_verified_purchase']
    ordering_fields = ['created_at', 'rating', 'helpful_count']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id, is_approved=True)
        return queryset
    
    @decorators.action(detail=True, methods=['post'])
    def mark_helpful(self, request, pk=None):
        """Mark review as helpful"""
        review = self.get_object()
        review.helpful_count += 1
        review.save(update_fields=['helpful_count'])
        return Response({'helpful_count': review.helpful_count})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """Shipping Methods"""
    queryset = ShippingMethod.objects.filter(is_active=True)
    serializer_class = ShippingMethodSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['carrier', 'pricing_type', 'is_active', 'is_default']
    ordering_fields = ['is_default', 'name']


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class TaxConfigurationViewSet(viewsets.ReadOnlyModelViewSet):
    """Tax Configuration"""
    queryset = TaxConfiguration.objects.filter(is_active=True)
    serializer_class = TaxConfigurationSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['country', 'state_province', 'city', 'tax_type', 'is_active']


# ==================== CANONICAL PRICING ENGINE ====================

class PricingEngineView(APIView):
    """
    Canonical Pricing Engine Endpoint
    POST /v1/pricing/calculate/
    Deterministic, stateless pricing calculation
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from ..services.pricing_engine import PricingEngine
        from rest_framework import serializers
        
        class PricingRequestSerializer(serializers.Serializer):
            product_id = serializers.IntegerField(required=True)
            quantity = serializers.IntegerField(required=True, min_value=1)
            variables = serializers.DictField(required=False, allow_null=True)
            turnaround_id = serializers.IntegerField(required=False, allow_null=True)
            shipping_method_id = serializers.IntegerField(required=False, allow_null=True)
            coupon_code = serializers.CharField(required=False, allow_null=True, allow_blank=True)
            customer_type = serializers.ChoiceField(choices=['B2C', 'B2B'], default='B2C')
            currency = serializers.CharField(default='KES', max_length=3)
            customer_id = serializers.IntegerField(required=False, allow_null=True)
        
        serializer = PricingRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            result = PricingEngine.calculate(**serializer.validated_data)
            
            # Convert Decimal to float for JSON serialization
            return Response({
                "base_price": float(result["base_price"]),
                "variable_price": float(result["variable_price"]),
                "turnaround_price": float(result["turnaround_price"]),
                "discounts": float(result["discounts"]),
                "tax": float(result["tax"]),
                "shipping": float(result["shipping"]),
                "subtotal": float(result["subtotal"]),
                "total": float(result["total"]),
                "margin": float(result["margin"]),
                "currency": result["currency"],
            })
        except DjangoValidationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Pricing calculation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ProductConfigurationValidationView(APIView):
    """
    Product Configuration Rules Engine
    POST /v1/product-configurations/validate/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from ..services.product_configuration import ProductConfigurationValidator
        from rest_framework import serializers
        
        class ValidationRequestSerializer(serializers.Serializer):
            product_id = serializers.IntegerField(required=True)
            variables = serializers.DictField(required=True)
        
        serializer = ValidationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = ProductConfigurationValidator.validate(
            product_id=serializer.validated_data['product_id'],
            variables=serializer.validated_data['variables']
        )
        
        return Response(result)


class PreflightView(APIView):
    """
    Design & Artwork Intelligence - Preflight Service
    POST /v1/files/preflight/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        from ..services.preflight import PreflightService
        from rest_framework import serializers
        
        class PreflightRequestSerializer(serializers.Serializer):
            file_url = serializers.URLField(required=True)
            product_id = serializers.IntegerField(required=True)
            file_size = serializers.IntegerField(required=False, allow_null=True)
            file_format = serializers.CharField(required=False, allow_null=True, allow_blank=True)
        
        serializer = PreflightRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = PreflightService.validate(**serializer.validated_data)
        return Response(result)



@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))
class ProductRuleViewSet(viewsets.ModelViewSet):
    queryset = ProductRule.objects.all()
    serializer_class = ProductRuleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
class TimelineEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TimelineEvent.objects.all()
    serializer_class = TimelineEventSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['entity_type', 'entity_id', 'event_type']

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class DesignSessionViewSet(viewsets.ModelViewSet):
    queryset = DesignSession.objects.all()
    serializer_class = DesignSessionSerializer
    permission_classes = [AllowAny]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class DesignVersionViewSet(viewsets.ModelViewSet):
    queryset = DesignVersion.objects.all()
    serializer_class = DesignVersionSerializer
    permission_classes = [AllowAny]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class ProofApprovalViewSet(viewsets.ModelViewSet):
    queryset = ProofApproval.objects.all()
    serializer_class = ProofApprovalSerializer
    permission_classes = [AllowAny]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['order', 'status', 'carrier']

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
class PromotionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Promotion.objects.filter(is_active=True)
    serializer_class = PromotionSerializer
    permission_classes = [AllowAny]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Inventory Management']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Inventory Management']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Inventory Management']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Inventory Management']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Inventory Management']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Inventory Management']))
class MaterialInventoryViewSet(viewsets.ModelViewSet):
    queryset = MaterialInventory.objects.all()
    serializer_class = MaterialInventorySerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class CreditNoteViewSet(viewsets.ModelViewSet):
    queryset = CreditNote.objects.all()
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class AdjustmentViewSet(viewsets.ModelViewSet):
    queryset = Adjustment.objects.all()
    serializer_class = AdjustmentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Integrations']))
class WebhookSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = WebhookSubscription.objects.all()
    serializer_class = WebhookSubscriptionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Integrations']))
class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookDelivery.objects.all()
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated, IsAdmin]


# ============================================================================
# PHASE 2 & 3 VENDOR OPERATIONS & QUALITY CONTROL VIEWSETS
# ============================================================================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class PurchaseOrderProofViewSet(viewsets.ModelViewSet):
    """
    Purchase Order Proof ViewSet - Vendors submit proofs, PT approves/rejects.
    Phase 2 Implementation: Full REST API for vendor proof submission and approval workflow.
    """
    queryset = PurchaseOrderProof.objects.select_related('purchase_order', 'reviewed_by', 'purchase_order__vendor').all()
    serializer_class = PurchaseOrderProofSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsVendor]
    filterset_fields = ['purchase_order', 'status', 'proof_type']
    search_fields = ['purchase_order__po_number']
    ordering_fields = ['submitted_at', 'reviewed_at']
    ordering = ['-submitted_at']
    
    def get_queryset(self):
        """Filter proofs based on user role"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        # If user is a vendor, filter to their PO proofs only
        try:
            vendor = Vendor.objects.get(user=user, active=True)
            queryset = queryset.filter(purchase_order__vendor=vendor)
            return queryset
        except Vendor.DoesNotExist:
            pass  # Not a vendor, continue with PT logic
        
        # PT/Admin can view all
        return queryset
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def approve(self, request, pk=None):
        """PT approves vendor proof"""
        proof = self.get_object()
        
        if proof.status == 'approved':
            return Response(
                {'detail': 'Proof already approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proof.status = 'approved'
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.save()
        
        # Update PO status if all proofs approved
        po = proof.purchase_order
        pending_proofs = PurchaseOrderProof.objects.filter(
            purchase_order=po,
            status__in=['pending', 'rejected']
        ).count()
        
        if pending_proofs == 0:
            po.proofs_approved = True
            po.save()
            
            # Notify vendor
            if po.vendor:
                Notification.objects.create(
                    recipient=po.vendor.primary_contact if hasattr(po.vendor, 'primary_contact') else None,
                    notification_type='proof_approved',
                    title=f'All proofs approved for PO {po.po_number}',
                    message='Your proofs have been approved. Ready to proceed to next stage.',
                    link=f'/purchase-orders/{po.id}/',
                )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Proof Review',
            title=f'Proof Approved for PO {po.po_number}',
            description=f'Proof #{proof.id} for PO {po.po_number}. Status: Approved',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(proof)
        return Response({'detail': 'Proof approved', 'proof': serializer.data})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def reject(self, request, pk=None):
        """PT rejects vendor proof"""
        proof = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if proof.status == 'rejected':
            return Response(
                {'detail': 'Proof already rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proof.status = 'rejected'
        proof.rejection_reason = reason
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.save()
        
        # Notify vendor to resubmit
        po = proof.purchase_order
        if po.vendor:
            Notification.objects.create(
                recipient=po.vendor.primary_contact if hasattr(po.vendor, 'primary_contact') else None,
                notification_type='proof_rejected',
                title=f'Proof Rejected for PO {po.po_number}',
                message=f'Your proof has been rejected. Reason: {reason}. Please resubmit.',
                link=f'/purchase-orders/{po.id}/',
            )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Proof Review',
            title=f'Proof Rejected for PO {po.po_number}',
            description=f'Proof type: {proof.proof_type}. Reason: {reason}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(proof)
        return Response({'detail': 'Proof rejected', 'proof': serializer.data, 'reason': reason})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class PurchaseOrderIssueViewSet(viewsets.ModelViewSet):
    """
    Purchase Order Issue ViewSet - Track vendor issues, blocking items, and resolutions.
    Phase 2 Implementation: Full REST API for issue tracking and resolution workflow.
    """
    queryset = PurchaseOrderIssue.objects.select_related('purchase_order', 'resolved_by', 'purchase_order__vendor').all()
    serializer_class = PurchaseOrderIssueSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsVendor]
    filterset_fields = ['purchase_order', 'status', 'issue_type']
    search_fields = ['purchase_order__po_number', 'description']
    ordering_fields = ['created_at', 'resolved_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter issues based on user role"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        # If user is a vendor, filter to their PO issues only
        try:
            vendor = Vendor.objects.get(user=user, active=True)
            queryset = queryset.filter(purchase_order__vendor=vendor)
            return queryset
        except Vendor.DoesNotExist:
            pass  # Not a vendor, continue with PT logic
        
        # PT/Admin can view all
        return queryset
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def resolve(self, request, pk=None):
        """Mark issue as resolved"""
        issue = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        if not resolution_notes:
            return Response(
                {'error': 'Resolution notes are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        issue.status = 'resolved'
        issue.resolution_notes = resolution_notes
        issue.resolved_by = request.user
        issue.resolved_at = timezone.now()
        issue.save()
        
        # Update PO - unblock if no other active issues
        po = issue.purchase_order
        active_issues = PurchaseOrderIssue.objects.filter(
            purchase_order=po,
            status='open'
        ).count()
        
        if active_issues == 0 and po.is_blocked:
            po.is_blocked = False
            po.blocked_reason = None
            po.status = 'IN_PRODUCTION'
            po.save()
        
        # Notify vendor of resolution
        if po.vendor:
            Notification.objects.create(
                recipient=po.vendor.primary_contact if hasattr(po.vendor, 'primary_contact') else None,
                notification_type='issue_resolved',
                title=f'Issue Resolved for PO {po.po_number}',
                message=f'An issue with your PO has been resolved. Details: {resolution_notes}',
                link=f'/purchase-orders/{po.id}/',
            )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Issue Resolution',
            title=f'Issue Resolved for PO {po.po_number}',
            description=f'Issue type: {issue.issue_type}. Resolution: {resolution_notes}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(issue)
        return Response({'detail': 'Issue resolved', 'issue': serializer.data})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class PurchaseOrderNoteViewSet(viewsets.ModelViewSet):
    """
    Purchase Order Note ViewSet - Track notes, messages, and communication for POs.
    Phase 2 Implementation: Full REST API for vendor-PT communication.
    """
    queryset = PurchaseOrderNote.objects.select_related('purchase_order', 'sender', 'purchase_order__vendor').all()
    serializer_class = PurchaseOrderNoteSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsVendor]
    filterset_fields = ['purchase_order', 'category', 'sender']
    search_fields = ['purchase_order__po_number', 'message']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter notes based on user role"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        # If user is a vendor, filter to their PO notes only
        try:
            vendor = Vendor.objects.get(user=user, active=True)
            queryset = queryset.filter(purchase_order__vendor=vendor)
            return queryset
        except Vendor.DoesNotExist:
            pass  # Not a vendor, continue with PT logic
        
        # PT/Admin can view all
        return queryset
    
    def perform_create(self, serializer):
        """Auto-set sender to current user"""
        serializer.save(sender=self.request.user)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class MaterialSubstitutionRequestViewSet(viewsets.ModelViewSet):
    """
    Material Substitution Request ViewSet - Vendors request material changes.
    Phase 2 Implementation: Full REST API for material substitution workflow.
    """
    queryset = MaterialSubstitutionRequest.objects.select_related('purchase_order', 'reviewed_by', 'purchase_order__vendor').all()
    serializer_class = MaterialSubstitutionRequestSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsVendor]
    filterset_fields = ['purchase_order', 'status']
    search_fields = ['purchase_order__po_number', 'original_material', 'proposed_material']
    ordering_fields = ['created_at', 'reviewed_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter substitutions based on user role"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        # If user is a vendor, filter to their PO substitutions only
        try:
            vendor = Vendor.objects.get(user=user, active=True)
            queryset = queryset.filter(purchase_order__vendor=vendor)
            return queryset
        except Vendor.DoesNotExist:
            pass  # Not a vendor, continue with PT logic
        
        # PT/Admin can view all
        return queryset
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def approve(self, request, pk=None):
        """PT approves material substitution"""
        substitution = self.get_object()
        approval_notes = request.data.get('approval_notes', '')
        
        substitution.status = 'approved'
        substitution.approval_notes = approval_notes
        substitution.reviewed_by = request.user
        substitution.reviewed_at = timezone.now()
        substitution.save()
        
        # Notify vendor
        po = substitution.purchase_order
        if po.vendor:
            Notification.objects.create(
                recipient=po.vendor.primary_contact if hasattr(po.vendor, 'primary_contact') else None,
                notification_type='substitution_approved',
                title=f'Material Substitution Approved for PO {po.po_number}',
                message=f'Your request to substitute {substitution.original_material} with {substitution.proposed_material} has been approved.',
                link=f'/purchase-orders/{po.id}/',
            )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Material Substitution',
            title=f'Substitution Approved for PO {po.po_number}',
            description=f'{substitution.original_material} → {substitution.proposed_material}. Notes: {approval_notes}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(substitution)
        return Response({'detail': 'Substitution approved', 'substitution': serializer.data})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def reject(self, request, pk=None):
        """PT rejects material substitution"""
        substitution = self.get_object()
        rejection_reason = request.data.get('rejection_reason', '')
        
        if not rejection_reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        substitution.status = 'rejected'
        substitution.rejection_reason = rejection_reason
        substitution.reviewed_by = request.user
        substitution.reviewed_at = timezone.now()
        substitution.save()
        
        # Notify vendor
        po = substitution.purchase_order
        if po.vendor:
            Notification.objects.create(
                recipient=po.vendor.primary_contact if hasattr(po.vendor, 'primary_contact') else None,
                notification_type='substitution_rejected',
                title=f'Material Substitution Rejected for PO {po.po_number}',
                message=f'Your request to substitute {substitution.original_material} has been rejected. Reason: {rejection_reason}',
                link=f'/purchase-orders/{po.id}/',
            )
        
        # Log activity
        ActivityLog.objects.create(
            client=po.job.client,
            activity_type='Material Substitution',
            title=f'Substitution Rejected for PO {po.po_number}',
            description=f'Original: {substitution.original_material}. Reason: {rejection_reason}',
            created_by=request.user,
        )
        
        serializer = self.get_serializer(substitution)
        return Response({'detail': 'Substitution rejected', 'substitution': serializer.data})


# ============================================================================
# CLIENT PORTAL VIEWSETS - Complete B2B Client Management
# ============================================================================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientPortalUserViewSet(viewsets.ModelViewSet):
    """
    Client Portal User Management
    Manage portal access and permissions for client employees
    """
    queryset = ClientPortalUser.objects.select_related('user', 'client').all()
    serializer_class = ClientPortalUserSerializer
    permission_classes = [IsAuthenticated, IsClient | IsClientOwner]
    filterset_fields = ['client', 'role', 'is_active']
    search_fields = ['user__username', 'user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['created_at', 'role']
    
    def get_queryset(self):
        """Restrict to user's client only"""
        queryset = super().get_queryset()
        if getattr(self, 'swagger_fake_view', False):
            return queryset.none()
        
        user = self.request.user
        
        try:
            portal_user = ClientPortalUser.objects.get(user=user)
            # Show only portal users from same client
            return queryset.filter(client=portal_user.client)
        except ClientPortalUser.DoesNotExist:
            # Admin can see all
            if user.is_superuser or user.groups.filter(name="Admin").exists():
                return queryset
            return queryset.none()
    
    @decorators.action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsClient])
    def invite_user(self, request):
        """Invite new user to client portal"""
        email = request.data.get('email')
        role = request.data.get('role', 'user')
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            portal_user = ClientPortalUser.objects.get(user=request.user)
        except ClientPortalUser.DoesNotExist:
            return Response({'error': 'User is not a portal member'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user is owner/admin
        if portal_user.role not in ['owner', 'admin']:
            return Response({'error': 'Only owners/admins can invite users'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if user already exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Create new user - they'll set password on first login
            username = email.split('@')[0]
            # Ensure unique username
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User.objects.create_user(
                username=username,
                email=email,
                is_active=False  # Inactive until they accept invite
            )
        
        # Check if already a portal user for this client
        existing = ClientPortalUser.objects.filter(client=portal_user.client, user=user).first()
        if existing:
            return Response({'error': 'User is already a member'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create portal user
        new_portal_user = ClientPortalUser.objects.create(
            client=portal_user.client,
            user=user,
            role=role,
            is_active=False,
        )
        
        # Send invitation email - TODO: implement email service
        Notification.objects.create(
            recipient=user,
            notification_type='portal_invitation',
            title='Invited to Client Portal',
            message=f'You have been invited to join {portal_user.client.name} portal',
            link='/portal/invite-accept/',
        )
        
        serializer = ClientPortalUserSerializer(new_portal_user)
        return Response({
            'detail': 'Invitation sent',
            'portal_user': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsClient])
    def revoke_access(self, request, pk=None):
        """Revoke portal access for a user"""
        portal_user = self.get_object()
        
        try:
            current_user = ClientPortalUser.objects.get(user=request.user)
        except ClientPortalUser.DoesNotExist:
            return Response({'error': 'Current user is not a portal member'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check permissions
        if current_user.role not in ['owner', 'admin']:
            return Response({'error': 'Only owners/admins can revoke access'}, status=status.HTTP_403_FORBIDDEN)
        
        # Cannot revoke owner's access
        if portal_user.role == 'owner':
            return Response({'error': 'Cannot revoke owner access'}, status=status.HTTP_400_BAD_REQUEST)
        
        portal_user.is_active = False
        portal_user.revoked_at = timezone.now()
        portal_user.save()
        
        # Create notification
        Notification.objects.create(
            recipient=portal_user.user,
            notification_type='access_revoked',
            title='Portal Access Revoked',
            message=f'Your access to {portal_user.client.name} portal has been revoked',
        )
        
        serializer = self.get_serializer(portal_user)
        return Response({'detail': 'Access revoked', 'portal_user': serializer.data})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientOrderViewSet(viewsets.ModelViewSet):
    """
    Client Orders - B2B Purchase Orders from Approved Quotes
    Clients can view, place, track orders
    """
    queryset = ClientOrder.objects.select_related('client', 'quote', 'job', 'created_by').prefetch_related('items').all()
    serializer_class = ClientOrderSerializer
    permission_classes = [IsAuthenticated, IsClient | IsClientOwner]
    filterset_fields = ['client', 'status', 'quote']
    search_fields = ['co_number', 'quote__quote_id']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        if getattr(self, 'swagger_fake_view', False):
            return ClientOrder.objects.none()
        
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            return queryset.filter(client=portal_user.client)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsClient])
    def submit(self, request, pk=None):
        """Submit order for processing"""
        order = self.get_object()
        
        if order.status != 'draft':
            return Response(
                {'error': f'Cannot submit order in {order.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'submitted'
        order.submitted_at = timezone.now()
        order.save()
        
        # Create notification for PT
        pt_group = Group.objects.filter(name="Production Team").first()
        if pt_group:
            for user in pt_group.user_set.all():
                Notification.objects.create(
                    recipient=user,
                    notification_type='client_order_submitted',
                    title=f'Client Order {order.co_number} Submitted',
                    message=f'{order.client.name} submitted order {order.co_number}',
                    link=f'/client-orders/{order.id}/',
                )
        
        # Create activity log
        ClientActivityLog.objects.create(
            portal_user_id=ClientPortalUser.objects.get(user=request.user).id,
            client=order.client,
            action_type='order_created',
            title=f'Order {order.co_number} Submitted',
            description=f'Order submitted for processing',
            ip_address=self._get_client_ip(request),
        )
        
        serializer = self.get_serializer(order)
        return Response({'detail': 'Order submitted', 'order': serializer.data})
    
    @decorators.action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsClient])
    def cancel(self, request, pk=None):
        """Cancel pending order"""
        order = self.get_object()
        
        if order.status not in ['draft', 'submitted']:
            return Response(
                {'error': f'Cannot cancel order in {order.status} status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.status = 'cancelled'
        order.cancelled_at = timezone.now()
        order.save()
        
        # Create activity log
        ClientActivityLog.objects.create(
            portal_user_id=ClientPortalUser.objects.get(user=request.user).id,
            client=order.client,
            action_type='order_updated',
            title=f'Order {order.co_number} Cancelled',
            description='Order cancelled by client',
            ip_address=self._get_client_ip(request),
        )
        
        serializer = self.get_serializer(order)
        return Response({'detail': 'Order cancelled', 'order': serializer.data})
    
    def _get_client_ip(self, request):
        """Extract client IP from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientInvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Client Invoices - Read-only for viewing and downloading
    """
    queryset = ClientInvoice.objects.select_related('client', 'order').all()
    serializer_class = ClientInvoiceSerializer
    permission_classes = [IsAuthenticated, IsClient | IsClientOwner]
    filterset_fields = ['client', 'status', 'order']
    search_fields = ['inv_number', 'order__co_number']
    ordering_fields = ['created_at', 'due_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            return queryset.filter(client=portal_user.client)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()
    
    @decorators.action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download invoice as PDF"""
        invoice = self.get_object()
        
        # Generate PDF - TODO: implement PDF generation
        # For now, return file metadata
        return Response({
            'invoice_number': invoice.inv_number,
            'filename': f'{invoice.inv_number}.pdf',
            'file_size': 0,
            'generated_at': timezone.now().isoformat(),
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientPaymentViewSet(viewsets.ModelViewSet):
    """
    Client Payments - Submit and track payments
    """
    queryset = ClientPayment.objects.select_related('client', 'invoice', 'created_by').all()
    serializer_class = ClientPaymentSerializer
    permission_classes = [IsAuthenticated, IsClient | IsClientOwner]
    filterset_fields = ['client', 'status', 'payment_method']
    search_fields = ['pay_number', 'invoice__inv_number']
    ordering_fields = ['created_at', 'payment_date']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        if getattr(self, 'swagger_fake_view', False):
            return ClientPayment.objects.none()
        
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            return queryset.filter(client=portal_user.client)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()
    
    def perform_create(self, serializer):
        """Record payment submission"""
        payment = serializer.save(
            created_by=self.request.user,
            status='pending'  # Awaiting approval
        )
        
        # Create activity log
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            ClientActivityLog.objects.create(
                portal_user=portal_user,
                client=payment.client,
                action_type='payment_made',
                title=f'Payment {payment.pay_number} Submitted',
                description=f'Payment of {payment.amount} submitted via {payment.payment_method}',
                ip_address=self._get_client_ip(self.request),
            )
        except ClientPortalUser.DoesNotExist:
            pass
        
        # Send notification to Admin
        admin_group = Group.objects.filter(name="Admin").first()
        if admin_group:
            for user in admin_group.user_set.all():
                Notification.objects.create(
                    recipient=user,
                    notification_type='payment_received',
                    title=f'Payment {payment.pay_number} Received',
                    message=f'{payment.client.name} submitted payment of {payment.amount}',
                    link=f'/client-payments/{payment.id}/',
                )
    
    @decorators.action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Admin verifies payment completion"""
        payment = self.get_object()
        
        if not request.user.groups.filter(name="Admin").exists():
            return Response({'error': 'Only admins can verify payments'}, status=status.HTTP_403_FORBIDDEN)
        
        payment.status = 'completed'
        payment.verified_at = timezone.now()
        payment.save()
        
        # Create notification for client
        try:
            portal_user = ClientPortalUser.objects.get(client=payment.client)
            Notification.objects.create(
                recipient=portal_user.user,
                notification_type='payment_confirmed',
                title=f'Payment {payment.pay_number} Confirmed',
                message='Your payment has been received and processed',
                link=f'/portal/payments/',
            )
        except ClientPortalUser.DoesNotExist:
            pass
        
        serializer = self.get_serializer(payment)
        return Response({'detail': 'Payment verified', 'payment': serializer.data})
    
    def _get_client_ip(self, request):
        """Extract client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientSupportTicketViewSet(viewsets.ModelViewSet):
    """
    Client Support Tickets - Issue tracking and support workflow
    """
    queryset = ClientSupportTicket.objects.select_related('client', 'assigned_to', 'created_by').prefetch_related('replies').all()
    serializer_class = ClientSupportTicketSerializer
    permission_classes = [IsAuthenticated, IsClient | IsClientOwner]
    filterset_fields = ['client', 'status', 'priority']
    search_fields = ['tkt_number', 'subject']
    ordering_fields = ['created_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        if getattr(self, 'swagger_fake_view', False):
            return ClientSupportTicket.objects.none()
        
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            return queryset.filter(client=portal_user.client)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()
    
    def perform_create(self, serializer):
        """Auto-assign to support team"""
        ticket = serializer.save(
            created_by=self.request.user,
            status='open'
        )
        
        # Auto-assign to support team (first available)
        support_group = Group.objects.filter(name="Support").first()
        if support_group:
            support_user = support_group.user_set.first()
            if support_user:
                ticket.assigned_to = support_user
                ticket.save()
        
        # Create activity log
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            ClientActivityLog.objects.create(
                portal_user=portal_user,
                client=ticket.client,
                action_type='ticket_created',
                title=f'Ticket {ticket.tkt_number} Created',
                description=f'Support ticket: {ticket.subject}',
                ip_address=self._get_client_ip(self.request),
            )
        except ClientPortalUser.DoesNotExist:
            pass
        
        # Notify assigned user
        if ticket.assigned_to:
            Notification.objects.create(
                recipient=ticket.assigned_to,
                notification_type='ticket_assigned',
                title=f'Ticket {ticket.tkt_number} Assigned',
                message=f'{ticket.client.name}: {ticket.subject}',
                link=f'/client-tickets/{ticket.id}/',
            )
    
    @decorators.action(detail=True, methods=['post'])
    def add_reply(self, request, pk=None):
        """Add reply to ticket"""
        ticket = self.get_object()
        message = request.data.get('message')
        is_internal = request.data.get('is_internal', False)
        
        if not message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        reply = ClientTicketReply.objects.create(
            ticket=ticket,
            author=request.user,
            message=message,
            is_internal_note=is_internal,
        )
        
        # Update ticket status if customer replies
        if not is_internal and ticket.status == 'awaiting_customer':
            ticket.status = 'open'
            ticket.save()
        
        # Notify other side
        if is_internal:
            # Internal note - notify support team
            support_group = Group.objects.filter(name="Support").first()
            if support_group:
                for user in support_group.user_set.all():
                    if user != request.user:
                        Notification.objects.create(
                            recipient=user,
                            notification_type='ticket_internal_note',
                            title=f'Internal Note: {ticket.tkt_number}',
                            message=message[:100],
                            link=f'/client-tickets/{ticket.id}/',
                        )
        else:
            # Customer reply - notify support team
            if ticket.assigned_to:
                Notification.objects.create(
                    recipient=ticket.assigned_to,
                    notification_type='ticket_reply',
                    title=f'Reply: {ticket.tkt_number}',
                    message=message[:100],
                    link=f'/client-tickets/{ticket.id}/',
                )
        
        serializer = ClientTicketReplySerializer(reply)
        return Response({'detail': 'Reply added', 'reply': serializer.data})
    
    @decorators.action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve/close ticket"""
        ticket = self.get_object()
        
        if not request.user.groups.filter(name="Support").exists():
            return Response({'error': 'Only support can resolve tickets'}, status=status.HTTP_403_FORBIDDEN)
        
        ticket.status = 'resolved'
        ticket.resolved_at = timezone.now()
        ticket.save()
        
        # Notify customer
        try:
            portal_user = ClientPortalUser.objects.get(client=ticket.client)
            Notification.objects.create(
                recipient=portal_user.user,
                notification_type='ticket_resolved',
                title=f'Ticket {ticket.tkt_number} Resolved',
                message='Your support ticket has been resolved',
                link=f'/portal/tickets/',
            )
        except ClientPortalUser.DoesNotExist:
            pass
        
        serializer = self.get_serializer(ticket)
        return Response({'detail': 'Ticket resolved', 'ticket': serializer.data})
    
    def _get_client_ip(self, request):
        """Extract client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientDocumentLibraryViewSet(viewsets.ModelViewSet):
    """
    Client Document Library - Share documents with clients
    """
    queryset = ClientDocumentLibrary.objects.select_related('client', 'uploaded_by', 'accessible_to').all()
    serializer_class = ClientDocumentLibrarySerializer
    permission_classes = [IsAuthenticated, IsClient | IsClientOwner]
    filterset_fields = ['client', 'document_type', 'is_expired']
    search_fields = ['file_name', 'description']
    ordering_fields = ['uploaded_at', 'expires_at']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        if getattr(self, 'swagger_fake_view', False):
            return ClientDocumentLibrary.objects.none()
        
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            # Show documents for this client that are accessible to this user
            return queryset.filter(client=portal_user.client, accessible_to=portal_user)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()
    
    @decorators.action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download document"""
        document = self.get_object()
        
        # Log download
        try:
            portal_user = ClientPortalUser.objects.get(user=request.user)
            ClientActivityLog.objects.create(
                portal_user=portal_user,
                client=document.client,
                action_type='document_downloaded',
                title=f'Document Downloaded: {document.file_name}',
                description=f'File: {document.file_name}',
                ip_address=self._get_client_ip(request),
            )
        except ClientPortalUser.DoesNotExist:
            pass
        
        return Response({
            'file_name': document.file_name,
            'file_size': document.file_size,
            'file_url': document.file_url,
            'downloaded_at': timezone.now().isoformat(),
        })
    
    def _get_client_ip(self, request):
        """Extract client IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientPortalNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Client Portal Notifications - Real-time portal alerts
    """
    queryset = ClientPortalNotification.objects.select_related('client').all()
    serializer_class = ClientPortalNotificationSerializer
    permission_classes = [IsAuthenticated, IsClient]
    filterset_fields = ['client', 'notification_type', 'is_read']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            return queryset.filter(client=portal_user.client)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()
    
    @decorators.action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response({'detail': 'Marked as read', 'notification': serializer.data})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Client Portal']))
class ClientActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Client Portal Activity Log - Audit trail for all portal actions
    """
    queryset = ClientActivityLog.objects.select_related('client', 'portal_user').all()
    serializer_class = ClientActivityLogSerializer
    permission_classes = [IsAuthenticated, IsClient]
    filterset_fields = ['client', 'action_type', 'portal_user']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Restrict to user's client"""
        queryset = super().get_queryset()
        try:
            portal_user = ClientPortalUser.objects.get(user=self.request.user)
            # Only owner/admin can see full activity log
            if portal_user.role in ['owner', 'admin']:
                return queryset.filter(client=portal_user.client)
            # Regular users see only their own activities
            return queryset.filter(client=portal_user.client, portal_user=portal_user)
        except ClientPortalUser.DoesNotExist:
            return queryset.none()


# ============================================================================
# PRODUCTION TEAM PORTAL - NEW VIEWSETS FOR PT INTEGRATION
# ============================================================================

class ApprovalThresholdSerializer(serializers.ModelSerializer):
    """Serializer for ApprovalThreshold model"""
    class Meta:
        model = ApprovalThreshold
        fields = ['id', 'role', 'min_amount', 'max_amount', 'description', 'created_at', 'updated_at']
        ref_name = 'ApprovalThresholdDetail'


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['PT Portal']))
class ApprovalThresholdViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Approval Thresholds - Role-based spending limits
    Defines maximum invoice amounts each role can approve
    """
    queryset = ApprovalThreshold.objects.filter(is_active=True)
    serializer_class = ApprovalThresholdSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    ordering_fields = ['min_amount', 'max_amount']
    ordering = ['min_amount']
    
    @decorators.action(detail=False, methods=['get'])
    def my_threshold(self, request):
        """Get current user's approval threshold"""
        threshold = ApprovalThreshold.get_user_threshold(request.user)
        if threshold:
            serializer = self.get_serializer(threshold)
            return Response(serializer.data)
        return Response({'detail': 'No approval threshold configured'}, status=status.HTTP_404_NOT_FOUND)
    
    @decorators.action(detail=False, methods=['post'])
    def check_authority(self, request):
        """Check if user can approve a specific amount"""
        amount = Decimal(request.data.get('amount', 0))
        can_approve, message = ApprovalThreshold.can_user_approve_amount(request.user, amount)
        return Response({
            'can_approve': can_approve,
            'message': message,
            'amount': str(amount),
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['PT Portal']))
class InvoiceDisputeViewSet(viewsets.ModelViewSet):
    """
    Invoice Disputes - Track disputed invoices
    PT team can create disputes, vendors can respond
    """
    permission_classes = [IsAuthenticated, IsProductionTeam]
    filterset_fields = ['status', 'vendor', 'invoice']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get disputes, filter for PT team"""
        if self.request.user.groups.filter(name='Production Team').exists():
            return InvoiceDispute.objects.select_related('invoice', 'vendor', 'created_by')
        return InvoiceDispute.objects.none()
    
    def get_serializer_class(self):
        """Define serializer for disputes"""
        class DisputeSerializer(serializers.ModelSerializer):
            invoice_number = serializers.CharField(source='invoice.invoice_number', read_only=True)
            vendor_name = serializers.CharField(source='vendor.name', read_only=True)
            created_by_name = serializers.CharField(source='created_by.username', read_only=True)
            
            class Meta:
                model = InvoiceDispute
                fields = ['id', 'invoice', 'invoice_number', 'vendor', 'vendor_name', 'title', 
                         'description', 'status', 'resolution_notes', 'resolved_at', 'resolved_by',
                         'created_at', 'created_by', 'created_by_name', 'updated_at']
                ref_name = 'InvoiceDisputeDetail'
        
        return DisputeSerializer
    
    def perform_create(self, serializer):
        """Create dispute and log activity"""
        dispute = serializer.save(created_by=self.request.user)
        ActivityLog.objects.create(
            user=self.request.user,
            action_type='invoice_dispute_created',
            title=f'Invoice Dispute Created: {dispute.invoice.invoice_number}',
            description=f'{dispute.title}',
        )
        logger.info(f'Invoice dispute created by {self.request.user.username} for invoice {dispute.invoice.invoice_number}')
    
    @decorators.action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a dispute"""
        dispute = self.get_object()
        dispute.status = 'resolved'
        dispute.resolved_by = request.user
        dispute.resolved_at = timezone.now()
        dispute.resolution_notes = request.data.get('resolution_notes', '')
        dispute.save()
        
        ActivityLog.objects.create(
            user=request.user,
            action_type='invoice_dispute_resolved',
            title=f'Invoice Dispute Resolved: {dispute.invoice.invoice_number}',
        )
        
        # Notify vendor
        from .vendor_notifications import VendorNotificationService
        VendorNotificationService.notify_dispute_resolved(dispute)
        
        serializer = self.get_serializer(dispute)
        return Response({'detail': 'Dispute resolved', 'dispute': serializer.data})


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['PT Portal']))
class JobProgressUpdateViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Job Progress Updates - Track vendor progress on jobs
    Vendors submit, PT team reviews in real-time
    """
    permission_classes = [IsAuthenticated, IsProductionTeam]
    filterset_fields = ['job_vendor_stage', 'created_by']
    ordering_fields = ['created_at', 'progress_percentage']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Get progress updates for PT team"""
        if self.request.user.groups.filter(name='Production Team').exists():
            return JobProgressUpdate.objects.select_related('job_vendor_stage', 'created_by').all()
        return JobProgressUpdate.objects.none()
    
    def get_serializer_class(self):
        """Serializer for progress updates"""
        class ProgressSerializer(serializers.ModelSerializer):
            job_number = serializers.CharField(source='job_vendor_stage.job.job_number', read_only=True)
            vendor_name = serializers.CharField(source='job_vendor_stage.vendor.name', read_only=True)
            
            class Meta:
                model = JobProgressUpdate
                fields = ['id', 'job_vendor_stage', 'job_number', 'vendor_name', 'progress_percentage',
                         'status', 'notes', 'created_at', 'created_by']
                ref_name = 'JobProgressUpdateDetail'
        
        return ProgressSerializer


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['PT Portal']))
class SLAEscalationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    SLA Escalations - Track deadline breaches and escalations
    """
    permission_classes = [IsAuthenticated, IsProductionTeam]
    filterset_fields = ['level', 'job_vendor_stage']
    ordering_fields = ['created_at', 'days_overdue']
    ordering = ['-days_overdue', '-created_at']
    
    def get_queryset(self):
        """Get escalations for PT team"""
        if self.request.user.groups.filter(name='Production Team').exists():
            return SLAEscalation.objects.select_related('job_vendor_stage').all()
        return SLAEscalation.objects.none()
    
    def get_serializer_class(self):
        """Serializer for escalations"""
        class EscalationSerializer(serializers.ModelSerializer):
            
            class Meta:
                model = SLAEscalation
                fields = ['id', 'purchase_order', 'escalation_level', 'escalation_status',
                         'original_deadline', 'current_deadline', 'days_overdue', 
                         'escalation_reason', 'escalation_notes']
                ref_name = 'SLAEscalationDetail'
        
        return EscalationSerializer


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['PT Portal']))
class VendorPerformanceMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vendor Performance Metrics - Comprehensive vendor scoring
    On-time %, QC pass rate, response time, financial metrics
    """
    queryset = VendorPerformanceMetrics.objects.select_related('vendor').all()
    permission_classes = [IsAuthenticated, IsProductionTeam]
    filterset_fields = ['vendor']
    ordering_fields = ['on_time_percentage', 'qc_pass_rate', 'last_updated']
    ordering = ['-on_time_percentage']
    
    def get_serializer_class(self):
        """Serializer for performance metrics"""
        class MetricsSerializer(serializers.ModelSerializer):
            vendor_name = serializers.CharField(source='vendor.name', read_only=True)
            class Meta:
                model = VendorPerformanceMetrics
                fields = ['id', 'vendor', 'vendor_name', 'total_jobs', 'on_time_jobs', 'on_time_percentage',
                         'qc_passed_jobs', 'qc_failed_jobs', 'qc_pass_rate', 'avg_response_time_hours',
                         'total_invoice_amount', 'approved_invoice_amount', 'dispute_amount', 'last_updated']
                ref_name = 'VendorPerformanceMetricsDetail'
        
        return MetricsSerializer


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['PT Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['PT Portal']))
class ProfitabilityAnalysisViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Profitability Analysis - Job/Vendor/Product profitability tracking
    """
    queryset = ProfitabilityAnalysis.objects.all()
    permission_classes = [IsAuthenticated, IsProductionTeam]
    filterset_fields = ['entity_type', 'period_start', 'period_end']
    ordering_fields = ['margin_percentage', 'revenue', 'created_at']
    ordering = ['-margin_percentage']
    
    def get_serializer_class(self):
        """Serializer for profitability"""
        class ProfitSerializer(serializers.ModelSerializer):
            class Meta:
                model = ProfitabilityAnalysis
                fields = ['id', 'entity_type', 'entity_id', 'revenue', 'cost', 'margin',
                         'margin_percentage', 'period_start', 'period_end', 'created_at', 'updated_at']
                ref_name = 'ProfitabilityAnalysisDetail'
        
        return ProfitSerializer


# ============================================================================
# PHASE 2: MESSAGING, PROGRESS, & PROOFS VIEWSETS
# ============================================================================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 2 - Messaging']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Phase 2 - Messaging']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 2 - Messaging']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Phase 2 - Messaging']))
class MessageViewSet(viewsets.ModelViewSet):
    """
    Message ViewSet - Vendor-PT communication
    Features: Send messages, file attachments, task assignment with acknowledgment, read status
    Endpoints:
        GET /api/v1/messages/ - List messages (filtered by job)
        POST /api/v1/messages/ - Create new message
        GET /api/v1/messages/{id}/ - Retrieve single message
        POST /api/v1/messages/{id}/acknowledge_task/ - Acknowledge task message
        POST /api/v1/messages/{id}/mark_read/ - Mark message as read
        GET /api/v1/messages/unread_count/ - Get unread message count
    """
    queryset = Message.objects.select_related('job', 'sender_vendor', 'recipient_vendor').prefetch_related('attachments').all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsVendor]
    filterset_fields = ['job', 'sender_type', 'is_task', 'is_read', 'task_status']
    search_fields = ['content', 'sender_name', 'recipient_name']
    ordering = ['-created_at']
    pagination_class = None  # No pagination for messages (load all)

    def get_queryset(self):
        """Filter messages based on user role"""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Vendors can only see messages related to their jobs
        if hasattr(user, 'vendor'):
            queryset = queryset.filter(
                Q(sender_vendor=user.vendor) | Q(recipient_vendor=user.vendor)
            )
        
        return queryset

    def perform_create(self, serializer):
        """Create message with sender info"""
        user = self.request.user
        sender_type = self.request.data.get('sender_type', 'PT')
        
        message = serializer.save(
            sender_type=sender_type,
            sender_name=user.get_full_name() or user.username,
            sender_id=user.id if sender_type == 'PT' else None,
            sender_vendor=user.vendor if sender_type == 'Vendor' and hasattr(user, 'vendor') else None
        )
        
        # Auto-create notification for recipient
        self._create_notification(message)

    def _create_notification(self, message):
        """Create notification for message recipient"""
        if message.recipient_type == 'PT':
            Notification.objects.create(
                recipient_type='PT',
                recipient_id=message.recipient_id,
                notification_type='message',
                title=f"New message from {message.sender_name}",
                message=f"Job {message.job.job_number}: {message.content[:50]}...",
                related_object_type='Message',
                related_object_id=message.id
            )
        elif message.recipient_type == 'Vendor' and message.recipient_vendor:
            # TODO: Add vendor notification when vendor user model updated
            pass

    @action(detail=True, methods=['post'])
    def acknowledge_task(self, request, pk=None):
        """Acknowledge a task message"""
        message = self.get_object()
        
        if not message.is_task:
            return Response(
                {'detail': 'This message is not a task'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        message.task_status = 'acknowledged'
        message.save()
        
        return Response(
            {'detail': 'Task acknowledged', 'status': message.task_status},
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark message as read"""
        message = self.get_object()
        message.is_read = True
        message.read_at = timezone.now()
        message.save()
        
        return Response(
            {'detail': 'Message marked as read'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread messages for current user"""
        user = request.user
        
        # Count unread messages (recipient)
        unread = Message.objects.filter(
            is_read=False,
            recipient_type='PT',
            recipient_id=user.id
        ).count() if hasattr(user, 'id') else 0
        
        return Response({'unread_count': unread}, status=status.HTTP_200_OK)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 2 - Progress']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Phase 2 - Progress']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 2 - Progress']))
class ProgressUpdateViewSet(viewsets.ModelViewSet):
    """
    Progress Update ViewSet - Vendor job progress tracking
    Features: Update percentage complete, add status/issues, attach progress photos
    Endpoints:
        GET /api/v1/progress-updates/ - List updates (filtered by job/vendor)
        POST /api/v1/progress-updates/ - Create new progress update with photos
        GET /api/v1/progress-updates/{id}/ - Retrieve single update
    """
    queryset = ProgressUpdate.objects.select_related('job', 'vendor').prefetch_related('photos').all()
    serializer_class = ProgressUpdateSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsVendor]
    filterset_fields = ['job', 'vendor', 'status']
    ordering = ['-created_at']
    pagination_class = None

    def get_queryset(self):
        """Filter progress updates based on user role"""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Vendors can only see their own updates
        if hasattr(user, 'vendor'):
            queryset = queryset.filter(vendor=user.vendor)
        
        return queryset

    def perform_create(self, serializer):
        """Create progress update"""
        user = self.request.user
        job_id = self.request.data.get('job')
        
        # Verify vendor owns the job (if vendor submitting)
        if hasattr(user, 'vendor'):
            job = Job.objects.get(id=job_id)
            if job.vendor != user.vendor:
                raise ValidationError("You can only update progress on your own jobs")
        
        progress = serializer.save()
        
        # Auto-create notification to PT
        Notification.objects.create(
            recipient_type='PT',
            recipient_id=None,  # Will be set to job's PT coordinator
            notification_type='progress_update',
            title=f"Progress update: Job {progress.job.job_number}",
            message=f"{progress.vendor.name}: {progress.percentage_complete}% complete",
            related_object_type='ProgressUpdate',
            related_object_id=progress.id
        )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 2 - Proofs']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Phase 2 - Proofs']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 2 - Proofs']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Phase 2 - Proofs']))
class ProofSubmissionViewSet(viewsets.ModelViewSet):
    """
    Proof Submission ViewSet - QC review workflow
    Features: Submit final proofs, track approval status, revision requests
    Endpoints:
        GET /api/v1/proof-submissions/ - List submissions (filtered by job/status)
        POST /api/v1/proof-submissions/ - Submit new proofs
        GET /api/v1/proof-submissions/{id}/ - Retrieve submission
        POST /api/v1/proof-submissions/{id}/approve/ - Approve submission
        POST /api/v1/proof-submissions/{id}/reject/ - Request revisions
    """
    queryset = ProofSubmission.objects.select_related('job', 'vendor').all()
    serializer_class = ProofSubmissionSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsVendor]
    filterset_fields = ['job', 'vendor', 'status', 'proof_type']
    ordering = ['-created_at']
    pagination_class = None

    def get_queryset(self):
        """Filter proof submissions"""
        user = self.request.user
        queryset = super().get_queryset()
        
        # Vendors can only see their own submissions
        if hasattr(user, 'vendor'):
            queryset = queryset.filter(vendor=user.vendor)
        
        return queryset

    def perform_create(self, serializer):
        """Create proof submission"""
        user = self.request.user
        job_id = self.request.data.get('job')
        
        if hasattr(user, 'vendor'):
            job = Job.objects.get(id=job_id)
            if job.vendor != user.vendor:
                raise ValidationError("You can only submit proofs for your own jobs")
        
        proof = serializer.save(status='pending')
        
        # Auto-create QC notification
        Notification.objects.create(
            recipient_type='PT',
            notification_type='proof_submission',
            title=f"Proof submission: Job {proof.job.job_number}",
            message=f"Awaiting QC review - {proof.proof_type}",
            related_object_type='ProofSubmission',
            related_object_id=proof.id
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve proof submission"""
        proof = self.get_object()
        
        if request.user.groups.filter(name='ProductionTeam').exists() or request.user.is_staff:
            proof.status = 'approved'
            proof.reviewed_by = request.user
            proof.reviewed_at = timezone.now()
            proof.save()
            
            # Notify vendor of approval
            Notification.objects.create(
                recipient_type='Vendor',
                notification_type='proof_approved',
                title=f"Proof approved: Job {proof.job.job_number}",
                message="Your proof submission has been approved",
                related_object_type='ProofSubmission',
                related_object_id=proof.id
            )
            
            return Response({'detail': 'Proof approved', 'status': 'approved'})
        
        return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Request revision for proof submission"""
        proof = self.get_object()
        revision_reason = request.data.get('revision_reason', 'Please revise and resubmit')
        
        if request.user.groups.filter(name='ProductionTeam').exists() or request.user.is_staff:
            proof.status = 'revision_requested'
            proof.revision_reason = revision_reason
            proof.reviewed_by = request.user
            proof.reviewed_at = timezone.now()
            proof.save()
            
            # Notify vendor
            Notification.objects.create(
                recipient_type='Vendor',
                notification_type='proof_revision_requested',
                title=f"Revision requested: Job {proof.job.job_number}",
                message=revision_reason,
                related_object_type='ProofSubmission',
                related_object_id=proof.id
            )
            
            return Response({'detail': 'Revision requested', 'status': 'revision_requested'})
        
        return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 2 - Notifications']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 2 - Notifications']))
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Notification ViewSet - System notifications
    Features: List notifications, mark as read
    Endpoints:
        GET /api/v1/notifications/ - List notifications (filtered by recipient)
        GET /api/v1/notifications/{id}/ - Retrieve single notification
        POST /api/v1/notifications/{id}/mark_read/ - Mark notification as read
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['notification_type', 'is_read', 'recipient']
    ordering = ['-created_at']
    pagination_class = None

    def get_queryset(self):
        """Filter notifications for current user"""
        user = self.request.user
        queryset = super().get_queryset()

        if user.is_superuser or user.groups.filter(name='Admin').exists():
            return queryset

        return queryset.filter(recipient=user)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        
        return Response(
            {'detail': 'Notification marked as read'},
            status=status.HTTP_200_OK
        )


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 2 - Performance']))
class VendorPerformanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Vendor Performance ViewSet - VPS scores and metrics
    Features: Read-only access to vendor performance scores
    Endpoints:
        GET /api/v1/vendor-performance/ - List VPS scores (filtered by vendor)
        GET /api/v1/vendor-performance/{id}/ - Retrieve single score
        POST /api/v1/vendor-performance/recalculate_all/ - Recalculate all VPS scores
    """
    queryset = VendorPerformanceScore.objects.select_related('vendor').all()
    serializer_class = VendorPerformanceSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = ['vendor']
    ordering = ['-average_score']
    pagination_class = None

    @action(detail=False, methods=['post'])
    def recalculate_all(self, request):
        """
        Recalculate all VPS scores
        Formula: (on_time_percentage * 0.3) + (quality_score * 0.4) + (communication_score * 0.2) + (delivery_percentage * 0.1)
        """
        if not (request.user.groups.filter(name='ProductionTeam').exists() or request.user.is_staff):
            return Response({'detail': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        vendors = Vendor.objects.all()
        updated_count = 0
        
        for vendor in vendors:
            # Calculate on-time percentage
            completed_jobs = Job.objects.filter(vendor=vendor, status='completed')
            on_time_jobs = completed_jobs.filter(completed_date__lte=F('expected_completion')).count()
            on_time_percentage = (on_time_jobs / completed_jobs.count() * 100) if completed_jobs.exists() else 0
            
            # Calculate quality score (based on QC passes)
            qc_inspections = QCInspection.objects.filter(job__vendor=vendor)
            passed_qc = qc_inspections.filter(qc_status='passed').count()
            quality_score = (passed_qc / qc_inspections.count() * 100) if qc_inspections.exists() else 0
            
            # Calculate communication score (message response rate)
            # TODO: Implement based on message acknowledgment rate
            communication_score = 85.0  # Placeholder
            
            # Calculate delivery percentage
            delivery_percentage = 100.0 if on_time_percentage > 80 else 50.0
            
            # Calculate average score
            average_score = (
                (on_time_percentage * 0.3) +
                (quality_score * 0.4) +
                (communication_score * 0.2) +
                (delivery_percentage * 0.1)
            )
            
            # Update or create VPS record
            vps, created = VendorPerformanceScore.objects.update_or_create(
                vendor=vendor,
                defaults={
                    'on_time_percentage': on_time_percentage,
                    'quality_score': quality_score,
                    'communication_score': communication_score,
                    'average_score': average_score,
                    'on_time_jobs': on_time_jobs,
                    'total_jobs': completed_jobs.count(),
                    'delivery_percentage': delivery_percentage,
                    'quality_rating': quality_score,
                    'communication_rating': communication_score,
                    'last_recalculated': timezone.now()
                }
            )
            updated_count += 1
        
        return Response(
            {
                'detail': f'VPS scores recalculated for {updated_count} vendors',
                'updated_count': updated_count
            },
            status=status.HTTP_200_OK
        )


# ==================== PHASE 3: CLIENT PORTAL VIEWSETS ====================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
class ClientNotificationViewSet(viewsets.ModelViewSet):
    """
    Client Notification ViewSet - Notifications for clients
    Features: Create, list, mark as read
    Endpoints:
        GET /api/v1/client-notifications/ - List client's notifications
        GET /api/v1/client-notifications/{id}/ - Retrieve single notification
        PATCH /api/v1/client-notifications/{id}/mark_read/ - Mark as read
    """
    serializer_class = ClientNotificationSerializer
    permission_classes = [IsAuthenticated, IsClient]
    filterset_fields = ['is_read', 'notification_type']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return notifications for the authenticated client"""
        if not hasattr(self.request.user, 'client_profile'):
            return ClientNotification.objects.none()
        return ClientNotification.objects.filter(client=self.request.user.client_profile).select_related('order', 'proof')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        return Response({'detail': 'Notification marked as read'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read for this client"""
        if not hasattr(request.user, 'client_profile'):
            return Response({'detail': 'Not a client'}, status=status.HTTP_403_FORBIDDEN)
        
        client = request.user.client_profile
        unread = ClientNotification.objects.filter(client=client, is_read=False)
        count = unread.count()
        
        for notification in unread:
            notification.mark_as_read()
        
        return Response({
            'detail': f'{count} notifications marked as read',
            'count': count
        }, status=status.HTTP_200_OK)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
class ClientMessageViewSet(viewsets.ModelViewSet):
    """
    Client Message ViewSet - Real-time messaging between clients and PT team
    Features: Create messages, list messages, mark as read
    Endpoints:
        GET /api/v1/client-messages/?order=ID - List messages for order
        POST /api/v1/client-messages/ - Send message
        PATCH /api/v1/client-messages/{id}/mark_read/ - Mark as read
    """
    serializer_class = ClientMessageSerializer
    permission_classes = [IsAuthenticated, IsClient | IsProductionTeam]
    filterset_fields = ['order', 'sender_type']
    ordering = ['created_at']
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        """Return messages accessible to the user"""
        user = self.request.user
        
        # If client, return their own messages
        if hasattr(user, 'client_profile'):
            return ClientMessage.objects.filter(order__client=user.client_profile).select_related('sender', 'order')
        
        # If PT staff, return messages for orders they have access to
        return ClientMessage.objects.all().select_related('sender', 'order')
    
    def perform_create(self, serializer):
        """Create message and set sender info"""
        user = self.request.user
        sender_type = 'client' if hasattr(user, 'client_profile') else 'staff'
        serializer.save(sender=user, sender_type=sender_type)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a message as read"""
        message = self.get_object()
        message.mark_as_read()
        return Response({'detail': 'Message marked as read'}, status=status.HTTP_200_OK)


@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
class ClientDashboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Client Dashboard ViewSet - Client dashboard metrics
    Features: Read-only access to dashboard metrics
    Endpoints:
        GET /api/v1/client-dashboard/ - Get client's dashboard metrics
        POST /api/v1/client-dashboard/refresh/ - Refresh metrics
    """
    serializer_class = ClientDashboardSerializer
    permission_classes = [IsAuthenticated, IsClient]
    
    def get_queryset(self):
        """Return dashboard for authenticated client"""
        if not hasattr(self.request.user, 'client_profile'):
            return ClientDashboard.objects.none()
        return ClientDashboard.objects.filter(client=self.request.user.client_profile)
    
    @action(detail=False, methods=['get'])
    def my_dashboard(self, request):
        """Get current client's dashboard"""
        if not hasattr(request.user, 'client_profile'):
            return Response({'detail': 'Not a client'}, status=status.HTTP_403_FORBIDDEN)
        
        client = request.user.client_profile
        dashboard, created = ClientDashboard.objects.get_or_create(client=client)
        dashboard.refresh_metrics()
        
        serializer = self.get_serializer(dashboard)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def refresh(self, request):
        """Refresh dashboard metrics"""
        if not hasattr(request.user, 'client_profile'):
            return Response({'detail': 'Not a client'}, status=status.HTTP_403_FORBIDDEN)
        
        client = request.user.client_profile
        dashboard, created = ClientDashboard.objects.get_or_create(client=client)
        dashboard.refresh_metrics()
        
        serializer = self.get_serializer(dashboard)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Phase 3 - Client Portal']))
class ClientFeedbackViewSet(viewsets.ModelViewSet):
    """
    Client Feedback ViewSet - Feedback from clients about orders
    Features: Create feedback, list feedback, mark addressed
    Endpoints:
        GET /api/v1/client-feedback/?order=ID - List feedback
        POST /api/v1/client-feedback/ - Submit feedback
        PATCH /api/v1/client-feedback/{id}/mark_addressed/ - Mark as addressed
    """
    serializer_class = ClientFeedbackSerializer
    permission_classes = [IsAuthenticated, IsClient | IsProductionTeam | IsAdmin]
    filterset_fields = ['order', 'feedback_type', 'rating']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Return feedback accessible to the user"""
        user = self.request.user
        
        # Clients see their own feedback
        if hasattr(user, 'client_profile'):
            return ClientFeedback.objects.filter(client=user.client_profile)
        
        # PT staff and admin see all feedback
        return ClientFeedback.objects.all()
    
    def perform_create(self, serializer):
        """Create feedback and set client"""
        if hasattr(self.request.user, 'client_profile'):
            serializer.save(client=self.request.user.client_profile)
        else:
            serializer.save()
    
    @action(detail=True, methods=['post'])
    def mark_addressed(self, request, pk=None):
        """Mark feedback as addressed by PT"""
        feedback = self.get_object()
        feedback.is_addressed = True
        feedback.response = request.data.get('response', '')
        feedback.save()
        return Response({'detail': 'Feedback marked as addressed'}, status=status.HTTP_200_OK)


# ==================== PHASE 3: ANALYTICS VIEWSETS ====================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Analytics']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 3 - Analytics']))
class OrderMetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Order Metrics ViewSet - Monthly order metrics
    Features: Get order metrics by month/client
    Endpoints:
        GET /api/v1/order-metrics/?client=ID&month=YYYY-MM - List metrics
        GET /api/v1/order-metrics/trends/?client=ID - Get trends
    """
    queryset = OrderMetrics.objects.select_related('client').all()
    serializer_class = OrderMetricsSerializer
    permission_classes = [IsAuthenticated, IsClient | IsProductionTeam | IsAdmin]
    filterset_fields = ['client', 'month']
    ordering = ['-month']
    
    @action(detail=False, methods=['get'])
    def trends(self, request):
        """Get order trends for last N months"""
        client_id = request.query_params.get('client')
        months = request.query_params.get('months', 12)
        
        try:
            months = int(months)
        except:
            months = 12
        
        if not client_id:
            return Response({'detail': 'client parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.utils.timezone import now
        from datetime import timedelta
        from django.db.models import Avg, Sum, Q
        
        now_date = now().date()
        start_date = now_date.replace(day=1) - timedelta(days=months*30)
        
        metrics = OrderMetrics.objects.filter(
            client__id=client_id,
            month__gte=start_date
        ).order_by('month').values(
            'month'
        ).annotate(
            avg_value=Avg('total_value'),
            total_orders=Sum('total_orders'),
            completed_rate=Avg('completion_rate'),
            quality=Avg('avg_quality_score')
        )
        
        return Response(metrics, status=status.HTTP_200_OK)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Analytics']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 3 - Analytics']))
class VendorComparisonViewSet(viewsets.ModelViewSet):
    """
    Vendor Comparison ViewSet - Compare vendor performance
    Endpoints:
        GET /api/v1/vendor-comparison/ - List comparisons
        POST /api/v1/vendor-comparison/ - Create comparison
    """
    queryset = VendorComparison.objects.select_related('client', 'vendor1', 'vendor2').all()
    serializer_class = VendorComparisonSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]
    filterset_fields = ['client', 'vendor1', 'vendor2']
    ordering = ['-comparison_date']


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Analytics']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 3 - Analytics']))
class PerformanceAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Performance Analytics ViewSet - Vendor performance analytics
    Endpoints:
        GET /api/v1/performance-analytics/ - List analytics
        GET /api/v1/performance-analytics/by_month/ - Get analytics by month
        GET /api/v1/performance-analytics/rankings/ - Get vendor rankings
    """
    queryset = PerformanceAnalytics.objects.select_related('vendor').all()
    serializer_class = PerformanceAnalyticsSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]
    filterset_fields = ['vendor', 'month']
    ordering = ['-month', '-overall_trend']
    
    @action(detail=False, methods=['get'])
    def by_month(self, request):
        """Get performance analytics for a specific month"""
        month = request.query_params.get('month')
        
        if not month:
            return Response({'detail': 'month parameter required (YYYY-MM)'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            month_date = datetime.strptime(month, '%Y-%m').date().replace(day=1)
        except:
            return Response({'detail': 'Invalid month format'}, status=status.HTTP_400_BAD_REQUEST)
        
        analytics = PerformanceAnalytics.objects.filter(month=month_date).order_by('-overall_trend', '-quality_score')
        serializer = self.get_serializer(analytics, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def rankings(self, request):
        """Get vendor rankings by month"""
        month = request.query_params.get('month')
        
        if not month:
            return Response({'detail': 'month parameter required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from datetime import datetime
            month_date = datetime.strptime(month, '%Y-%m').date().replace(day=1)
        except:
            return Response({'detail': 'Invalid month format'}, status=status.HTTP_400_BAD_REQUEST)
        
        analytics = PerformanceAnalytics.objects.filter(
            month=month_date
        ).order_by('ranking').values(
            'vendor__name', 'ranking', 'percentile', 'quality_score',
            'on_time_delivery_percentage', 'overall_trend'
        )
        
        return Response(analytics, status=status.HTTP_200_OK)


# ==================== PHASE 3: PAYMENT TRACKING VIEWSETS ====================

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Payment Tracking']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Phase 3 - Payment Tracking']))
class PaymentStatusViewSet(viewsets.ModelViewSet):
    """
    Payment Status ViewSet - Track payment status for invoices
    Endpoints:
        GET /api/v1/payment-status/ - List payment statuses
        PATCH /api/v1/payment-status/{id}/ - Update payment status
        POST /api/v1/payment-status/{id}/mark_paid/ - Mark as paid
    """
    queryset = PaymentStatus.objects.select_related('invoice').all()
    serializer_class = PaymentStatusSerializer
    permission_classes = [IsAuthenticated, IsClient | IsProductionTeam | IsAdmin]
    filterset_fields = ['status', 'invoice']
    ordering = ['due_date']
    
    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Mark payment as paid"""
        payment_status = self.get_object()
        payment_status.status = 'paid'
        payment_status.paid_date = timezone.now().date()
        payment_status.amount_paid = payment_status.amount_due
        payment_status.amount_pending = Decimal('0.00')
        payment_status.is_overdue = False
        payment_status.save()
        
        serializer = self.get_serializer(payment_status)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get all overdue payments"""
        from django.utils import timezone
        overdue = PaymentStatus.objects.filter(
            status__in=['pending', 'partial', 'overdue'],
            due_date__lt=timezone.now().date()
        ).select_related('invoice')
        
        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Phase 3 - Payment Tracking']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Phase 3 - Payment Tracking']))
class PaymentHistoryViewSet(viewsets.ModelViewSet):
    """
    Payment History ViewSet - Track individual payment transactions
    Endpoints:
        GET /api/v1/payment-history/ - List payments
        POST /api/v1/payment-history/ - Record payment
        POST /api/v1/payment-history/{id}/reconcile/ - Mark as reconciled
    """
    queryset = PaymentHistory.objects.select_related('payment_status', 'created_by', 'reconciled_by').all()
    serializer_class = PaymentHistorySerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsProductionTeam]
    filterset_fields = ['payment_status', 'payment_method']
    ordering = ['-payment_date']
    
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark payment as reconciled"""
        payment = self.get_object()
        payment.reconciled = True
        payment.reconciled_by = request.user
        payment.reconciled_at = timezone.now()
        payment.save()
        
        serializer = self.get_serializer(payment)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def unreconciled(self, request):
        """Get all unreconciled payments"""
        unreconciled = PaymentHistory.objects.filter(reconciled=False)
        serializer = self.get_serializer(unreconciled, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# Task 8: Deadline Alerts
class DeadlineAlertViewSet(viewsets.ModelViewSet):
    """API for deadline alerts and notifications"""
    queryset = DeadlineAlert.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['job', 'urgency', 'status', 'alert_type']
    ordering_fields = ['created_at', 'days_until_deadline', 'urgency']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        from clientapp.api_serializers import DeadlineAlertSerializer
        return DeadlineAlertSerializer
    
    def get_queryset(self):
        """Filter by user's assigned jobs"""
        if getattr(self, 'swagger_fake_view', False):
            return DeadlineAlert.objects.none()
        
        user = self.request.user
        if user.groups.filter(name='Account Manager').exists() or user.is_superuser:
            return DeadlineAlert.objects.all()
        return DeadlineAlert.objects.filter(job__person_in_charge=user)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active deadline alerts"""
        alerts = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get alerts for jobs with approaching deadlines (next 5 days)"""
        from datetime import datetime, timedelta
        cutoff = timedelta(days=5)
        alerts = self.get_queryset().filter(
            days_until_deadline__lte=5,
            days_until_deadline__gt=0,
            status='active'
        )
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue deadline alerts"""
        alerts = self.get_queryset().filter(days_until_deadline__lt=0, status='active')
        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge a deadline alert"""
        alert = self.get_object()
        alert.status = 'acknowledged'
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = request.user
        alert.save()
        
        # Broadcast update
        from clientapp.websocket_helpers import broadcast_deadline_acknowledged
        broadcast_deadline_acknowledged(alert)
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark deadline alert as resolved"""
        alert = self.get_object()
        alert.status = 'resolved'
        alert.save()
        
        # Broadcast update
        from clientapp.websocket_helpers import broadcast_deadline_resolved
        broadcast_deadline_resolved(alert)
        
        serializer = self.get_serializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def urgency_summary(self, request):
        """Get summary of alerts by urgency"""
        alerts = self.get_queryset().filter(status='active')
        summary = {
            'critical': alerts.filter(urgency='critical').count(),
            'high': alerts.filter(urgency='high').count(),
            'medium': alerts.filter(urgency='medium').count(),
            'low': alerts.filter(urgency='low').count(),
            'total': alerts.count(),
        }
        return Response(summary)


# Task 9: Job Files & Document Sharing
class JobFileViewSet(viewsets.ModelViewSet):
    """API for job file uploads"""
    queryset = JobFile.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['job', 'file_type', 'is_shared']
    ordering_fields = ['uploaded_at', 'file_size']
    ordering = ['-uploaded_at']
    
    def get_serializer_class(self):
        from clientapp.api_serializers import JobFileSerializer
        return JobFileSerializer
    
    def get_queryset(self):
        """Filter by user's jobs or shared files"""
        if getattr(self, 'swagger_fake_view', False):
            return JobFile.objects.none()
        
        user = self.request.user
        if user.groups.filter(name='Account Manager').exists() or user.is_superuser:
            return JobFile.objects.all()
        
        # Return files from assigned jobs or shared with user
        from django.db.models import Q
        return JobFile.objects.filter(
            Q(job__person_in_charge=user) |
            Q(shared_with=user) |
            Q(is_shared=True)
        ).distinct()
    
    def perform_create(self, serializer):
        """Attach current user as uploader"""
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        """Share a file with users"""
        file = self.get_object()
        share_type = request.data.get('share_type', 'team')
        user_ids = request.data.get('user_ids', [])
        
        shares_created = 0
        for user_id in user_ids:
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            share = DocumentShare.objects.create(
                file=file,
                share_type=share_type,
                shared_with_user=user,
                shared_by=request.user
            )
            shares_created += 1
        
        return Response({
            'success': True,
            'shares_created': shares_created
        })
    
    @action(detail=True, methods=['post'])
    def download(self, request, pk=None):
        """Register a download and return file"""
        file = self.get_object()
        file.download_count += 1
        file.last_downloaded_at = timezone.now()
        file.save()
        
        # Broadcast download notification
        from clientapp.websocket_helpers import broadcast_file_downloaded
        broadcast_file_downloaded(file, request.user)
        
        return Response({
            'download_url': file.file.url,
            'file_name': file.file_name,
            'file_size': file.file_size,
        })
    
    @action(detail=True, methods=['post'])
    def toggle_share(self, request, pk=None):
        """Toggle file sharing status"""
        file = self.get_object()
        file.is_shared = not file.is_shared
        file.save()
        
        serializer = self.get_serializer(file)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recently uploaded files"""
        files = self.get_queryset()[:10]
        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def shared(self, request):
        """Get all shared files accessible to user"""
        files = self.get_queryset().filter(is_shared=True)
        serializer = self.get_serializer(files, many=True)
        return Response(serializer.data)


class DocumentShareViewSet(viewsets.ModelViewSet):
    """API for document sharing and access control"""
    queryset = DocumentShare.objects.all()
    permission_classes = [IsAuthenticated]
    filterset_fields = ['file', 'share_type', 'status']
    ordering_fields = ['share_date', 'access_count']
    ordering = ['-share_date']
    
    def get_serializer_class(self):
        from clientapp.api_serializers import DocumentShareSerializer
        return DocumentShareSerializer
    
    def get_queryset(self):
        """Filter by user's shares"""
        if getattr(self, 'swagger_fake_view', False):
            return DocumentShare.objects.none()
        
        user = self.request.user
        if user.is_superuser:
            return DocumentShare.objects.all()
        
        from django.db.models import Q
        return DocumentShare.objects.filter(
            Q(shared_by=user) |
            Q(shared_with_user=user)
        )
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """Revoke sharing access"""
        share = self.get_object()
        share.status = 'revoked'
        share.save()
        
        return Response({
            'success': True,
            'message': 'Sharing access revoked'
        })
    
    @action(detail=False, methods=['get'])
    def shared_with_me(self, request):
        """Get documents shared with me"""
        shares = DocumentShare.objects.filter(
            shared_with_user=request.user,
            status='active'
        )
        serializer = self.get_serializer(shares, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_shares(self, request):
        """Get documents I've shared"""
        shares = DocumentShare.objects.filter(shared_by=request.user)
        serializer = self.get_serializer(shares, many=True)
        return Response(serializer.data)


class ContactFormView(APIView):
    """Public API endpoint for website contact form submissions"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Handle contact form submission and send email notification"""
        try:
            first_name = request.data.get('first_name', '').strip()
            last_name = request.data.get('last_name', '').strip()
            email = request.data.get('email', '').strip()
            message = request.data.get('message', '').strip()
            inquiry_type = request.data.get('inquiry_type', 'General inquiry')
            
            if not all([first_name, last_name, email, message]):
                return Response(
                    {'error': 'All fields are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError as DjangoValidationError
            
            try:
                validate_email(email)
            except DjangoValidationError:
                return Response(
                    {'error': 'Invalid email address'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            context = {
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
                'message': message,
                'inquiry_type': inquiry_type,
            }
            
            html_message = render_to_string(
                'emails/contact_inquiry_notification.html',
                context
            )
            
            email_message = EmailMultiAlternatives(
                subject=f'New Contact Inquiry from {first_name} {last_name}',
                body=f'New {inquiry_type} from {first_name} {last_name} ({email})\n\nMessage:\n{message}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=['query@printduka.co.ke'],
                reply_to=[email],
            )
            email_message.attach_alternative(html_message, "text/html")
            email_message.send()
            
            logger.info(f'Contact form submission from {email} sent successfully')
            
            return Response(
                {'message': 'Thank you for contacting us. We will get back to you shortly.'},
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            logger.error(f'Error processing contact form: {str(e)}')
            return Response(
                {'error': 'Unable to process your request. Please try again later.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets, status, decorators, serializers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from decimal import Decimal
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator



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
    ProductReviewSettings,
    ProductFAQ,
    ProductShipping,
    ProductLegal,
    ProductProduction,
    ProductChangeHistory,
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
    WebhookDelivery,
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
    ProductImageSerializer,
    ProductVideoSerializer,
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
    ProductTemplateSerializer,
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
)
from .permissions import (
    IsAdmin,
    IsAccountManager,
    IsProductionTeam,
    IsOwnerOrAdmin,
)

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))

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
        serializer.save()

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

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["customization_level", "status", "is_visible", "primary_category", "sub_category"]
    search_fields = ["name", "internal_code"]
    ordering_fields = ["created_at", "updated_at", "base_price"]


#storefront- for later use
@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

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

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))

class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client", "lead", "created_by").prefetch_related("line_items")
    serializer_class = QuoteSerializer
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]
    filterset_fields = ["status", "production_status", "client", "lead", "channel", "checkout_status"]
    search_fields = ["quote_id", "product_name", "reference_number"]
    ordering_fields = ["created_at", "quote_date", "valid_until"]

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
                {"detail": "Can only clone locked (approved) quotes. Use direct edit for draft quotes."},
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
        
        # Create notification if user assigned
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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Account Manager']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Account Manager']))

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

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsAccountManager | IsAdmin])
    def remind(self, request, pk=None):
        """
        Send a reminder notification to the assigned Production Team member.
        Implements 4-hour cooldown period to prevent spam.
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
        
        # Log activity with timestamp for cooldown tracking
        ActivityLog.objects.create(
            client=job.client,
            activity_type="Job",
            title=f"Reminder Sent for Job {job.job_number}",
            description=f"Reminder sent to {job.person_in_charge.get_full_name() or job.person_in_charge.username}",
            created_by=request.user,
        )
        
        return Response({
            "detail": "Reminder sent successfully",
            "recipient": job.person_in_charge.get_full_name() or job.person_in_charge.username,
            "next_reminder_allowed": (timezone.now() + timedelta(hours=4)).isoformat()
        })

    @decorators.action(detail=True, methods=["post"], permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin])
    def send_to_vendor(self, request, pk=None):
        """
        Send job specifications to a vendor.
        Packages job attachments and specs into a vendor-ready format.
        """
        job = self.get_object()
        vendor_id = request.data.get("vendor_id")
        stage_name = request.data.get("stage_name", "Production")
        expected_days = int(request.data.get("expected_days", 3))
        
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
        
        # Get job attachments
        attachments = job.attachments.all()
        attachment_list = [{
            "file_name": att.file_name,
            "file_size": att.file_size,
            "uploaded_at": att.uploaded_at,
        } for att in attachments]
        
        # Create notification for vendor (if vendor has user account)
        # activity log
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
        
        return Response({
            "detail": "Job sent to vendor successfully",
            "vendor_stage_id": vendor_stage.id,
            "vendor_name": vendor.name,
            "expected_completion": vendor_stage.expected_completion,
            "attachments_count": len(attachment_list),
            "attachments": attachment_list,
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))

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
    filterset_fields = ["vps_score", "active"]
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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))

class PropertyTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PropertyType.objects.all()
    serializer_class = PropertyTypeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["property_type", "affects_price"]
    search_fields = ["name", "description"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))

class PropertyValueViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PropertyValue.objects.select_related("property_type").all()
    serializer_class = PropertyValueSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["property_type", "is_active"]
    search_fields = ["value", "description"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))

class ProductPropertyViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProductProperty.objects.select_related("product", "property_value", "property_value__property_type").all()
    serializer_class = ProductPropertySerializer
    permission_classes = [AllowAny]
    filterset_fields = ["product", "property_value__property_type", "is_available"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))

class QuantityPricingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = QuantityPricing.objects.select_related("product").all()
    serializer_class = QuantityPricingSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["product"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))

class TurnAroundTimeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TurnAroundTime.objects.select_related("product").all()
    serializer_class = TurnAroundTimeSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["product", "is_available", "is_default"]


# ===== Costing Process ViewSets =====

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Pricing & Costing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Pricing & Costing']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Notifications & Logging']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Notifications & Logging']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Notifications & Logging']))

class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ActivityLog.objects.select_related("client", "created_by").all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["client", "activity_type"]
    search_fields = ["title", "description"]
    ordering_fields = ["created_at"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

class SystemSettingViewSet(viewsets.ModelViewSet):
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


# ===== Product Metadata ViewSets =====

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.select_related("product").all()
    serializer_class = ProductImageSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["product", "image_type", "is_primary"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

class ProductVideoViewSet(viewsets.ModelViewSet):
    queryset = ProductVideo.objects.select_related("product").all()
    serializer_class = ProductVideoSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = ["product", "video_type"]


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Product Catalog']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Product Catalog']))

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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Integrations']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Integrations']))

class QuickBooksSyncViewSet(viewsets.ViewSet):
    """
    in quickbooks.py
    Placeholder ViewSet for QuickBooks Online synchronization endpoints.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def list(self, request):
        return Response({"detail": "QuickBooks sync endpoints"}, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["post"])
    def push_clients(self, request):
        return Response({"detail": "Client sync not yet implemented"}, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["post"])
    def push_invoices(self, request):
        return Response({"detail": "Invoice sync not yet implemented"}, status=status.HTTP_200_OK)


# ===== QC, Delivery, Attachments, Notes, Alerts =====

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))

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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields = ["is_active", "is_superuser"]
    search_fields = ["username", "email", "first_name", "last_name"]

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
        return Response(serializer.data)


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['System & Configuration']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['System & Configuration']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['System & Configuration']))

class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


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


# ===== Dashboard / Analytics =====

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))

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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))

class AnalyticsViewSet(viewsets.ViewSet):
    """
    Expose rich analytics from admin_dashboard.py for Account Manager portal.
    """
    permission_classes = [IsAuthenticated, IsAccountManager | IsAdmin]

    def list(self, request):
        """Return comprehensive analytics data."""
        from .admin_dashboard import (
            get_dashboard_stats,
            get_sales_performance_trend,
            get_top_selling_products,
            get_conversion_metrics,
            get_average_order_value,
            get_revenue_by_category,
            get_profit_margin_data,
            get_time_based_insights,
        )
        from decimal import Decimal
        import json

        # Get all analytics
        dashboard_stats = get_dashboard_stats()
        sales_trend = get_sales_performance_trend(months=6)
        top_products = get_top_selling_products(limit=10)
        conversion_metrics = get_conversion_metrics()
        avg_order_value = get_average_order_value()
        revenue_by_category = get_revenue_by_category()
        profit_margins = get_profit_margin_data()
        time_insights = get_time_based_insights()

        # Format sales trend for JSON serialization
        formatted_sales_trend = []
        for item in sales_trend:
            formatted_sales_trend.append({
                "month": item["month"].strftime("%Y-%m") if hasattr(item["month"], "strftime") else str(item["month"]),
                "revenue": float(item["revenue"]) if isinstance(item["revenue"], Decimal) else item["revenue"],
                "orders": item["orders"],
            })

        return Response({
            "dashboard_stats": dashboard_stats,
            "sales_performance_trend": formatted_sales_trend,
            "top_products": top_products,
            "conversion_metrics": conversion_metrics,
            "average_order_value": float(avg_order_value) if isinstance(avg_order_value, Decimal) else avg_order_value,
            "revenue_by_category": revenue_by_category,
            "profit_margins": {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in profit_margins.items()
            },
            "time_insights": {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in time_insights.items()
            },
        }, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["get"])
    def am_performance(self, request):
        """
        Get personalized AM performance analytics for the logged-in Account Manager.
        Shows conversion rates, total revenue closed, and pending quotes.
        """
        user = request.user
        from decimal import Decimal
        from django.db.models import Sum, Count, Q
        
        # Get all quotes created by this AM
        am_quotes = Quote.objects.filter(created_by=user)
        
        # Total quotes created
        total_quotes = am_quotes.count()
        
        # Approved quotes (revenue closed)
        approved_quotes = am_quotes.filter(status='Approved')
        approved_count = approved_quotes.count()
        
        # Calculate conversion rate
        conversion_rate = (approved_count / total_quotes * 100) if total_quotes > 0 else 0
        
        # Total revenue from approved quotes
        total_revenue = approved_quotes.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        # Pending quotes (not yet approved or lost)
        pending_quotes = am_quotes.filter(status__in=['Draft', 'Sent to PT', 'Costed', 'Sent to Customer'])
        pending_count = pending_quotes.count()
        
        # Lost quotes
        lost_quotes = am_quotes.filter(status='Lost')
        lost_count = lost_quotes.count()
        
        # Total clients managed
        managed_clients = Client.objects.filter(account_manager=user).count()
        
        # Total leads created
        total_leads = Lead.objects.filter(created_by=user).count()
        
        # Converted leads
        converted_leads = Lead.objects.filter(created_by=user, status='Converted').count()
        
        # Lead conversion rate
        lead_conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
        
        return Response({
            "account_manager": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            "quotes": {
                "total": total_quotes,
                "approved": approved_count,
                "pending": pending_count,
                "lost": lost_count,
                "conversion_rate_percent": round(conversion_rate, 2),
                "total_revenue": float(total_revenue),
                "average_quote_value": float(total_revenue / approved_count) if approved_count > 0 else 0,
            },
            "leads": {
                "total": total_leads,
                "converted": converted_leads,
                "conversion_rate_percent": round(lead_conversion_rate, 2),
            },
            "clients": {
                "managed": managed_clients,
            },
            "performance_summary": {
                "status": "strong" if conversion_rate >= 50 else "good" if conversion_rate >= 25 else "needs_improvement",
                "top_metric": f"${float(total_revenue)} in revenue closed" if total_revenue > 0 else "No closed revenue yet",
            }
        })


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Dashboard & Analytics']))

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

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))

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
                "vps_score": pv.vendor.vps_score,
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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))

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


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))

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
            created_at__gte=ninety_days_ago,
            status='completed',
            expected_completion__isnull=False,
            actual_completion__isnull=False
        )
        
        on_time_count = 0
        late_count = 0
        for stage in vendor_stages:
            if stage.actual_completion <= stage.expected_completion:
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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """Shipping Methods"""
    queryset = ShippingMethod.objects.filter(is_active=True)
    serializer_class = ShippingMethodSerializer
    permission_classes = [AllowAny]
    
    filterset_fields = ['carrier', 'pricing_type', 'is_active', 'is_default']
    ordering_fields = ['is_default', 'name']


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

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
        except ValidationError as e:
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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Timeline & Tracking']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Design & Ecommerce']))

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
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Integrations']))

@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Integrations']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Integrations']))

class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookDelivery.objects.all()
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated, IsAdmin]
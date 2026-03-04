"""
Storefront API ViewSets
Product catalog, estimate quotes, customer auth, messaging, chatbot
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal
import uuid
import secrets
import string

from clientapp.models import (
    EstimateQuote, StorefrontCustomer,
    StorefrontMessage, ChatbotConversation, QuotePricingSnapshot,
    ProductionUnit, Lead, Quote, StorefrontProduct
)
from clientapp.storefront_serializers import (
    StorefrontProductSerializer, EstimateQuoteSerializer,
    EstimateQuoteCreateSerializer, StorefrontCustomerSerializer,
    StorefrontCustomerUpdateSerializer, StorefrontMessageSerializer,
    ContactEmailSerializer, ContactWhatsAppSerializer,
    CallRequestSerializer, ChatbotMessageSerializer,
    ChatbotMessageResponseSerializer, ChatbotConversationSerializer,
    ProductionUnitSerializer, ProductionUnitCreateSerializer,
    QuotePricingSnapshotSerializer, CustomerPreferencesSerializer,
    CustomerRegistrationSerializer, EstimateQuoteShareSerializer,
    ProductPriceCalculationSerializer
)
from clientapp.storefront_services import (
    EmailService, MessagingService, TaxService, ChatbotService
)


# ============================================================================
# PRODUCTS & CATALOG
# ============================================================================

class StorefrontProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public product catalog endpoint
    No authentication required
    """
    queryset = StorefrontProduct.objects.filter(storefront_visible=True)
    serializer_class = StorefrontProductSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['category', 'featured']
    search_fields = ['name', 'description_short']
    ordering_fields = ['sort_order', 'rating', 'base_price', 'name']
    ordering = ['sort_order', '-featured']
    
    def get_queryset(self):
        """Filter products"""
        queryset = super().get_queryset()
        
        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            queryset = queryset.filter(base_price__gte=Decimal(min_price))
        if max_price:
            queryset = queryset.filter(base_price__lte=Decimal(max_price))
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description_short__icontains=search)
            )
        
        return queryset.order_by('sort_order', '-featured')
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.AllowAny])
    def calculate_price(self, request, pk=None):
        """Calculate price for product with given options"""
        product = self.get_object()
        serializer = ProductPriceCalculationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        quantity = serializer.validated_data['quantity']
        turnaround = serializer.validated_data['turnaround_time']
        
        # Get unit price based on quantity
        unit_price = product.get_price_for_quantity(quantity)
        
        # Add turnaround surcharge
        surcharge = Decimal('0.00')
        if turnaround == 'rush':
            surcharge = product.turnaround_rush_surcharge * quantity
        elif turnaround == 'expedited':
            surcharge = product.turnaround_expedited_surcharge * quantity
        
        line_total = (unit_price * quantity) + surcharge
        
        # Calculate tax
        tax_amount = TaxService.calculate_tax(line_total)
        total_with_tax = line_total + tax_amount
        
        return Response({
            'product_id': product.product_id,
            'quantity': quantity,
            'unit_price': str(unit_price),
            'surcharge': str(surcharge),
            'subtotal': str(line_total),
            'tax_amount': str(tax_amount),
            'total': str(total_with_tax),
            'turnaround_time': turnaround,
            'tax_rate': str(TaxService.get_tax_rate())
        })


# ============================================================================
# ESTIMATE QUOTES
# ============================================================================

class EstimateQuoteViewSet(viewsets.ModelViewSet):
    """
    Draft/Estimate quotes created from storefront
    Public creation (no auth), AM can access & modify
    """
    queryset = EstimateQuote.objects.all()
    permission_classes = [permissions.AllowAny]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EstimateQuoteCreateSerializer
        return EstimateQuoteSerializer
    
    def create(self, request, *args, **kwargs):
        """Create estimate quote (no auth required)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        estimate = serializer.instance
        
        # Create pricing snapshot
        QuotePricingSnapshot.objects.create(
            estimate_quote=estimate,
            snapshot_type='estimate_created',
            base_amount=estimate.subtotal,
            total_amount=estimate.total_amount
        )
        
        # Return full estimate serializer (includes estimate_id and share_token)
        return_serializer = EstimateQuoteSerializer(estimate)
        return Response(return_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def by_token(self, request):
        """Get estimate by share token (public)"""
        token = request.query_params.get('token')
        if not token:
            return Response(
                {'detail': 'token query param required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            estimate = EstimateQuote.objects.get(share_token=token)
        except EstimateQuote.DoesNotExist:
            return Response(
                {'detail': 'Estimate not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(estimate)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def share(self, request):
        """Share estimate quote via WhatsApp/Email"""
        estimate_id = request.data.get('estimate_id')
        channel = request.data.get('channel')  # 'whatsapp' or 'email'
        recipient = request.data.get('recipient')  # phone or email
        
        if not estimate_id or not channel or not recipient:
            return Response(
                {'detail': 'estimate_id, channel, and recipient required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            estimate = EstimateQuote.objects.get(estimate_id=estimate_id)
        except EstimateQuote.DoesNotExist:
            return Response(
                {'detail': 'Estimate not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Generate share link
        share_link = f"{request.META.get('HTTP_ORIGIN')}/quotes/{estimate.share_token}"
        
        # Update status
        estimate.status = 'shared_with_am'
        estimate.shared_via = channel
        estimate.share_timestamp = timezone.now()
        estimate.save()
        
        # Send via chosen channel
        success = False
        if channel == 'email':
            success = EmailService.send_estimate_shared_email(estimate, recipient, share_link)
        elif channel == 'whatsapp':
            success = MessagingService.send_estimate_via_whatsapp(estimate, recipient, share_link)
        
        if success:
            return Response({
                'success': True,
                'estimate_id': estimate.estimate_id,
                'share_link': share_link,
                'message': f'Estimate shared via {channel}'
            })
        else:
            return Response(
                {'detail': f'Failed to send via {channel}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='share-whatsapp', permission_classes=[permissions.AllowAny])
    def share_whatsapp(self, request, pk=None):
        """Share a specific estimate via WhatsApp (by id)"""
        try:
            estimate = self.get_object()
        except EstimateQuote.DoesNotExist:
            return Response({'detail': 'Estimate not found'}, status=status.HTTP_404_NOT_FOUND)

        recipient = request.data.get('phone')
        if not recipient:
            return Response({'detail': 'phone required'}, status=status.HTTP_400_BAD_REQUEST)

        share_link = f"{request.META.get('HTTP_ORIGIN')}/quotes/{estimate.share_token}"
        success = MessagingService.send_estimate_via_whatsapp(estimate, recipient, share_link)

        if success:
            estimate.status = 'shared_with_am'
            estimate.shared_via = 'whatsapp'
            estimate.share_timestamp = timezone.now()
            estimate.save()
            return Response({'success': True, 'estimate_id': estimate.estimate_id, 'share_link': share_link})
        return Response({'detail': 'Failed to send whatsapp'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='share-email', permission_classes=[permissions.AllowAny])
    def share_email(self, request, pk=None):
        """Share a specific estimate via Email (by id)"""
        try:
            estimate = self.get_object()
        except EstimateQuote.DoesNotExist:
            return Response({'detail': 'Estimate not found'}, status=status.HTTP_404_NOT_FOUND)

        recipient = request.data.get('email')
        if not recipient:
            return Response({'detail': 'email required'}, status=status.HTTP_400_BAD_REQUEST)

        share_link = f"{request.META.get('HTTP_ORIGIN')}/quotes/{estimate.share_token}"
        success = EmailService.send_estimate_shared_email(estimate, recipient, share_link)

        if success:
            estimate.status = 'shared_with_am'
            estimate.shared_via = 'email'
            estimate.share_timestamp = timezone.now()
            estimate.save()
            return Response({'success': True, 'estimate_id': estimate.estimate_id, 'share_link': share_link})
        return Response({'detail': 'Failed to send email'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def convert_to_quote(self, request):
        """
        Convert estimate to official quote (for AM or registered customer)
        Creates Lead and Quote in system
        """
        estimate_id = request.data.get('estimate_id')
        adjust_data = request.data.get('adjustments', {})
        
        try:
            estimate = EstimateQuote.objects.get(estimate_id=estimate_id)
        except EstimateQuote.DoesNotExist:
            return Response(
                {'detail': 'Estimate not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Use adjusted data if provided, else use original
        final_amount = Decimal(str(adjust_data.get('total_amount', estimate.total_amount)))
        
        # Create Lead from customer info
        lead_id = f"LD-{timezone.now().year}-{EstimateQuote.objects.count():05d}"
        lead = Lead.objects.create(
            lead_id=lead_id,
            name=estimate.customer_name,
            email=estimate.customer_email,
            phone=estimate.customer_phone,
            source='Storefront',
            status='Qualified',
            preferred_client_type='B2B'
        )
        
        # Create Quote
        quote = Quote.objects.create(
            quote_id=f"QT-{timezone.now().year}-{Quote.objects.count():05d}",
            lead=lead,
            status='Draft',
            total_amount=final_amount,
            created_by=request.user if request.user.is_authenticated else None,
            source='storefront_shared'
        )
        
        # Archive estimate
        estimate.status = 'converted_to_quote'
        estimate.converted_quote_id = quote.quote_id
        estimate.save()
        
        # Create pricing snapshot
        QuotePricingSnapshot.objects.create(
            estimate_quote=estimate,
            quote_id=quote.quote_id,
            snapshot_type='quote_created',
            base_amount=estimate.subtotal,
            adjustments=adjust_data,
            total_amount=final_amount,
            applied_by=request.user if request.user.is_authenticated else None
        )
        
        return Response({
            'success': True,
            'lead_id': lead.lead_id,
            'quote_id': quote.quote_id,
            'message': 'Estimate converted to official quote'
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive an estimate quote"""
        estimate = self.get_object()
        estimate.archived = True
        estimate.status = 'archived'
        estimate.save()
        
        return Response({
            'success': True,
            'estimate_id': estimate.estimate_id,
            'archived': True,
            'message': 'Estimate archived'
        })
    
    @action(detail=True, methods=['get'])
    def edit(self, request, pk=None):
        """Get estimate data for editing (for AM)"""
        estimate = self.get_object()
        serializer = self.get_serializer(estimate)
        return Response(serializer.data)


# ============================================================================
# CUSTOMER AUTHENTICATION & PROFILES
# ============================================================================

class CustomerRegistrationView(APIView):
    """Register new storefront customer"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Register customer"""
        serializer = CustomerRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user
        user = serializer.save()
        
        # Create storefront customer profile
        customer = StorefrontCustomer.objects.create(
            user=user,
            phone=request.data.get('phone', ''),
            company=request.data.get('company', '')
        )
        
        # Generate email verification token
        verification_token = secrets.token_urlsafe(32)
        
        # Store token in customer profile (you may want to add this field to model)
        # For now, using a simple approach - store in session/cache
        from django.core.cache import cache
        cache.set(f'email_verification_{user.email}', verification_token, 86400)  # 24 hours
        
        # Send verification email
        EmailService.send_email_verification(user, verification_token)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'success': True,
            'message': 'Registration successful. Please verify your email.',
            'user_id': user.id,
            'customer_id': customer.customer_id,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh)
        }, status=status.HTTP_201_CREATED)


class EmailVerificationView(APIView):
    """Verify customer email address"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Verify email with token"""
        token = request.data.get('token')
        email = request.data.get('email')
        
        if not token or not email:
            return Response(
                {'detail': 'token and email required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Check token in cache
            from django.core.cache import cache
            stored_token = cache.get(f'email_verification_{email}')
            
            if not stored_token or stored_token != token:
                return Response(
                    {'detail': 'Invalid or expired verification token'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get user and mark as verified
            user = User.objects.get(email=email)
            customer = StorefrontCustomer.objects.get(user=user)
            customer.email_verified = True
            customer.save()
            
            # Clear token from cache
            cache.delete(f'email_verification_{email}')
            
            return Response({
                'success': True,
                'message': 'Email verified successfully'
            })
        except User.DoesNotExist:
            return Response(
                {'detail': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'detail': f'Verification failed: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PhoneVerificationView(APIView):
    """Send and verify OTP for phone number"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Send OTP to phone number"""
        phone = request.data.get('phone')
        action = request.data.get('action', 'send')  # send or verify
        
        if not phone:
            return Response(
                {'detail': 'phone number required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if action == 'send':
            # Generate OTP
            otp = ''.join(secrets.choice(string.digits) for _ in range(6))
            
            # Store OTP in cache (10 minutes)
            from django.core.cache import cache
            cache.set(f'phone_otp_{phone}', otp, 600)
            
            # Send OTP via SMS
            success = MessagingService.send_otp_sms(phone, otp)
            
            if success:
                return Response({
                    'success': True,
                    'message': f'OTP sent to {phone}'
                })
            else:
                return Response(
                    {'detail': 'Failed to send OTP'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        elif action == 'verify':
            otp_code = request.data.get('otp')
            if not otp_code:
                return Response(
                    {'detail': 'otp required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                from django.core.cache import cache
                stored_otp = cache.get(f'phone_otp_{phone}')
                
                if not stored_otp or stored_otp != otp_code:
                    return Response(
                        {'detail': 'Invalid or expired OTP'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Find customer and mark phone as verified
                try:
                    customer = StorefrontCustomer.objects.get(phone=phone)
                    customer.phone_verified = True
                    customer.save()
                except StorefrontCustomer.DoesNotExist:
                    pass  # Phone not linked to customer yet
                
                # Clear OTP from cache
                cache.delete(f'phone_otp_{phone}')
                
                return Response({
                    'success': True,
                    'message': 'Phone verified successfully'
                })
            except Exception as e:
                return Response(
                    {'detail': f'Verification failed: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )



class CustomerProfileViewSet(viewsets.ViewSet):
    """Customer profile management"""
    permission_classes = [permissions.IsAuthenticated]
    
    def list(self, request):
        """Get current user's profile"""
        try:
            customer = StorefrontCustomer.objects.get(user=request.user)
        except StorefrontCustomer.DoesNotExist:
            return Response(
                {'detail': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = StorefrontCustomerSerializer(customer)
        return Response(serializer.data)
    
    def update(self, request):
        """Update customer profile"""
        try:
            customer = StorefrontCustomer.objects.get(user=request.user)
        except StorefrontCustomer.DoesNotExist:
            return Response(
                {'detail': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = StorefrontCustomerUpdateSerializer(
            customer, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def update_preferences(self, request):
        """Update communication preferences"""
        try:
            customer = StorefrontCustomer.objects.get(user=request.user)
        except StorefrontCustomer.DoesNotExist:
            return Response(
                {'detail': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CustomerPreferencesSerializer(
            customer, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'preferences': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# MESSAGING & CONTACT
# ============================================================================

class ContactEmailView(APIView):
    """Send email to sales"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Send email inquiry"""
        serializer = ContactEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Create message record
        message = StorefrontMessage.objects.create(
            message_type='email_inquiry',
            channel='email',
            customer_name=data['name'],
            customer_email=data['email'],
            customer_phone=data.get('phone', ''),
            subject=data['subject'],
            message_content=data['message'],
            status='new'
        )
        
        # Send confirmation email to customer
        EmailService.send_inquiry_confirmation(message)
        
        # Notify sales team
        EmailService.notify_sales_team_inquiry(message)
        
        return Response({
            'success': True,
            'message_id': message.message_id,
            'message': 'Email sent. Sales team will respond shortly.'
        })


class ContactWhatsAppView(APIView):
    """Initiate WhatsApp contact"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Create WhatsApp contact message"""
        serializer = ContactWhatsAppSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Create message record
        message = StorefrontMessage.objects.create(
            message_type='whatsapp_inquiry',
            channel='whatsapp',
            customer_name=data['name'],
            customer_phone=data['phone'],
            message_content=data['message'],
            status='new'
        )
        
        # Send WhatsApp message
        MessagingService.send_whatsapp_message(
            data['phone'],
            f"Hi {data['name']}, thanks for reaching out! Our team will get back to you soon."
        )
        
        # Notify sales team via email
        EmailService.notify_sales_team_inquiry(message)
        
        return Response({
            'success': True,
            'message_id': message.message_id,
            'whatsapp_link': f"https://wa.me/{data['phone']}"
        })


class CallRequestView(APIView):
    """Request a phone call"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Create call request"""
        serializer = CallRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Create message record
        message = StorefrontMessage.objects.create(
            message_type='call_request',
            channel='phone',
            customer_name=data['name'],
            customer_phone=data['phone'],
            message_content=f"Call request for {data['preferred_time']}",
            status='new'
        )
        
        # Send confirmation SMS/email to customer
        EmailService.send_inquiry_confirmation(message)
        MessagingService.send_whatsapp_message(
            data['phone'],
            f"Hi {data['name']}, we received your call request for {data['preferred_time']}. "
            f"Our team will call you soon!"
        )
        
        # Notify sales team
        EmailService.notify_sales_team_inquiry(message)
        
        return Response({
            'success': True,
            'message_id': message.message_id,
            'message': 'Call request received. Sales team will contact you shortly.'
        })


class StorefrontMessageViewSet(viewsets.ModelViewSet):
    """List and manage storefront messages (for AM)"""
    queryset = StorefrontMessage.objects.all()
    serializer_class = StorefrontMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter messages for assigned AM"""
        from clientapp.storefront_permissions import IsAccountManager
        
        # Check if user is account manager
        is_am = IsAccountManager().has_permission(self.request, self)
        
        if is_am:
            queryset = super().get_queryset()
            # Show assigned to current user or unassigned
            queryset = queryset.filter(
                Q(assigned_to=self.request.user) | Q(assigned_to__isnull=True)
            )
        else:
            # Non-AM users can only see their own messages
            if getattr(self, 'swagger_fake_view', False):
                queryset = StorefrontMessage.objects.none()
            else:
                queryset = StorefrontMessage.objects.filter(
                    customer_email=self.request.user.email
                )
        
        return queryset.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def assign_to_me(self, request, pk=None):
        """Assign message to current user"""
        message = self.get_object()
        message.assigned_to = request.user
        message.status = 'in_progress'
        message.save()
        
        return Response({
            'success': True,
            'assigned_to': message.assigned_to.get_full_name()
        })
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark message as resolved"""
        message = self.get_object()
        message.status = 'resolved'
        message.response_message = request.data.get('response', '')
        message.response_at = timezone.now()
        message.save()
        
        return Response({'success': True, 'status': 'resolved'})


# ============================================================================
# CHATBOT
# ============================================================================

class ChatbotMessageView(APIView):
    """Chatbot message endpoint"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Send message to chatbot"""
        serializer = ChatbotMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        message_text = serializer.validated_data['message']
        conversation_id = serializer.validated_data.get('conversation_id', '')
        
        # Get or create conversation
        if conversation_id:
            try:
                conversation = ChatbotConversation.objects.get(
                    conversation_id=conversation_id
                )
            except ChatbotConversation.DoesNotExist:
                conversation = ChatbotConversation.objects.create(
                    conversation_id=conversation_id,
                    session_id=request.session.get('session_key', str(uuid.uuid4()))
                )
        else:
            conversation = ChatbotConversation.objects.create(
                session_id=request.session.get('session_key', str(uuid.uuid4()))
            )
        
        # Add customer message
        conversation.messages.append({
            'timestamp': timezone.now().isoformat(),
            'sender': 'customer',
            'text': message_text,
            'action': None
        })
        
        # Detect intent and generate response
        intent = ChatbotService.detect_intent(message_text)
        bot_response = ChatbotService.generate_response(intent, message_text)
        suggestions = ChatbotService.get_suggested_actions(intent)
        
        # Add bot response
        conversation.messages.append({
            'timestamp': timezone.now().isoformat(),
            'sender': 'bot',
            'text': bot_response,
            'action': None
        })
        
        conversation.save()
        
        return Response({
            'conversation_id': conversation.conversation_id,
            'response': bot_response,
            'suggestions': suggestions,
            'intent': intent
        })


class ChatbotConversationViewSet(viewsets.ReadOnlyModelViewSet):
    """View chatbot conversations (for analytics)"""
    queryset = ChatbotConversation.objects.all()
    serializer_class = ChatbotConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter conversations - only AM/Staff can view"""
        from clientapp.storefront_permissions import IsAccountManager
        
        is_am = IsAccountManager().has_permission(self.request, self)
        if is_am or self.request.user.is_staff:
            return super().get_queryset()
        
        # Regular users can only see their own conversations
        return ChatbotConversation.objects.filter(
            session_id=self.request.session.get('session_key', '')
        )


# ============================================================================
# PRODUCTION UNITS
# ============================================================================

class ProductionUnitViewSet(viewsets.ModelViewSet):
    """Job production units (for PT)"""
    queryset = ProductionUnit.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProductionUnitCreateSerializer
        return ProductionUnitSerializer
    
    def get_queryset(self):
        """Filter production units for job"""
        from clientapp.storefront_permissions import IsProductionTeam
        
        # Only PT can access production units
        if not IsProductionTeam().has_permission(self.request, self):
            return ProductionUnit.objects.none()
        
        job_id = self.request.query_params.get('job_id')
        if job_id:
            return ProductionUnit.objects.filter(job_id=job_id)
        return super().get_queryset()
    
    @action(detail=True, methods=['post'])
    def send_po(self, request, pk=None):
        """Send PO to vendor"""
        unit = self.get_object()
        
        # Generate PO and send (placeholder)
        unit.status = 'po_sent'
        unit.save()
        
        return Response({
            'success': True,
            'unit_id': unit.unit_id,
            'message': 'PO sent to vendor'
        })
    
    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """Get unit progress"""
        unit = self.get_object()
        
        return Response({
            'unit_id': unit.unit_id,
            'status': unit.status,
            'progress_percentage': self._calculate_progress(unit),
            'timeline': {
                'expected_start': unit.expected_start_date,
                'expected_end': unit.expected_end_date,
                'actual_start': unit.actual_start_date,
                'actual_end': unit.actual_end_date
            }
        })
    
    def _calculate_progress(self, unit):
        """Calculate production unit progress"""
        status_map = {
            'pending_po': 0,
            'po_sent': 25,
            'accepted': 50,
            'in_progress': 75,
            'completed': 100,
            'delayed': 60,
            'cancelled': 0
        }
        return status_map.get(unit.status, 0)


# ============================================================================
# MISSING CRITICAL ENDPOINTS (Quote Management & Customer Account)
# ============================================================================

class CustomerLoginView(APIView):
    """
    Customer login endpoint
    POST /api/v1/customers/login/
    
    Request: {email, password}
    Response: {access_token, refresh_token, user}
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        from django.contrib.auth import authenticate
        
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Authenticate user by email
        try:
            user = User.objects.get(email=email)
            user_obj = authenticate(username=user.username, password=password)
            
            if user_obj is None:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check if email is verified
            customer = StorefrontCustomer.objects.get(user=user_obj)
            if not customer.email_verified:
                return Response(
                    {'error': 'Email not verified. Please verify your email first.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user_obj)
            
            return Response({
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': user_obj.id,
                    'email': user_obj.email,
                    'username': user_obj.username,
                    'first_name': user_obj.first_name,
                    'last_name': user_obj.last_name,
                    'email_verified': customer.email_verified,
                    'phone_verified': customer.phone_verified,
                    'company': customer.company,
                    'customer_type': customer.customer_type,
                }
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except StorefrontCustomer.DoesNotExist:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class CustomerQuotesListView(APIView):
    """
    Get authenticated customer's saved quotes
    GET /api/v1/customer/quotes/
    
    Requires: Authentication (JWT token)
    Response: [Quote objects filtered by customer]
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            customer = StorefrontCustomer.objects.get(user=request.user)
            
            # Get customer's quotes (from lead or direct)
            quotes = Quote.objects.filter(
                Q(customer=customer) | Q(created_by=request.user)
            ).exclude(
                status__in=['archived', 'deleted']
            ).order_by('-created_at')
            
            # Paginate
            page = request.query_params.get('page', 1)
            limit = request.query_params.get('limit', 10)
            
            try:
                page = int(page)
                limit = int(limit)
            except ValueError:
                page, limit = 1, 10
            
            start = (page - 1) * limit
            end = start + limit
            
            total = quotes.count()
            paginated_quotes = quotes[start:end]
            
            # Serialize
            from clientapp.storefront_serializers import QuoteListSerializer
            serializer = QuoteListSerializer(paginated_quotes, many=True)
            
            return Response({
                'count': total,
                'page': page,
                'limit': limit,
                'total_pages': (total + limit - 1) // limit,
                'results': serializer.data
            })
            
        except StorefrontCustomer.DoesNotExist:
            return Response(
                {'error': 'Customer profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class SaveQuoteFromStorefrontView(APIView):
    """
    Convert EstimateQuote to official Quote
    POST /api/v1/quotes/save-from-storefront/
    
    Request: {estimate_id, save_action}
    Response: {quote_id, quote_number, status, lead_id}
    
    This is the CRITICAL endpoint that converts customer estimates
    into official quotes in the system.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        estimate_id = request.data.get('estimate_id')
        save_action = request.data.get('save_action', 'save_only')
        
        if not estimate_id:
            return Response(
                {'error': 'estimate_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get estimate quote
            estimate = EstimateQuote.objects.get(id=estimate_id)
            
            # Create or get Lead from estimate customer info
            lead, created = Lead.objects.get_or_create(
                name=estimate.customer_name,
                phone=estimate.customer_phone,
                defaults={
                    'email': estimate.customer_email,
                    'company': estimate.customer_company or '',
                    'status': 'new',
                    'source': 'storefront_shared'
                }
            )
            
            # Create official Quote
            quote = Quote.objects.create(
                customer=lead,
                status='Draft',
                created_by=request.user if request.user.is_authenticated else None,
                source='storefront_shared',
                total_amount=estimate.total_amount or 0,
            )
            
            # Copy line items from estimate (if stored as JSON or related objects)
            # This assumes estimate stores line items - adjust based on your model
            if hasattr(estimate, 'line_items'):
                # Handle line items copy (implementation depends on EstimateQuote model)
                pass
            
            # Mark estimate as archived
            estimate.archived = True
            estimate.converted_quote = quote
            estimate.status = 'converted_to_quote'
            estimate.save()
            
            # Send notifications via email service
            email_service = EmailService()
            try:
                email_service.notify_sales_team_quote_conversion(quote, estimate)
                email_service.notify_customer_quote_received(estimate, quote)
            except Exception as e:
                # Don't fail if notification fails
                pass
            
            # Create activity log
            from clientapp.models import ActivityLog
            ActivityLog.objects.create(
                content_type_id=None,
                user=request.user if request.user.is_authenticated else None,
                action=f'Converted EstimateQuote #{estimate_id} to Quote #{quote.id}',
                change_message=f'Customer estimate converted to official quote'
            )
            
            return Response({
                'quote_id': quote.id,
                'quote_number': getattr(quote, 'quote_id', f'QT-{quote.id}'),
                'status': quote.status,
                'lead_id': lead.id,
                'lead_name': lead.name,
                'amount_total': float(quote.total_amount),
                'created_at': quote.created_at.isoformat() if quote.created_at else None,
            }, status=status.HTTP_201_CREATED)
            
        except EstimateQuote.DoesNotExist:
            return Response(
                {'error': f'EstimateQuote with id {estimate_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class ChatbotKnowledgeView(APIView):
    """
    Get chatbot knowledge base
    GET /api/v1/chatbot/knowledge/
    
    Returns product catalog, FAQs, company info for chatbot training
    No authentication required
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        from django.conf import settings
        
        # Get products
        products = StorefrontProduct.objects.filter(
            storefront_visible=True
        ).values('id', 'name', 'description', 'base_price')
        
        # Get FAQs
        faqs = []
        try:
            from clientapp.models import ProductFAQ
            faqs_qs = ProductFAQ.objects.all().values('question', 'answer')
            faqs = list(faqs_qs)
        except:
            pass
        
        # Company info
        company_info = {
            'name': getattr(settings, 'COMPANY_NAME', 'Our Company'),
            'phone': getattr(settings, 'COMPANY_PHONE', '+254701234567'),
            'email': getattr(settings, 'COMPANY_EMAIL', 'info@company.com'),
            'address': getattr(settings, 'COMPANY_ADDRESS', ''),
            'turnaround_standard_days': getattr(settings, 'TURNAROUND_STANDARD_DAYS', 7),
            'turnaround_rush_days': getattr(settings, 'TURNAROUND_RUSH_DAYS', 3),
            'turnaround_expedited_days': getattr(settings, 'TURNAROUND_EXPEDITED_DAYS', 1),
        }
        
        return Response({
            'products': list(products),
            'faqs': faqs,
            'company_info': company_info,
            'intents': [
                'product_inquiry', 'pricing', 'order_status',
                'contact_sales', 'custom_quote', 'delivery_info',
                'payment_terms', 'customization_options'
            ]
        })


# ============================================================================
# FRONTEND TEMPLATE VIEWS (HTML Page Serving)
# ============================================================================

from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class StorefrontBaseTemplateView(TemplateView):
    """
    Base view for storefront frontend pages.
    CSRF is exempt because frontend uses token-based authentication (JWT).
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['api_base_url'] = '/api/v1'
        return context


class StorefrontHomeView(StorefrontBaseTemplateView):
    """Home/Landing page - product features and CTA"""
    template_name = 'index.html'


class StorefrontProductsPageView(StorefrontBaseTemplateView):
    """Product catalog page - browse, search, filter products"""
    template_name = 'products.html'


class StorefrontLoginPageView(StorefrontBaseTemplateView):
    """Customer login page"""
    template_name = 'login.html'


class StorefrontRegisterPageView(StorefrontBaseTemplateView):
    """Customer registration page"""
    template_name = 'register.html'


class StorefrontQuoteBuilderPageView(StorefrontBaseTemplateView):
    """Interactive quote builder page - create estimates"""
    template_name = 'quote-builder.html'


class StorefrontContactPageView(StorefrontBaseTemplateView):
    """Contact/Support page - multi-channel inquiry form"""
    template_name = 'contact.html'


class StorefrontDashboardPageView(StorefrontBaseTemplateView):
    """Customer dashboard page - profile, estimates, quotes, messages"""
    template_name = 'dashboard.html'

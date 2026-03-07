import decimal
import json
import uuid
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.core.exceptions import ValidationError
from functools import wraps
from django.contrib.auth import login
from django.contrib.auth.models import User, Group
from .models import BrandAsset

# WebSocket real-time updates (imported safely)
try:
    from .websocket_helpers import (
        broadcast_job_update,
        broadcast_dashboard_update,
        broadcast_substitution_update,
        send_job_assigned_notification,
        send_substitution_approved_notification,
        send_substitution_rejected_notification,
        send_invoice_status_notification,
        send_deadline_approaching_notification,
    )
except ImportError:
    # Channels not installed yet, define dummy functions
    def broadcast_job_update(*args, **kwargs): pass
    def broadcast_dashboard_update(*args, **kwargs): pass
    def broadcast_substitution_update(*args, **kwargs): pass
    def send_job_assigned_notification(*args, **kwargs): pass
    def send_substitution_approved_notification(*args, **kwargs): pass
    def send_substitution_rejected_notification(*args, **kwargs): pass
    def send_invoice_status_notification(*args, **kwargs): pass
    def send_deadline_approaching_notification(*args, **kwargs): pass

logger = logging.getLogger(__name__)
from django.core.paginator import Paginator



from .forms import (
    LeadForm,
    ClientForm,
    QuoteCostingForm,
    ProductionUpdateForm,
    VendorForm,
)

from .models import (
    Lead,
    Client,
    ClientContact,
    ClientPortalUser,
    ComplianceDocument,
    Product,
    Quote,
    QuoteLineItem,
    ActivityLog,
    ProductionUpdate,
    Notification,
    Job,
    JobProduct,
    JobReminder,
    JobMessage,
    JobNote,
    ProductTag,
    LPO,
    LPOLineItem,
    SystemAlert,
    ProcessVariableRange,
    Process,
    Vendor,
    Payment,
    VendorInvoice,
)

# Import comprehensive CRUD API endpoints
from .admin_api import (
    api_admin_leads,
    api_admin_lead_detail,
    api_admin_products,
    api_admin_product_detail,
    api_admin_vendors,
    api_admin_vendor_detail,
    api_admin_lpos,
    api_admin_payments,
    api_admin_qc_inspections,
    api_admin_deliveries,
    api_admin_create_user,
    api_admin_get_user,
    api_admin_update_user,
    api_admin_delete_user,
    api_admin_create_client,
    api_admin_get_client,
    api_admin_update_client,
    api_admin_delete_client,
    api_admin_create_lead,
    api_admin_get_lead,
    api_admin_update_lead,
    api_admin_delete_lead,
    api_admin_create_quote,
    api_admin_get_quote,
    api_admin_update_quote,
    api_admin_delete_quote,
    api_admin_create_product,
    api_admin_get_product,
    api_admin_update_product,
    api_admin_delete_product,
)

# Import admin dashboard views
from .admin_views import (
    admin_dashboard,
    clients_list,
    leads_list,
    quotes_list,
    products_list,
    jobs_list,
    vendors_list,
    processes_list,
    qc_list,
    deliveries_list,
    lpos_list,
    payments_list,
    analytics_view,
    users_list,
    get_object_detail,
    create_object,
    update_object,
    delete_object,
)

def notification_count_processor(request):
    """Add unread notification count to all templates"""
    if request.user.is_authenticated:
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return {'unread_notifications_count': unread_count}
    return {'unread_notifications_count': 0}

from clientapp.quote_approval_services import QuoteApprovalService
def send_quote_email(quote_id, request):
    """
    Send quote to client via email with approval link
    """
    from clientapp.quote_approval_services import QuoteApprovalService
    
    try:
        # Get quote
        quotes = Quote.objects.filter(quote_id=quote_id)
        if not quotes.exists():
            return {'success': False, 'message': 'Quote not found'}
        
        first_quote = quotes.first()
        
        # Sending email to generate token
        result = QuoteApprovalService.send_quote_via_email(first_quote, request)
        
        return result
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'message': str(e)}

def group_required(group_name, allow_superuser=False):
    """
    Require authenticated user to belong to group_name.
    Redirect anonymous users to login, and show a friendly redirect for
    authenticated users without permission.
    """
    login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(f"{login_url}?next={request.get_full_path()}")
            if allow_superuser and user.is_superuser:
                return view_func(request, *args, **kwargs)
            if user.groups.filter(name=group_name).exists():
                return view_func(request, *args, **kwargs)

            messages.warning(request, "You don't have access to that section.")
            if user.groups.filter(name='Production Team').exists():
                return redirect(reverse('production2_dashboard'))
            elif user.groups.filter(name='Account Manager').exists():
                return redirect(reverse('dashboard'))
            else:
                # User has no recognized group → send to login
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("Access denied. Please contact administrator.")

        return _wrapped
    return decorator


@login_required
def search(request):
    """Global search for clients, leads, quotes, and jobs"""
    q = request.GET.get('q', '').strip()
    clients = leads = quotes = jobs = []
    if q:
        clients = Client.objects.filter(
            Q(name__icontains=q) | Q(company__icontains=q) | Q(email__icontains=q) | Q(client_id__icontains=q)
        ).order_by('name')[:25]
        leads = Lead.objects.filter(
            Q(name__icontains=q) | Q(email__icontains=q) | Q(lead_id__icontains=q)
        ).order_by('-created_at')[:25]
        quotes = Quote.objects.filter(
            Q(quote_id__icontains=q) | Q(product_name__icontains=q)
        ).select_related('client', 'lead').order_by('-created_at')[:25]
        jobs = Job.objects.filter(
            Q(job_number__icontains=q) | Q(job_name__icontains=q) | Q(product__icontains=q)
        ).select_related('client').order_by('-created_at')[:25]

    context = {
        'q': q,
        'clients': clients,
        'leads': leads,
        'quotes': quotes,
        'jobs': jobs,
        'current_view': 'search',
    }
    return render(request, 'search_results.html', context)


@login_required
@group_required('Account Manager')
def edit_client(request, pk):
    """Edit client details (Account Manager) - Dynamic B2B/B2C form"""
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Client updated successfully.')
            return redirect('client_profile', pk=client.pk)
    else:
        form = ClientForm(instance=client)

    # Gather B2B-specific data if client is B2B
    context = {
        'form': form,
        'client': client,
        'current_view': 'clients',
    }

    if client.client_type == 'B2B':
        # Fetch contacts for this B2B client
        contacts = ClientContact.objects.filter(client=client).order_by('-is_primary', 'full_name')
        context['contacts'] = contacts

        # Fetch brand assets for this B2B client
        brand_assets = BrandAsset.objects.filter(client=client).order_by('asset_type', '-uploaded_at')
        context['brand_assets'] = brand_assets

        # Fetch compliance documents for this B2B client
        compliance_docs = ComplianceDocument.objects.filter(client=client).order_by('-uploaded_at')
        context['compliance_documents'] = compliance_docs

    return render(request, 'client_edit.html', context)


    

def group_required(group_name, allow_superuser=False):
    """
    Require authenticated user to belong to group_name.
    - redirects anonymous users to settings.LOGIN_URL (with ?next=...)
    - returns 403 for authenticated users not in the group
    - allow_superuser=False by default so superusers do NOT bypass unless you opt in
    """
    login_url = getattr(settings, 'LOGIN_URL', '/accounts/login/')

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect(f"{login_url}?next={request.get_full_path()}")
            if allow_superuser and user.is_superuser:
                return view_func(request, *args, **kwargs)
            if user.groups.filter(name=group_name).exists():
                return view_func(request, *args, **kwargs)

            #redirect instead of 403
            messages.warning(request, "You don't have access to that section.")

            # Determine best fallback based on user's groups
            fallback_name = 'dashboard'
            if user.groups.filter(name='Production Team').exists():
                fallback_name = 'production2_dashboard'
            elif user.groups.filter(name='Account Manager').exists():
                fallback_name = 'dashboard'

            return redirect(reverse(fallback_name))
        return _wrapped
    return decorator

@login_required
@group_required('Account Manager')
def dashboard(request):
    """Account Manager Dashboard - Matches original template structure"""
    from datetime import timedelta
    from django.db.models import Count, Sum, Q
    from decimal import Decimal
    
    # Date ranges
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    thirty_days_ago = today - timedelta(days=30)
  
    
        # Total leads 
    total_leads = Lead.objects.all().count()
    
    # Converted leads 
    converted_leads = Lead.objects.filter(status='Converted').count()
    
    # Active clients
    active_clients = Client.objects.filter(account_manager=request.user, status='Active').count()
    
    # B2B and B2C clients
    b2b_clients = Client.objects.filter(account_manager=request.user, client_type='B2B').count()
    b2c_clients = Client.objects.filter(account_manager=request.user, client_type='B2C').count()
    
    # ========== JOB METRICS ==========
    total_jobs = Job.objects.filter(client__account_manager=request.user).count()
    pending_jobs = Job.objects.filter(client__account_manager=request.user, status='pending').count()
    in_progress_jobs = Job.objects.filter(client__account_manager=request.user, status='in_progress').count()
    completed_jobs = Job.objects.filter(client__account_manager=request.user, status='completed').count()
    
    # ========== QUOTE METRICS ==========
    # Total quotes
    total_quotes = Quote.objects.filter(created_by=request.user).values('quote_id').distinct().count()
    
    # Draft quotes
    draft_quotes = Quote.objects.filter(created_by=request.user, status='Draft').values('quote_id').distinct().count()
    
    # Pending/Quoted
    pending_quotes = Quote.objects.filter(
        created_by=request.user, 
        status__in=['Quoted', 'Client Review']
    ).values('quote_id').distinct().count()
    
    # Approved quotes
    approved_quotes = Quote.objects.filter(created_by=request.user, status='Approved').values('quote_id').distinct().count()
    
    # Total revenue (from approved quotes)
    total_revenue = Quote.objects.filter(
        created_by=request.user,
        status='Approved'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Conversion rate
    conversion_rate = round((approved_quotes / total_quotes * 100), 1) if total_quotes > 0 else 0
    
    # ========== MY PERSONAL KPIs ==========
    my_quotes_this_month = Quote.objects.filter(
        created_by=request.user,
        created_at__gte=this_month_start
    ).values('quote_id').distinct().count()
    
    my_quotes_won = Quote.objects.filter(
        created_by=request.user,
        status='Approved',
        created_at__gte=this_month_start
    ).values('quote_id').distinct().count()
    
    my_clients_this_month = Client.objects.filter(
        account_manager=request.user,
        created_at__gte=this_month_start
    ).count()
    
    my_revenue = Quote.objects.filter(
        created_by=request.user,
        status='Approved',
        created_at__gte=this_month_start
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    my_win_rate = round((my_quotes_won / my_quotes_this_month * 100), 1) if my_quotes_this_month > 0 else 0
    
    # Changes from last period
    quotes_change = 0
    clients_change = 0
    revenue_change = Decimal('0')
    clients_change_abs = 0
    quotes_change_abs = 0
    revenue_change_abs = 0
    
    # ========== RECENT ITEMS ==========
    recent_quotes = Quote.objects.filter(
        created_by=request.user
    ).select_related('client', 'lead').order_by('-created_at')[:5]
    
    recent_clients = Client.objects.filter(
        account_manager=request.user
    ).order_by('-created_at')[:5]
    
    # ========== UPCOMING ACTIONS ==========
    upcoming_actions = []
    
    # Get quotes that need follow-up
    follow_up_quotes = Quote.objects.filter(
        created_by=request.user,
        status='Quoted',
        created_at__gte=timezone.now() - timedelta(days=7)
    ).select_related('client', 'lead')[:3]
    
    for quote in follow_up_quotes:
        client_name = quote.client.name if quote.client else (quote.lead.name if quote.lead else 'Unknown')
        upcoming_actions.append({
            'type': 'quote',
            'icon_color': 'blue',
            'title': 'Follow Up Quote',
            'description': f'Quote #{quote.quote_id} - {quote.product_name}',
            'client': client_name,
            'due_date': quote.created_at + timedelta(days=3),
            'time': (quote.created_at + timedelta(days=3)).strftime('%I:%M %p'),
        })
    
    # ========== RECENT ACTIVITY ==========
    recent_activity = []
    
    # Recent clients added
    for client in recent_clients[:3]:
        time_diff = timezone.now() - client.created_at
        recent_activity.append({
            'client': client.name,
            'action': 'New Client Onboarded',
            'time': format_time_diff(time_diff),
            'type': 'Client'
        })
    
    # Recent quotes
    for quote in recent_quotes[:3]:
        time_diff = timezone.now() - quote.created_at
        client_name = quote.client.name if quote.client else (quote.lead.name if quote.lead else 'Unknown')
        recent_activity.append({
            'client': client_name,
            'action': f'Quote {quote.quote_id} Created',
            'time': format_time_diff(time_diff),
            'type': 'Quote'
        })
    
    # ========== TOP PRODUCTS ==========
    top_products = Quote.objects.filter(
        created_by=request.user,
        status='Approved'
    ).values('product_name').annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    # ========== NOTIFICATIONS ==========
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]
    
    unread_notifications_count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    
    context = {
        'current_view': 'dashboard',
        
        # Lead/Client Metrics
        'total_leads': total_leads,
        'converted_leads': converted_leads,
        'active_clients': active_clients,
        'b2b_clients': b2b_clients,
        'b2c_clients': b2c_clients,
        
        # Production Metrics
        'total_jobs': total_jobs,
        'pending_jobs': pending_jobs,
        'in_progress_jobs': in_progress_jobs,
        'completed_jobs': completed_jobs,
        
        # Quote Metrics
        'total_quotes': total_quotes,
        'draft_quotes': draft_quotes,
        'pending_quotes': pending_quotes,
        'approved_quotes': approved_quotes,
        'total_revenue': total_revenue,
        'conversion_rate': conversion_rate,
        
        # Personal KPIs
        'my_new_clients': my_clients_this_month,
        'clients_change': clients_change,
        'clients_change_abs': clients_change_abs,
        'my_win_rate': my_win_rate,
        'my_quotes_sent': my_quotes_this_month,
        'quotes_change': quotes_change,
        'quotes_change_abs': quotes_change_abs,
        'my_revenue': my_revenue,
        'revenue_change': revenue_change,
        'revenue_change_abs': revenue_change_abs,
        
        # Activity & History
        'recent_activity': recent_activity,
        'recent_quotes': recent_quotes,
        'recent_clients': recent_clients,
        'top_products': top_products,
        'upcoming_actions': upcoming_actions,
        
        # Notifications
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        
        # New Dashboard Sections
        'jobs_nearing_deadline': Job.objects.filter(
            client__account_manager=request.user,
            status__in=['pending', 'in_progress'],
            expected_completion__lte=timezone.now().date() + timedelta(days=5),
            expected_completion__gte=timezone.now().date()
        ).select_related('client').order_by('expected_completion')[:5],
        'active_jobs_count': pending_jobs + in_progress_jobs,
        

    }
    
    return render(request, 'dashboard.html', context)


def format_time_diff(time_diff):
    """Helper function to format time differences"""
    if time_diff.days > 0:
        return f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
    elif time_diff.seconds // 3600 > 0:
        hours = time_diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    else:
        minutes = time_diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"


# ========== ACCOUNT MANAGER VIEWS ==========

@group_required('Account Manager')
def quote_management(request):
    """
    Quote Management - Account Manager only
    This is the ONLY view under Production tab for AM
    """
    from django.db.models import Count, Sum
    from decimal import Decimal
    
    # Get all quotes with aggregations
    all_quotes = Quote.objects.select_related('client', 'lead', 'created_by').order_by('-created_at')
    
    # Filter by status 
    status_filter = request.GET.get('status', 'All')
    if status_filter != 'All':
        all_quotes = all_quotes.filter(status=status_filter)
    
    # Group quotes by quote_id
    quotes_dict = {}
    for quote in all_quotes:
        if quote.quote_id not in quotes_dict:
            quotes_dict[quote.quote_id] = {
                'quote': quote,
                'items': [],
                'total_amount': Decimal('0'),
                'subtotal': Decimal('0'),
                'discount_total': Decimal('0'),
                'tax_total': Decimal('0'),
                'shipping_charges': Decimal('0'),
                'adjustment_amount': Decimal('0')
            }
        quotes_dict[quote.quote_id]['items'].append(quote)
        # Use stored totals from the Quote model
        quotes_dict[quote.quote_id]['total_amount'] = quote.total_amount
        quotes_dict[quote.quote_id]['subtotal'] = quote.subtotal
        quotes_dict[quote.quote_id]['discount_total'] = quote.discount_total
        quotes_dict[quote.quote_id]['tax_total'] = quote.tax_total
        quotes_dict[quote.quote_id]['shipping_charges'] = quote.shipping_charges
        quotes_dict[quote.quote_id]['adjustment_amount'] = quote.adjustment_amount
    
    quotes_list = list(quotes_dict.values())
    
    # Quote statistics
    quote_stats = {
        'total': len(quotes_list),
        'draft': Quote.objects.filter(status='Draft').values('quote_id').distinct().count(),
        'quoted': Quote.objects.filter(status='Quoted').values('quote_id').distinct().count(),
        'approved': Quote.objects.filter(status='Approved').values('quote_id').distinct().count(),
        'lost': Quote.objects.filter(status='Lost').values('quote_id').distinct().count(),
    }
    
    # Calculate total values using stored totals
    total_value = sum(q['total_amount'] for q in quotes_list)
    approved_value = Quote.objects.filter(status='Approved').aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    clients = Client.objects.filter(status='Active').order_by('name')
    leads = Lead.objects.exclude(status__in=['Converted', 'Lost']).order_by('name')
    products = Product.objects.filter(is_visible=True).order_by('name')

    # Calculate Average Margin
    total_revenue_all = 0
    total_cost_all = 0
    for q_dict in quotes_list:
        # Sum up for all items 
        for item in q_dict['items']:
            total_revenue_all += item.total_amount
            total_cost_all += (item.production_cost or Decimal('0'))
            
    avg_margin = 0
    if total_revenue_all > 0:
        avg_margin = ((total_revenue_all - total_cost_all) / total_revenue_all) * 100

    context = {
        'current_view': 'quote_management',
        'quotes': quotes_list,
        'quote_stats': quote_stats,
        'status_filter': status_filter,
        'total_value': total_value,
        'approved_value': approved_value,
        'avg_margin': avg_margin,
        'clients': clients,
        'leads': leads,
        'products': products,
    }
    
    return render(request, 'quote_management.html', context)


@login_required
@group_required('Account Manager')
def create_multi_quote(request):
    """
    Create a new quote from the multi-product quotes modal form
    """
    if request.method == 'POST':
        try:
            from decimal import Decimal
            from django.contrib import messages
            
            # Get form data
            quote_type = request.POST.get('quote_type')
            client_id = request.POST.get('client_id')
            lead_id = request.POST.get('lead_id')
            product_id = request.POST.get('product')
            quantity = int(request.POST.get('quantity', 1))
            unit_price = Decimal(request.POST.get('unit_price', '0'))
            notes = request.POST.get('notes', '')
            
            # Validate required fields
            if not product_id:
                messages.error(request, 'Please select a product')
                return redirect('quote_management')
            
            if not (client_id or lead_id):
                messages.error(request, 'Please select a client or lead')
                return redirect('quote_management')
            
            # Get the product
            product = Product.objects.get(id=product_id)
            
            # Create the quote
            quote = Quote.objects.create(
                client_id=client_id if quote_type == 'client' else None,
                lead_id=lead_id if quote_type == 'lead' else None,
                product=product,
                product_name=product.name,
                quantity=quantity,
                unit_price=unit_price,
                notes=notes,
                status='Draft',
                created_by=request.user,
            )
            
            messages.success(request, f'Quote {quote.quote_id} created successfully!')
            return redirect('quote_detail', quote_id=quote.quote_id)
            
        except Product.DoesNotExist:
            messages.error(request, 'Selected product not found')
            return redirect('quote_management')
        except Exception as e:
            messages.error(request, f'Error creating quote: {str(e)}')
            return redirect('quote_management')
    
    return redirect('quote_management')



@login_required
@group_required('Account Manager')
def analytics(request):
    """Vendor Performance Analytics Dashboard"""
    # Check permission
    if not (request.user.groups.filter(name='Account Manager').exists() or request.user.is_superuser):
        return redirect('login')
    
    context = {
        'current_view': 'analytics',
        'page_title': 'Vendor Performance Analytics',
    }
    
    return render(request, 'account_manager/analytics_dashboard.html', context)


@group_required('Account Manager')
def product_catalog(request):
    """Product catalog view for account managers (read-only) - returns only published products"""

    search = request.GET.get('search', '').strip()
    product_type = request.GET.get('product_type', 'all')
    availability = request.GET.get('availability', 'all')
    category = request.GET.get('category', 'all')
    customization = request.GET.get('customization', 'all')
    stock_status = request.GET.get('stock_status', 'all')
    status = request.GET.get('status', 'all')

    # Only show published and visible products
    products = Product.objects.filter(
        status='published',
        is_visible=True
    )

    if search:
        products = products.filter(Q(name__icontains=search) | Q(internal_code__icontains=search))

    if product_type != 'all':
        products = products.filter(product_type=product_type)

    if availability != 'all':
        products = products.filter(availability=availability)
    
    if category != 'all':
        products = products.filter(primary_category=category)
    
    if customization != 'all':
        products = products.filter(customization_level=customization)
    
    if stock_status != 'all':
        products = products.filter(stock_status=stock_status)
    
    if status != 'all':
        products = products.filter(status=status)
    
    context = {
        'current_view': 'product_catalog',
        'products': products.order_by('name'),
        'search': search,
        'product_type': product_type,
        'availability': availability,
        'selected_category': category,
        'selected_status': status,
    }
    
    return render(request, 'product_catalog.html', context)



@login_required
@group_required('Account Manager')
def account_manager_jobs_list(request):
    """List of jobs for Account Manager - Enhanced with messaging & reminders"""
    jobs = Job.objects.filter(
        client__account_manager=request.user
    ).exclude(status='completed').select_related('client', 'person_in_charge').order_by('-created_at')
    
    # Calculate metrics
    overdue_count = 0
    for job in jobs:
        # Check for delivery status
        try:
            if hasattr(job, 'delivery') and job.delivery.status == 'delivered':
                job.delivery_status = 'delivered'
            else:
                job.delivery_status = None
        except:
            job.delivery_status = None
            
        # Check if overdue
        if job.expected_completion and job.expected_completion < timezone.now().date() and job.status not in ['completed']:
            job.is_overdue = True
            overdue_count += 1
        else:
            job.is_overdue = False

    context = {
        'jobs': jobs,
        'overdue_count': overdue_count,
        'current_view': 'jobs',
    }
    return render(request, 'account_manager/jobs_list_enhanced.html', context)

@login_required
@group_required('Account Manager')
def job_assignment_board(request):
    """Kanban-style job assignment board for Account Managers"""
    # Get all jobs for this account manager
    jobs = Job.objects.filter(
        client__account_manager=request.user
    ).exclude(status='completed').select_related('client', 'person_in_charge').order_by('-created_at')
    
    # Get production users for assignment dropdown
    production_group = Group.objects.filter(name='Production Team').first()
    production_users = production_group.user_set.all() if production_group else []
    
    # Separate jobs by status and assignment
    unassigned_jobs = []
    assigned_jobs = []
    in_progress_jobs = []
    
    for job in jobs:
        # Calculate days remaining
        if job.expected_completion:
            job.days_remaining = (job.expected_completion - timezone.now().date()).days
            job.is_overdue = job.days_remaining < 0
        else:
            job.days_remaining = None
            job.is_overdue = False
        
        # Categorize
        if not job.person_in_charge:
            unassigned_jobs.append(job)
        elif job.status == 'in_progress':
            in_progress_jobs.append(job)
        else:
            assigned_jobs.append(job)
    
    # Count jobs by status
    stats = {
        'total': jobs.count(),
        'unassigned': len(unassigned_jobs),
        'assigned': len(assigned_jobs),
        'in_progress': len(in_progress_jobs),
    }
    
    context = {
        'unassigned_jobs': unassigned_jobs,
        'assigned_jobs': assigned_jobs,
        'in_progress_jobs': in_progress_jobs,
        'unassigned_count': len(unassigned_jobs),
        'assigned_count': len(assigned_jobs),
        'in_progress_count': len(in_progress_jobs),
        'stats': stats,
        'production_users': production_users,
        'current_view': 'jobs',
    }
    
    return render(request, 'account_manager/job_assignment_board.html', context)

#Job management for account manager
@login_required
@group_required('Account Manager')
def account_manager_job_detail(request, pk):
    """Job detail view for Account Manager"""
    job = get_object_or_404(Job, pk=pk)
    
    # Get production users
    production_group = Group.objects.filter(name='Production Team').first()
    production_users = production_group.user_set.all() if production_group else []
    
    # Calculate metrics
    days_active = (timezone.now().date() - job.start_date).days
    days_remaining = (job.expected_completion - timezone.now().date()).days if job.expected_completion else 0
    
    # Check if overdue
    job.is_overdue = False
    if job.expected_completion and job.expected_completion < timezone.now().date() and job.status != 'completed':
        job.is_overdue = True

    context = {
        'job': job,
        'production_users': production_users,
        'days_active': max(0, days_active),
        'days_remaining': days_remaining,
        'current_view': 'jobs',
    }
    return render(request, 'account_manager/job_detail.html', context)


@login_required
@group_required('Account Manager')
def account_manager_job_update(request, pk):
    """Update job assignment and status"""
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        person_in_charge = request.POST.get('person_in_charge')
        status = request.POST.get('status')
        
        if person_in_charge:
            job.person_in_charge = person_in_charge
        
        if status:
            job.status = status
            
        job.save()
        messages.success(request, f'Job {job.job_number} updated successfully.')
        
    return redirect('account_manager_job_detail', pk=pk)


@login_required
@group_required('Account Manager')
def account_manager_send_reminder(request, pk):
    """Send reminder to production team"""
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        # Create notification for production team
                
        production_group = Group.objects.filter(name='Production Team').first()
        if production_group:
            recipients = production_group.user_set.all()
            
            
            if job.person_in_charge:
                specific_user = User.objects.filter(
                    Q(username__iexact=job.person_in_charge) | 
                    Q(first_name__icontains=job.person_in_charge) | 
                    Q(last_name__icontains=job.person_in_charge)
                ).first()
                if specific_user:
                    recipients = [specific_user]
            
            for recipient in recipients:
                Notification.objects.create(
                    recipient=recipient,
                    notification_type='job_reminder',
                    title=f' Reminder: {job.job_name}',
                    message=f'Reminder for job {job.job_number} ({job.client.name}). Due date: {job.expected_completion}. Please update status.',
                    link=f'/job/{job.pk}/', # Link to PT job detail
                    related_job=job
                )
            
            messages.success(request, f'Reminder sent to production team for {job.job_number}.')
        else:
            messages.warning(request, 'No production team members found to notify.')
            
    return redirect('account_manager_job_detail', pk=pk)


# ==================== JOB INTERACTION APIs (AJAX Endpoints) ====================

@login_required
@group_required('Account Manager')
def api_assign_job(request, job_id):
    """API endpoint to assign job to production team member"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        job = Job.objects.get(pk=job_id)
        user_id = request.POST.get('user_id')
        assignment_notes = request.POST.get('assignment_notes', '')
        remind_days = request.POST.get('remind_days_before', 2)
        
        assigned_user = User.objects.get(pk=user_id)
        
        # Assign job
        job.person_in_charge = assigned_user
        job.assignment_notes = assignment_notes
        job.remind_days_before = int(remind_days)
        job.save()
        
        # Create notification for assigned user
        Notification.objects.create(
            recipient=assigned_user,
            notification_type='job_assigned',
            title=f'🎯 Job Assigned: {job.job_name}',
            message=f'You have been assigned to job {job.job_number} for {job.client.name}. Due: {job.expected_completion}',
            link=f'/job/{job.pk}/',
            related_job=job
        )
        
        # Create job message with assignment notes
        if assignment_notes:
            JobMessage.objects.create(
                job=job,
                sender=request.user,
                recipient=assigned_user,
                message_type='instruction',
                content=f'Assignment Notes:\n{assignment_notes}'
            )
        
        # ✨ WebSocket: Broadcast job assignment to all connected clients
        broadcast_job_update(
            job_id=job.id,
            update_type='status_changed',
            data={
                'status': 'assigned',
                'assigned_to': assigned_user.get_full_name(),
                'assigned_at': timezone.now().isoformat(),
                'assignment_notes': assignment_notes
            }
        )
        
        # ✨ WebSocket: Update assigned user's dashboard job count
        broadcast_dashboard_update(
            dashboard_type='jobs',
            user_id=assigned_user.id,
            type='job_count_updated',
            data={
                'total_jobs': Job.objects.filter(person_in_charge=assigned_user).count(),
                'pending_jobs': Job.objects.filter(
                    person_in_charge=assigned_user,
                    status='pending'
                ).count(),
                'in_progress_jobs': Job.objects.filter(
                    person_in_charge=assigned_user,
                    status='in_progress'
                ).count()
            }
        )
        
        # ✨ WebSocket: Send job assignment notification to assigned user
        send_job_assigned_notification(
            user_id=assigned_user.id,
            job_id=job.id,
            job_number=job.job_number,
            priority=getattr(job, 'priority', 'normal')
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Job assigned to {assigned_user.get_full_name()} with real-time update',
            'assigned_to': assigned_user.get_full_name()
        })
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@group_required('Account Manager')
def api_send_job_reminder(request, job_id):
    """API endpoint to send reminder to job assignee"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        job = Job.objects.get(pk=job_id)
        reminder_message = request.POST.get('reminder_message', '')
        
        if not job.person_in_charge:
            return JsonResponse({'error': 'Job not assigned to anyone'}, status=400)
        
        # Calculate days until deadline
        days_until = (job.expected_completion - timezone.now().date()).days if job.expected_completion else 0
        
        # Create reminder record
        reminder = JobReminder.objects.create(
            job=job,
            sent_to_user=job.person_in_charge,
            sent_by_user=request.user,
            reminder_message=reminder_message,
            days_until_deadline=days_until
        )
        
        # Create notification for assigned user
        Notification.objects.create(
            recipient=job.person_in_charge,
            notification_type='job_reminder',
            title=f'⏰ Reminder: {job.job_name}',
            message=f'Reminder from {request.user.get_full_name()}: {reminder_message[:100]}...',
            link=f'/job/{job.pk}/',
            related_job=job
        )
        
        # Create message record
        JobMessage.objects.create(
            job=job,
            sender=request.user,
            recipient=job.person_in_charge,
            message_type='update',
            content=f'📌 REMINDER ({days_until} days to deadline):\n{reminder_message}'
        )
        
        # Update job reminder tracking
        job.last_reminder_sent = timezone.now()
        job.reminder_count += 1
        job.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Reminder sent to {job.person_in_charge.get_full_name()}',
            'reminder_id': reminder.id
        })
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@group_required('Account Manager')
def api_send_job_message(request, job_id):
    """API endpoint to send message/note to job assignee"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        job = Job.objects.get(pk=job_id)
        message_content = request.POST.get('message_content', '')
        message_type = request.POST.get('message_type', 'note')
        
        if not job.person_in_charge:
            return JsonResponse({'error': 'Job not assigned to anyone'}, status=400)
        
        if not message_content.strip():
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Create message
        message = JobMessage.objects.create(
            job=job,
            sender=request.user,
            recipient=job.person_in_charge,
            message_type=message_type,
            content=message_content
        )
        
        # Create notification
        type_icon = {
            'note': '📝',
            'update': '📋',
            'question': '❓',
            'instruction': '📌'
        }.get(message_type, '💬')
        
        Notification.objects.create(
            recipient=job.person_in_charge,
            notification_type='job_message',
            title=f'{type_icon} New Message: {job.job_name}',
            message=f'{request.user.get_full_name()}: {message_content[:80]}...',
            link=f'/job/{job.pk}/',
            related_job=job
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Message sent',
            'message_id': message.id,
            'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@group_required('Account Manager')
def api_get_job_details(request, job_id):
    """API endpoint to get job details for modal"""
    try:
        job = Job.objects.get(pk=job_id)
        
        # Calculate metrics
        days_until = (job.expected_completion - timezone.now().date()).days if job.expected_completion else 0
        is_overdue = days_until < 0 and job.status != 'completed'
        
        return JsonResponse({
            'success': True,
            'job': {
                'id': job.id,
                'job_number': job.job_number,
                'job_name': job.job_name,
                'client': job.client.name,
                'product': job.product,
                'quantity': job.quantity,
                'status': job.status,
                'priority': job.priority,
                'assigned_to': job.person_in_charge.get_full_name() if job.person_in_charge else 'Unassigned',
                'assigned_to_id': job.person_in_charge.id if job.person_in_charge else None,
                'due_date': job.expected_completion.strftime('%Y-%m-%d'),
                'days_until': days_until,
                'is_overdue': is_overdue,
                'assignment_notes': job.assignment_notes,
                'reminder_count': job.reminder_count,
                'last_reminder': job.last_reminder_sent.strftime('%Y-%m-%d %H:%M') if job.last_reminder_sent else 'Never',
                'notes': job.notes,
            }
        })
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@group_required('Account Manager')
def api_get_job_messages(request, job_id):
    """API endpoint to get job messages/conversation"""
    try:
        job = Job.objects.get(pk=job_id)
        
        # Get all messages for this job, ordered by newest first
        messages_list = JobMessage.objects.filter(job=job).select_related('sender', 'recipient').order_by('-created_at')[:50]
        
        messages_data = []
        for msg in reversed(messages_list):  # Reverse to show oldest first
            messages_data.append({
                'id': msg.id,
                'sender': msg.sender.get_full_name(),
                'sender_id': msg.sender.id,
                'sender_avatar': msg.sender.username[0].upper(),
                'type': msg.message_type,
                'content': msg.content,
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M'),
                'is_read': msg.is_read,
            })
        
        return JsonResponse({
            'success': True,
            'messages': messages_data,
            'total': len(messages_data)
        })
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@group_required('Account Manager')
def api_get_production_users(request):
    """API endpoint to get list of production team users"""
    try:
        production_group = Group.objects.filter(name='Production Team').first()
        
        if production_group:
            users = production_group.user_set.all().values('id', 'first_name', 'last_name', 'email')
            users_list = [
                {
                    'id': u['id'],
                    'name': f"{u['first_name']} {u['last_name']}".strip() or u['email'],
                    'email': u['email']
                }
                for u in users
            ]
        else:
            users_list = []
        
        return JsonResponse({
            'success': True,
            'users': users_list
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_create_substitution_request(request):
    """API endpoint to create material substitution request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get the purchase order
            po = PurchaseOrder.objects.get(pk=data['purchase_order'])
            
            # Create substitution request
            substitution = MaterialSubstitutionRequest.objects.create(
                purchase_order=po,
                original_material=data.get('original_material'),
                proposed_material=data.get('proposed_material'),
                match_percentage=data.get('match_percentage', 0),
                justification=data.get('justification'),
                status='pending'
            )
            
            # Add cost info if provided
            if 'original_cost' in data or 'substitute_cost' in data:
                cost_obj, _ = MaterialSubstitutionApproval.objects.get_or_create(
                    purchase_order=po
                )
                cost_obj.original_cost = data.get('original_cost', 0)
                cost_obj.substitute_cost = data.get('substitute_cost', 0)
                cost_obj.save()
            
            return JsonResponse({
                'success': True,
                'id': substitution.id,
                'message': 'Substitution request created successfully'
            })
        except PurchaseOrder.DoesNotExist:
            return JsonResponse({'error': 'Purchase order not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def api_get_substitution_request(request, pk):
    """API endpoint to get substitution request details"""
    try:
        substitution = MaterialSubstitutionRequest.objects.get(pk=pk)
        
        approval = MaterialSubstitutionApproval.objects.filter(
            purchase_order=substitution.purchase_order
        ).first()
        
        return JsonResponse({
            'id': substitution.id,
            'purchase_order': substitution.purchase_order.id,
            'original_material': substitution.original_material,
            'proposed_material': substitution.proposed_material,
            'match_percentage': substitution.match_percentage,
            'justification': substitution.justification,
            'status': substitution.status,
            'created_at': substitution.created_at.isoformat(),
            'approval': {
                'original_cost': float(approval.original_cost) if approval else 0,
                'substitute_cost': float(approval.substitute_cost) if approval else 0,
            } if approval else None
        })
    except MaterialSubstitutionRequest.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
def api_approve_substitution(request, pk):
    """API endpoint to approve substitution request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            substitution = MaterialSubstitutionRequest.objects.get(pk=pk)
            
            # Update status
            substitution.status = 'approved'
            substitution.save()
            
            # Update approval record
            approval, _ = MaterialSubstitutionApproval.objects.get_or_create(
                purchase_order=substitution.purchase_order
            )
            approval.original_material = substitution.original_material
            approval.substitute_material = substitution.proposed_material
            approval.reason = substitution.justification
            approval.approval_status = 'approved'
            approval.approved_by = request.user
            approval.approved_at = timezone.now()
            
            if data.get('notify_customer'):
                approval.customer_notified = True
                approval.customer_notified_at = timezone.now()
            
            approval.save()
            
            # ✨ WebSocket: Broadcast substitution approval to all connected clients
            broadcast_substitution_update(
                substitution_id=substitution.id,
                update_type='status_changed',
                data={
                    'status': 'approved',
                    'approved_by': request.user.get_full_name(),
                    'approved_at': substitution.updated_at.isoformat() if hasattr(substitution, 'updated_at') else timezone.now().isoformat()
                }
            )
            
            # ✨ WebSocket: Send notification to vendor
            if hasattr(substitution, 'vendor_user') and substitution.vendor_user:
                send_substitution_approved_notification(
                    user_id=substitution.vendor_user.id,
                    sub_id=substitution.id,
                    po_num=substitution.purchase_order.order_number if hasattr(substitution.purchase_order, 'order_number') else 'N/A',
                    original=substitution.original_material,
                    proposed=substitution.proposed_material
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Substitution approved and updated in real-time'
            })
        except MaterialSubstitutionRequest.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_reject_substitution(request, pk):
    """API endpoint to reject substitution request"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            substitution = MaterialSubstitutionRequest.objects.get(pk=pk)
            
            # Update status
            substitution.status = 'rejected'
            substitution.save()
            
            # Update approval record
            approval, _ = MaterialSubstitutionApproval.objects.get_or_create(
                purchase_order=substitution.purchase_order
            )
            approval.approval_status = 'rejected'
            approval.reason = data.get('reason', '')
            approval.approved_by = request.user
            approval.approved_at = timezone.now()
            approval.save()
            
            # ✨ WebSocket: Broadcast substitution rejection to all connected clients
            broadcast_substitution_update(
                substitution_id=substitution.id,
                update_type='status_changed',
                data={
                    'status': 'rejected',
                    'rejected_by': request.user.get_full_name(),
                    'reason': approval.reason,
                    'rejected_at': timezone.now().isoformat()
                }
            )
            
            # ✨ WebSocket: Send rejection notification to vendor
            if hasattr(substitution, 'vendor_user') and substitution.vendor_user:
                send_substitution_rejected_notification(
                    user_id=substitution.vendor_user.id,
                    sub_id=substitution.id,
                    po_num=substitution.purchase_order.order_number if hasattr(substitution.purchase_order, 'order_number') else 'N/A',
                    reason=approval.reason
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Substitution rejected and updated in real-time'
            })
        except MaterialSubstitutionRequest.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_get_substitution_comments(request, pk):
    """API endpoint to get comments on substitution"""
    try:
        substitution = MaterialSubstitutionRequest.objects.get(pk=pk)
        
        # For now, we'll return an empty list
        # You can expand this to use a Comment model if needed
        comments = []
        
        return JsonResponse(comments, safe=False)
    except MaterialSubstitutionRequest.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
def api_add_substitution_comment(request, pk):
    """API endpoint to add comment to substitution"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            substitution = MaterialSubstitutionRequest.objects.get(pk=pk)
            
            # Add comment logic here
            # For now, just return success
            
            return JsonResponse({
                'success': True,
                'message': 'Comment added'
            })
        except MaterialSubstitutionRequest.DoesNotExist:
            return JsonResponse({'error': 'Not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


@login_required
def api_get_purchase_order_details(request, pk):
    """API endpoint to get purchase order details"""
    try:
        po = PurchaseOrder.objects.get(pk=pk)
        
        return JsonResponse({
            'id': po.id,
            'po_number': po.po_number,
            'description': po.description,
            'quantity': po.quantity,
            'material': getattr(po, 'material', ''),
            'vendor': po.vendor_stage.vendor.name if po.vendor_stage else 'Unknown',
            'products': po.description,
        })
    except PurchaseOrder.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@login_required
def api_job_progress(request, job_id):
    """API endpoint to get and add job progress updates
    
    GET: Any logged-in user can view progress
    POST: Only Account Managers or the assigned PT user can add updates
    """
    try:
        job = Job.objects.get(pk=job_id)
        
        if request.method == 'GET':
            # Get progress updates (anyone logged in can view)
            updates = ProductionUpdate.objects.filter(
                job=job,
                update_type='job'
            ).values(
                'id', 'status', 'progress', 'notes', 
                'created_by__first_name', 'created_by__last_name', 'created_at'
            ).order_by('-created_at')
            
            # Calculate overall progress (average of all updates, or latest)
            latest = updates.first() if updates.exists() else None
            overall_progress = latest['progress'] if latest else 0
            
            updates_list = [
                {
                    'id': u['id'],
                    'status': u['status'],
                    'status_display': dict(ProductionUpdate.UPDATE_TYPE_CHOICES).get(u['status'], u['status']),
                    'progress': u['progress'],
                    'notes': u['notes'],
                    'created_by': f"{u['created_by__first_name']} {u['created_by__last_name']}".strip() if u['created_by__first_name'] else 'Unknown',
                    'created_at': u['created_at'].strftime('%b %d, %Y %I:%M %p')
                }
                for u in updates
            ]
            
            return JsonResponse({
                'success': True,
                'overall_progress': overall_progress,
                'updates': updates_list
            })
        
        elif request.method == 'POST':
            # Check permissions: Only AM or the assigned PT user can add progress
            user_groups = request.user.groups.values_list('name', flat=True)
            is_account_manager = 'Account Manager' in user_groups
            is_assigned_user = job.person_in_charge and job.person_in_charge.id == request.user.id
            
            if not (is_account_manager or is_assigned_user):
                return JsonResponse({
                    'error': 'Only Account Managers or the assigned user can add progress updates'
                }, status=403)
            
            # Add progress update
            status = request.POST.get('status', 'in_production')
            progress = int(request.POST.get('progress', 0))
            notes = request.POST.get('notes', '')
            
            # Validate progress percentage
            if progress < 0 or progress > 100:
                return JsonResponse({'error': 'Progress must be between 0 and 100'}, status=400)
            
            # Create update
            update = ProductionUpdate.objects.create(
                job=job,
                update_type='job',
                status=status,
                progress=progress,
                notes=notes,
                created_by=request.user
            )
            
            # If job is assigned to someone, create notification for the AM who assigned it
            # Find the user who assigned this job (from JobReminder or just notify the AM group)
            am_group = Group.objects.filter(name='Account Manager').first()
            if am_group:
                for am in am_group.user_set.all():
                    Notification.objects.create(
                        recipient=am,
                        notification_type='progress_update',
                        title=f'📊 Progress Update: {job.job_name}',
                        message=f'{request.user.get_full_name()} updated progress to {progress}% - {status.replace("_", " ").title()}',
                        link=f'/job/{job.pk}/',
                        related_job=job
                    )
            
            # If progress is 100%, auto-complete
            if progress == 100:
                job.status = 'Completed'
                job.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Progress updated successfully',
                'update_id': update.id,
                'progress': progress
            })
        
        else:
            return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    except Job.DoesNotExist:
        return JsonResponse({'error': 'Job not found'}, status=404)
    except ValueError:
        return JsonResponse({'error': 'Invalid progress value'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@group_required('Account Manager')
def lead_intake(request):
    """Lead intake with automatic notification creation"""
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            # Save the lead with the current user as creator
            lead = form.save(commit=False)
            lead.created_by = request.user
            lead.save()
            
            #  CREATE NOTIFICATION: Remind AM to create quote
            Notification.objects.create(
                recipient=request.user,
                notification_type='quote_reminder',
                title=f' Create Quote for {lead.name}',
                message=f'New lead created: {lead.name} ({lead.lead_id}). Remember to send them a quote.',
                link=f'/create/quote?lead_id={lead.id}',
                related_lead=lead,
                action_url=f'/create/quote?lead_id={lead.id}',
                action_label='Create Quote'
            )
            
            # Notify all other account managers
            other_ams = User.objects.filter(groups__name='Account Manager').exclude(id=request.user.id)
            for am in other_ams:
                Notification.objects.create(
                    recipient=am,
                    notification_type='lead_created',
                    title=f' New Lead: {lead.name}',
                    message=f'{request.user.get_full_name() or request.user.username} created a new lead',
                    link='/leads/',
                    related_lead=lead
                )
            
            messages.success(request, f' Lead {lead.name} created! Check notifications for next steps.')
            return redirect('lead_intake')
        else:
            messages.error(request, 'Please fill in all required fields')
    else:
        form = LeadForm()
    
    # GET request - show leads list
    search_query = request.GET.get('search', '')
    leads = Lead.objects.all().order_by('-created_at')
    
    if search_query:
        leads = leads.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(lead_id__icontains=search_query)
        )
    
    # Get products for the form
    products = Product.objects.filter(is_visible=True).order_by('name')
    
    context = {
        'current_view': 'leads',
        'leads': leads,
        'form': form,
        'search_query': search_query,
        'products': products,
    }
    return render(request, 'lead_intake.html', context)


def qualify_lead(request, lead_id):
    """Qualify a lead"""
    lead = get_object_or_404(Lead, lead_id=lead_id)
    lead.status = 'Qualified'
    lead.save()
    messages.success(request, f'Lead {lead.lead_id} qualified successfully')
    return redirect('lead_intake')


def convert_lead(request, lead_id):
    """Convert lead to client"""
    lead = get_object_or_404(Lead, lead_id=lead_id)
    lead.status = 'Converted'
    lead.save()
    
    # Pre-fill client form with lead data
    prefilled_data = {
        'name': lead.name,
        'email': lead.email,
        'phone': lead.phone,
        'lead_source': lead.source if hasattr(lead, 'source') else '',
    }
    
    # Only add preferred_contact if it exists in the Lead model
    if hasattr(lead, 'preferred_contact'):
        prefilled_data['preferred_channel'] = lead.preferred_contact
    
    request.session['prefilled_lead'] = prefilled_data
    messages.info(request, f'Converting lead {lead.name} to client')
    return redirect('client_onboarding')

def client_onboarding(request):
    """Client onboarding workflow - Matches HTML template B2B/B2C structure"""
    prefilled_data = None
    
    # Check if lead_id is passed as query parameter (from Onboard button click)
    # Only prefill if lead_id is explicitly provided - do NOT use session
    lead_id = request.GET.get('lead_id')
    if lead_id:
        try:
            lead = Lead.objects.get(pk=lead_id)
            # Prefill with lead data ONLY if lead_id is in current request
            prefilled_data = {
                'name': lead.name,
                'email': lead.email,
                'phone': lead.phone,
                'lead_source': lead.source,
                'product_interest': lead.product_interest,
                'preferred_client_type': lead.preferred_client_type,
            }
        except Lead.DoesNotExist:
            logger.warning(f"Lead with id {lead_id} not found for onboarding")
    
    if request.method == 'POST':
        client_type = request.POST.get('client_type', 'B2B')
        
        try:
            if client_type == 'B2C':
                # ============ B2C SIMPLIFIED ONBOARDING  ============
                company = request.POST.get('company_b2c', '').strip()  # Optional
                name = request.POST.get('name_b2c', '').strip()  # Required
                email = request.POST.get('email_b2c', '').strip()  # Optional now
                phone = request.POST.get('phone_b2c', '').strip()  # Required
                preferred_channel = request.POST.get('preferred_channel_b2c', 'Email')
                lead_source = request.POST.get('lead_source_b2c', '')
                delivery_address = request.POST.get('delivery_address_b2c', '').strip()
                
                # Validate required B2C fields
                if not name:
                    messages.error(request, 'Contact Person is required')
                    return redirect('client_onboarding')
                if not phone:
                    messages.error(request, 'Phone is required')
                    return redirect('client_onboarding')
                
                # validating phone formats
                import re
                phone_cleaned = re.sub(r'[\s\-\(\)]', '', phone)
                kenyans_patterns = [
                    r'^\+254[17]\d{8}$',
                    r'^254[17]\d{8}$',
                    r'^0[17]\d{8}$',
                ]
                is_valid_phone = any(re.match(pattern, phone_cleaned) for pattern in kenyans_patterns)

                if not is_valid_phone:
                    messages.error(request, 'Please enter a valid Kenya n phone number(+254)')
                    return redirect('client_onboarding')
                
                # standardize phone
                if phone_cleaned.startswith('0'):
                    phone_cleaned = '+254' + phone_cleaned[1:]
                elif phone_cleaned.startswith('254'):
                    phone_cleaned = '+' + phone_cleaned

                # checking for duplicate phone
                if Client.objects.filter(phone=phone_cleaned).exists():
                    messages.error(request, f'A client with this phone {phone_cleaned} already exists')

                
                # Check for duplicate email only if provided
                if email and Client.objects.filter(email=email).exists():
                    messages.error(request, f'A client with email {email} already exists')
                    return redirect('client_onboarding')

                # LEAD CONVERSION CHECK (B2C)
                # Check if this phone/email belongs to a Lead and link it
                existing_lead = Lead.objects.filter(Q(phone=phone) | Q(email=email) if email else Q(phone=phone)).first()
                
                # Create B2C client
                client = Client.objects.create(
                    client_type='B2C',
                    company=company if company else '',
                    name=name,
                    email=email or '',
                    phone=phone,
                    preferred_channel=preferred_channel,
                    lead_source=lead_source,
                    payment_terms='Prepaid',
                    risk_rating='Low',
                    credit_limit=0,
                    is_reseller=False,
                    status='Active',
                    onboarded_by=request.user,
                    account_manager=request.user,
                    converted_from_lead=existing_lead,
                    delivery_address=delivery_address
                )
                
                # If lead exists, mark it as converted
                if existing_lead:
                    existing_lead.status = 'Converted'
                    existing_lead.converted_to_client = True
                    existing_lead.converted_at = timezone.now()
                    existing_lead.save()
                
                # Log activity
                ActivityLog.objects.create(
                    client=client,
                    activity_type='Note',
                    title=f"B2C Client Profile Created",
                    description=f"B2C client {client.name} onboarded successfully.",
                    created_by=request.user
                )
                
                # Clear session data
                if 'prefilled_lead' in request.session:
                    del request.session['prefilled_lead']
                
                messages.success(request, f'B2C Client {client.client_id} created successfully!')
                return redirect('client_profile', pk=client.pk)
                
            else:
                # ============ B2B FULL ONBOARDING - 3 STEPS ============
                company = request.POST.get('company', '').strip()
                name = request.POST.get('name', '').strip()
                email = request.POST.get('email', '').strip()
                phone = request.POST.get('phone', '').strip()
                preferred_channel = request.POST.get('preferred_channel', 'Email')
                lead_source = request.POST.get('lead_source', '')
                delivery_address = request.POST.get('delivery_address', '').strip()
                
                # Financial fields
                vat_tax_id = request.POST.get('vat_tax_id', '')
                payment_terms = request.POST.get('payment_terms', 'Prepaid')
                risk_rating = request.POST.get('risk_rating', 'Low')
                is_reseller = request.POST.get('is_reseller') == 'on'
                
                # Validate required B2B fields
                if not company or not name or not email or not phone:
                    messages.error(request, 'Please fill in all required fields (Company, Name, Email, Phone)')
                    return redirect('client_onboarding')
                
                # Check for duplicate email
                if Client.objects.filter(email=email).exists():
                    messages.error(request, f'A client with email {email} already exists')
                    return redirect('client_onboarding')

                # LEAD CONVERSION CHECK (B2B) - Link lead if exists
                existing_lead = Lead.objects.filter(Q(email=email) | Q(phone=phone)).first()
                # (Removed strict approved quote requirement for direct onboarding)
                
                # Create B2B client
                client = Client.objects.create(
                    client_type='B2B',
                    company=company,
                    name=name,
                    email=email,
                    phone=phone,
                    preferred_channel=preferred_channel,
                    lead_source=lead_source,
                    vat_tax_id=vat_tax_id,
                    payment_terms=payment_terms,
                    risk_rating=risk_rating,
                    is_reseller=is_reseller,
                    status='Active',
                    onboarded_by=request.user,
                    account_manager=request.user,
                    converted_from_lead=existing_lead,
                    delivery_address=delivery_address
                )

                # If lead exists, mark it as converted
                if existing_lead:
                    existing_lead.status = 'Converted'
                    existing_lead.converted_to_client = True
                    existing_lead.converted_at = timezone.now()
                    existing_lead.save()
                
                # STEP 2: Contacts
                contact_names = request.POST.getlist('contact_name[]')
                contact_emails = request.POST.getlist('contact_email[]')
                contact_phones = request.POST.getlist('contact_phone[]')
                contact_roles = request.POST.getlist('contact_role[]')
                
                for i, contact_name in enumerate(contact_names):
                    if contact_name.strip():
                        ClientContact.objects.create(
                            client=client,
                            full_name=contact_name.strip(),
                            email=contact_emails[i].strip() if i < len(contact_emails) else '',
                            phone=contact_phones[i].strip() if i < len(contact_phones) else '',
                            role=contact_roles[i] if i < len(contact_roles) else 'None',
                        )
                
                # STEP 3: Compliance Documents
                compliance_files = request.FILES.getlist('compliance_files')
                doc_type = request.POST.get('doc_type', '')
                doc_expiry = request.POST.get('doc_expiry', None)
                
                if compliance_files and doc_type:
                    for file in compliance_files:
                        ComplianceDocument.objects.create(
                            client=client,
                            document_type=doc_type,
                            file=file,
                            expiry_date=doc_expiry if doc_expiry else None,
                            uploaded_by=request.user
                        )

                # BRAND ASSETS
                brand_files = request.FILES.getlist('brand_files')
                brand_asset_type = request.POST.get('brand_asset_type', 'Logo')
                if brand_files:
                    from .models import BrandAsset
                    for file in brand_files:
                        BrandAsset.objects.create(
                            client=client,
                            asset_type=brand_asset_type,
                            file=file,
                            description='',
                            uploaded_by=request.user
                        )
                
                # Log activity
                ActivityLog.objects.create(
                    client=client,
                    activity_type='Note',
                    title=f"B2B Client Profile Created",
                    description=f"B2B client {client.company} onboarded successfully.",
                    created_by=request.user
                )
                
                # Clear session data
                if 'prefilled_lead' in request.session:
                    del request.session['prefilled_lead']
                
                messages.success(request, f'B2B Client {client.client_id} created successfully!')
                return redirect('client_profile', pk=client.pk)
        
        except Exception as e:
            messages.error(request, f'Error creating client: {str(e)}')
            import traceback
            print(traceback.format_exc())
            return redirect('client_onboarding')
        phone = phone_cleaned
    
    # GET request - show form
    form = ClientForm(initial=prefilled_data) if prefilled_data else ClientForm()
    
    context = {
        'current_view': 'onboarding',
        'form': form,
        'prefilled_lead': prefilled_data,
    }
    return render(request, 'client_onboarding.html', context)
    
def client_list(request):
    """Client list view with filters"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    filter_type = request.GET.get('type', 'All')
    filter_status = request.GET.get('status', 'All')
    
    clients = Client.objects.all()
    
    # Apply filters
    if search_query:
        clients = clients.filter(
            Q(name__icontains=search_query) |
            Q(company__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(client_id__icontains=search_query)
        )
    
    if filter_type != 'All':
        clients = clients.filter(client_type=filter_type)
    
    if filter_status != 'All':
        clients = clients.filter(status=filter_status)
    
    context = {
        'current_view': 'clients',
        'clients': clients,
        'search_query': search_query,
        'filter_type': filter_type,
        'filter_status': filter_status,
    }
    return render(request, 'client_list.html', context)


def check_duplicate_lead(request):
    """Check for duplicate leads - AJAX endpoint"""
    name = request.GET.get('name', '')
    email = request.GET.get('email', '')
    phone = request.GET.get('phone', '')
    
    # Check only for the provided field (not all three)
    if email:
        duplicate = Lead.objects.filter(email__iexact=email).first()
    elif phone:
        duplicate = Lead.objects.filter(phone=phone).first()
    elif name:
        duplicate = Lead.objects.filter(name__iexact=name).first()
    else:
        duplicate = None
    
    if duplicate:
        return JsonResponse({
            'duplicate': True,
            'id': duplicate.id,
            'name': duplicate.name,
            'lead_id': duplicate.lead_id,
            'email': duplicate.email,
            'phone': duplicate.phone,
            'message': f'Similar lead found: {duplicate.name} ({duplicate.lead_id})'
        })
    return JsonResponse({'duplicate': False})

# ========= QUOTE CREATION =========


@login_required
@group_required('Account Manager')
@transaction.atomic
def create_quote(request):
    """Create a single quote for a client or lead"""
    if request.method == 'POST':
        try:
            quote_type = request.POST.get('quote_type')
            client_id = request.POST.get('client_id')
            lead_id = request.POST.get('lead_id')

            client = None
            lead = None

            # Determine entity type
            if quote_type == 'client' and client_id:
                client = get_object_or_404(Client, id=client_id)
            elif quote_type == 'lead' and lead_id:
                lead = get_object_or_404(Lead, id=lead_id)
            else:
                messages.error(request, "Please select a valid client or lead.")
                return redirect('create_quote')

            # Extract form data
            product_name = request.POST.get('product_name', '').strip()
            quantity = int(request.POST.get('quantity', 1))
            
            # Check if this is a modal submission (no unit_price provided)
            is_modal_submission = not request.POST.get('unit_price', '').strip()
            
            if is_modal_submission:
                # For modal submissions, get price from Product model
                product_sku = request.POST.get('product_sku', '').strip()
                if product_sku:
                    try:
                        product = Product.objects.get(sku=product_sku, is_visible=True)
                        unit_price = product.base_price
                    except Product.DoesNotExist:
                        messages.error(request, f"Product with SKU {product_sku} not found.")
                        return redirect('create_quote')
                else:
                    # Fallback: try to find product by name
                    try:
                        product = Product.objects.filter(name=product_name, is_visible=True).first()
                        unit_price = product.base_price if product else Decimal('0')
                    except:
                        unit_price = Decimal('0')
            else:
                # Full form submission
                unit_price_raw = request.POST.get('unit_price', '').strip()
                unit_price = Decimal(unit_price_raw) if unit_price_raw else Decimal('0')
            
            include_vat = request.POST.get('include_vat') == 'on'
            payment_terms = request.POST.get('payment_terms', 'Prepaid')
            status = request.POST.get('status', 'Draft')
            notes = request.POST.get('notes', '')
            terms = request.POST.get('terms', '')
            valid_until_str = request.POST.get('valid_until')
            quote_date_str = request.POST.get('quote_date')

            if not product_name:
                error_msg = "Product name is required."
                if is_modal_submission:
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('create_quote')

            if quantity <= 0:
                error_msg = "Quantity must be greater than zero."
                if is_modal_submission:
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('create_quote')

            # Set dates
            quote_date = timezone.now().date()
            valid_until = quote_date + timedelta(days=3)
            if quote_date_str:
                quote_date = timezone.datetime.fromisoformat(quote_date_str).date()
            if valid_until_str:
                valid_until = timezone.datetime.fromisoformat(valid_until_str).date()

            # Create quote
            quote = Quote.objects.create(
                client=client,
                lead=lead,
                product_name=product_name,
                quantity=quantity,
                unit_price=unit_price,
                payment_terms=payment_terms,
                status=status,
                include_vat=include_vat,
                quote_date=quote_date,
                valid_until=valid_until,
                notes=notes,
                terms=terms,
                created_by=request.user
            )

            # Create activity log
            if client:
                ActivityLog.objects.create(
                    client=client,
                    activity_type='Quote',
                    title=f"Quote {quote.quote_id} Created",
                    description=f"Quote for {product_name} (x{quantity})",
                    related_quote=quote,
                    created_by=request.user
                )

            if is_modal_submission:
                return JsonResponse({
                    'success': True, 
                    'message': f'Quote {quote.quote_id} created successfully!',
                    'quote_id': quote.quote_id
                })
            else:
                messages.success(request, f"Quote {quote.quote_id} created successfully!")
                if client:
                    return redirect('client_profile', pk=client.pk)
                elif lead:
                    return redirect('lead_intake')
                return redirect('dashboard')

        except Exception as e:
            messages.error(request, f"Error creating quote: {str(e)}")
            import traceback; print(traceback.format_exc())
            return redirect('create_quote')

    # GET — Render form
    clients = Client.objects.filter(status='Active').order_by('name')
    leads = Lead.objects.exclude(status__in=['Converted', 'Lost']).order_by('-created_at')
    # Only show published and visible products for quote creation
    products = Product.objects.filter(
        status='published',
        is_visible=True
    ).order_by('name')
    
    today = timezone.now().date()
    default_valid_until = today + timedelta(days=3)
    
    # Get account manager name
    account_manager_name = request.user.get_full_name() or request.user.username
    
    context = {
        'clients': clients,
        'leads': leads,
        'products': products,
        'today': today.isoformat(),
        'default_valid_until': default_valid_until.isoformat(),
        'current_year': today.year,
        'account_manager_name': account_manager_name,
    }
    return render(request, 'quote_detail.html', context)



@login_required
@group_required('Account Manager')
def quote_create(request):
    """Create multi-product quote with product customization logic"""
    from clientapp.models import resolve_unit_price, QuoteLineItem
    
    if request.method == 'POST':
        try:
            # 1. Get Core Form Data
            client_name = request.POST.get('client_name', '').strip()
            valid_until = request.POST.get('valid_until')
            delivery_deadline = request.POST.get('delivery_deadline')
            special_instructions = request.POST.get('special_instructions', '')
            action = request.POST.get('action', 'save_draft')
            
            # Zoho-style additional fields
            reference_number = request.POST.get('reference_number', '').strip()
            shipping_charges = Decimal(request.POST.get('shipping_charges', '0') or '0')
            adjustment_amount = Decimal(request.POST.get('adjustment_amount', '0') or '0')
            adjustment_reason = request.POST.get('adjustment_reason', '').strip()
            tax_rate = Decimal(request.POST.get('tax_rate', '16') or '16')
            custom_terms = request.POST.get('terms_conditions', '').strip()
            
            client_id = request.POST.get('client_id')
            lead_id = request.POST.get('lead_id')

            # 2. Validate Client Selection
            client = None
            lead = None
            if client_id:
                client = get_object_or_404(Client, id=client_id)
            elif lead_id:
                lead = get_object_or_404(Lead, id=lead_id)
            else:
                messages.error(request, "Please select a valid client or lead.")
                return redirect('quote_create')

            # 3. Parse Line Items
            product_ids = request.POST.getlist('product_id[]')
            quantities = request.POST.getlist('quantity[]')
            rates = request.POST.getlist('rate[]')  # Unit prices from form
            variable_amounts = request.POST.getlist('variable_amount[]', [])  # For semi-customizable products
            discount_amounts = request.POST.getlist('discount[]', [])  # Discount values
            discount_types = request.POST.getlist('discount_type[]', [])  # Discount types (percent/fixed)

            if not product_ids:
                messages.error(request, 'Please add at least one product to the quote')
                return redirect('quote_create')

            # 4. Check if editing existing quote
            existing_quote_id = request.POST.get('existing_quote_id', '').strip()
            is_editing = bool(existing_quote_id)
            
            # 5. Generate unique quote ID (only for new quotes)
            if is_editing:
                quote_group_id = existing_quote_id
                # Get existing quote
                existing_quote = Quote.objects.filter(quote_id=quote_group_id).first()
                if not existing_quote:
                    messages.error(request, f'Quote {quote_group_id} not found')
                    return redirect('quotes_list')
                
                # Check if quote is locked (sent to PT for costing)
                if existing_quote.status == 'Sent to PT' and request.user.groups.filter(name='Account Manager').exists():
                    messages.error(request, f'Quote {quote_group_id} is locked. Production Team is currently costing this quote. Please wait for costing to complete before editing.')
                    return redirect('quote_detail', quote_id=quote_group_id)
            else:
                quote_group_id = f"Q-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
            
            # Initialize variables for email sending (if needed)
            quote_pk = None
            quote_id_for_redirect = quote_group_id
            
            # 6. Process and Save Quote with Line Items
            with transaction.atomic():
                if is_editing:
                    # Update existing quote
                    quote = existing_quote
                    quote.client = client
                    quote.lead = lead
                    quote.valid_until = timezone.datetime.fromisoformat(valid_until).date() if valid_until else quote.valid_until
                    quote.notes = special_instructions
                    
                    QuoteLineItem.objects.filter(quote=quote).delete()
                else:
                    # Create new Quote record
                    quote = Quote(
                        quote_id=quote_group_id,
                        client=client,
                        lead=lead,
                        product_name='',  # Will be set from line items
                        quantity=1,  # Placeholder, actual quantity in line items
                        unit_price=Decimal('0'),  # Will be calculated from line items
                        total_amount=Decimal('0'),  # Will be calculated
                        status='Draft',
                        quote_date=timezone.now().date(),
                        valid_until=timezone.datetime.fromisoformat(valid_until).date() if valid_until else timezone.now().date() + timedelta(days=3),
                        notes=special_instructions,
                        reference_number=reference_number,
                        shipping_charges=shipping_charges,
                        adjustment_amount=adjustment_amount,
                        adjustment_reason=adjustment_reason,
                        tax_rate=tax_rate,
                        custom_terms=custom_terms,
                        created_by=request.user
                    )
                
                
                quote.save()
                
                # Verify quote has a primary key
                if not quote.pk:
                    raise ValueError("Quote was not saved properly - no primary key assigned")
                
               
                
                # Create line items with pricing
                subtotal = Decimal('0')
                discount_total = Decimal('0')
                total_amount = Decimal('0')
                has_fully_customizable = False
                
                for i in range(len(product_ids)):
                    product = Product.objects.get(id=product_ids[i])
                    qty = int(quantities[i]) if i < len(quantities) else 1
                    var_amount = Decimal(variable_amounts[i]) if i < len(variable_amounts) and variable_amounts[i] else Decimal('0')
                    
                    # Get discount data
                    disc_amount = Decimal(discount_amounts[i]) if i < len(discount_amounts) and discount_amounts[i] else Decimal('0')
                    disc_type = discount_types[i] if i < len(discount_types) and discount_types[i] else 'percent'
                    
                    # Get unit price
                    if i < len(rates) and rates[i]:
                        try:
                            unit_price = Decimal(rates[i])
                        except (ValueError, TypeError):
                            unit_price = resolve_unit_price(product)
                    else:
                        unit_price = resolve_unit_price(product)
                    
                    # quote has a PK
                    line_item = QuoteLineItem.objects.create(
                        quote=quote,
                        product=product,
                        product_name=product.name,
                        customization_level_snapshot=product.customization_level,
                        base_price_snapshot=product.base_price,
                        quantity=qty,
                        unit_price=unit_price,
                        variable_amount=var_amount,
                        discount_amount=disc_amount,
                        discount_type=disc_type,
                        order=i
                    )
                    
                    # Calculate subtotal and discount for this line
                    line_subtotal = (unit_price + var_amount) * qty
                    line_discount = Decimal('0')
                    if disc_amount > 0:
                        if disc_type == 'percent':
                            line_discount = line_subtotal * (disc_amount / Decimal('100'))
                        else:
                            line_discount = disc_amount
                    
                    subtotal += line_subtotal
                    discount_total += line_discount
                    
                    # Check if product is fully customizable
                    if product.customization_level == 'fully_customizable':
                        has_fully_customizable = True
                
                # Calculate Tax
                after_discount = subtotal - discount_total
                tax_total = (after_discount * tax_rate / Decimal('100'))
                
                # Final Total
                final_total = after_discount + tax_total + shipping_charges + adjustment_amount
                
                # Update quote totals
                quote.product_name = f"{len(product_ids)} item(s)" if len(product_ids) > 1 else QuoteLineItem.objects.filter(quote=quote).first().product_name if QuoteLineItem.objects.filter(quote=quote).exists() else ''
                quote.quantity = sum(item.quantity for item in QuoteLineItem.objects.filter(quote=quote))
                quote.subtotal = subtotal
                quote.discount_total = discount_total
                quote.tax_total = tax_total
                quote.total_amount = final_total
                quote.save()

                # 8. Finalize
                if action == 'save_draft':
                    quote.status = 'Draft'
                    quote.save()
                    if is_editing:
                        msg = f" Quote {quote_group_id} updated and saved as draft."
                    else:
                        msg = f" Quote {quote_group_id} saved as draft."
                
                elif action == 'save_send_pt':
                    # Check if quote can be sent to PT
                    can_send, error_msg = quote.can_send_to_pt()
                    if not can_send:
                        messages.error(request, error_msg)
                        quote.delete()  # Clean up
                        return redirect('quote_create')
                    
                    quote.status = 'Sent to PT'
                    quote.production_status = 'pending'
                    quote.save()
                    
                    # Notify Production Team
                    from django.contrib.auth.models import User
                    pt_users = User.objects.filter(groups__name='Production Team')
                    for pt in pt_users:
                        Notification.objects.create(
                            recipient=pt,
                            notification_type='quote_sent_pt',
                            title=f' Quote {quote_group_id} Needs Costing',
                            message=f'New quote from {request.user.get_full_name()} requires costing.',
                            link=f'/production/quote-costing-v2/{quote_group_id}/',
                            related_quote_id=quote_group_id
                        )
                    if is_editing:
                        msg = f" Quote {quote_group_id} updated and sent to PT for costing."
                    else:
                        msg = f" Quote {quote_group_id} sent to PT for costing."
                
                elif action == 'send_to_customer':
                    # Check if quote can be sent to customer
                    can_send, error_msg = quote.can_send_to_customer()
                    if not can_send:
                        messages.error(request, error_msg)
                        return redirect('quote_detail', quote_id=quote_group_id)
                    
                    # Save
                    quote.save()
                    
                    
                    quote_pk = quote.pk
                    quote_id_for_redirect = quote_group_id
                    msg = f" Quote {quote_group_id} prepared for sending."
                
                # Log the Activity (only if client exists - leads don't have activity logs)
                if client:
                    ActivityLog.objects.create(
                        client=client,
                        activity_type='Quote',
                        title=f"Quote {quote_group_id} Created",
                        description=f"Quote with {len(product_ids)} items created.",
                        created_by=request.user
                    )

           
            
            # After transaction commits, handle email sending if needed
            if action == 'send_to_customer':
                
                quote_for_email = Quote.objects.get(pk=quote_pk)
                
                # Use the send_quote view to handle email sending
                from .quote_approval_services import QuoteApprovalService
                result = QuoteApprovalService.send_quote_via_email(quote_for_email, request)
                
                if result['success']:
                    # Update quote status
                    quote_for_email.status = 'Sent to Customer'
                    quote_for_email.production_status = 'sent_to_client'
                    quote_for_email.save()
                    messages.success(request, f" Quote {quote_id_for_redirect} sent to customer via email.")
                    return redirect('quote_detail', quote_id=quote_id_for_redirect)
                else:
                    messages.error(request, f"Error sending quote: {result.get('message', 'Unknown error')}")
                    return redirect('quote_detail', quote_id=quote_id_for_redirect)
            
            messages.success(request, msg)
            return redirect('quote_detail', quote_id=quote_group_id)

        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('quote_create')

    # GET request logic - handle both new quotes and editing existing quotes
    quote_id = request.GET.get('quote_id')
    existing_quote = None
    existing_line_items = []
    
    if quote_id:
        # Load existing quote for editing
        existing_quote = Quote.objects.filter(quote_id=quote_id).first()
        if existing_quote:
            existing_line_items = QuoteLineItem.objects.filter(quote=existing_quote).order_by('order', 'created_at')
    
    context = {
        'clients': Client.objects.filter(status='Active').order_by('name'),
        'leads': Lead.objects.exclude(status__in=['Converted', 'Lost']).order_by('-created_at'),
        'products': Product.objects.filter(status='published', is_visible=True).order_by('name'),
        'existing_quote': existing_quote,
        'existing_quotes': existing_line_items,  # Template expects 'existing_quotes' for line items
        'existing_line_items': existing_line_items,
        'quote_id': quote_id,
    }
    return render(request, 'quote_create.html', context)

@login_required
def download_quote_pdf(request, quote_id):
    """
    Download quote as PDF
    Accessible to account managers and authorized users
    """
    try:
        from .pdf_utils import QuotePDFGenerator
        
        # Verify quote exists and user has access
        quote = Quote.objects.filter(quote_id=quote_id).first()
        if not quote:
            messages.error(request, f'Quote {quote_id} not found')
            return redirect('quotes_list')
        
        # Generate and return PDF
        return QuotePDFGenerator.download_quote_pdf(quote_id, request)
        
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        import traceback
        traceback.print_exc()
        return redirect('quotes_list')


@login_required
def clone_quote(request, quote_id):
    """Clone an existing quote - creates a new quote with copied data"""
    from clientapp.models import QuoteLineItem
    
    original_quote = get_object_or_404(Quote, quote_id=quote_id)
    
    # Generate new quote ID
    new_quote_id = f"Q-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    try:
        with transaction.atomic():
            # Create new quote with copied data
            new_quote = Quote.objects.create(
                quote_id=new_quote_id,
                client=original_quote.client,
                lead=original_quote.lead,
                product_name=original_quote.product_name,
                quantity=original_quote.quantity,
                unit_price=original_quote.unit_price,
                subtotal=original_quote.subtotal,
                discount_total=original_quote.discount_total,
                tax_total=original_quote.tax_total,
                total_amount=original_quote.total_amount,
                status='Draft',
                quote_date=timezone.now().date(),
                valid_until=timezone.now().date() + timedelta(days=30),
                notes=original_quote.notes,
                reference_number='',  # Clear reference for new quote
                shipping_charges=original_quote.shipping_charges,
                adjustment_amount=original_quote.adjustment_amount,
                adjustment_reason=original_quote.adjustment_reason,
                tax_rate=original_quote.tax_rate,
                custom_terms=original_quote.custom_terms,
                include_vat=original_quote.include_vat,
                created_by=request.user
            )
            
            # Clone line items
            for item in QuoteLineItem.objects.filter(quote=original_quote).order_by('order'):
                QuoteLineItem.objects.create(
                    quote=new_quote,
                    product=item.product,
                    product_name=item.product_name,
                    customization_level_snapshot=item.customization_level_snapshot,
                    base_price_snapshot=item.base_price_snapshot,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    line_total=item.line_total,
                    discount_amount=item.discount_amount,
                    discount_type=item.discount_type,
                    variable_amount=item.variable_amount,
                    order=item.order
                )
            
            messages.success(request, f' Quote cloned successfully! New quote: {new_quote_id}')
            return redirect('quote_detail', quote_id=new_quote_id)
            
    except Exception as e:
        messages.error(request, f'Error cloning quote: {str(e)}')
        return redirect('quote_detail', quote_id=quote_id)


@login_required
def convert_quote_to_job(request, quote_id):
    """Convert an approved quote directly to a job"""
    quote = get_object_or_404(Quote, quote_id=quote_id)
    
    # Validate quote status
    if quote.status != 'Approved':
        messages.error(request, 'Only approved quotes can be converted to jobs.')
        return redirect('quote_detail', quote_id=quote_id)
    
    # Check if job already exists for this quote
    existing_job = Job.objects.filter(quote=quote).first()
    if existing_job:
        messages.info(request, f'Job {existing_job.job_number} already exists for this quote.')
        return redirect('job_detail', pk=existing_job.pk)
    
    try:
        with transaction.atomic():
            # Generate job number
            job_number = f"JOB-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
            
            # Create job from quote
            job = Job.objects.create(
                job_number=job_number,
                quote=quote,
                client=quote.client,
                product_name=quote.product_name,
                quantity=quote.quantity,
                status='Pending',
                priority='Medium',
                created_by=request.user
            )
            
            # Log activity
            if quote.client:
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='Order',
                    title=f"Job {job_number} Created from Quote {quote_id}",
                    description=f"Quote converted to production job.",
                    created_by=request.user
                )
            
            messages.success(request, f' Job {job_number} created successfully from quote {quote_id}.')
            return redirect('job_detail', pk=job.pk)
            
    except Exception as e:
        messages.error(request, f'Error converting quote to job: {str(e)}')
        return redirect('quote_detail', quote_id=quote_id)

def client_profile(request, pk):
    """Unified Client Profile View — includes jobs, quotes, activities, and financials"""
    client = get_object_or_404(Client, pk=pk)

    #Jobs
    jobs = client.jobs.all().order_by('-created_at')

    # Quotes
    all_quotes = client.quotes.all().order_by('-created_at')

    # Group quotes by quote_id (some quotes may have multiple line items)
    quotes_dict = {}
    for quote in all_quotes:
        if quote.quote_id not in quotes_dict:
            quotes_dict[quote.quote_id] = {
                'quote': quote,
                'items': [],
                'total_amount': Decimal('0'),
                'subtotal': Decimal('0')
            }
        quotes_dict[quote.quote_id]['items'].append(quote)
        quotes_dict[quote.quote_id]['total_amount'] += quote.total_amount
        quotes_dict[quote.quote_id]['subtotal'] += (quote.unit_price * quote.quantity)

    quotes_list = list(quotes_dict.values())

    #ACTIVITIES 
    activities = client.activities.all().order_by('-created_at')
    recent_activities = activities[:5]
    all_activities = activities

    # DOCUMENTS
    compliance_documents = ComplianceDocument.objects.filter(client=client)
    brand_assets = BrandAsset.objects.filter(client=client)

    # CONTACTS
    client_contacts = ClientContact.objects.filter(client=client)

    # ================= FINANCIAL METRICS =================
    total_revenue = all_quotes.filter(status='Approved').aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    total_jobs_count = jobs.count()
    
    # Conversion rate (approved quotes / total quotes)
    total_quotes = len(quotes_list)
    approved_quotes = sum(1 for q in quotes_list if q['quote'].status == 'Approved')
    conversion_rate = round((approved_quotes / total_quotes * 100), 1) if total_quotes > 0 else 0
    
    # Last activity
    last_activity_date = recent_activities.first().created_at if recent_activities.exists() else None

    # ================= CONTEXT =================
    context = {
        'client': client,
        'client_quotes': all_quotes,  
        'quotes': quotes_list,
        'client_jobs': jobs,
        'recent_activities': recent_activities,
        'all_activities': all_activities,
        'compliance_documents': compliance_documents,
        'brand_assets': brand_assets,
        'client_contacts': client_contacts,
        
        # Metrics for Overview tab
        'total_jobs': total_jobs_count,
        'total_revenue': total_revenue,
        'conversion_rate': conversion_rate,
        'last_activity_date': last_activity_date,
    }

    return render(request, 'client_profile.html', context)

def update_quote_status(request):
    """Handle quote approval, rejection, and discount requests"""
    if request.method == 'POST':
        quote_id = request.POST.get('quote_id')
        action = request.POST.get('action')
        
        try:
            # Get the first quote with this quote_id 
            quote = Quote.objects.filter(quote_id=quote_id).first()
            if not quote:
                return JsonResponse({'success': False, 'error': 'Quote not found'})
            
            if action == 'approve':
                quote.status = 'Approved'
                quote.save()
                
                # Create job automatically
                job = Job.objects.create(
                    client=quote.client,
                    quote=quote,
                    job_name=f"Job for {quote.product_name}",
                    job_type='printing',  
                    product=quote.product_name,
                    quantity=quote.quantity,
                    person_in_charge=None,  # Can be assigned later via API
                    status='pending',
                    expected_completion=quote.valid_until,
                    created_by=request.user
                )
                
                # Create activity log
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='Quote',
                    title=f"Quote {quote.quote_id} Approved - Job {job.job_number} Created",
                    description=f"Quote approved and job created for production",
                    related_quote=quote,
                    created_by=request.user
                )
                
                return JsonResponse({'success': True, 'message': f'Quote {quote.quote_id} approved successfully!'})
                
            elif action == 'reject':
                reject_reason = request.POST.get('reject_reason', '')
                quote.status = 'Lost'
                quote.loss_reason = reject_reason or 'Rejected by account manager'
                quote.save()
                
                # Create activity log
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='Quote',
                    title=f"Quote {quote.quote_id} Rejected",
                    description=f"Quote rejected: {reject_reason}",
                    related_quote=quote,
                    created_by=request.user
                )
                
                return JsonResponse({'success': True, 'message': f'Quote {quote.quote_id} rejected.'})
                
            elif action == 'discount':
                discount_notes = request.POST.get('discount_notes', '')
                # Create a notification or activity for discount request
                ActivityLog.objects.create(
                    client=quote.client,
                    activity_type='Quote',
                    title=f"Discount Requested - Quote {quote.quote_id}",
                    description=f"Discount request: {discount_notes}",
                    related_quote=quote,
                    created_by=request.user
                )
                
                return JsonResponse({'success': True, 'message': 'Discount request submitted to production team.'})
                
            elif action == 'status_update':
                new_status = request.POST.get('new_status')
                loss_reason = request.POST.get('loss_reason', '')
                
                quote.status = new_status
                if new_status == 'Lost':
                    quote.loss_reason = loss_reason
                quote.save()
                
                return JsonResponse({'success': True, 'message': f'Quote status updated to {new_status}.'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})



def quote_detail(request, quote_id):
    """View detailed quote with all items - Zoho-style with proper button visibility"""
    # Get quote (using quote_id, not pk)
    quote = Quote.objects.filter(quote_id=quote_id).first()
    
    if not quote:
        messages.error(request, 'Quote not found')
        return redirect('dashboard')
    
    # Get line items (preferred) or fallback to old quote records
    line_items = QuoteLineItem.objects.filter(quote=quote).order_by('order', 'created_at')
    
    # Calculate totals from line items
    if line_items.exists():
        subtotal = sum(item.line_total for item in line_items)
        quotes = []  # Empty for backward compatibility
    else:
        # Fallback: use old quote records
        quotes = Quote.objects.filter(quote_id=quote_id).order_by('id')
        subtotal = sum(q.unit_price * q.quantity for q in quotes)
        line_items = []
    
    vat_amount = subtotal * Decimal('0.16') if quote.include_vat else Decimal('0')
    total_amount = subtotal + vat_amount
    
    # Button visibility logic 
    can_send_to_customer, send_to_customer_error = quote.can_send_to_customer()
    can_send_to_pt, send_to_pt_error = quote.can_send_to_pt()
    
    # Check if quote is locked (sent to PT) - Account Managers cannot edit when sent to PT
    is_locked = quote.status == 'Sent to PT' and request.user.groups.filter(name='Account Manager').exists()
    
    # Pass error message to template
    context = {
        'quote_id': quote_id,
        'quote': quote,
        'quotes': quotes, 
        'line_items': line_items,
        'first_quote': quote,  
        'client': quote.client,
        'lead': quote.lead,
        'subtotal': subtotal,
        'can_send_to_customer': can_send_to_customer,
        'can_send_to_pt': can_send_to_pt,
        'send_to_customer_error': send_to_customer_error,
        'send_to_pt_error': send_to_pt_error,
        'is_locked': is_locked,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
        'production_updates': ProductionUpdate.objects.filter(quote=quote).select_related('created_by').order_by('-created_at'),
    }
    
    return render(request, 'quote_detail.html', context)



def delete_quote(request, quote_id):
    """Delete a quote and all its items"""
    if request.method == 'POST':
        # Delete all quotes with this quote_id
        quotes = Quote.objects.filter(quote_id=quote_id)
        client = quotes.first().client if quotes.exists() else None
        
        quotes.delete()
        
        messages.success(request, f'Quote {quote_id} deleted successfully')
        
        if client:
            return redirect('client_profile', pk=client.pk)
        return redirect('dashboard')
    
    return redirect('dashboard')

@login_required
def handle_quote_approval(request, quote_id):
    """
    Handle quote approval from client
    Creates notifications across all portals
    """
    try:
        quotes = Quote.objects.filter(quote_id=quote_id)
        if not quotes.exists():
            messages.error(request, 'Quote not found')
            return redirect('quotes_list')
        
        first_quote = quotes.first()
        lead = first_quote.lead
        
        # Update status
        quotes.update(status='Approved', approved_at=timezone.now())
        
        
        
        # 1. Notify the Account Manager who created the quote
        if first_quote.created_by:
            Notification.objects.create(
                recipient=first_quote.created_by,
                notification_type='quote_approved',
                title=f' Quote {quote_id} Approved!',
                message=f'Client approved your quote. Time to onboard them!',
                link=f'/client-onboarding/?lead_id={lead.id}' if lead else '/clients/',
                related_quote_id=quote_id,
                action_url=f'/client-onboarding/?lead_id={lead.id}' if lead else None,
                action_label='Onboard Client' if lead else None
            )
        
        # 2. Notify all Production Team members
        pt_users = User.objects.filter(groups__name='Production Team')
        for pt in pt_users:
            Notification.objects.create(
                recipient=pt,
                notification_type='quote_approved',
                title=f' Quote {quote_id} Approved',
                message=f'New approved quote ready for production. Value: KES {first_quote.total_amount:,.0f}',
                link=f'/quote-detail/{quote_id}/',
                related_quote_id=quote_id
            )
        
        # 3. Notify all Admins
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                notification_type='quote_approved',
                title=f'Quote {quote_id} Approved',
                message=f'Value: KES {first_quote.total_amount:,.0f}',
                link='/admin/clientapp/quote/',
                related_quote_id=quote_id
            )
        
        messages.success(request, f'Quote {quote_id} approved! Notifications sent.')
        return redirect('quote_detail', quote_id=quote_id)
        
    except Exception as e:
        messages.error(request, f'Error: {str(e)}')
        return redirect('quotes_list')


@login_required
@group_required('Account Manager')
def quotes_list(request):
    """List all quotes with filters"""
    from decimal import Decimal
    from datetime import datetime, timedelta
    
    all_quotes = Quote.objects.select_related('client', 'lead', 'created_by').order_by('-created_at')
    
    # Group quotes by quote_id
    quotes_dict = {}
    for quote in all_quotes:
        if quote.quote_id not in quotes_dict:
            # Determine client name
            client_name = '-'
            if quote.client:
                client_name = quote.client.name
            elif quote.lead:
                client_name = quote.lead.name
            
            # Determine account manager
            account_manager = '-'
            if quote.created_by:
                account_manager = quote.created_by.get_full_name() or quote.created_by.username
            
            # Calculate valid until date (30 days from creation)
            valid_until = quote.created_at + timedelta(days=30)
            days_remaining = (valid_until.date() - datetime.now().date()).days
            
            quotes_dict[quote.quote_id] = {
                'id': quote.id,
                'quote_number': quote.quote_id,
                'client_name': client_name,
                'account_manager': account_manager,
                'item_count': 0,
                'approved_items': 0,
                'total_value': Decimal('0'),
                'total_cost': Decimal('0'),
                'margin': 0,
                'status': quote.status,
                'created_date': quote.created_at.strftime('%b %d, %Y'),
                'valid_until': valid_until.strftime('%b %d, %Y'),
                'days_remaining': days_remaining,
            }
        
        # Increment counters
        quotes_dict[quote.quote_id]['item_count'] += 1
        quotes_dict[quote.quote_id]['total_value'] += quote.total_amount
        if quote.production_cost: 
            quotes_dict[quote.quote_id]['total_cost'] += quote.production_cost
        # Count approved items
        if quote.status == 'Approved':
            quotes_dict[quote.quote_id]['approved_items'] += 1
        
        # Calculate margin 
        if quote.unit_price > 0:
            
            quotes_dict[quote.quote_id]['margin'] = 25.0
        for q in quotes_dict.values():
            if q['total_value'] > 0:
                cost = q['total_cost']
                q['margin'] = ((q['total_value'] - cost) / q['total_value']) * 100
            else:
                q['margin'] = 0
    quotes_list = list(quotes_dict.values())

    total_quotes_count = len(quotes_list)
    pending_approval_count = sum(1 for q in quotes_list if q['status'] == 'Pending PT Approval')
    total_value = sum(q['total_value'] for q in quotes_list)
    avg_margin = sum(q['margin'] for q in quotes_list) / total_quotes_count if total_quotes_count > 0 else 0
    
    # Apply status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter and status_filter != 'all':
        quotes_list = [q for q in quotes_list if q['status'] == status_filter]
    
    # Apply search filter
    search_query = request.GET.get('search', '')
    if search_query:
        quotes_list = [q for q in quotes_list if 
                      search_query.lower() in q['quote_number'].lower() or 
                      search_query.lower() in q['client_name'].lower()]
    
    context = {
        'quotes': quotes_list,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_quotes_count': total_quotes_count,
        'pending_approval_count': pending_approval_count,
        'total_value': total_value,
        'avg_margin': avg_margin,
    }
    
    return render(request, 'quote_list.html', context)


def get_client_details(request, client_id):
    """API endpoint to get client details for quote form"""
    try:
        client = get_object_or_404(Client, id=client_id)
        data = {
            'success': True,
            'name': client.company if client.company else client.name,
            'email': client.email,
            'phone': client.phone,
            'address': client.address,
            'default_markup': float(client.default_markup),
            'payment_terms': client.payment_terms,
            'client_type': client.client_type,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def get_lead_details(request, lead_id):
    """API endpoint to get lead details for quote form"""
    try:
        lead = get_object_or_404(Lead, id=lead_id)
        data = {
            'success': True,
            'name': lead.name,
            'email': lead.email,
            'phone': lead.phone,
            'default_markup': 35,  
            'payment_terms': 'Prepaid',
            'source': lead.source if hasattr(lead, 'source') else '',
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def save_quote_draft(request):
    """Save quote as draft via AJAX"""
    if request.method == 'POST':
        try:
            # Get JSON data
            data = json.loads(request.body)
            
            quote_type = data.get('quote_type')
            client_id = data.get('client_id')
            lead_id = data.get('lead_id')
            
            client = None
            lead = None
            
            if quote_type == 'client' and client_id:
                client = get_object_or_404(Client, id=client_id)
            elif quote_type == 'lead' and lead_id:
                lead = get_object_or_404(Lead, id=lead_id)
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Please select a client or lead'
                }, status=400)
            
            items = data.get('items', [])
            
            if not items:
                return JsonResponse({
                    'success': False,
                    'error': 'Please add at least one item'
                }, status=400)
            
            # Create draft quotes
            created_quotes = []
            for item in items:
                quote = Quote.objects.create(
                    client=client,
                    lead=lead,
                    product_name=item['description'],
                    quantity=item['quantity'],
                    cost_price=Decimal(str(item['cost'])),
                    markup_percentage=Decimal(str(item['markup'])),
                    selling_price=Decimal(str(item['price'])),
                    status='Draft',
                    notes=data.get('notes', ''),
                    created_by=request.user
                )
                created_quotes.append(quote)
            
            return JsonResponse({
                'success': True,
                'message': 'Draft saved successfully',
                'quote_id': created_quotes[0].quote_id if created_quotes else None
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    }, status=400)

@login_required
@group_required('Production Team')
@transaction.atomic
def create_job(request):
    """Create a new production job with detailed line items"""
    clients = Client.objects.filter(status='Active').order_by('name')

    def parse_date(value):
        if not value:
            return None
        try:
            return datetime.fromisoformat(value).date()
        except ValueError:
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return None

    if request.method == 'POST':
            client_id = request.POST.get('client_id')
            if not client_id:
                messages.error(request, 'Please select a client.')
                return redirect('create_job')
            
            client = get_object_or_404(Client, id=client_id)
            
            job_name = request.POST.get('job_name', '').strip()
            job_type = request.POST.get('job_type', 'other')
            priority = request.POST.get('priority', 'normal')
            person_in_charge = request.POST.get('person_in_charge', '').strip()
            status = request.POST.get('status', 'pending').lower()
            notes = request.POST.get('notes', '')
            
            if status not in dict(Job.STATUS_CHOICES):
                status = 'pending'

            if not job_name or not person_in_charge:
                messages.error(request, 'Job name and person in charge are required.')
                return redirect('create_job')
            
            products_data = []
            for idx in range(1, 6):
                product_name = request.POST.get(f'product_name_{idx}', '').strip()
                if not product_name:
                    continue
                quantity_raw = request.POST.get(f'quantity_{idx}', '1')
                try:
                    quantity_val = int(quantity_raw)
                except ValueError:
                    quantity_val = 1
                if quantity_val <= 0:
                    quantity_val = 1
                unit = request.POST.get(f'unit_{idx}', 'pcs')
                specs = request.POST.get(f'specifications_{idx}', '')
                products_data.append({
                    'name': product_name,
                    'quantity': quantity_val,
                    'unit': unit,
                    'specs': specs,
                })
            
            if not products_data:
                messages.error(request, 'Please add at least one product line item.')
                return redirect('create_job')
            
            start_date = parse_date(request.POST.get('start_date')) or timezone.now().date()
            expected_completion = parse_date(request.POST.get('expected_completion')) or start_date
            delivery_date = parse_date(request.POST.get('delivery_date'))
            delivery_method = request.POST.get('delivery_method', 'pickup')

            main_product = products_data[0]

            job = Job.objects.create(
                client=client,
                job_name=job_name,
                job_type=job_type,
                priority=priority,
                product=main_product['name'],
                quantity=main_product['quantity'],
                person_in_charge=person_in_charge,
                status=status,
                start_date=start_date,
                expected_completion=expected_completion,
                delivery_date=delivery_date,
                delivery_method=delivery_method,
                notes=notes,
                created_by=request.user
            )

            for product_data in products_data:
                JobProduct.objects.create(
                    job=job,
                    product_name=product_data['name'],
                    quantity=product_data['quantity'],
                    unit=product_data['unit'],
                    specifications=product_data['specs'],
                )

                ActivityLog.objects.create(
                    client=client,
                    activity_type='Order',
                    title=f"Job Created - {job.job_number}",
                    description=f"Job {job.job_name} created with priority {job.priority} and status {job.status}.",
                    created_by=request.user
                )
                
            ProductionUpdate.objects.create(
                update_type='job',
                job=job,
                status='pending',
                progress=0,
                notes='Job created and scheduled.',
                created_by=request.user
            )
                
            messages.success(request, f"Job '{job.job_name}' created successfully for {client.name}.")
            return redirect('job_detail', pk=job.pk)
    
    context = {
        'clients': clients,
        'current_year': timezone.now().year,
        'current_view': 'production_jobs',
    }
    return render(request, 'create_job.html', context)


@login_required
def job_detail(request, pk):
    """View job details with all related information"""
    from django.utils import timezone
    from datetime import timedelta
    from decimal import Decimal
    
    job = get_object_or_404(Job.objects.select_related('client', 'quote', 'created_by'), pk=pk)
    
    # Get related data
    attachments = job.attachments.select_related('uploaded_by').order_by('-uploaded_at')
    notes = job.job_notes.select_related('created_by').order_by('-created_at')
    production_updates = job.production_updates.select_related('created_by').order_by('-created_at')
    
    # Get vendor stages
    vendor_stages = job.vendor_stages.select_related('vendor').order_by('stage_order') if hasattr(job, 'vendor_stages') else []
    
    # Get QC inspection if exists
    qc_inspection = None
    try:
        qc_inspection = job.qc_inspection
    except:
        pass
    
    # Calculate progress
    overall_progress = 0
    current_stage = None
    if vendor_stages:
        total_stages = len(vendor_stages)
        completed_stages = sum(1 for s in vendor_stages if s.status == 'completed')
        in_progress_stage = next((s for s in vendor_stages if s.status in ['in_production', 'sent_to_vendor']), None)
        
        if in_progress_stage:
            # Calculate based on stages + current stage progress
            base_progress = (completed_stages / total_stages) * 100
            stage_contribution = (in_progress_stage.progress / total_stages)
            overall_progress = int(base_progress + stage_contribution)
            current_stage = in_progress_stage
        else:
            overall_progress = int((completed_stages / total_stages) * 100) if completed_stages > 0 else 0
    elif job.status == 'completed':
        overall_progress = 100
    elif job.status == 'in_progress':
        # Get from last production updatee
        last_update = production_updates.first()
        overall_progress = last_update.progress if last_update else 50
    else:
        overall_progress = 0
    
    # Calculate deadline
    now = timezone.now()
    deadline = timezone.make_aware(
        timezone.datetime.combine(job.expected_completion, timezone.datetime.min.time())
    ) if job.expected_completion else now
    time_remaining = deadline - now
    hours_remaining = int(time_remaining.total_seconds() / 3600)
    is_overdue = hours_remaining < 0
    
    if is_overdue:
        deadline_text = f"Overdue by {abs(hours_remaining)}h"
    elif hours_remaining < 24:
        deadline_text = f"{hours_remaining}h remaining"
    else:
        days_remaining = hours_remaining // 24
        deadline_text = f"{days_remaining} days remaining"
    
    # Get primary vendor
    primary_vendor = None
    if vendor_stages:
        current = current_stage or vendor_stages[0]
        primary_vendor = current.vendor
    
    # Get account manager who created this job
    am_name = "System"
    if job.created_by:
        am_name = job.created_by.get_full_name() or job.created_by.username
    
    # Calculate current stage info
    current_stage_text = "Not Started"
    if current_stage:
        current_stage_text = f"{current_stage.stage_name} (Day {(now - current_stage.started_at).days + 1 if current_stage.started_at else 1} of {(current_stage.expected_completion - current_stage.started_at).days if current_stage.started_at and current_stage.expected_completion else '?'})"
    elif job.status == 'completed':
        current_stage_text = "Completed"
    elif job.status == 'in_progress':
        current_stage_text = "Vendor Production"
    
    # Get job specs from quote
    specs = {}
    if job.quote:
        specs = {
            'product_type': job.quote.product_name or job.product,
            'colors': '4/4 (CMYK both sides)',  # Default, could be stored in quote
            'size': 'A4 (210mm × 297mm)',  
            'finishing': 'Matt Lamination',  # Default
            'quantity': f"{job.quantity:,} pcs",
            'folding': 'Tri-fold',  # Default
            'material': '150gsm Gloss Art Paper', 
            'binding': 'None', 
        }
    else:
        specs = {
            'product_type': job.product,
            'colors': '4/4 (CMYK both sides)',
            'size': 'A4 (210mm × 297mm)',
            'finishing': 'Matt Lamination',
            'quantity': f"{job.quantity:,} pcs",
            'folding': 'None',
            'material': 'Standard',
            'binding': 'None',
        }
    
    # Check if user can manage
    can_manage = request.user.groups.filter(name='Production Team').exists()
    
    # Get all jobs for the same client
    client_jobs = []
    job_stats = {'total': 0, 'in_progress': 0, 'overdue': 0, 'completed': 0, 'pending': 0}
    
    if job.client:
        client_jobs_qs = Job.objects.filter(client=job.client).select_related('quote').order_by('-created_at')
        for cj in client_jobs_qs:
            # Calculate progress for each job
            cj_progress = 0
            if cj.status == 'completed':
                cj_progress = 100
            elif cj.status == 'in_progress':
                cj_progress = 50
            elif cj.status == 'pending':
                cj_progress = 10
            
            # Calculate deadline info
            cj_days = (cj.expected_completion - now.date()).days if cj.expected_completion else 0
            cj_is_overdue = cj_days < 0
            
            client_jobs.append({
                'id': cj.id,
                'job_number': cj.job_number,
                'product': cj.product,
                'quantity': cj.quantity,
                'status': cj.status,
                'status_display': cj.get_status_display(),
                'priority': cj.priority,
                'priority_display': cj.get_priority_display(),
                'expected_completion': cj.expected_completion,
                'days_remaining': cj_days,
                'is_overdue': cj_is_overdue,
                'progress': cj_progress,
                'is_current': cj.id == job.id,
                'job_type': cj.get_job_type_display(),
                'person_in_charge': cj.person_in_charge,
                'notes': cj.notes[:50] + '...' if cj.notes and len(cj.notes) > 50 else cj.notes,
            })
            
            # Update stats
            job_stats['total'] += 1
            if cj.status == 'in_progress':
                job_stats['in_progress'] += 1
            elif cj.status == 'completed':
                job_stats['completed'] += 1
            elif cj.status == 'pending':
                job_stats['pending'] += 1
            if cj_is_overdue and cj.status != 'completed':
                job_stats['overdue'] += 1
    
    context = {
        'job': job,
        'current_view': 'my_jobs',
        'client_jobs': client_jobs,
        'job_stats': job_stats,
        
        # Progress info
        'overall_progress': overall_progress,
        'current_stage': current_stage,
        'current_stage_text': current_stage_text,
        
        # Deadline info
        'deadline_text': deadline_text,
        'hours_remaining': hours_remaining,
        'is_overdue': is_overdue,
        
        # Related data
        'attachments': attachments,
        'notes': notes,
        'production_updates': production_updates,
        'vendor_stages': vendor_stages,
        'qc_inspection': qc_inspection,
        
        # Vendor info
        'primary_vendor': primary_vendor,
        'am_name': am_name,
        
        # Job specs
        'specs': specs,
        
        # Permissions
        'can_manage': can_manage,
        
        # For vendor/process lists
        'vendors': Vendor.objects.filter(active=True).order_by('name'),
    }
    
    return render(request, 'job_detail.html', context)


@login_required
@require_POST
def add_job_note(request, pk):
    """Add a note to a job"""
    job = get_object_or_404(Job, pk=pk)
    
    content = request.POST.get('content', '').strip()
    note_type = request.POST.get('note_type', 'general')
    
    if not content:
        return JsonResponse({'success': False, 'message': 'Note content is required'})
    
    try:
        from clientapp.models import JobNote
        
        note = JobNote.objects.create(
            job=job,
            content=content,
            note_type=note_type,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Note added successfully',
            'note': {
                'id': note.id,
                'content': note.content,
                'note_type': note.note_type,
                'created_by': note.created_by.get_full_name() or note.created_by.username,
                'created_at': note.created_at.strftime('%b %d, %H:%M'),
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def upload_job_file(request, pk):
    """Upload a file attachment to a job"""
    job = get_object_or_404(Job, pk=pk)
    
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'message': 'No file provided'})
    
    uploaded_file = request.FILES['file']
    
    # Validate file size (max 10MB)
    if uploaded_file.size > 10 * 1024 * 1024:
        return JsonResponse({'success': False, 'message': 'File too large (max 10MB)'})
    
    try:
        from clientapp.models import JobAttachment
        
        attachment = JobAttachment.objects.create(
            job=job,
            file=uploaded_file,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            uploaded_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'File uploaded successfully',
            'attachment': {
                'id': attachment.id,
                'file_name': attachment.file_name,
                'file_size': f"{attachment.file_size / 1024:.1f} KB" if attachment.file_size < 1024*1024 else f"{attachment.file_size / (1024*1024):.1f} MB",
                'uploaded_at': attachment.uploaded_at.strftime('%b %d, %H:%M'),
                'download_url': attachment.file.url,
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def update_job_progress(request, pk):
    """Update job progress and vendor stage"""
    job = get_object_or_404(Job, pk=pk)
    
    try:
        import json
        data = json.loads(request.body)
        
        stage_id = data.get('stage_id')
        progress = data.get('progress', 0)
        status = data.get('status')
        notes = data.get('notes', '')
        
        if stage_id:
            from clientapp.models import JobVendorStage
            stage = get_object_or_404(JobVendorStage, pk=stage_id, job=job)
            stage.progress = progress
            if status:
                stage.status = status
                if status == 'completed' and not stage.completed_at:
                    stage.completed_at = timezone.now()
                elif status == 'in_production' and not stage.started_at:
                    stage.started_at = timezone.now()
            if notes:
                stage.notes = notes
            stage.save()
        
        # Update overall job status
        if data.get('mark_completed'):
            job.status = 'completed'
            job.actual_completion = timezone.now().date()
            job.save()
            
            # Also update related LPO status to 'completed'
            if job.quote and hasattr(job.quote, 'lpo'):
                try:
                    lpo = job.quote.lpo
                    if lpo.status != 'completed':
                        lpo.status = 'completed'
                        lpo.save()
                except:
                    pass
        
        return JsonResponse({'success': True, 'message': 'Progress updated'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def add_vendor_stage(request, pk):
    """Add a new vendor stage to a job"""
    job = get_object_or_404(Job, pk=pk)
    
    try:
        from clientapp.models import JobVendorStage
        
        vendor_id = request.POST.get('vendor_id')
        stage_name = request.POST.get('stage_name', 'Production')
        expected_days = int(request.POST.get('expected_days', 3))
        vendor_cost = request.POST.get('vendor_cost', 0)
        
        vendor = get_object_or_404(Vendor, pk=vendor_id)
        
        # Get next stage order
        last_stage = job.vendor_stages.order_by('-stage_order').first()
        next_order = (last_stage.stage_order + 1) if last_stage else 1
        
        stage = JobVendorStage.objects.create(
            job=job,
            vendor=vendor,
            stage_order=next_order,
            stage_name=stage_name,
            expected_completion=timezone.now() + timedelta(days=expected_days),
            vendor_cost=vendor_cost,
        )
        
        # Update job status 
        if next_order == 1:
            job.status = 'in_progress'
            job.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Stage "{stage_name}" added',
            'stage_id': stage.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@group_required('Production Team')
def qc_inspection_start(request, job_id):
    """Start a QC inspection for a completed job"""
    job = get_object_or_404(Job.objects.select_related('client'), pk=job_id)
    
    # Check if QC inspection already exists
    try:
        existing_qc = job.qc_inspection
        
        return redirect('qc_inspection', inspection_id=existing_qc.id)
    except:
        pass
    
   
    
    # Create new QC inspection
    try:
        from clientapp.models import QCInspection, Vendor
        
        # Generate reference number
        from django.utils import timezone
        year = timezone.now().year
        month = timezone.now().month
        count = QCInspection.objects.filter(
            created_at__year=year,
            created_at__month=month
        ).count() + 1
        ref_number = f"QC-{year}{month:02d}-{count:04d}"
        
        # Get vendor from job's vendor stages if available
        vendor = None
        if hasattr(job, 'vendor_stages') and job.vendor_stages.exists():
            last_stage = job.vendor_stages.order_by('-stage_order').first()
            vendor = last_stage.vendor if last_stage else None
        
        # If no vendor, get the first active vendor as default
        if not vendor:
            vendor = Vendor.objects.filter(active=True).first()
        
        if not vendor:
            messages.error(request, 'No vendor available for QC inspection. Please add a vendor first.')
            return redirect('job_detail', pk=job_id)
        
        qc = QCInspection.objects.create(
            job=job,
            status='pending',
            inspector=request.user
        )
        
        messages.success(request, f'QC Inspection {ref_number} started.')
        return redirect('qc_inspection', inspection_id=qc.id)
    except Exception as e:
        messages.error(request, f'Error creating QC inspection: {str(e)}')
        return redirect('job_detail', pk=job_id)

#sidebar
@login_required
@group_required('Account Manager')
def base_view(request):
    """Simple base view used by sidebar link"""
    return render(request, 'base2.html', {})


@login_required
@group_required('Production Team')
def quote_review_queue(request):
    """Quote review / queue for Production Team"""
    status_filter = request.GET.get('status', 'pending')
    search = request.GET.get('search', '').strip()

    quotes_qs = Quote.objects.select_related('client', 'lead', 'created_by').order_by('-created_at')

    if status_filter == 'pending':
        quotes_qs = quotes_qs.filter(production_status__in=['pending', 'in_progress'])
    elif status_filter == 'costed':
        quotes_qs = quotes_qs.filter(production_status='costed')
    elif status_filter == 'sent':
        quotes_qs = quotes_qs.filter(status__in=['Quoted', 'Client Review'])
    elif status_filter == 'approved':
        quotes_qs = quotes_qs.filter(status='Approved')

    if search:
        quotes_qs = quotes_qs.filter(
            Q(quote_id__icontains=search) |
            Q(product_name__icontains=search) |
            Q(client__name__icontains=search) |
            Q(lead__name__icontains=search)
        )

    quotes = list(quotes_qs)
    cost_forms = {quote.quote_id: QuoteCostingForm(instance=quote) for quote in quotes}

    context = {
        'current_view': 'production_quotes',
        'quotes': quotes,
        'status_filter': status_filter,
        'search': search,
        'cost_forms': cost_forms,
        'pending_count': Quote.objects.filter(production_status__in=['pending', 'in_progress']).count(),
        'costed_count': Quote.objects.filter(production_status='costed').count(),
        'sent_count': Quote.objects.filter(status__in=['Quoted', 'Client Review']).count(),
        'approved_count': Quote.objects.filter(status='Approved').count(),
    }
    return render(request, 'quote_review.html', context)


@login_required
@group_required('Production Team')
@transaction.atomic
def update_quote_costing(request, quote_id):
    """Update costing details for a quote"""
    quote = get_object_or_404(Quote, quote_id=quote_id)
    related_quotes = Quote.objects.filter(quote_id=quote.quote_id).order_by('created_at')

    if request.method == 'POST':
        form = QuoteCostingForm(request.POST, instance=quote)
        if form.is_valid():
            if not form.has_changed():
                messages.info(request, 'No changes detected in the costing form.')
                return redirect('production_quote_review')

            quote_obj = form.save(commit=False)
            if quote_obj.production_status == 'pending':
                quote_obj.production_status = 'costed'
            if quote_obj.status == 'Draft' and quote_obj.production_status in ['costed', 'sent_to_client']:
                quote_obj.status = 'Quoted'
            quote_obj.costed_by = request.user
            quote_obj.save()

            progress = 50
            if quote_obj.production_status in ['sent_to_client', 'in_production', 'completed']:
                progress = 100

            ProductionUpdate.objects.create(
                update_type='quote',
                quote=quote_obj,
                status=quote_obj.production_status,
                progress=progress,
                notes=form.cleaned_data.get('production_notes', ''),
                created_by=request.user
            )

            messages.success(request, f'Quote {quote_obj.quote_id} updated successfully.')
            return redirect('my_quotes')
    else:
        form = QuoteCostingForm(instance=quote)

    context = {
        'quote': quote,
        'related_quotes': related_quotes,
        'form': form,
        'current_view': 'production_quotes',
        'processes': Process.objects.filter(status='active'),
    }
    return render(request, 'approve_quote.html', context)



@login_required
@group_required('Production Team')
@transaction.atomic
def update_quote_costing_v2(request, quote_id):
    """
    Updated quote costing with Process integration
    Automatically pulls costs from linked processes
    """
    quote = get_object_or_404(Quote, quote_id=quote_id)
    related_quotes = Quote.objects.filter(quote_id=quote.quote_id).order_by('created_at')
    
    if request.method == 'POST':
        try:
            # Get form data
            action = request.POST.get('action', 'save')
            
            # Get line items
            line_items = QuoteLineItem.objects.filter(quote=quote).order_by('order', 'created_at')
            
            if line_items.exists():
                # Update QuoteLineItem prices with PT costing
                total_amount = Decimal('0')
                
                for item in line_items:
                    # Get costs from form (use line item ID)
                    unit_price_key = f'unit_price_{item.id}'
                    production_cost_key = f'production_cost_{item.id}'
                    vendor_id_key = f'selected_vendor_{item.id}'
                    
                    # Update unit price if provided
                    if unit_price_key in request.POST and request.POST[unit_price_key]:
                        try:
                            item.unit_price = Decimal(request.POST[unit_price_key])
                            item.save()  
                        except (ValueError, TypeError):
                            pass
                    
                    # Store production cost if provided
                    if production_cost_key in request.POST and request.POST[production_cost_key]:
                        try:
                            quote.production_cost = Decimal(request.POST[production_cost_key])
                        except (ValueError, TypeError):
                            pass
                    
                    total_amount += item.line_total
                
                # Update quote totals from line items
                quote.total_amount = total_amount
                if quote.include_vat:
                    vat_amount = total_amount * Decimal('0.16')
                    quote.total_amount = total_amount + vat_amount
            else:
                # Fallback
                for q in related_quotes:
                    production_cost = request.POST.get(f'production_cost_{q.id}')
                    vendor_id = request.POST.get(f'selected_vendor_{q.id}')
                    
                    if production_cost:
                        q.production_cost = Decimal(production_cost)
                    q.save()
            
            # Update status based on action
            if action == 'approve':
                quote.production_status = 'costed'
                quote.costed_by = request.user
                
                if quote.status == 'Draft':
                    # Temporarily bypass validation to set intermediate status
                    quote._skip_status_validation = True
                    quote.status = 'Sent to PT'
                    quote.save()
                    quote._skip_status_validation = False
                # Now transition to Costed
                quote.status = 'Costed'
                quote.save()
            
            # Create production update
            ProductionUpdate.objects.create(
                update_type='quote',
                quote=quote,
                status='costed' if action == 'approve' else 'in_progress',
                progress=100 if action == 'approve' else 50,
                notes=request.POST.get('production_notes', ''),
                created_by=request.user
            )
            
            if action == 'approve':
                # Notify AM
                Notification.objects.create(
                    recipient=quote.created_by,
                    notification_type='quote_pt_approved',
                    title=f' Quote {quote_id} Costed & Ready',
                    message=f'Production team has costed your quote. You can now send it to the client.',
                    link=reverse('quote_detail', args=[quote_id]),
                    related_quote_id=quote_id,
                    action_url=reverse('quote_detail', args=[quote_id]),
                    action_label='View Quote'
                )
                
                messages.success(request, f' Quote {quote_id} costed and approved!')
            else:
                messages.success(request, f' Quote {quote_id} costing saved as draft.')
            
            return redirect('production_quote_review')
            
        except Exception as e:
            messages.error(request, f'Error saving costing: {str(e)}')
            import traceback
            traceback.print_exc()
            return redirect('production_quote_costing_v2', quote_id=quote_id)
    
    
    
    # Get all available processes
    processes = Process.objects.filter(status='active').order_by('process_name')
    
    # Get line items 
    line_items_objs = QuoteLineItem.objects.filter(quote=quote).order_by('order', 'created_at')
    
    # Prepare line items 
    line_items = []
    
    if line_items_objs.exists():
        # Use QuoteLineItem
        for item in line_items_objs:
            suggested_process = None
            process_cost = None
            available_vendors = []
            
            # Try to find matching process by product
            if item.product and hasattr(item.product, 'pricing'):
                pricing = item.product.pricing
                if pricing.process:
                    suggested_process = pricing.process
                elif pricing.formula_process:
                    suggested_process = pricing.formula_process
                elif pricing.tier_process:
                    suggested_process = pricing.tier_process
            
            # If no process linked, search by product name similarity
            if not suggested_process:
                for process in processes:
                    if item.product_name.lower() in process.process_name.lower() or \
                       process.process_name.lower() in item.product_name.lower():
                        suggested_process = process
                        break
            
            # Get pricing based on quantity
            if suggested_process and suggested_process.pricing_type == 'tier':
                tier = suggested_process.tiers.filter(
                    quantity_from__lte=item.quantity,
                    quantity_to__gte=item.quantity
                ).first()
                if tier:
                    process_cost = tier.cost
            
            # Get vendors
            if suggested_process:
                available_vendors = suggested_process.process_vendors.all().order_by('-vps_score')
            
            line_items.append({
                'line_item': item,
                'quote': None,  
                'suggested_process': suggested_process,
                'process_cost': process_cost,
                'available_vendors': available_vendors,
                'current_cost': item.unit_price or Decimal('0'),
            })
    else:
        # Fallback: use old quote records
        for q in related_quotes:
            suggested_process = None
            process_cost = None
            available_vendors = []
            
            # Search for process by product name similarity
            for process in processes:
                if q.product_name.lower() in process.process_name.lower() or \
                   process.process_name.lower() in q.product_name.lower():
                    suggested_process = process
                    
                    # Get pricing based on quantity
                    if process.pricing_type == 'tier':
                        tier = process.tiers.filter(
                            quantity_from__lte=q.quantity,
                            quantity_to__gte=q.quantity
                        ).first()
                        if tier:
                            process_cost = tier.cost
                    
                    # Get vendors
                    available_vendors = process.process_vendors.all().order_by('-vps_score')
                    break
            
            line_items.append({
                'line_item': None,
                'quote': q,
                'suggested_process': suggested_process,
                'process_cost': process_cost,
                'available_vendors': available_vendors,
                'current_cost': q.production_cost or Decimal('0'),
            })
    
    context = {
        'quote_id': quote_id,
        'quote': quote,
        'line_items': line_items,
        'processes': processes,
        'current_view': 'production_quotes',
    }
    
    return render(request, 'quote_costing_v2.html', context)


@login_required
@group_required('Production Team')
def production_catalog(request):
    """Production Team product/catalog view with create & update actions"""
    search = request.GET.get('search', '').strip()
    product_type = request.GET.get('product_type', 'all')
    availability = request.GET.get('availability', 'all')

    products = Product.objects.all()

    # Apply filters
    if search:
        products = products.filter(Q(name__icontains=search) | Q(internal_code__icontains=search))
    if product_type != 'all':
        products = products.filter(product_type=product_type)
    if availability != 'all':
        products = products.filter(availability=availability)

    products = products.order_by('name')

    editing_product = None
    form = ProductionUpdateForm()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        product_id = request.POST.get('product_id')

        if action == 'toggle' and product_id:
            product = get_object_or_404(Product, pk=product_id)
            product.is_active = not product.is_active
            product.updated_by = request.user
            product.save(update_fields=['is_active', 'updated_at', 'updated_by'])
            messages.success(request, f'{product.name} status updated.')
            return redirect('production_catalog')

        if product_id:
            editing_product = get_object_or_404(Product, pk=product_id)

        form = ProductionUpdateForm(request.POST, instance=editing_product)
        if form.is_valid():
            product = form.save(commit=False)
            if editing_product is None:
                product.created_by = request.user
            product.updated_by = request.user
            product.save()
            messages.success(request, f'Product {product.name} saved successfully.')
            return redirect('production_catalog')
    else:
        product_id = request.GET.get('product_id')
        if product_id:
            editing_product = get_object_or_404(Product, pk=product_id)
            form = ProductionUpdateForm(instance=editing_product)

    context = {
        'current_view': 'production_catalog',
        'products': products,
        'form': form,
        'editing_product': editing_product,
        'search': search,
        'product_type': product_type,
        'availability': availability,
    }
    return render(request, 'product_catalog.html', context)



# PROCESS MANAGEMENT VIEWS (FORMULA-BASED PRICING)

@login_required
@require_POST
def ajax_delete_process(request, process_id):
    """Delete a process via AJAX"""
    try:
        process = get_object_or_404(Process, pk=process_id)
        process_name = process.process_name
        process.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Process "{process_name}" deleted successfully'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

@login_required
def process_variable_ranges_manager(request, process_id):
    """
    Web interface to manage variable ranges for a process
    """
    from .models import Process, ProcessVariable, ProcessVariableRange
    from django.contrib import messages
    
    process = get_object_or_404(Process, pk=process_id)
    
    if process.pricing_type != 'formula':
        messages.error(request, f"Process {process.process_name} is not formula-based.")
        return redirect('process_list')
    
    variables = process.variables.all().prefetch_related('ranges')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_range':
            return add_variable_range(request, process)
        elif action == 'delete_range':
            return delete_variable_range(request, process)
        elif action == 'create_sample_ranges':
            return create_sample_ranges(request, process)
    
    context = {
        'process': process,
        'variables': variables,
    }
    
    return render(request, 'process_variable_ranges_manager.html', context)

@login_required
def add_variable_range(request, process):
    """
    Add a new variable range via AJAX
    """
    from .models import ProcessVariable, ProcessVariableRange
    from django.contrib import messages
    
    try:
        variable_id = request.POST.get('variable_id')
        min_value = request.POST.get('min_value')
        max_value = request.POST.get('max_value')
        price = request.POST.get('price')
        rate = request.POST.get('rate') or '1.0'
        order = request.POST.get('order') or '1'
        
        variable = get_object_or_404(ProcessVariable, pk=variable_id, process=process)
        
        # Convert to Decimal
        min_val = Decimal(min_value) if min_value else None
        max_val = Decimal(max_value) if max_value else None
        price_val = Decimal(price) if price else Decimal('0')
        rate_val = Decimal(rate)
        order_val = int(order)
        
        # Create the range
        range_obj = ProcessVariableRange.objects.create(
            variable=variable,
            min_value=min_val,
            max_value=max_val,
            price=price_val,
            rate=rate_val,
            order=order_val
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Range added successfully',
                'range': {
                    'id': range_obj.id,
                    'min_value': str(range_obj.min_value) if range_obj.min_value else '',
                    'max_value': str(range_obj.max_value) if range_obj.max_value else '',
                    'price': str(range_obj.price),
                    'rate': str(range_obj.rate),
                    'order': range_obj.order
                }
            })
        
        messages.success(request, 'Variable range added successfully!')
        
    except Exception as e:
        error_msg = f'Error adding range: {str(e)}'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_msg})
        messages.error(request, error_msg)
    
    return redirect('process_variable_ranges_manager', process_id=process.id)

@login_required
def delete_variable_range(request, process):
    """
    Delete a variable range via AJAX
    """
    from .models import ProcessVariableRange
    from django.contrib import messages
    
    try:
        range_id = request.POST.get('range_id')
        range_obj = get_object_or_404(ProcessVariableRange, pk=range_id, variable__process=process)
        range_obj.delete()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Range deleted successfully'
            })
        
        messages.success(request, 'Variable range deleted successfully!')
        
    except Exception as e:
        error_msg = f'Error deleting range: {str(e)}'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_msg})
        messages.error(request, error_msg)
    
    return redirect('process_variable_ranges_manager', process_id=process.id)

@login_required
def create_sample_ranges(request, process):
    """
    Create sample ranges for all variables in a process
    """
    from .models import ProcessVariable, ProcessVariableRange
    from django.contrib import messages
    
    try:
        variables = process.variables.all()
        ranges_created = 0
        
        for variable in variables:
            # Check if ranges already exist
            if variable.ranges.exists():
                continue
            
            # Create sample ranges based on variable type and name
            ranges_created += create_sample_ranges_for_variable(variable)
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Created {ranges_created} sample ranges',
                'ranges_created': ranges_created
            })
        
        messages.success(request, f'Created {ranges_created} sample ranges!')
        
    except Exception as e:
        error_msg = f'Error creating sample ranges: {str(e)}'
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': error_msg})
        messages.error(request, error_msg)
    
    return redirect('process_variable_ranges_manager', process_id=process.id)

def create_sample_ranges_for_variable(variable):
    """
    Create sample ranges for a specific variable
    """
    from .models import ProcessVariableRange
    
    ranges_created = 0
    
    # Stitch Count ranges
    if 'stitch' in variable.variable_name.lower():
        sample_ranges = [
            (1, 1000, Decimal('0.15'), Decimal('1.0'), 1),
            (1001, 5000, Decimal('0.12'), Decimal('1.0'), 2),
            (5001, 15000, Decimal('0.10'), Decimal('1.0'), 3),
            (15001, 30000, Decimal('0.08'), Decimal('1.0'), 4),
            (30001, 50000, Decimal('0.06'), Decimal('1.0'), 5),
        ]
    # Size ranges
    elif 'size' in variable.variable_name.lower() and variable.variable_type == 'number':
        sample_ranges = [
            (1, 5, Decimal('0.50'), Decimal('1.0'), 1),
            (6, 10, Decimal('0.75'), Decimal('1.0'), 2),
            (11, 20, Decimal('1.00'), Decimal('1.0'), 3),
            (21, 30, Decimal('1.50'), Decimal('1.0'), 4),
        ]
    # Color ranges
    elif 'color' in variable.variable_name.lower():
        sample_ranges = [
            (1, 2, Decimal('25.00'), Decimal('1.0'), 1),
            (3, 4, Decimal('40.00'), Decimal('1.0'), 2),
            (5, 6, Decimal('60.00'), Decimal('1.0'), 3),
            (7, 8, Decimal('85.00'), Decimal('1.0'), 4),
            (9, 12, Decimal('120.00'), Decimal('1.0'), 5),
        ]
    # Generic number ranges
    elif variable.variable_type == 'number':
        sample_ranges = [
            (1, 10, Decimal('10.00'), Decimal('1.0'), 1),
            (11, 50, Decimal('8.00'), Decimal('1.0'), 2),
            (51, 100, Decimal('6.00'), Decimal('1.0'), 3),
            (101, 500, Decimal('4.00'), Decimal('1.0'), 4),
            (501, 1000, Decimal('2.00'), Decimal('1.0'), 5),
        ]
    # Generic dropdown ranges
    else:
        sample_ranges = [
            (1, 1, Decimal('20.00'), Decimal('1.0'), 1),
            (2, 2, Decimal('35.00'), Decimal('1.0'), 2),
            (3, 3, Decimal('50.00'), Decimal('1.0'), 3),
            (4, 4, Decimal('70.00'), Decimal('1.0'), 4),
            (5, 5, Decimal('90.00'), Decimal('1.0'), 5),
        ]
    
    # Create the ranges
    for min_val, max_val, price, rate, order in sample_ranges:
        ProcessVariableRange.objects.create(
            variable=variable,
            min_value=Decimal(str(min_val)),
            max_value=Decimal(str(max_val)),
            price=price,
            rate=rate,
            order=order
        )
        ranges_created += 1
    
    return ranges_created

@login_required
def process_list(request):
    """
    List all processes with links to manage variable ranges
    """
    from .models import Process
    
    processes = Process.objects.filter(pricing_type='formula').prefetch_related('variables__ranges')
    
    context = {
        'processes': processes,
    }
    
    return render(request, 'process_list.html', context)

    if search:
        products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))
    if product_type != 'all':
        products = products.filter(product_type=product_type)
    if availability != 'all':
        products = products.filter(availability=availability)

    products = products.order_by('name')

    editing_product = None
    form = ProductionUpdateForm()

    if request.method == 'POST':
        action = request.POST.get('action', 'save')
        product_id = request.POST.get('product_id')

        if action == 'toggle' and product_id:
            product = get_object_or_404(Product, pk=product_id)
            product.is_active = not product.is_active
            product.updated_by = request.user
            product.save(update_fields=['is_active', 'updated_at', 'updated_by'])
            messages.success(request, f'{product.name} status updated.')
            return redirect('production_catalog')

        if product_id:
            editing_product = get_object_or_404(Product, pk=product_id)

        form = ProductionUpdateForm(request.POST, instance=editing_product)
        if form.is_valid():
            product = form.save(commit=False)
            if editing_product is None:
                product.created_by = request.user
            product.updated_by = request.user
            product.save()
            messages.success(request, f'Product {product.name} saved successfully.')
            return redirect('production_catalog')
    else:
        product_id = request.GET.get('product_id')
        if product_id:
            editing_product = get_object_or_404(Product, pk=product_id)
            form = ProductionUpdateForm(instance=editing_product)

    context = {
        'current_view': 'production_catalog',
        'products': products,
        'form': form,
        'editing_product': editing_product,
        'search': search,
        'product_type': product_type,
        'availability': availability,
    }
    return render(request, 'product_catalog.html', context)

@login_required
@group_required('Production Team')
def production2_dashboard(request):
    """Production Team dashboard with REAL data"""
    from django.db.models import Q, Count
    from datetime import timedelta
    
    # Get current user
    user = request.user
    
    
    total_jobs = Job.objects.count()
    completed_jobs = Job.objects.filter(status='completed').count()
    active_jobs = Job.objects.filter(status__in=['in_progress', 'pending']).count()
    
    # Quotes awaiting approval from PT
    quote_jobs = Quote.objects.filter(
        production_status='pending',
        status='Draft'
    ).count()
    
    # Jobs with issues (overdue or on hold)
    today = timezone.now().date()
    issue_jobs = Job.objects.filter(
        Q(status='on_hold')
        | Q(expected_completion__lt=today, status__in=['pending', 'in_progress'])
    ).count()
    
   
    # Jobs due within 3 days
    three_days_from_now = today + timedelta(days=3)
    urgent_jobs = Job.objects.filter(
        status__in=['pending', 'in_progress'],
        expected_completion__lte=three_days_from_now
    ).select_related('client').order_by('expected_completion')[:5]
    
    # Add calculated fields
    for job in urgent_jobs:
        job.product_name = job.product
        days_left = (job.expected_completion - today).days
        if days_left == 0:
            job.urgency_label = "Due Today"
        elif days_left < 0:
            job.urgency_label = f"Overdue by {abs(days_left)} days"
        else:
            job.urgency_label = f"{days_left} days left"
    
    
    # Show jobs created by user or assigned to user
    my_active_jobs = Job.objects.filter(
        Q(created_by=user) | Q(person_in_charge=user),
        status__in=['pending', 'in_progress']
    ).select_related('client').order_by('expected_completion')[:5]
    
    # Add status badges and deadline info
    for job in my_active_jobs:
        job.status_class = job.status.replace('_', '-')
        job.status_label = job.get_status_display()
        
        days_until = (job.expected_completion - today).days
        if days_until < 0:
            job.deadline_warning = True
            job.deadline_text = f"Overdue by {abs(days_until)} days"
        elif days_until == 0:
            job.deadline_warning = True
            job.deadline_text = "Due Today"
        else:
            job.deadline_warning = False
            job.deadline_text = job.expected_completion.strftime("%b %d")

    # Jobs completed by user
    user_jobs_query = Q(created_by=user) | Q(person_in_charge=user)
    
    user_jobs_total = Job.objects.filter(user_jobs_query).count()
    user_jobs_completed = Job.objects.filter(
        user_jobs_query, status='completed'
    ).count()
    user_completion_rate = (
        round((user_jobs_completed / user_jobs_total) * 100, 1)
        if user_jobs_total > 0
        else 0
    )

    # Average costing time (in hours) for quotes costed by this user
    costed_quotes = Quote.objects.filter(
        costed_by=user,
        production_status__in=['costed', 'sent_to_client', 'in_production', 'completed'],
    )
    total_hours = 0
    count_costed = 0
    for q in costed_quotes:
        # Use created_at -> updated_at as a proxy for costing duration
        if q.created_at and q.updated_at and q.updated_at > q.created_at:
            delta = q.updated_at - q.created_at
            total_hours += delta.total_seconds() / 3600.0
            count_costed += 1

    average_costing_time = round(total_hours / count_costed, 1) if count_costed > 0 else 0.0
    
    context = {
        'current_view': 'production_dashboard',
        'user': user,
        
        # Job counts
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'active_jobs': active_jobs,
        'quote_jobs': quote_jobs,
        'issue_jobs': issue_jobs,
        
        # Urgent section
        'urgent_jobs': urgent_jobs,
        
        # My active jobs
        'my_active_jobs': my_active_jobs,
        
        # Performance metrics
        'user_jobs_total': user_jobs_total,
        'user_jobs_completed': user_jobs_completed,
        'user_completion_rate': user_completion_rate,
        'average_costing_time': average_costing_time,
    }
    
    return render(request, 'production2_dashboard.html', context)


@login_required
@group_required('Production Team')
def jobs2_list(request):
    """Enhanced Jobs management page"""
    context = {
        'current_view': 'jobs2_list',
    }
    return render(request, 'jobs2_list.html', context)


@login_required
@group_required('Production Team')
def invoices2_list(request):
    """Enhanced Invoices review page"""
    context = {
        'current_view': 'invoices2_list',
    }
    return render(request, 'invoices2_list.html', context)


@login_required
@group_required('Production Team')
def proofs2_list(request):
    """Enhanced QC Proofs review page"""
    context = {
        'current_view': 'proofs2_list',
    }
    return render(request, 'proofs2_list.html', context)


@login_required
@group_required('Production Team')
def messages2_list(request):
    """Enhanced Messages page"""
    context = {
        'current_view': 'messages2_list',
    }
    return render(request, 'messages2_list.html', context)


@login_required
@group_required('Production Team')
def vendors2_list(request):
    """Enhanced Vendor directory page"""
    context = {
        'current_view': 'vendors2_list',
    }
    return render(request, 'vendors2_list.html', context)


@login_required
@group_required('Production Team')
def production_analytics(request):
    """Production-side analytics"""
    # 1. Total Revenue (90d)
    ninety_days_ago = timezone.now().date() - timedelta(days=90)
    
    # Calculate revenue from completed jobs in last 90 days
    completed_jobs_revenue = Job.objects.filter(
        status='completed',
        actual_completion__gte=ninety_days_ago
    ).aggregate(total=Sum('quote__total_amount'))['total'] or 0
    
    # 2. Quote Conversion (Approved / Total Quoted)
    total_quotes_90d = Quote.objects.filter(created_at__gte=ninety_days_ago).count()
    approved_quotes_90d = Quote.objects.filter(
        created_at__gte=ninety_days_ago, 
        status='Approved'
    ).count()
    quote_conversion = (approved_quotes_90d / total_quotes_90d * 100) if total_quotes_90d > 0 else 0
    
    # 3. Avg Profit Margin
    margin_quotes = Quote.objects.filter(
        status='Approved',
        production_cost__gt=0,
        total_amount__gt=0,
        created_at__gte=ninety_days_ago
    )
    
    total_margin_revenue = margin_quotes.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_margin_cost = margin_quotes.aggregate(Sum('production_cost'))['production_cost__sum'] or 0
    
    avg_profit_margin = 0
    if total_margin_revenue > 0:
        avg_profit_margin = ((total_margin_revenue - total_margin_cost) / total_margin_revenue) * 100
        
    # 4. Catalog Health Score
    total_products = Product.objects.count()
    healthy_products = Product.objects.exclude(description='').count()
    catalog_health = (healthy_products / total_products * 100) if total_products > 0 else 0
    
    # 5. Top Products
    top_products = Job.objects.filter(
        status='completed',
        actual_completion__gte=ninety_days_ago
    ).values(
        'product__name'
    ).annotate(
        revenue=Sum('quote__total_amount'),
        count=Count('id')
    ).order_by('-revenue')[:5]
    
    context = {
        'current_view': 'production_analytics',
        'total_revenue': completed_jobs_revenue,
        'quote_conversion': round(quote_conversion, 1),
        'avg_profit_margin': round(avg_profit_margin, 1),
        'catalog_health': round(catalog_health),
        'top_products': top_products,
        'quotes_by_status': Quote.objects.values('production_status').annotate(count=Count('id')),
        'jobs_by_status': Job.objects.values('status').annotate(count=Count('id')),
    }
    return render(request, 'production_analytics.html', context)

@login_required
@group_required('Production Team')
def production_settings(request):
    """Production Team Settings"""
    context = {
        'current_view': 'production_settings',
    }
    return render(request, 'production_settings.html', context)


@login_required
@group_required('Production Team')
def self_quote(request):
    return render(request, 'self_quote.html')


@login_required
@group_required('Production Team')
def production_job_assignment(request):
    """Job Assignment UI for Production Team - GAP #10"""
    from django.db.models import Count, Q, Avg
    
    # Get unassigned or recently created jobs (jobs without purchase orders)
    jobs = Job.objects.filter(
        status__in=['pending', 'in_progress']
    ).exclude(
        purchase_orders__isnull=False
    ).select_related('client').order_by('-created_at')[:50]
    
    # Get vendors with capacity and stats
    vendors = Vendor.objects.annotate(
        active_jobs=Count('purchase_orders', filter=Q(purchase_orders__status__in=['NEW', 'ACCEPTED', 'IN_PROGRESS'])),
        quality_score=Avg('purchase_orders__job__quality_score')
    ).values(
        'id', 'name', 'active_jobs', 'quality_score'
    )
    
    # Calculate capacity percentage for each vendor
    vendor_list = []
    for vendor in vendors:
        capacity_pct = min(int((vendor['active_jobs'] / 10) * 100), 100)  # Assuming 10 job capacity
        vendor_obj = {
            'id': vendor['id'],
            'name': vendor['name'],
            'active_jobs': vendor['active_jobs'],
            'capacity_percentage': capacity_pct,
            'quality_score': vendor['quality_score'] or 8.5
        }
        vendor_list.append(vendor_obj)
    
    context = {
        'current_view': 'production_job_assignment',
        'jobs': jobs,
        'vendors': vendor_list,
    }
    return render(request, 'production_job_assignment.html', context)


@login_required
@group_required('Production Team')
def production_job_assignment_submit(request):
    """Handle job assignment submission - GAP #10"""
    if request.method == 'POST':
        try:
            job_id = request.POST.get('job_id')
            vendor_id = request.POST.get('vendor_id')
            priority = request.POST.get('priority', 'normal')
            notes = request.POST.get('notes', '')
            
            # Get job and vendor
            job = Job.objects.get(id=job_id)
            vendor = Vendor.objects.get(id=vendor_id)
            
            # Update job priority and notes
            job.priority = priority
            job.assignment_notes = notes
            job.save()
            
            # Create a Purchase Order to link vendor to job
            from decimal import Decimal
            from django.utils import timezone
            from datetime import timedelta
            
            purchase_order, created = PurchaseOrder.objects.get_or_create(
                job=job,
                vendor=vendor,
                defaults={
                    'product_type': job.product if hasattr(job, 'product') else 'Production Job',
                    'product_description': job.job_notes or 'Production assignment',
                    'quantity': 1,
                    'total_cost': Decimal('0.00'),
                    'status': 'NEW',
                    'milestone': 'awaiting_acceptance',
                    'required_by': timezone.now() + timedelta(days=14),
                }
            )
            
            # Log the assignment
            messages.success(request, f'Successfully assigned job {job.job_number} to {vendor.name}')
            
        except Job.DoesNotExist:
            messages.error(request, 'Job not found.')
        except Vendor.DoesNotExist:
            messages.error(request, 'Vendor not found.')
        except Exception as e:
            messages.error(request, f'Error assigning job: {str(e)}')
        
        return redirect('production_job_assignment')
    
    return redirect('production_job_assignment')


@login_required
@group_required('Production Team')
def production_invoice_approval(request):
    """Invoice Approval UI for Production Team - GAP #11"""
    from django.db.models import Q
    
    # Get pending invoices with related vendor info
    invoices = Invoice.objects.filter(
        Q(approval_status__in=['pending', 'hold']) |
        Q(approval_status__isnull=True)
    ).select_related('vendor').order_by('-date')
    
    # Get list of vendors for filtering
    vendors = Vendor.objects.all().values('id', 'name')
    
    context = {
        'current_view': 'production_invoice_approval',
        'invoices': invoices,
        'vendors': vendors,
    }
    return render(request, 'production_invoice_approval.html', context)


@login_required
@group_required('Production Team')
def production_invoice_approval_submit(request):
    """Handle invoice approval submission - GAP #11"""
    if request.method == 'POST':
        try:
            invoice_id = request.POST.get('invoice_id')
            decision = request.POST.get('decision')
            notes = request.POST.get('notes', '')
            
            # Get invoice
            invoice = Invoice.objects.get(id=invoice_id)
            
            # Update invoice status
            invoice.approval_status = decision
            invoice.approved_by = request.user
            invoice.approval_date = timezone.now()
            invoice.approval_notes = notes
            invoice.save()
            
            # Log the decision
            status_text = {
                'approve': 'approved',
                'reject': 'rejected',
                'hold': 'placed on hold'
            }.get(decision, 'updated')
            
            messages.success(request, f'Invoice {invoice.number} has been {status_text}.')
            
        except Invoice.DoesNotExist:
            messages.error(request, 'Invoice not found.')
        except Exception as e:
            messages.error(request, f'Error updating invoice: {str(e)}')
        
        return redirect('production_invoice_approval')
    
    return redirect('production_invoice_approval')


@login_required
@group_required('Production Team')
def production_proof_approval(request):
    """Proof Approval with QC Assessment UI - GAP #12"""
    from django.db.models import Q
    
    # Get proofs awaiting approval
    proofs = Proof.objects.filter(
        Q(qc_status__in=['pending', 'rework']) |
        Q(qc_status__isnull=True)
    ).select_related('job').order_by('-created_at')
    
    # Add image URLs to proofs
    for proof in proofs:
        proof.image_url = proof.file.url if proof.file else ''
        proof.thumbnail_url = proof.file.url if proof.file else ''
        proof.po_number = proof.job.po_number if proof.job else f'PO-{proof.job_id}'
    
    context = {
        'current_view': 'production_proof_approval',
        'proofs': proofs,
    }
    return render(request, 'production_proof_approval.html', context)


@login_required
@group_required('Production Team')
def production_proof_approval_submit(request):
    """Handle proof approval submission with VPS recalculation - GAP #12"""
    if request.method == 'POST':
        try:
            proof_id = request.POST.get('proof_id')
            decision = request.POST.get('decision')  # 'pass', 'rework', 'reject'
            qc_notes = request.POST.get('qc_notes', '')
            
            # Get proof
            proof = Proof.objects.get(id=proof_id)
            
            # Update proof QC status
            proof.qc_status = decision
            proof.qc_notes = qc_notes
            proof.qc_approved_by = request.user
            proof.qc_approval_date = timezone.now()
            proof.save()
            
            # If proof is rejected, potentially hold invoice (GAP #14)
            if decision == 'reject':
                if proof.job and proof.job.invoice:
                    proof.job.invoice.auto_held_qc = True
                    proof.job.invoice.hold_reason = f'QC Proof Rejection - {qc_notes}'
                    proof.job.invoice.save()
            
            # Trigger VPS recalculation if needed (GAP #15)
            if decision in ['pass', 'reject']:
                try:
                    from rest_framework.request import Request as DRFRequest
                    from rest_framework.test import APIRequestFactory
                    
                    # Create VPS recalculation record
                    recalc_data = {
                        'vendor': proof.job.vendor_id,
                        'trigger_type': 'proof_approval',
                        'trigger_id': proof_id,
                        'previous_score': float(proof.job.vendor.vps_score_value) if proof.job.vendor else 0,
                    }
                    # Calculate new score based on decision
                    if decision == 'pass':
                        recalc_data['new_score'] = recalc_data['previous_score'] + 2
                    else:  # reject
                        recalc_data['new_score'] = recalc_data['previous_score'] - 5
                    
                    # VPS recalculation happens via background task or API
                except Exception as vps_error:
                    pass  # VPS recalculation optional, don't fail on it
            
            # Log action
            decision_text = {
                'pass': 'approved',
                'rework': 'sent for rework',
                'reject': 'rejected'
            }.get(decision, 'updated')
            
            messages.success(request, f'Proof has been {decision_text}.')
            
        except Proof.DoesNotExist:
            messages.error(request, 'Proof not found.')
        except Exception as e:
            messages.error(request, f'Error updating proof: {str(e)}')
        
        return redirect('production_proof_approval')
    
    return redirect('production_proof_approval')


@login_required
def vendor_progress_submit(request):
    """Vendor Progress Update Submission - GAP #7"""
    from django.db.models import Q
    
    if request.method == 'GET':
        # Get vendor from request user
        try:
            vendor = Vendor.objects.get(user=request.user)
        except Vendor.DoesNotExist:
            messages.error(request, 'Vendor profile not found.')
            return redirect('vendor_dashboard')
        
        # Get purchase orders assigned to this vendor in progress
        purchase_orders = PurchaseOrder.objects.filter(
            vendor=vendor,
            status__in=['IN_PRODUCTION', 'AWAITING_APPROVAL', 'AT_RISK']
        ).select_related('job__client').order_by('-created_at')
        
        context = {
            'purchase_orders': purchase_orders,
            'current_view': 'vendor_progress_submit',
        }
        return render(request, 'vendor_progress_submit.html', context)
    
    elif request.method == 'POST':
        try:
            po_id = request.POST.get('po_id')
            percentage_complete = int(request.POST.get('percentage_complete', 0))
            milestone = request.POST.get('milestone', 'in_production')
            notes = request.POST.get('notes', '')
            
            # Get purchase order
            po = PurchaseOrder.objects.get(id=po_id)
            
            # Verify vendor access
            vendor = Vendor.objects.get(user=request.user)
            if po.vendor != vendor:
                messages.error(request, 'You do not have access to this purchase order.')
                return redirect('vendor_progress_submit')
            
            # Create progress update batch (GAP #7)
            progress_batch = ProgressUpdateBatch.objects.create(
                purchase_order=po,
                percentage_complete=percentage_complete,
                status=milestone,
                submitted_by=request.user,
                notes=notes
            )
            
            # Handle attachments
            attachments = request.FILES.getlist('attachments')
            if attachments:
                for attachment in attachments:
                    progress_batch.attachments.add(attachment)
            
            messages.success(request, f'Progress update submitted successfully. ({percentage_complete}% complete)')
            
        except PurchaseOrder.DoesNotExist:
            messages.error(request, 'Purchase order not found.')
        except Vendor.DoesNotExist:
            messages.error(request, 'Vendor profile not found.')
        except ValueError:
            messages.error(request, 'Invalid percentage value.')
        except Exception as e:
            messages.error(request, f'Error submitting progress: {str(e)}')
        
        return redirect('vendor_progress_submit')


# Add these updated views to your views.py file

@login_required
def notifications(request):
    """Display notifications with mark as read functionality"""
    if request.method == 'POST':
        # Mark specific notification as read
        notif_id = request.POST.get('mark_read')
        if notif_id:
            try:
                notification = Notification.objects.get(id=notif_id, recipient=request.user)
                notification.is_read = True
                notification.save()
                messages.success(request, 'Notification marked as read')
            except Notification.DoesNotExist:
                pass
        else:
            # Mark all as read
            Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
            messages.success(request, 'All notifications marked as read')
        
        return redirect('notifications')
    
    # GET request - show notifications
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')
    
    context = {
        'current_view': 'notifications',
        'notifications': notifications,
    }
    
    return render(request, 'notifications.html', context)


def permission_denied_view(request, *args, **kwargs):
    messages.warning(request, "You don't have access to that section.")
    fallback = 'dashboard'
    if request.user.groups.filter(name='Production Team').exists():
        fallback = 'production2_dashboard'
    return redirect(reverse(fallback))
def login_redirect(request):
    """
    Custom login redirect view that sends users to appropriate dashboard based on their group
    NOTE: This view should NOT have @login_required decorator
    """
    if not request.user.is_authenticated:
        return redirect('login')

    user = request.user

    if user.is_superuser:
        return redirect('admin_dashboard_index')

    if user.groups.filter(name='Production Team').exists():
        return redirect('production2_dashboard')
    elif user.groups.filter(name='Account Manager').exists():
        return redirect('dashboard')
    elif user.groups.filter(name='Admin').exists() or user.is_staff:
        return redirect('admin_dashboard_index')

    from django.conf import settings
    frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')

    from .models import ClientPortalUser
    if ClientPortalUser.objects.filter(user=user, is_active=True).exists():
        return redirect(f'{frontend_url}/portal')

    try:
        from .models import Vendor
        if Vendor.objects.filter(user=user, active=True).exists():
            return redirect(f'{frontend_url}/vendor')
    except Exception:
        pass

    from django.shortcuts import render
    return render(request, 'no_group_error.html', {
        'user': user,
        'message': 'Your account is not assigned to any group. Please contact the administrator.',
    })

from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json

def ajax_get_product_image(request, image_id):
    """AJAX endpoint to get product image data"""
    try:
        image = ProductImage.objects.get(id=image_id)
        return JsonResponse({
            'success': True,
            'image_url': image.image.url,
            'file_name': image.image.name.split('/')[-1],
            'file_size': f"{image.image.size / 1024:.1f} KB" if hasattr(image.image, 'size') else 'Unknown',
            'dimensions': 'Unknown',  
            'alt_text': image.alt_text or '',
            'caption': image.caption or '',
            'image_type': image.image_type or 'product-photo'
        })
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)

@require_POST
def ajax_update_product_image(request, image_id):
    """AJAX endpoint to update product image metadata"""
    try:
        image = ProductImage.objects.get(id=image_id)
        data = json.loads(request.body)
        
        image.alt_text = data.get('alt_text', '')
        image.caption = data.get('caption', '')
        image.image_type = data.get('image_type', 'product-photo')
        image.save()
        
        return JsonResponse({'success': True})
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def ajax_delete_product_image(request, image_id):
    """AJAX endpoint to delete product image"""
    try:
        image = ProductImage.objects.get(id=image_id)
        image.delete()
        return JsonResponse({'success': True})
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
def ajax_replace_product_image(request, image_id):
    """AJAX endpoint to replace product image"""
    try:
        image = ProductImage.objects.get(id=image_id)
        
        if 'image' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No image file provided'}, status=400)
        
        # Delete old file
        if image.image:
            image.image.delete(save=False)
        
        # Save new file
        image.image = request.FILES['image']
        image.save()
        
        return JsonResponse({
            'success': True,
            'new_image_url': image.image.url
        })
    except ProductImage.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Image not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

        
@login_required
@group_required('Production Team')
def production_jobs(request):
    """Production Team jobs management - list view"""
    jobs = Job.objects.all().order_by('-created_at')
    
    # Filter options
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        jobs = jobs.filter(status=status_filter)
    
    context = {
        'current_view': 'production_jobs',
        'jobs': jobs,
        'status_filter': status_filter,
    }
    return render(request, 'production_jobs.html', context)



def finance_required(view_func):
    """Require Finance group membership"""
    return group_required('Finance')(view_func)

# 
@finance_required
def finance_client_entity(request, client_id):
    """Map client to Django Ledger entity"""
    client = get_object_or_404(Client, id=client_id)
    
    entity_field_names = {f.name for f in EntityModel._meta.get_fields()}
    entity_name = f"{client.name} ({client.client_id})"
    entity = EntityModel.objects.filter(name=entity_name).first()
    if not entity:
        defaults = {}
        if 'admin' in entity_field_names:
            defaults['admin'] = request.user
        if 'address_1' in entity_field_names:
            defaults['address_1'] = getattr(client, 'address', '') or ''
        if 'phone' in entity_field_names:
            defaults['phone'] = getattr(client, 'phone', '') or ''
        if 'email' in entity_field_names:
            defaults['email'] = getattr(client, 'email', '') or ''
        if 'country' in entity_field_names:
            defaults['country'] = 'KE'
        if 'currency' in entity_field_names:
            defaults['currency'] = 'KES'
        try:
            if hasattr(EntityModel, 'add_root'):
                entity = EntityModel.add_root(name=entity_name, **defaults)
            else:
                entity = EntityModel.objects.create(name=entity_name, **defaults)
        except Exception:
            minimal_kwargs = {'name': entity_name}
            if 'admin' in entity_field_names:
                minimal_kwargs['admin'] = request.user
            entity = EntityModel.objects.create(**minimal_kwargs)
    
    # Render within our theme using an iframe wrapper
    return render(request, 'finance_entity.html', {'entity': entity, 'current_view': 'finance_dashboard'})
# No need for finance anymore

#  LPO MANAGEMENT VIEWS

@login_required
@group_required('Production Team')
def lpo_list(request):
    """List all LPOs for production team"""
    from clientapp.models import LPO
    
    # Get filter parameters
    status_filter = request.GET.get('status', 'all')
    sync_filter = request.GET.get('sync', 'all')
    search_query = request.GET.get('search', '').strip()
    
    lpos = LPO.objects.select_related('client', 'quote').order_by('-created_at')
    
    # Apply filters
    if status_filter != 'all':
        lpos = lpos.filter(status=status_filter)
    
    if sync_filter == 'synced':
        lpos = lpos.filter(synced_to_quickbooks=True)
    elif sync_filter == 'not_synced':
        lpos = lpos.filter(synced_to_quickbooks=False)
    
    if search_query:
        lpos = lpos.filter(
            Q(lpo_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(client__company__icontains=search_query) |
            Q(quote__quote_id__icontains=search_query)
        )
    
    # Count by status
    status_counts = {
        'all': LPO.objects.count(),
        'pending': LPO.objects.filter(status='pending').count(),
        'approved': LPO.objects.filter(status='approved').count(),
        'in_production': LPO.objects.filter(status='in_production').count(),
        'completed': LPO.objects.filter(status='completed').count(),
        'synced': LPO.objects.filter(synced_to_quickbooks=True).count(),
        'not_synced': LPO.objects.filter(synced_to_quickbooks=False, status='completed').count(),
    }
    
    context = {
        'current_view': 'lpo_list',
        'lpos': lpos,
        'status_filter': status_filter,
        'sync_filter': sync_filter,
        'search_query': search_query,
        'status_counts': status_counts,
    }
    
    return render(request, 'lpo_list.html', context)


@login_required
def lpo_detail(request, lpo_number):
    """View LPO details"""
    from clientapp.models import LPO
    
    lpo = get_object_or_404(LPO, lpo_number=lpo_number)
    
    # Check permissions
    is_am = request.user.groups.filter(name='Account Manager').exists()
    is_production = request.user.groups.filter(name='Production Team').exists()
    
    if not (is_am or is_production or request.user.is_superuser):
        messages.error(request, "You don't have permission to view this LPO")
        return redirect('dashboard')
    
    # Get related job
    job = None
    job_completed = False
    if hasattr(lpo.quote, 'job'):
        job = lpo.quote.job
        job_completed = job.status == 'completed'
    
    # Allow sync when: user is production team, not already synced
    can_sync = (is_production or is_am) and not lpo.synced_to_quickbooks and (lpo.status == 'completed' or job_completed)
    
    context = {
        'lpo': lpo,
        'quote': lpo.quote,
        'job': job,
        'line_items': lpo.line_items.all(),
        'can_sync': can_sync,
        'current_view': 'lpo_detail',
    }
    
    return render(request, 'lpo_detail.html', context)


@login_required
@group_required('Production Team')
def sync_to_quickbooks(request, lpo_number):
    """Sync LPO to QuickBooks when production is complete"""
    if request.method == 'POST':
        try:
            from clientapp.models import LPO
            
            lpo = get_object_or_404(LPO, lpo_number=lpo_number)
            
            # Check if already synced
            if lpo.synced_to_quickbooks:
                return JsonResponse({
                    'success': False,
                    'message': 'LPO already synced to QuickBooks'
                })
            
            # Check if production is complete
            job_completed = False
            if hasattr(lpo.quote, 'job') and lpo.quote.job:
                job_completed = lpo.quote.job.status == 'completed'
            
            if lpo.status != 'completed' and not job_completed:
                return JsonResponse({
                    'success': False,
                    'message': 'Production must be completed before syncing to QuickBooks'
                })
            
            # Sync to QuickBooks
            result = lpo.sync_to_quickbooks(request.user)
            
            if result['success']:
                messages.success(request, result['message'])
            
            return JsonResponse(result)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })


@login_required
@group_required('Production Team')
def complete_job(request, pk):
    """Mark job as completed and update LPO status"""
    if request.method == 'POST':
        try:
            job = get_object_or_404(Job, pk=pk)
            
            # Update job status
            job.status = 'completed'
            job.actual_completion = timezone.now().date()
            job.save()
            
            # Update LPO status if exists
            if hasattr(job.quote, 'lpo'):
                lpo = job.quote.lpo
                lpo.status = 'completed'
                lpo.save()
                
                # Create notification for AM to sync to QuickBooks
                # production-
                if job.client.account_manager:
                    Notification.objects.create(
                        recipient=job.client.account_manager,
                        title=f'Job {job.job_number} Completed',
                        message=f'Job {job.job_number} is complete. LPO {lpo.lpo_number} ready to sync to QuickBooks.',
                        link=reverse('lpo_detail', kwargs={'lpo_number': lpo.lpo_number})
                    )
            
            # Create activity log
            ActivityLog.objects.create(
                client=job.client,
                activity_type='Order',
                title=f'Job {job.job_number} Completed',
                description=f'Production completed for {job.job_name}',
                created_by=request.user
            )
            
            messages.success(request, f'Job {job.job_number} marked as completed!')
            return redirect('job_detail', pk=job.pk)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('job_detail', pk=pk)
    
    return redirect('job_detail', pk=pk)


@login_required
@group_required('Account Manager')
@login_required
@group_required('Account Manager')
def send_quote(request, quote_id):
    """Send quote to client/lead via email"""
    if request.method == 'POST':
        from .quote_approval_services import QuoteApprovalService
        import traceback
        
        try:
            quote = Quote.objects.filter(quote_id=quote_id).first()
            if not quote:
                return JsonResponse({
                    'success': False,
                    'message': 'Quote not found'
                })
            
            send_method = request.POST.get('send_method', 'email')
            
            try:
                if send_method == 'email':
                    result = QuoteApprovalService.send_quote_via_email(quote, request)
                elif send_method == 'whatsapp':
                    result = QuoteApprovalService.send_quote_via_whatsapp(quote)
                else:
                    result = {
                        'success': False,
                        'message': 'Invalid send method'
                    }
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error in send_quote_via_{send_method}: {e}")
                return JsonResponse({
                    'success': False,
                    'message': f'Error sending quote: {str(e)}'
                }, status=400)
            
            if result['success']:
                # Create activity log
                if quote.client:
                    ActivityLog.objects.create(
                        client=quote.client,
                        activity_type='Quote',
                        title=f"Quote {quote.quote_id} Sent",
                        description=f"Quote sent via {send_method} to {quote.client.email if quote.client else quote.lead.email}",
                        related_quote=quote,
                        created_by=request.user
                    )
            
            return JsonResponse(result)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error in send_quote view: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method'
    })

from clientapp.quote_approval_services import QuoteApprovalService
def quote_approval(request, token):
    """
    Public view for quote approval (no login required)
    Client clicks link from email
    GET: Display quote details with approve/request discount options
    POST: Handle approval or price reduction request
    """
    if request.method == 'GET':
        # Display quote details
        result = QuoteApprovalService.get_quote_from_token(token)
        
        if not result['success']:
            from django.http import HttpResponse
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to get quote from token: {token[:20]}..., error: {result.get('message', 'Unknown error')}")
            
            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Approval Failed</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-50">
                <div class="min-h-screen flex items-center justify-center px-4">
                    <div class="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
                        <div class="text-6xl mb-4">N</div>
                        <h1 class="text-2xl font-bold text-gray-900 mb-4">Approval Failed</h1>
                        <p class="text-gray-600 mb-6">{result['message']}</p>
                        <p class="text-sm text-gray-500 mb-4">Please contact us at info@printduka.com for assistance.</p>
                        <p class="text-xs text-gray-400">If you received this link via email, please check that you're using the complete link from the email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return HttpResponse(error_html)
        
        # Render quote approval page
        quote = result['quote']
        quote_items = result['quote_items']
        totals = result['totals']
        
        context = {
            'quote': quote,
            'quote_items': quote_items,
            'subtotal': totals['subtotal'],
            'vat_amount': totals['vat_amount'],
            'total_amount': totals['total_amount'],
            'total': totals['total_amount'],
            'token': token,
            'token_valid': result['token_valid'],
            'token_used': result['token_used'],
        }
        
        return render(request, 'quote_approval.html', context)
    
    elif request.method == 'POST':
        # Handle approval or price reduction request
        action = request.POST.get('action', 'approve')
        
        if action == 'approve':
            # Call the service to approve the quote
            result = QuoteApprovalService.approve_quote(token)
        elif action == 'request_discount':
            # Handle price reduction request
            discount_notes = request.POST.get('discount_notes', '')
            if not discount_notes:
                from django.http import HttpResponse
                error_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Request Failed</title>
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="bg-gray-50">
                    <div class="min-h-screen flex items-center justify-center px-4">
                        <div class="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
                            <div class="text-6xl mb-4"></div>
                            <h1 class="text-2xl font-bold text-gray-900 mb-4">Request Failed</h1>
                            <p class="text-gray-600 mb-6">Please provide details about your price reduction request.</p>
                            <a href="javascript:history.back()" class="text-blue-600 hover:underline">Go Back</a>
                        </div>
                    </div>
                </body>
                </html>
                """
                return HttpResponse(error_html)
            
            result = QuoteApprovalService.request_price_reduction(token, discount_notes)
        elif action == 'request_adjustment':
            # Handle quote adjustment request
            adjustment_notes = request.POST.get('adjustment_notes', '')
            if not adjustment_notes:
                from django.http import HttpResponse
                error_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Request Failed</title>
                    <script src="https://cdn.tailwindcss.com"></script>
                </head>
                <body class="bg-gray-50">
                    <div class="min-h-screen flex items-center justify-center px-4">
                        <div class="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
                            <div class="text-6xl mb-4"></div>
                            <h1 class="text-2xl font-bold text-gray-900 mb-4">Request Failed</h1>
                            <p class="text-gray-600 mb-6">Please provide details about the adjustments you need.</p>
                            <a href="javascript:history.back()" class="text-blue-600 hover:underline">Go Back</a>
                        </div>
                    </div>
                </body>
                </html>
                """
                return HttpResponse(error_html)
            
            result = QuoteApprovalService.request_quote_adjustment(token, adjustment_notes)
        else:
            result = {'success': False, 'message': 'Invalid action'}
        
        if not result['success']:
            # Approval failed
            from django.http import HttpResponse
            error_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Approval Failed</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    min-height: 100vh;
                    margin: 0;
                    background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                }}
                .container {{
                    background: white;
                    padding: 3rem;
                    border-radius: 1rem;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                    max-width: 500px;
                }}
                .error-icon {{
                    font-size: 4rem;
                    color: #ef4444;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    color: #1f2937;
                    margin-bottom: 1rem;
                }}
                p {{
                    color: #6b7280;
                    font-size: 1.1rem;
                    line-height: 1.6;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon"></div>
                <h1>Approval Failed</h1>
                <p>{result['message']}</p>
                <p style="margin-top: 2rem; font-size: 0.9rem; color: #9ca3af;">
                    Please contact us if you need assistance.
                </p>
            </div>
        </body>
        </html>
            """
            return HttpResponse(error_html)
        
        
        if action == 'approve':
            # Approval success
            quote = result['quote']
            lpo = result.get('lpo')
            job = result.get('job')
            
            # Return success page
            from django.http import HttpResponse
            success_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Quote Approved</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 3rem;
                border-radius: 1rem;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 600px;
            }}
            .success-icon {{
                font-size: 4rem;
                color: #10b981;
                margin-bottom: 1rem;
            }}
            h1 {{
                color: #1f2937;
                margin-bottom: 1rem;
            }}
            p {{
                color: #6b7280;
                font-size: 1.1rem;
                line-height: 1.6;
            }}
            .quote-id {{
                background: #f3f4f6;
                padding: 0.5rem 1rem;
                border-radius: 0.5rem;
                font-family: monospace;
                color: #4f46e5;
                font-weight: bold;
                margin: 1rem 0;
            }}
            .details {{
                background: #f9fafb;
                padding: 1.5rem;
                border-radius: 0.5rem;
                margin: 1.5rem 0;
                text-align: left;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 0.5rem 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .detail-row:last-child {{
                border-bottom: none;
            }}
            .detail-label {{
                font-weight: 600;
                color: #4b5563;
            }}
            .detail-value {{
                color: #1f2937;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="success-icon"></div>
            <h1>Quote Approved Successfully!</h1>
            <p class="quote-id">{quote.quote_id}</p>
            
            <div class="details">
                <div class="detail-row">
                    <span class="detail-label">LPO Number:</span>
                    <span class="detail-value">{lpo.lpo_number if lpo else 'Generated'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Job Number:</span>
                    <span class="detail-value">{job.job_number if job else 'Created'}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Product:</span>
                    <span class="detail-value">{quote.product_name}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Quantity:</span>
                    <span class="detail-value">{quote.quantity}</span>
                </div>
            </div>
            
            <p>Thank you for approving your quote! We have:</p>
            <ul style="text-align: left; color: #4b5563; line-height: 2;">
                <li> Generated your Local Purchase Order (LPO)</li>
                <li> Created a production job</li>
                <li> Notified our production team</li>
            </ul>
            
            <p style="margin-top: 2rem;">
                Our production team will begin work on your order shortly. 
                You'll receive updates on the progress.
            </p>
            
            <p style="margin-top: 2rem; font-size: 0.9rem; color: #9ca3af;">
                You can now close this window.
            </p>
        </div>
    </body>
    </html>
    """
    
            return HttpResponse(success_html)
        elif action == 'request_discount':
            # Price reduction request success
            from django.http import HttpResponse
            discount_success_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Request Submitted</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-50">
                <div class="min-h-screen flex items-center justify-center px-4">
                    <div class="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
                        <div class="text-6xl mb-4"></div>
                        <h1 class="text-2xl font-bold text-gray-900 mb-4">Request Submitted</h1>
                        <p class="text-gray-600 mb-6">{result['message']}</p>
                        <p class="text-sm text-gray-500">We will review your request and get back to you shortly.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return HttpResponse(discount_success_html)
        elif action == 'request_adjustment':
            # Quote adjustment request success
            from django.http import HttpResponse
            adjustment_success_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Request Submitted</title>
                <script src="https://cdn.tailwindcss.com"></script>
            </head>
            <body class="bg-gray-50">
                <div class="min-h-screen flex items-center justify-center px-4">
                    <div class="bg-white rounded-lg shadow-lg p-8 max-w-md text-center">
                        <div class="text-6xl mb-4"></div>
                        <h1 class="text-2xl font-bold text-gray-900 mb-4">Request Submitted</h1>
                        <p class="text-gray-600 mb-6">{result['message']}</p>
                        <p class="text-sm text-gray-500">We will review your request and send you an updated quote shortly.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            return HttpResponse(adjustment_success_html)



#  PRODUCT CATALOG VIEWS 
"""
Complete Product Management Views
Handles all product creation and editing with multi-tab interface
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.utils.text import slugify
from decimal import Decimal
import decimal
import json

from .models import (
    Product, ProductCategory, ProductSubCategory, ProductFamily,
    ProductTag, Vendor, ProductPricing, ProductVariable,
    ProductVariableOption, ProductImage, ProductVideo,
    ProductDownloadableFile, ProductSEO, ProductReviewSettings,
    ProductFAQ, ProductShipping, ProductLegal, ProductProduction,
    ProductChangeHistory, ActivityLog,
    Process, ProcessVariable, ProcessTier, QCInspection, Delivery
)

from .product_forms import (
    ProductGeneralInfoForm, ProductPricingForm, ProductSEOForm,
    ProductShippingForm, ProductLegalForm, ProductProductionForm
)

from django.db import models

def group_required_production(group_name):
    """Decorator to require Production Team group membership"""
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if not request.user.groups.filter(name=group_name).exists():
                messages.error(request, "You don't have permission to access this page.")
                return redirect('production2_dashboard')
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator

# Catalog
@login_required
@group_required('Production Team')
def product_catalog(request):
    """List all products - Production Team view"""
    
    search = request.GET.get('search', '').strip()
    category = request.GET.get('category', 'all')
    status = request.GET.get('status', 'all')
    
    products = Product.objects.all()
    
    # Apply filters
    if search:
        products = products.filter(
            models.Q(name__icontains=search) | 
            models.Q(internal_code__icontains=search)
        )
    
    if category != 'all':
        products = products.filter(primary_category__slug=category)
    
    if status != 'all':
        products = products.filter(status=status)
    
    # Get categories for filter dropdown
    categories = ProductCategory.objects.all().order_by('name')
    
    context = {
        'current_view': 'production_catalog',
        'products': products.order_by('-created_at'),
        'categories': categories,
        'search': search,
        'selected_category': category,
        'selected_status': status,
    }
    
    return render(request, 'product_catalog.html', context)



def _get_product_form_context(product, general_form=None):
    """Build context for product create/edit form"""
    from clientapp.product_forms import ProductGeneralInfoForm
    
    if general_form is None:
        if product:
            general_form = ProductGeneralInfoForm(instance=product)
        else:
            general_form = ProductGeneralInfoForm()
    
    # Get processes for pricing integration
    processes = Process.objects.filter(status='active').order_by('process_name')
    
    # Get vendors
    vendors = Vendor.objects.filter(is_active=True).order_by('name')
    
    # Prepare existing variables JSON for editing
    existing_variables_json = '[]'
    if product and hasattr(product, 'variables'):
        try:
            variables_list = list(product.variables.all().values(
                'id', 'name', 'variable_type', 'options', 'default_value', 
                'is_required', 'affects_pricing', 'order'
            ))
            existing_variables_json = json.dumps(variables_list)
        except:
            existing_variables_json = '[]'
    
    context = {
        'current_view': 'production_catalog',
        'product': product,
        'is_edit': product is not None,
        'general_form': general_form,
        'pricing_form': ProductPricingForm(instance=product.pricing if product and hasattr(product, 'pricing') else None),
        'seo_form': ProductSEOForm(instance=product.seo if product and hasattr(product, 'seo') else None),
        'shipping_form': ProductShippingForm(instance=product.shipping if product and hasattr(product, 'shipping') else None),
        'legal_form': ProductLegalForm(instance=product.legal if product and hasattr(product, 'legal') else None),
        'production_form': ProductProductionForm(instance=product.production if product and hasattr(product, 'production') else None),
        'processes': processes,
        'vendors': vendors,
        'existing_variables_json': existing_variables_json,
        'primary_image': product.images.filter(is_primary=True).first() if product else None,
        'gallery_images': product.images.filter(is_primary=False).order_by('display_order') if product else [],
        'existing_images': product.images.filter(is_primary=False).order_by('display_order') if product else [],
        'gallery_images_count': product.images.filter(is_primary=False).count() if product else 0,
        'has_primary_image': product.images.filter(is_primary=True).exists() if product else False,
        'categories': ProductCategory.objects.all().order_by('name'),
        'subcategories': ProductSubCategory.objects.all().order_by('name'),
        'families': ProductFamily.objects.all().order_by('name'),
        'all_tags': ProductTag.objects.all().order_by('name'),
        'history': product.change_history.all().order_by('-changed_at') if product else [],
    }
    
    return context



    
    # Review Settings
    review_settings, created = ProductReviewSettings.objects.get_or_create(product=product)
    review_settings.enable_reviews = request.POST.get('enable_reviews') == 'on'
    review_settings.require_purchase = request.POST.get('require_purchase') == 'on'
    review_settings.auto_approve_reviews = request.POST.get('auto_approve_reviews') == 'on'
    review_settings.review_reminder = request.POST.get('review_reminder', '7')
    review_settings.save()
    
    # FAQs - Delete existing and create new
    product.faqs.all().delete()
    
    faq_questions = request.POST.getlist('faq_question[]')
    faq_answers = request.POST.getlist('faq_answer[]')
    
    for idx, question in enumerate(faq_questions):
        if question.strip() and idx < len(faq_answers) and faq_answers[idx].strip():
            ProductFAQ.objects.create(
                product=product,
                question=question.strip(),
                answer=faq_answers[idx].strip(),
                display_order=idx,
                is_active=True
            )


def _handle_shipping_tab(request, product):
    """Handle shipping tab"""
    from clientapp.product_forms import ProductShippingForm
    
    # Get or create shipping instance
    shipping, created = ProductShipping.objects.get_or_create(product=product)
    
    shipping_form = ProductShippingForm(request.POST, instance=shipping)
    if shipping_form.is_valid():
        shipping = shipping_form.save(commit=False)
        shipping.product = product
        shipping.save()
    else:
        # Fallback
        shipping.shipping_weight = Decimal(request.POST.get('shipping_weight', '0') or '0')
        shipping.shipping_weight_unit = request.POST.get('shipping_weight_unit', 'kg')
        shipping.save()


def _handle_legal_tab(request, product):
    """Handle legal tab"""
    from clientapp.product_forms import ProductLegalForm
    
    # Get or create legal instance
    legal, created = ProductLegal.objects.get_or_create(product=product)
    
    legal_form = ProductLegalForm(request.POST, instance=legal)
    if legal_form.is_valid():
        legal = legal_form.save(commit=False)
        legal.product = product
        legal.save()


def _handle_production_tab(request, product):
    """Handle production tab - COMPLETE VERSION"""
    from clientapp.product_forms import ProductProductionForm
    
    # Get or create production instance
    production, created = ProductProduction.objects.get_or_create(product=product)
    
    production_form = ProductProductionForm(request.POST, instance=production)
    if production_form.is_valid():
        production = production_form.save(commit=False)
        production.product = product
        production.save()
    else:
        # Fallback to manual saving if form fails for some reason
        production.production_method_detail = request.POST.get('production_method_detail', '')
        production.machine_equipment = request.POST.get('machine_equipment', '')
        production.checklist_artwork = request.POST.get('checklist_artwork') == 'on'
        production.checklist_preflight = request.POST.get('checklist_preflight') == 'on'
        production.checklist_material = request.POST.get('checklist_material') == 'on'
        production.checklist_proofs = request.POST.get('checklist_proofs') == 'on'
        production.save()

# PRODUCT MANAGEMENT VIEWS

from django.utils.text import slugify
from django.urls import reverse
import json
from decimal import Decimal

@login_required
def product_detail(request, pk):
    """Display comprehensive product details - Read-only view"""
    product = get_object_or_404(Product, pk=pk)
    
    # Fetch all related data with explicit queryset to ensure images are loaded
    # Use .all() to force fresh query from database
    images = product.images.all().order_by('display_order')
    pricing = ProductPricing.objects.filter(product=product)
    change_history = ProductChangeHistory.objects.filter(product=product).order_by('-changed_at')[:20]
    
    # If no pricing tiers exist but product has base_price, create a default one
    if not pricing.exists() and product.base_price and product.base_price > 0:
        pricing_tier, created = ProductPricing.objects.get_or_create(
            product=product,
            defaults={
                'pricing_model': 'fixed',
                'base_cost': product.base_price * 0.5,  # Assume 50% cost
                'price_display': 'from',
                'default_margin': 30,
                'minimum_margin': 15,
            }
        )
        pricing = ProductPricing.objects.filter(product=product)
    
    # Calculate total cost from formula-based process variables
    formula_process_variables_cost = None
    if pricing.exists() and pricing.first().formula_process:
        formula_process = pricing.first().formula_process
        # Sum all variable prices in the formula process
        from decimal import Decimal
        variables = formula_process.variables.all()
        if variables.exists():
            total_cost = Decimal('0')
            for var in variables:
                # Use variable price if available, else use the first range price
                if var.price and var.price > 0:
                    total_cost += var.price
                elif var.ranges.exists():
                    # If no direct price, use the base price of first range
                    total_cost += var.ranges.first().price
            formula_process_variables_cost = total_cost if total_cost > 0 else None
    
    # Try to get SEO data if it exists
    seo_data = None
    try:
        seo_data = ProductSEO.objects.get(product=product)
    except ProductSEO.DoesNotExist:
        pass
    
    # Check if user is in Production Team group
    is_production_team = request.user.groups.filter(name='Production Team').exists()
    
    context = {
        'product': product,
        'images': images,
        'pricing': pricing,
        'formula_process_variables_cost': formula_process_variables_cost,
        'seo_data': seo_data,
        'change_history': change_history,
        'is_production_team': is_production_team,
        'current_view': 'product_catalog',
    }
    
    return render(request, 'product_detail_view.html', context)


@login_required
@group_required('Production Team')
@transaction.atomic
def product_create(request):
    """Create new product - Multi-tab form"""
    
    if request.method == 'POST':
        try:
            action = request.POST.get('action', '').strip()
            next_tab = request.POST.get('next_tab', '')
            
            # Require explicit action - don't default to save_draft
            if not action:
                return JsonResponse({
                    'success': False,
                    'message': 'Please explicitly click "Save Draft" or "Publish" to create a product',
                }, status=400)
            
            # Auto-save is disabled for new product creation
            # Users must explicitly click "Save Draft" or "Publish" to create a product
            if action == 'auto_save':
                return JsonResponse({
                    'success': True,
                    'message': 'Please save your product by clicking "Save Draft" or "Publish" button',
                })
            
            # TAB 1: GENERAL INFO
            
            from django.http import QueryDict
            general_post_data = QueryDict(mutable=True)
            for key in request.POST.keys():
                if key != 'base_price':  # Exclude base_price - handled in pricing tab
                    values = request.POST.getlist(key)
                    for value in values:
                        general_post_data.appendlist(key, value)
            
            try:
                general_form = ProductGeneralInfoForm(general_post_data)
            except (KeyError, AttributeError, ValueError) as e:
                
                error_str = str(e).lower()
                if 'base_price' in error_str or 'no field named' in error_str:
                    # Create a completely clean QueryDict without base_price
                    from django.http import QueryDict
                    clean_data = QueryDict(mutable=True)
                    for key in request.POST.keys():
                        if key != 'base_price':
                            values = request.POST.getlist(key)
                            for value in values:
                                clean_data.appendlist(key, value)
                    general_form = ProductGeneralInfoForm(clean_data)
                else:
                    raise
            except Exception as e:
                # Log the error for debugging
                import traceback
                print(f"Unexpected error in ProductGeneralInfoForm: {e}")
                print(traceback.format_exc())
                raise
            
            if not general_form.is_valid():
                messages.error(request, 'Please correct the errors in General Info tab')
                for field, errors in general_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                context = _get_product_form_context(None, general_form=general_form)
                return render(request, 'product_create_edit.html', context)
            
            product = general_form.save(commit=False)
            product.created_by = request.user
            product.updated_by = request.user
            
            # Set customization_level from form 
            customization_level = request.POST.get('customization_level', 'non_customizable')
            if customization_level:
                product.customization_level = customization_level
            
            # Set status based on action
            if action == 'publish':
                product.status = 'published'
            else:
                product.status = 'draft'
            
           
            product.save(skip_validation=True)
            general_form.save_m2m()
            
            # Handle dynamic tags
            tag_names = request.POST.getlist('new_tag[]')
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if tag_name:
                    tag_slug = slugify(tag_name)
                    tag, created = ProductTag.objects.get_or_create(
                        slug=tag_slug,
                        defaults={'name': tag_name}
                    )
                    product.tags.add(tag)
            
            # Handle custom unit
            if product.unit_of_measure == 'other':
                custom_unit = request.POST.get('unit_of_measure_custom', '').strip()
                if custom_unit:
                    product.unit_of_measure_custom = custom_unit
                    product.save()
            
            # Handle all tabs - use savepoints to isolate each handler
            from django.db import transaction
            
            try:
                _handle_pricing_tab(request, product)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f'Error saving pricing: {str(e)}')
            
            try:
                _handle_images_tab(request, product)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f'Error saving images: {str(e)}')
            
            try:
                _handle_seo_tab(request, product)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f'Error saving SEO: {str(e)}')
            
            try:
                _handle_shipping_tab(request, product)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f'Error saving shipping: {str(e)}')
            
            try:
                _handle_legal_tab(request, product)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f'Error saving legal: {str(e)}')
            
            try:
                _handle_production_tab(request, product)
            except Exception as e:
                transaction.set_rollback(True)
                messages.error(request, f'Error saving production: {str(e)}')
            
            
            try:
                product.full_clean()  # Validate with proper base_price
                product.save() 
            except ValidationError as e:
                # If validation fails
                if action == 'publish':
                    product.status = 'draft'
                    product.save(skip_validation=True)
                # Handle both dict and non-dict ValidationError formats
                if hasattr(e, 'error_dict'):
                    for field, errors in e.error_dict.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                elif hasattr(e, 'message'):
                    messages.error(request, str(e.message))
                else:
                    messages.error(request, str(e))
                context = _get_product_form_context(product)
                return render(request, 'product_create_edit.html', context)
            
            # Validate product
            if action == 'publish':
                #validation for costing processes
                can_publish, error_msg = product.can_be_published()
                if not can_publish:
                    messages.error(request, f'Cannot publish product: {error_msg}')
                    product.status = 'draft'
                    product.save(skip_validation=True)
                    context = _get_product_form_context(product)
                    return render(request, 'product_create_edit.html', context)
            
            # Create history
            ProductChangeHistory.objects.create(
                product=product,
                changed_by=request.user,
                change_type='created',
                notes=f'Product created with status: {product.status}'
            )
            
            # Success message
            if action == 'publish':
                messages.success(request, f'✓ Product "{product.name}" ({product.internal_code}) published successfully!')
            else:
                messages.success(request, f'✓ Product "{product.name}" ({product.internal_code}) saved as draft!')
            
            # Redirect based on next_tab or action
            if next_tab and action != 'publish':
                return redirect(f"{reverse('product_edit', kwargs={'pk': product.pk})}?tab={next_tab}")
            elif action == 'publish':
                # After publish, go to catalog
                return redirect('production_catalog')
            else:
                return redirect('product_edit', pk=product.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating product: {str(e)}')
            import traceback
            traceback.print_exc()
            context = _get_product_form_context(None)
            return render(request, 'product_create_edit.html', context)
    
    # GET request
    context = _get_product_form_context(None)
    return render(request, 'product_create_edit.html', context)


@login_required
@group_required('Production Team')
@transaction.atomic
def product_edit(request, pk):
    """Edit existing product - Multi-tab form"""
    
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        try:
            action = request.POST.get('action', '').strip()
            next_tab = request.POST.get('next_tab', '')
            
            # Require explicit action for product creation/updates
            if not action:
                return JsonResponse({
                    'success': False,
                    'message': 'Please explicitly click "Save Draft" or "Publish" to save changes',
                }, status=400)
            
            # Handle auto-save - return JSON response
            if action == 'auto_save':
                try:
                    from django.http import QueryDict
                    general_post_data = QueryDict(mutable=True)
                    for key in request.POST.keys():
                        if key not in ['action', 'next_tab', 'base_price'] and not key.startswith('delete_'):
                            values = request.POST.getlist(key)
                            for value in values:
                                general_post_data.appendlist(key, value)
                    
                    general_form = ProductGeneralInfoForm(general_post_data, instance=product)
                    
                    if general_form.is_valid():
                        product = general_form.save(commit=False)
                        product.updated_by = request.user
                        customization_level = request.POST.get('customization_level', 'non_customizable')
                        if customization_level:
                            product.customization_level = customization_level
                        product.save(skip_validation=True)
                        general_form.save_m2m()
                        
                        # Auto-save all tabs that have data
                        try:
                            _handle_pricing_tab(request, product)
                        except:
                            pass  # Don't fail auto-save if pricing fails
                        
                        try:
                            _handle_images_tab(request, product)
                        except:
                            pass  # Don't fail auto-save if images fail
                        
                        try:
                            _handle_seo_tab(request, product)
                        except:
                            pass
                        
                        try:
                            _handle_shipping_tab(request, product)
                        except:
                            pass
                        
                        try:
                            _handle_legal_tab(request, product)
                        except:
                            pass
                        
                        try:
                            _handle_production_tab(request, product)
                        except:
                            pass
                        
                        return JsonResponse({
                            'success': True,
                            'message': 'Product auto-saved successfully',
                            'timestamp': timezone.now().isoformat()
                        })
                    else:
                        return JsonResponse({
                            'success': False,
                            'message': 'Validation failed',
                            'errors': general_form.errors
                        }, status=400)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return JsonResponse({
                        'success': False,
                        'message': str(e)
                    }, status=400)
           
            from django.http import QueryDict
            general_post_data = QueryDict(mutable=True)
            for key in request.POST.keys():
                if key != 'base_price':  # Exclude base_price - handled in pricing tab
                    values = request.POST.getlist(key)
                    for value in values:
                        general_post_data.appendlist(key, value)
            
            try:
                general_form = ProductGeneralInfoForm(general_post_data, instance=product)
            except Exception as e:
                
                if 'base_price' in str(e).lower():
                    general_form = ProductGeneralInfoForm(instance=product)
                    messages.warning(request, 'Note: base_price is handled in Pricing & Variables tab')
                else:
                    raise
            
            if not general_form.is_valid():
                messages.error(request, 'Please correct the errors in General Info tab')
                for field, errors in general_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
                context = _get_product_form_context(product, general_form=general_form)
                return render(request, 'product_create_edit.html', context)
            
            product = general_form.save(commit=False)
            product.updated_by = request.user
            
            # Update customization_level from form
            customization_level = request.POST.get('customization_level', 'non_customizable')
            if customization_level:
                product.customization_level = customization_level
            
            # Update status if publishing
            if action == 'publish':
                old_status = product.status
                product.status = 'published'
                if old_status != 'published':
                    ProductChangeHistory.objects.create(
                        product=product,
                        changed_by=request.user,
                        change_type='published',
                        field_changed='status',
                        old_value=old_status,
                        new_value='published'
                    )
            
            # Save product first 
            product.save(skip_validation=True)
            general_form.save_m2m()
            
            # Handle dynamic tags
            product.tags.clear()
            tag_names = request.POST.getlist('new_tag[]')
            for tag_name in tag_names:
                tag_name = tag_name.strip()
                if tag_name:
                    tag, created = ProductTag.objects.get_or_create(
                        name=tag_name,
                        defaults={'slug': slugify(tag_name)}
                    )
                    product.tags.add(tag)
            
            # Handle custom unit
            if product.unit_of_measure == 'other':
                custom_unit = request.POST.get('unit_of_measure_custom', '').strip()
                if custom_unit:
                    product.unit_of_measure_custom = custom_unit
                    product.save(skip_validation=True)
            
            # Update all tabs (this will set base_price properly)
            try:
                _handle_pricing_tab(request, product)
            except Exception as e:
                messages.warning(request, f'Error saving pricing: {str(e)}')
            
            try:
                _handle_images_tab(request, product)
            except Exception as e:
                messages.warning(request, f'Error saving images: {str(e)}')
            
            try:
                _handle_seo_tab(request, product)
            except Exception as e:
                messages.warning(request, f'Error saving SEO: {str(e)}')
            
            try:
                _handle_shipping_tab(request, product)
            except Exception as e:
                messages.warning(request, f'Error saving shipping: {str(e)}')
            
            try:
                _handle_legal_tab(request, product)
            except Exception as e:
                messages.warning(request, f'Error saving legal: {str(e)}')
            
            try:
                _handle_production_tab(request, product)
            except Exception as e:
                messages.warning(request, f'Error saving production: {str(e)}')
            
            
            try:
                product.full_clean()  # Validate with proper base_price
                product.save()  # Save with validation
            except ValidationError as e:
                # If validation fails, show errors
                if action == 'publish':
                    product.status = 'draft'
                    product.save(skip_validation=True)
                # Handle both dict and non-dict ValidationError formats
                if hasattr(e, 'error_dict'):
                    for field, errors in e.error_dict.items():
                        for error in errors:
                            messages.error(request, f"{field}: {error}")
                elif hasattr(e, 'message'):
                    messages.error(request, str(e.message))
                else:
                    messages.error(request, str(e))
                context = _get_product_form_context(product)
                return render(request, 'product_create_edit.html', context)
            
            # Validate product before publishing
            if action == 'publish':
                # Additional validation for costing processes
                can_publish, error_msg = product.can_be_published()
                if not can_publish:
                    messages.error(request, f'Cannot publish product: {error_msg}')
                    product.status = 'draft'
                    product.save(skip_validation=True)
                    context = _get_product_form_context(product)
                    return render(request, 'product_create_edit.html', context)
            
            # Create change history
            ProductChangeHistory.objects.create(
                product=product,
                changed_by=request.user,
                change_type='updated',
                notes=f'Product updated - Action: {action}'
            )
            
            # Success messages
            if action == 'publish':
                messages.success(request, f'✓ Product "{product.name}" published successfully!')
                return redirect('production_catalog')
            else:
                messages.success(request, f'✓ Product "{product.name}" updated successfully!')
            
            # Redirect based on next_tab
            if next_tab:
                return redirect(f"{reverse('product_edit', kwargs={'pk': product.pk})}?tab={next_tab}")
            else:
                return redirect('product_edit', pk=product.pk)
            
        except Exception as e:
            messages.error(request, f'Error updating product: {str(e)}')
            import traceback
            traceback.print_exc()
            return redirect('product_edit', pk=product.pk)
    
    # GET request
    context = _get_product_form_context(product)
    return render(request, 'product_create_edit.html', context)


# ========== HELPER FUNCTIONS ==========

def _get_product_form_context(product, general_form=None):
    """Get context for product form"""
    
    # Existing variables JSON
    existing_variables = []
    if product:
        for var in product.variables.all():
            options = []
            for opt in var.options.all():
                options.append({
                    'value': opt.name,
                    'price_adjustment': float(opt.price_modifier),
                    'is_default': opt.is_default
                })
            existing_variables.append({
                'name': var.name,
                'display_order': var.display_order,
                'variable_type': var.variable_type,
                'pricing_type': var.pricing_type,
                'options': options
            })
    
    context = {
        'current_view': 'production_catalog',
        'general_form': general_form or ProductGeneralInfoForm(instance=product),
        'pricing_form': ProductPricingForm(instance=product.pricing if product and hasattr(product, 'pricing') else None),
        'seo_form': ProductSEOForm(instance=product.seo if product and hasattr(product, 'seo') else None),
        'shipping_form': ProductShippingForm(instance=product.shipping if product and hasattr(product, 'shipping') else None),
        'legal_form': ProductLegalForm(instance=product.legal if product and hasattr(product, 'legal') else None),
        'production_form': ProductProductionForm(instance=product.production if product and hasattr(product, 'production') else None),
        'product': product,
        'is_edit': product is not None,
        'existing_variables_json': json.dumps(existing_variables),
        'primary_image': product.images.filter(is_primary=True).first() if product else None,
        'existing_images': product.images.filter(is_primary=False).order_by('display_order') if product else [],
        'categories': ProductCategory.objects.all().order_by('name'),
        'subcategories': ProductSubCategory.objects.all().order_by('name'),
        'families': ProductFamily.objects.all().order_by('name'),
        'vendors': Vendor.objects.filter(active=True).order_by('name'),
        'all_tags': ProductTag.objects.all().order_by('name'),
        'processes': Process.objects.filter(status='active').order_by('process_name'),
    }
    
    return context

def _handle_pricing_tab(request, product):
    """Handle pricing and variables tab"""
    
    # Get or create pricing instance
    pricing, created = ProductPricing.objects.get_or_create(product=product)
    
    # Save basic pricing fields
    pricing.pricing_model = request.POST.get('pricing_model', 'variable')
    
    # Base cost - ensure it's never NULL
    base_cost = request.POST.get('base_cost', '').strip()
    if not base_cost or base_cost == '':
        base_cost = '15'  # Default value matching the form
    try:
        pricing.base_cost = Decimal(base_cost)
    except (ValueError, decimal.InvalidOperation):
        pricing.base_cost = Decimal('15')
    
    # Price display format and amount
    pricing.price_display = request.POST.get('price_display', 'from')
    
    # Margins
    try:
        pricing.default_margin = Decimal(request.POST.get('default_margin', '30'))
        pricing.minimum_margin = Decimal(request.POST.get('minimum_margin', '15'))
    except:
        pricing.default_margin = Decimal('30')
        pricing.minimum_margin = Decimal('15')
    
    # Minimum order value
    try:
        pricing.minimum_order_value = Decimal(request.POST.get('minimum_order_value', '0'))
    except:
        pricing.minimum_order_value = Decimal('0')
    
    # Production & Vendor Information
    try:
        pricing.lead_time_value = int(request.POST.get('lead_time_value', '3'))
    except:
        pricing.lead_time_value = 3
    
    pricing.lead_time_unit = request.POST.get('lead_time_unit', 'days')
    pricing.production_method = request.POST.get('production_method', 'digital-offset')
    
    # Handle custom production method
    if pricing.production_method == 'other':
        custom_method = request.POST.get('production_method_custom', '').strip()
        if custom_method:
            pricing.production_method = custom_method
    
    # Primary vendor
    primary_vendor_id = request.POST.get('primary_vendor')
    if primary_vendor_id:
        try:
            pricing.primary_vendor = Vendor.objects.get(id=primary_vendor_id)
        except Vendor.DoesNotExist:
            pass
    
    # Minimum quantity
    try:
        pricing.minimum_quantity = int(request.POST.get('minimum_quantity', '1'))
    except:
        pricing.minimum_quantity = 1
    
    # Rush production
    pricing.rush_available = request.POST.get('rush_available') == 'on'
    
    if pricing.rush_available:
        try:
            pricing.rush_lead_time_value = int(request.POST.get('rush_lead_time_value', '1'))
        except:
            pricing.rush_lead_time_value = 1
        
        pricing.rush_lead_time_unit = request.POST.get('rush_lead_time_unit', 'days')
        
        try:
            pricing.rush_upcharge = Decimal(request.POST.get('rush_upcharge', '0'))
        except:
            pricing.rush_upcharge = Decimal('0')
    
    # Conditional logic and conflict detection
    pricing.enable_conditional_logic = request.POST.get('enable_conditional_logic') == 'on'
    pricing.enable_conflict_detection = request.POST.get('enable_conflict_detection') == 'on'
    
    # Handle tier and formula processes
    tier_process_id = request.POST.get('tier_process', '').strip()
    if tier_process_id:
        try:
            pricing.tier_process = Process.objects.get(id=tier_process_id)
        except Process.DoesNotExist:
            pass
    else:
        pricing.tier_process = None
    
    formula_process_id = request.POST.get('formula_process', '').strip()
    if formula_process_id:
        try:
            pricing.formula_process = Process.objects.get(id=formula_process_id)
        except Process.DoesNotExist:
            pass
    else:
        pricing.formula_process = None
    
    pricing.save()
    
    # Handle Product.base_price based on customization_level
    customization_level = product.customization_level
    base_price_str = request.POST.get('base_price', '').strip()
    
    if customization_level == 'non_customizable':
        # Non-customizable: base_price is required
        if not base_price_str:
            # Calculate from base_cost + margin if base_price not provided
            if pricing.base_cost and pricing.return_margin:
                margin = pricing.return_margin / Decimal('100')
                product.base_price = pricing.base_cost * (Decimal('1') + margin)
            else:
                # Use default calculation
                product.base_price = pricing.base_cost * Decimal('1.30')  
        else:
            try:
                product.base_price = Decimal(base_price_str)
            except (ValueError, decimal.InvalidOperation):
                # Fallback to calculated price
                if pricing.base_cost and pricing.return_margin:
                    margin = pricing.return_margin / Decimal('100')
                    product.base_price = pricing.base_cost * (Decimal('1') + margin)
                else:
                    product.base_price = pricing.base_cost * Decimal('1.30')
    elif customization_level == 'semi_customizable':
        # Semi-customizable: base_price is REQUIRED
        if not base_price_str:
            # Calculate from base_cost + margin if base_price not provided
            if pricing.base_cost and pricing.return_margin:
                margin = pricing.return_margin / Decimal('100')
                product.base_price = pricing.base_cost * (Decimal('1') + margin)
            else:
                product.base_price = pricing.base_cost * Decimal('1.30')
        else:
            try:
                product.base_price = Decimal(base_price_str)
            except (ValueError, decimal.InvalidOperation):
                if pricing.base_cost and pricing.return_margin:
                    margin = pricing.return_margin / Decimal('100')
                    product.base_price = pricing.base_cost * (Decimal('1') + margin)
                else:
                    product.base_price = pricing.base_cost * Decimal('1.30')
    else:  # fully_customizable
        # Fully customizable: base_price must be NULL
        product.base_price = None
    
    product.save(skip_validation=True, update_fields=['base_price'])
    
    # Handle alternative vendors (many-to-many)
    alt_vendor_ids = request.POST.getlist('alternative_vendors')
    pricing.alternative_vendors.clear()
    for vendor_id in alt_vendor_ids:
        try:
            vendor = Vendor.objects.get(id=vendor_id)
            pricing.alternative_vendors.add(vendor)
        except Vendor.DoesNotExist:
            pass
    
    # Check minimum margin trigger - send notification to admin
    if pricing.default_margin < pricing.minimum_margin:
        from django.contrib.auth.models import User
        admins = User.objects.filter(is_superuser=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                title=f'Margin Approval Required - {product.name}',
                message=f'Product margin ({pricing.default_margin}%) is below minimum ({pricing.minimum_margin}%). Approval required.',
                link=reverse('product_edit', kwargs={'pk': product.pk})
            )
    
    # Handle Product Variables
    variables_json = request.POST.get('product_variables_json')
    if variables_json:
        try:
            # Delete existing variables
            product.variables.all().delete()
            
            # Create new variables
            variables_data = json.loads(variables_json)
            for idx, var_data in enumerate(variables_data):
                variable = ProductVariable.objects.create(
                    product=product,
                    name=var_data.get('name', f'Variable {idx+1}'),
                    display_order=var_data.get('display_order', idx),
                    variable_type=var_data.get('variable_type', 'required'),
                    pricing_type=var_data.get('pricing_type', 'fixed'),
                    is_active=True
                )
                
                for opt_idx, opt_data in enumerate(var_data.get('options', [])):
                    ProductVariableOption.objects.create(
                        variable=variable,
                        name=opt_data.get('value', f'Option {opt_idx+1}'),
                        display_order=opt_idx,
                        is_default=opt_data.get('is_default', False),
                        price_modifier=Decimal(str(opt_data.get('price_adjustment', 0))),
                        is_active=True
                    )
        except json.JSONDecodeError as e:
            messages.warning(request, f"Error processing variables: {str(e)}")



def _handle_images_tab(request, product):
    """Handle images and media tab - COMPLETE WORKING VERSION"""
    
    # Pri IMage
    primary_image = request.FILES.get('primary_image')
    if primary_image:
        # Validate file
        if not primary_image.content_type.startswith('image/'):
            messages.warning(request, 'Primary image must be an image file')
        elif primary_image.size > 2 * 1024 * 1024:  
            messages.warning(request, 'Primary image must be less than 2MB')
        else:
            
            ProductImage.objects.filter(product=product, is_primary=True).delete()
            # Create new primary
            ProductImage.objects.create(
                product=product,
                image=primary_image,
                alt_text=request.POST.get('primary_image_alt', product.name),
                is_primary=True,
                display_order=0,
                image_type='product-photo'
            )
    
    #Images
    gallery_images = request.FILES.getlist('gallery_images')
    if gallery_images:
        # Get max display order
        max_order = product.images.aggregate(
            models.Max('display_order')
        )['display_order__max'] or 0
        
        for idx, img_file in enumerate(gallery_images, start=1):
            # Validate file
            if not img_file.content_type.startswith('image/'):
                continue
            if img_file.size > 2 * 1024 * 1024:
                messages.warning(request, f'{img_file.name} is too large (max 2MB)')
                continue
            
            ProductImage.objects.create(
                product=product,
                image=img_file,
                alt_text=f"{product.name} - Image {max_order + idx}",
                is_primary=False,
                display_order=max_order + idx,
                image_type='product-photo'
            )
    
    # Image Deletion
    delete_image_ids = request.POST.getlist('delete_images[]')
    if delete_image_ids:
        ProductImage.objects.filter(
            product=product,
            id__in=delete_image_ids,
            is_primary=False  
        ).delete()
    
    # Product Videos
    for video in product.videos.all():
        video_url = request.POST.get(f'video_url_{video.pk}', '').strip()
        if video_url:
            video.video_url = video_url
            video.video_type = request.POST.get(f'video_type_{video.pk}', 'demo')
            
            # Handle thumbnail update
            thumbnail = request.FILES.get(f'video_thumbnail_{video.pk}')
            if thumbnail:
                video.thumbnail = thumbnail
            
            video.save()
    
    # Add new videos
    new_video_urls = request.POST.getlist('new_video_url[]')
    new_video_types = request.POST.getlist('new_video_type[]')
    new_video_thumbnails = request.FILES.getlist('new_video_thumbnail[]')
    
    for idx, url in enumerate(new_video_urls):
        if url.strip():
            video_data = {
                'product': product,
                'video_url': url.strip(),
                'video_type': new_video_types[idx] if idx < len(new_video_types) else 'demo',
                'display_order': product.videos.count() + idx
            }
            
            # Thumbnails
            if idx < len(new_video_thumbnails):
                video_data['thumbnail'] = new_video_thumbnails[idx]
            
            ProductVideo.objects.create(**video_data)
    
    # Existing files
    for file_obj in product.downloadable_files.all():
        file_name = request.POST.get(f'file_name_{file_obj.pk}', '').strip()
        if file_name:
            file_obj.file_name = file_name
            file_obj.file_type = request.POST.get(f'file_type_{file_obj.pk}', file_obj.file_type)
            file_obj.description = request.POST.get(f'file_desc_{file_obj.pk}', '')
            file_obj.save()
    
    # Add new files
    new_files = request.FILES.getlist('new_downloadable_files')
    new_file_names = request.POST.getlist('new_file_name[]')
    new_file_types = request.POST.getlist('new_file_type[]')
    new_file_descriptions = request.POST.getlist('new_file_description[]')
    
    for idx, file in enumerate(new_files):
        # Validate file size (max 10MB)
        if file.size > 10 * 1024 * 1024:
            messages.warning(request, f'{file.name} is too large (max 10MB)')
            continue
        
        # Get file extension
        file_ext = file.name.split('.')[-1].lower()
        
        # Map extension to file type
        file_type_map = {
            'ai': 'illustrator',
            'pdf': 'pdf',
            'psd': 'psd',
            'indd': 'indd',
            'zip': 'zip'
        }
        file_type = new_file_types[idx] if idx < len(new_file_types) else file_type_map.get(file_ext, 'pdf')
        file_name = new_file_names[idx] if idx < len(new_file_names) and new_file_names[idx].strip() else file.name
        file_desc = new_file_descriptions[idx] if idx < len(new_file_descriptions) else ''
        
        ProductDownloadableFile.objects.create(
            product=product,
            file_name=file_name,
            file=file,
            file_type=file_type,
            description=file_desc,
            file_size=file.size,
            display_order=product.downloadable_files.count() + idx
        )

@login_required
@group_required('Production Team')
def product_update_image_metadata(request, image_pk):
    """Update image metadata via AJAX"""
    if request.method == 'POST':
        try:
            image = get_object_or_404(ProductImage, pk=image_pk)
            
            image.alt_text = request.POST.get('alt_text', image.alt_text)
            image.caption = request.POST.get('caption', '')
            image.image_type = request.POST.get('image_type', image.image_type)
            
            # Handle variable associations if provided
            var_id = request.POST.get('associated_variable')
            opt_id = request.POST.get('associated_option')
            
            if var_id:
                try:
                    image.associated_variable_id = int(var_id)
                except (ValueError, TypeError):
                    pass
            
            if opt_id:
                try:
                    image.associated_option_id = int(opt_id)
                except (ValueError, TypeError):
                    pass
            
            image.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Image updated successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def _handle_seo_tab(request, product):
    """Handle SEO and e-commerce tab - COMPLETE VERSION"""
    
    # Get or create SEO instance
    seo, created = ProductSEO.objects.get_or_create(product=product)
    
    # Basic SEO fields
    seo.meta_title = request.POST.get('meta_title', '')[:60]
    seo.meta_description = request.POST.get('meta_description', '')[:160]
    seo.focus_keyword = request.POST.get('focus_keyword', '')
    seo.additional_keywords = request.POST.get('additional_keywords', '')
    
    # Slug handling
    seo.auto_generate_slug = request.POST.get('auto_generate_slug') == 'on'
    if seo.auto_generate_slug or not seo.slug:
        slug_value = slugify(product.name)
        # If slug is empty (e.g., product has no name yet), use product ID
        if not slug_value:
            slug_value = f'product-{product.id}'
        seo.slug = slug_value
    else:
        slug_value = slugify(request.POST.get('slug', product.name))
        # Ensure slug is not empty
        if not slug_value:
            slug_value = f'product-{product.id}'
        seo.slug = slug_value
    
    # Display settings
    seo.show_price = request.POST.get('show_price') == 'on'
    seo.price_display_format = request.POST.get('price_display_format', 'from')
    seo.show_stock_status = request.POST.get('show_stock_status', 'in-stock-only')
    
    seo.save()
    
    # Handle related products (many-to-many)
    related_product_ids = request.POST.getlist('related_products')
    seo.related_products.clear()
    for prod_id in related_product_ids:
        try:
            related_prod = Product.objects.get(id=prod_id)
            seo.related_products.add(related_prod)
        except Product.DoesNotExist:
            pass
    
    # Handle upsell products
    upsell_product_ids = request.POST.getlist('upsell_products')
    seo.upsell_products.clear()
    for prod_id in upsell_product_ids:
        try:
            upsell_prod = Product.objects.get(id=prod_id)
            seo.upsell_products.add(upsell_prod)
        except Product.DoesNotExist:
            pass
    
    # Handle frequently bought together
    bundle_product_ids = request.POST.getlist('frequently_bought_together')
    seo.frequently_bought_together.clear()
    for prod_id in bundle_product_ids:
        try:
            bundle_prod = Product.objects.get(id=prod_id)
            seo.frequently_bought_together.add(bundle_prod)
        except Product.DoesNotExist:
            pass
    
    # Review Settings
    review_settings, created = ProductReviewSettings.objects.get_or_create(product=product)
    review_settings.enable_reviews = request.POST.get('enable_reviews') == 'on'
    review_settings.require_purchase = request.POST.get('require_purchase') == 'on'
    review_settings.auto_approve_reviews = request.POST.get('auto_approve_reviews') == 'on'
    review_settings.review_reminder = request.POST.get('review_reminder', '7')
    review_settings.save()
    
    # FAQs - Delete existing and create new
    product.faqs.all().delete()
    
    faq_questions = request.POST.getlist('faq_question[]')
    faq_answers = request.POST.getlist('faq_answer[]')
    
    for idx, question in enumerate(faq_questions):
        if question.strip() and idx < len(faq_answers) and faq_answers[idx].strip():
            ProductFAQ.objects.create(
                product=product,
                question=question.strip(),
                answer=faq_answers[idx].strip(),
                display_order=idx,
                is_active=True
            )


def _handle_production_tab(request, product):
    """Handle production tab - COMPLETE VERSION"""
    
    # Get or create production instance
    production, created = ProductProduction.objects.get_or_create(product=product)
    
    # Production specifications
    production.production_method_detail = request.POST.get('production_method_detail', '')
    production.machine_equipment = request.POST.get('machine_equipment', '')
    
    # Additional production fields 
    production_data = {
        'print_layout': request.POST.get('print_layout', ''),
        'color_profile': request.POST.get('color_profile', ''),
        'finishing': {
            'lamination': request.POST.get('finishing_lamination') == 'on',
            'packaging': request.POST.get('finishing_packaging') == 'on',
            'die_cutting': request.POST.get('finishing_die_cutting') == 'on',
            'embossing': request.POST.get('finishing_embossing') == 'on',
            'registration': request.POST.get('finishing_registration') == 'on',
            'cutting_accuracy': request.POST.get('finishing_cutting_accuracy') == 'on',
        },
        'quality_control': {
            'color_match': request.POST.get('qc_color_match') == 'on',
            'finish_quality': request.POST.get('qc_finish_quality') == 'on',
            'registration': request.POST.get('qc_registration') == 'on',
            'cutting': request.POST.get('qc_cutting') == 'on',
        },
        'bom': {
            'material1': {
                'type': request.POST.get('bom_mat1_type', ''),
                'sheet_size': request.POST.get('bom_mat1_sheet_size', ''),
                'quantity': request.POST.get('bom_mat1_quantity', ''),
                'supplier': request.POST.get('bom_mat1_supplier', ''),
                'cost_per': request.POST.get('bom_mat1_cost_per', '0'),
            },
            'material2': {
                'type': request.POST.get('bom_mat2_type', ''),
                'width': request.POST.get('bom_mat2_width', ''),
                'length': request.POST.get('bom_mat2_length', ''),
                'supplier': request.POST.get('bom_mat2_supplier', ''),
                'cost_per': request.POST.get('bom_mat2_cost_per', '0'),
            },
            'material3': {
                'type': request.POST.get('bom_mat3_type', ''),
                'coverage': request.POST.get('bom_mat3_coverage', ''),
                'estimated': request.POST.get('bom_mat3_estimated', ''),
            }
        },
        'special_instructions': request.POST.get('production_special_instructions', ''),
    }
    
    # Store as JSON in production_notes
    import json
    production.production_notes = json.dumps(production_data, indent=2)
    
    # Pre-Production Checklist
    production.checklist_artwork = request.POST.get('checklist_artwork') == 'on'
    production.checklist_preflight = request.POST.get('checklist_preflight') == 'on'
    production.checklist_material = request.POST.get('checklist_material') == 'on'
    production.checklist_proofs = request.POST.get('checklist_proofs') == 'on'
    
    production.save()

def _handle_shipping_tab(request, product):
    """Handle shipping tab"""
    
    shipping_form = ProductShippingForm(
        request.POST,
        instance=product.shipping if hasattr(product, 'shipping') else None
    )
    
    if shipping_form.is_valid():
        shipping = shipping_form.save(commit=False)
        shipping.product = product
        shipping.save()


def _handle_legal_tab(request, product):
    """Handle legal tab"""
    
    legal_form = ProductLegalForm(
        request.POST,
        instance=product.legal if hasattr(product, 'legal') else None
    )
    
    if legal_form.is_valid():
        legal = legal_form.save(commit=False)
        legal.product = product
        legal.save()


#  AJAX ENDPOINTS 

@login_required
@group_required('Production Team')
def product_delete_image(request, product_pk, image_pk):
    """Delete product image via AJAX"""
    
    if request.method == 'POST':
        try:
            product = get_object_or_404(Product, pk=product_pk)
            image = get_object_or_404(ProductImage, pk=image_pk, product=product)
            
            if image.is_primary:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot delete primary image. Upload a new primary image first.'
                })
            
            image.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Image deleted successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# Pricing endpoint
@login_required
@group_required('Production Team')
def calculate_pricing(request):
    """Calculate pricing breakdown via AJAX"""
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            quantity = int(data.get('quantity', 1))
            base_price = Decimal(str(data.get('base_price', 0)))
            margin = Decimal(str(data.get('margin', 30)))
            
            # Get selected variable options
            variable_costs = Decimal('0')
            for var_option in data.get('variable_options', []):
                variable_costs += Decimal(str(var_option.get('price_adjustment', 0)))
            
            # Calculate
            unit_cost = base_price + variable_costs
            subtotal_evp = unit_cost * quantity
            margin_amount = subtotal_evp * (margin / 100)
            customer_pays = subtotal_evp + margin_amount
            per_unit = customer_pays / quantity if quantity > 0 else Decimal('0')
            
            return JsonResponse({
                'success': True,
                'breakdown': {
                    'base_cost': float(base_price * quantity),
                    'variable_costs': float(variable_costs * quantity),
                    'subtotal_evp': float(subtotal_evp),
                    'margin_percentage': float(margin),
                    'margin_amount': float(margin_amount),
                    'customer_pays': float(customer_pays),
                    'per_unit': float(per_unit)
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

# ADMIN AJAX

@login_required
def dismiss_alert(request, alert_id):
    """Dismiss a system alert"""
    if request.method == 'POST':
        try:
            from .models import SystemAlert
            alert = get_object_or_404(SystemAlert, id=alert_id)
            alert.dismiss(request.user)
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Invalid method'})


@login_required
def export_dashboard_report(request, report_type):
    """Export dashboard reports to CSV"""
    import csv
    from django.http import HttpResponse
    from datetime import datetime
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="report_{report_type}_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'products':
        from .admin_dashboard import get_top_selling_products
        products = get_top_selling_products(limit=50)
        
        writer.writerow(['Rank', 'Product Name', 'Total Revenue', 'Total Quantity', 'Order Count'])
        for idx, product in enumerate(products, 1):
            writer.writerow([
                idx,
                product['product_name'],
                product['total_revenue'],
                product['total_quantity'],
                product['order_count']
            ])
    
    elif report_type == 'margins':
        from .admin_dashboard import get_profit_margin_data
        margins = get_profit_margin_data()
        
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Total Revenue', margins.get('total_revenue', 0)])
        writer.writerow(['Total Cost', margins.get('total_cost', 0)])
        writer.writerow(['Overall Margin %', margins.get('overall_margin', 0)])
    
    return response


from django.contrib.auth.decorators import login_required



@login_required
def quote_detail2(request, quote_id):
    """Display detailed quote information with REAL data"""
    
    # Get all line items for this quote
    quote_items = Quote.objects.filter(quote_id=quote_id).select_related('client', 'lead', 'created_by')
    
    if not quote_items.exists():
        messages.error(request, f'Quote {quote_id} not found')
        return redirect('my_quotes')
    
    first_quote = quote_items.first()
    
    # Calculate totals
    subtotal = sum(item.unit_price * item.quantity for item in quote_items)
    vat_amount = subtotal * Decimal('0.16') if first_quote.include_vat else Decimal('0')
    total_amount = subtotal + vat_amount
    
    # Determine client
    if first_quote.client:
        client = first_quote.client
        client_name = client.name
        client_email = client.email
        client_phone = client.phone
    elif first_quote.lead:
        client_name = first_quote.lead.name
        client_email = first_quote.lead.email
        client_phone = first_quote.lead.phone
        client = None
    else:
        client_name = "Unknown"
        client_email = "-"
        client_phone = "-"
        client = None
    
    # Calculate progress
    completed_items = sum(1 for item in quote_items if item.production_status == 'completed')
    in_progress_items = sum(1 for item in quote_items if item.production_status == 'in_progress')
    pending_items = sum(1 for item in quote_items if item.production_status == 'pending')
    
    total_items = quote_items.count()
    progress_percentage = int((completed_items / total_items) * 100) if total_items > 0 else 0
    
    # Days remaining
    days_remaining = (first_quote.valid_until - timezone.now().date()).days
    
    # Timeline events
    timeline_events = [
        {
            'title': 'Quote Created',
            'date': first_quote.created_at,
            'completed': True
        },
    ]
    
    if first_quote.production_status in ['costed', 'sent_to_client', 'in_production', 'completed']:
        timeline_events.append({
            'title': 'Costing Completed',
            'date': first_quote.updated_at,
            'completed': True
        })
    
    if first_quote.status == 'Approved':
        timeline_events.append({
            'title': 'Client Approved',
            'date': first_quote.approved_at or first_quote.updated_at,
            'completed': True
        })
    
    context = {
        'current_view': 'quote_detail',
        'quote_id': quote_id,
        'first_quote': first_quote,
        'quote_items': quote_items,
        'client_name': client_name,
        'client_email': client_email,
        'client_phone': client_phone,
        'client': client,
        'account_manager': first_quote.created_by,
        'subtotal': subtotal,
        'vat_amount': vat_amount,
        'total_amount': total_amount,
        'progress_percentage': progress_percentage,
        'completed_items': completed_items,
        'in_progress_items': in_progress_items,
        'pending_items': pending_items,
        'days_remaining': days_remaining,
        'timeline_events': timeline_events,
    }
    
    return render(request, 'quote_detail2.html', context)


from django.views.decorators.http import require_POST

@login_required
@group_required('Production Team')
def quote_action(request, quote_id):
    """Handle PT actions on quotes: Approve or Reject"""
    if request.method == 'POST':
        action = request.POST.get('action')
        quotes = Quote.objects.filter(quote_id=quote_id)
        
        if not quotes.exists():
            messages.error(request, 'Quote not found')
            return redirect('my_quotes')
        
        first_quote = quotes.first()
        
        if action == 'approve':
            # Approve quote for sending to client
            quotes.update(
                production_status='approved',
                status='Ready to Send',
                costed_by=request.user
                
            )
            
            # Notify the AM who created it
            Notification.objects.create(
                recipient=first_quote.created_by,
                notification_type='quote_pt_approved',
                title=f' Quote {quote_id} Approved by PT',
                message=f'You can now send this quote to the client!',
                link=f'/create/quote?quote_id={quote_id}',
                related_quote_id=quote_id,
                action_url=f'/create/quote?quote_id={quote_id}',
                action_label='Send to Client'
            )
            
            messages.success(request, f' Quote {quote_id} approved!')
            
        elif action == 'reject':
            reason = request.POST.get('reason', 'No reason provided')
            
            # Reject quote
            quotes.update(
                production_status='rejected',
                status='Rejected',
                production_notes=reason
            )
            
            # Notify the AM
            Notification.objects.create(
                recipient=first_quote.created_by,
                notification_type='quote_pt_rejected',
                title=f' Quote {quote_id} Rejected by PT',
                message=f'Reason: {reason}',
                link=f'/create/quote?quote_id={quote_id}',
                related_quote_id=quote_id
            )
            
            messages.warning(request, f'Quote {quote_id} rejected')
        
        return redirect('my_quotes')
    
    # GET request
    messages.error(request, 'Invalid request')
    return redirect('my_quotes')

# =Jobs
@login_required
@group_required('Production Team')
def my_jobs(request):
    """Show jobs for production team"""
    
    # Get all jobs
    jobs = Job.objects.select_related('client').prefetch_related('vendor_stages').order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        jobs = jobs.filter(status=status_filter)
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        jobs = jobs.filter(
            Q(job_number__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(product__icontains=search_query)
        )
    
    # Prepare jobs data
    today = timezone.now().date()
    jobs_list = []
    
    for job in jobs:
        # Check if job has been assigned to vendors
        vendor_stages = job.vendor_stages.all()
        vendor_count = vendor_stages.count()
        
        # Determine vendor assignment status
        if vendor_count > 0:
            # Get unique vendors assigned
            vendors_assigned = list(set([vs.vendor.name for vs in vendor_stages]))
            vendor_status = f"Assigned to {', '.join(vendors_assigned[:2])}" + ("..." if len(vendors_assigned) > 2 else "")
        else:
            vendor_status = "Not Assigned"
        
        # Determine status class
        days_until_deadline = (job.expected_completion - today).days
        
        if job.status == 'completed':
            status_class = 'completed'
        elif days_until_deadline < 0:
            status_class = 'urgent'
        elif days_until_deadline <= 2:
            status_class = 'urgent'
        elif job.status == 'in_progress':
            status_class = 'in-progress'
        else:
            status_class = 'on-track'
        
        # Calculate progress
        if job.status == 'completed':
            progress = 100
        elif job.status == 'in_progress':
            progress = 60
        elif job.status == 'pending':
            progress = 20
        else:
            progress = 0
        
        jobs_list.append({
            'id': job.id,
            'job_number': job.job_number,
            'client_name': job.client.name if job.client else 'N/A',
            'product_name': job.product,
            'quantity': job.quantity,
            'status_class': status_class,
            'status_label': job.get_status_display(),
            'vendor_status': vendor_status,
            'vendor_count': vendor_count,
            'deadline': job.expected_completion,
            'deadline_time': job.expected_completion.strftime("%I:%M %p") if hasattr(job.expected_completion, 'strftime') else "12:00 PM",
            'days_remaining': f"{days_until_deadline} days" if days_until_deadline > 0 else f"Overdue by {abs(days_until_deadline)} days",
            'is_overdue': days_until_deadline < 0,
            'progress': progress,
        })
    
    context = {
        'current_view': 'my_jobs',
        'jobs': jobs_list,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'my_jobs.html', context)

@login_required
@group_required('Production Team')
def my_quotes(request):
    """Show quotes for Production Team approval/costing"""
    from django.db.models import Q, Count
    
    # Get all quotes except those that have been costed
    
    quotes = Quote.objects.select_related(
        'client', 'lead', 'created_by'
    ).exclude(
        production_status='costed' 
    ).order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'urgent':
        quotes = quotes.filter(production_status='pending', status='Draft')
    elif status_filter == 'active':
        quotes = quotes.filter(production_status='in_progress')
    elif status_filter == 'completed':
        quotes = quotes.filter(production_status='completed')
    
    search_query = request.GET.get('search', '').strip()
    if search_query:
        quotes = quotes.filter(
            Q(quote_id__icontains=search_query) |
            Q(client__name__icontains=search_query) |
            Q(lead__name__icontains=search_query) |
            Q(product_name__icontains=search_query)
        )
    
    # Calculate snapshot counts 
    active_quotes_count = Quote.objects.filter(
        production_status__in=['pending', 'in_progress']
    ).values('quote_id').distinct().count()
    
    in_costing_count = Quote.objects.filter(
        production_status='in_progress'
    ).values('quote_id').distinct().count()
    
    awaiting_delivery_count = Quote.objects.filter(
        status='Approved',
        production_status='completed'
    ).values('quote_id').distinct().count()
    
    completed_today_count = Quote.objects.filter(
        production_status='completed',
        updated_at__date=timezone.now().date()
    ).values('quote_id').distinct().count()
    
    # Group quotes by quote_id 
    quotes_dict = {}
    for quote in quotes:
        if quote.quote_id not in quotes_dict:
            # Determine client name
            client_name = '-'
            if quote.client:
                client_name = quote.client.name
            elif quote.lead:
                client_name = quote.lead.name
            
            # Calculate days remaining
            days_remaining = (quote.valid_until - timezone.now().date()).days
            
            quotes_dict[quote.quote_id] = {
                'id': quote.id,
                'quote_id': quote.quote_id,
                'client_name': client_name,
                'account_manager': quote.created_by.get_full_name() if quote.created_by else '-',
                'total_amount': quote.total_amount,
                'status': quote.production_status,
                'status_display': quote.get_production_status_display(),
                'created_date': quote.created_at,
                'days_remaining': days_remaining,
                'line_items': [],
            }
        
        quotes_dict[quote.quote_id]['line_items'].append({
            'product_name': quote.product_name,
            'quantity': quote.quantity,
            'status': quote.production_status,
        })
    
    quotes_list = list(quotes_dict.values())
    
    context = {
        'current_view': 'my_quotes',
        'quotes': quotes_list,
        'active_quotes_count': active_quotes_count,
        'in_costing_count': in_costing_count,
        'awaiting_delivery_count': awaiting_delivery_count,
        'completed_today_count': completed_today_count,
        'status_filter': status_filter,
        'search_query': search_query,
        'clients': Client.objects.filter(status='Active').order_by('name'),
    }
    
    return render(request, 'my_quotes.html', context)

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Job, Vendor, VendorQuote, QCInspection
import json

@login_required
def vendor_comparison(request, job_id):
    """
    Vendor comparison page for selecting vendors.
    
    Displays all vendor quotes for a specific job with filtering options
    based on VPS score and lead time. Shows vendor details including:
    - Lead time and cost
    - VPS score and rating
    - Specialties
    - Any notices or special conditions
    """
    job = get_object_or_404(Job, id=job_id)
    
    # Get all vendor quotes for this job
    vendor_quotes = VendorQuote.objects.filter(job=job).select_related('vendor')
    
    # Search filter
    search_query = request.GET.get('search', '').strip()
    if search_query:
        vendor_quotes = vendor_quotes.filter(
            Q(vendor__name__icontains=search_query) |
            Q(vendor__specialties__name__icontains=search_query)
        ).distinct()
    
    # Filter vendors based on VPS score grade
    vps_filter = request.GET.get('vps_score', 'all')
    if vps_filter == 'A':
        vendor_quotes = vendor_quotes.filter(vendor__vps_score_value__gte=90)
    elif vps_filter == 'B':
        vendor_quotes = vendor_quotes.filter(vendor__vps_score_value__gte=75, vendor__vps_score_value__lt=90)
    elif vps_filter == 'C':
        vendor_quotes = vendor_quotes.filter(vendor__vps_score_value__gte=60, vendor__vps_score_value__lt=75)
    
    # Filter by lead time if specified
    lead_time_filter = request.GET.get('lead_time', 'all')
    if lead_time_filter != 'all':
        try:
            lead_time = int(lead_time_filter)
            if lead_time == 5: 
                vendor_quotes = vendor_quotes.filter(lead_time__gte=5)
            else:
                vendor_quotes = vendor_quotes.filter(lead_time=lead_time)
        except ValueError:
            pass
    
    context = {
        'job': job,
        'vendor_quotes': vendor_quotes,
        'total_vendors': VendorQuote.objects.filter(job=job).count(),
        'vps_filter': vps_filter,
        'lead_time_filter': lead_time_filter,
        'search_query': search_query,
    }
    
    return render(request, 'procurement/vendor_comparison.html', context)

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import base64

# QC Inspection View 
@login_required
@group_required('Production Team')
def qc_inspection(request, inspection_id):
    """
    Quality control inspection page - FULLY FUNCTIONAL
    """
    inspection = get_object_or_404(
        QCInspection.objects.select_related('job', 'vendor', 'job__client', 'inspector'),
        id=inspection_id
    )
    
    job = inspection.job
    vendor = inspection.vendor
    
    # Get vendor's recent QC history
    vendor_history = QCInspection.objects.filter(
        vendor=vendor,
        status='passed'
    ).exclude(
        id=inspection.id
        ).order_by('-created_at')[:3]
    
    # Calculate vendor's average QC score
       
    if vendor:
        total_inspections = QCInspection.objects.filter(vendor=vendor).count()
        passed_inspections = QCInspection.objects.filter(vendor=vendor, status='passed').count()
        vendor_pass_rate = (passed_inspections / total_inspections * 100) if total_inspections > 0 else 0
    else:
        vendor_pass_rate = 0
    
    # Calculate sampling requirement
    quantity = job.quantity
    if quantity < 100:
        sample_percentage = 20
    elif quantity < 1000:
        sample_percentage = 10
    elif quantity < 5000:
        sample_percentage = 10
    else:
        sample_percentage = 5
    
    required_sample = max(int(quantity * sample_percentage / 100), 1)
    
    context = {
        'current_view': 'qc_inspection',
        'inspection': inspection,
        'job': job,
        'vendor': vendor,
        'vendor_history': vendor_history,
        'vendor_pass_rate': round(vendor_pass_rate),
        'required_sample': required_sample,
        'sample_percentage': sample_percentage,
    }
    
    return render(request, 'quality_control.html', context)


@login_required
@group_required('Production Team')
@require_POST
def submit_qc(request):
    """
    AJAX endpoint to submit QC inspection results
    """
    try:
        data = json.loads(request.body)
        inspection_id = data.get('inspection_id')
        
        if not inspection_id:
            return JsonResponse({
                'success': False,
                'message': 'Inspection ID is required'
            }, status=400)
        
        inspection = get_object_or_404(QCInspection, id=inspection_id)
        
        # Update inspection ratings
        inspection.print_quality_score = data.get('print_quality')
        inspection.color_accuracy_score = data.get('color_accuracy')
        inspection.material_quality_score = data.get('material_quality')
        inspection.finishing_quality_score = data.get('finishing_quality')
        inspection.overall_quality_score = data.get('overall_quality')
        
        # Update notes
        inspection.print_quality_notes = data.get('print_quality_notes', '')
        inspection.color_accuracy_notes = data.get('color_accuracy_notes', '')
        inspection.material_quality_notes = data.get('material_quality_notes', '')
        inspection.finishing_quality_notes = data.get('finishing_quality_notes', '')
        inspection.overall_quality_notes = data.get('overall_quality_notes', '')
        
        inspection.delivery_notes = data.get('delivery_notes', '')
        inspection.notes_to_am = data.get('notes_to_am', '')
        
        # Delivery preparation data
        inspection.shelf_location = data.get('shelf_location', '')
        inspection.box_count = data.get('box_count', 1)
        
        # Packaging verification
        inspection.packaging_verified = {
            'all_items_packed': data.get('pack1', False),
            'job_id_label': data.get('pack2', False),
            'quantity_marked': data.get('pack3', False),
            'fragile_stickers': data.get('pack4', False),
        }
        
        # Set decision and status
        decision = data.get('decision')
        inspection.decision = decision
        inspection.status = 'completed'
        inspection.inspector = request.user
        inspection.completed_date = timezone.now()
        
        inspection.save()
        
        # Update vendor VPS 
        vendor = inspection.vendor
        if decision == 'pass':
            vendor.vps_score_value += 1.0
            messages.success(request, f' QC passed! Vendor VPS +1.0')
        elif decision == 'fail':
            vendor.vps_score_value -= 2.0
            messages.warning(request, f' QC failed. Vendor VPS -2.0')
        
        # Recalculate VPS letter grade — now derived automatically from vps_score_value
        vendor.save()
        
        # Update job status
        job = inspection.job
        if decision == 'pass':
            job.status = 'completed'
            job.actual_completion = timezone.now().date()
        elif decision == 'conditions':
            job.status = 'completed' 
        else:  
            job.status = 'on_hold'
        
        job.save()
        
        # Create notification for AM
        if job.client and job.client.account_manager:
            notification_title = {
                'pass': f' Job {job.job_number} - QC Passed',
                'conditions': f' Job {job.job_number} - QC Passed with Conditions',
                'fail': f' Job {job.job_number} - QC Failed'
            }
            
            notification_message = {
                'pass': f'Quality inspection passed ({inspection.overall_score_percentage:.0f}%). Ready for delivery.',
                'conditions': f'Quality inspection passed with conditions. Review notes before delivery.',
                'fail': f'Quality inspection failed. Vendor must rework. Check inspection notes.'
            }
            
            Notification.objects.create(
                recipient=job.client.account_manager,
                notification_type='job_completed' if decision != 'fail' else 'general',
                title=notification_title[decision],
                message=notification_message[decision],
                link=reverse('job_detail', kwargs={'pk': job.pk}),
                related_job=job,
                action_url=reverse('delivery_handoff', kwargs={'job_id': job.id}) if decision == 'pass' else None,
                action_label='Prepare Delivery' if decision == 'pass' else None
            )
        
        # Create activity log
        if job.client:
            ActivityLog.objects.create(
                client=job.client,
                activity_type='Order',
                title=f'QC Inspection Completed - {job.job_number}',
                description=f'QC Decision: {decision.upper()}. Score: {inspection.overall_score_percentage:.0f}%',
                created_by=request.user
            )
        
        logger.info(f'QC inspection {inspection.reference_number} completed by {request.user.username}')
        
        return JsonResponse({
            'success': True,
            'message': 'QC inspection submitted successfully',
            'decision': decision,
            'score': inspection.overall_score_percentage
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'Error submitting QC: {str(e)}')
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# Delivery
@login_required
@group_required('Production Team')
def delivery_handoff(request, job_id):
    """
    Delivery handoff page - FULLY FUNCTIONAL
    """
    job = get_object_or_404(Job.objects.select_related('client', 'quote'), id=job_id)
    
    # Get QC inspection if exists
    qc_inspection = QCInspection.objects.filter(job=job).order_by('-created_at').first()
    
    # Check if delivery already exists
    delivery = Delivery.objects.filter(job=job).first()
    
    # Calculate costs
    locked_evp = job.quote.production_cost if job.quote else Decimal('0')
    actual_cost = locked_evp  
    
    # Add VAT
    locked_evp_with_vat = locked_evp * Decimal('1.16')
    actual_cost_with_vat = actual_cost * Decimal('1.16')
    
    context = {
        'current_view': 'delivery',
        'job': job,
        'qc_inspection': qc_inspection,
        'delivery': delivery,
        'locked_evp': locked_evp_with_vat,
        'actual_cost': actual_cost_with_vat,
        'variance': actual_cost_with_vat - locked_evp_with_vat,
        'variance_percentage': ((actual_cost_with_vat - locked_evp_with_vat) / locked_evp_with_vat * 100) if locked_evp_with_vat > 0 else 0,
    }
    
    return render(request, 'delivery.html', context)


@login_required
@group_required('Production Team')
@require_POST
def submit_delivery_handoff(request):
    """
    AJAX endpoint to complete delivery handoff - FULLY FUNCTIONAL
    """
    try:
        data = json.loads(request.body)
        job_id = data.get('job_id')
        
        if not job_id:
            return JsonResponse({
                'success': False,
                'message': 'Job ID is required'
            }, status=400)
        
        job = get_object_or_404(Job, id=job_id)
        
        # Get or create delivery
        delivery, created = Delivery.objects.get_or_create(
            job=job,
            defaults={
                'created_by': request.user
            }
        )
        
        # Update delivery details
        delivery.staging_location = data.get('staging_location', 'shelf-b')
        delivery.notes_to_am = data.get('notes_to_am', '')
        
        # Packaging verification
        delivery.packaging_verified = {
            'boxes_sealed': data.get('boxes_sealed', False),
            'job_labels': data.get('job_labels', False),
            'quantity_marked': data.get('quantity_marked', False),
            'total_quantity': data.get('total_quantity', False),
            'fragile_stickers': data.get('fragile_stickers', False),
        }
        
        # Costs
        delivery.locked_evp = Decimal(str(data.get('locked_evp', 0)))
        delivery.actual_cost = Decimal(str(data.get('actual_cost', 0)))
        
        # Handoff confirmation
        delivery.handoff_confirmed = True
        delivery.handoff_confirmed_at = timezone.now()
        delivery.handoff_confirmed_by = request.user
        
        # Notification settings
        delivery.notify_am = data.get('notify_am', True)
        delivery.notify_via_email = data.get('notify_via_email', True)
        delivery.mark_urgent = data.get('mark_urgent', False)
        
        # Status
        delivery.status = 'staged'
        
        delivery.save()
        
        # Update job status
        job.status = 'completed'
        job.actual_completion = timezone.now().date()
        job.save()
        
        # Notify Account Manager
        if job.client and job.client.account_manager and delivery.notify_am:
            Notification.objects.create(
                recipient=job.client.account_manager,
                notification_type='delivery_ready',
                title=f' Job {job.job_number} Ready for Delivery',
                message=f'Staged at {delivery.get_staging_location_display()}. {delivery.notes_to_am[:100]}',
                link=reverse('job_detail', kwargs={'pk': job.pk}),
                related_job=job,
                action_url=reverse('job_detail', kwargs={'pk': job.pk}),
                action_label='View Job Details'
            )
            
            # Send email if requested
            if delivery.notify_via_email:
                try:
                    from django.core.mail import send_mail
                    send_mail(
                        subject=f'Job {job.job_number} Ready for Delivery',
                        message=f'Job {job.job_number} has been completed and is ready for delivery.\n\nLocation: {delivery.get_staging_location_display()}\n\nNotes: {delivery.notes_to_am}',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[job.client.account_manager.email],
                        fail_silently=True
                    )
                except Exception as e:
                    logger.warning(f'Failed to send delivery email: {str(e)}')
        
        # Create activity log
        if job.client:
            ActivityLog.objects.create(
                client=job.client,
                activity_type='Order',
                title=f'Delivery Handoff Complete - {job.job_number}',
                description=f'Job handed off to AM. Staged at {delivery.get_staging_location_display()}',
                created_by=request.user
            )
        
        logger.info(f'Delivery for {job.job_number} handed off by {request.user.username}')
        
        return JsonResponse({
            'success': True,
            'message': 'Delivery handoff completed successfully',
            'delivery_id': delivery.id,
            'job_number': job.job_number
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f'Error submitting delivery handoff: {str(e)}')
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# Delivery List View
@login_required
def delivery_list(request):
    """Display list of all deliveries"""
    
    # Check user permissions
    is_production = request.user.groups.filter(name='Production Team').exists()
    is_am = request.user.groups.filter(name='Account Manager').exists()
    
    if is_production:
        # PT sees all deliveries
        deliveries = Delivery.objects.all()
    elif is_am:
        # AM sees only their client deliveries
        deliveries = Delivery.objects.filter(job__client__account_manager=request.user)
    else:
        deliveries = Delivery.objects.none()
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        deliveries = deliveries.filter(status=status_filter)
    
    # Search
    search_query = request.GET.get('search', '').strip()
    if search_query:
        deliveries = deliveries.filter(
            Q(delivery_number__icontains=search_query) |
            Q(job__job_number__icontains=search_query) |
            Q(job__client__name__icontains=search_query)
        )
    
    deliveries = deliveries.select_related('job', 'job__client', 'qc_inspection').order_by('-created_at')
    
    context = {
        'current_view': 'deliveries',
        'deliveries': deliveries,
        'status_filter': status_filter,
        'search_query': search_query,
    }
    
    return render(request, 'delivery_list.html', context)


@login_required
@require_POST
def select_vendor(request):
    """
    AJAX endpoint to select a vendor and continue to PO creation.
    
    Updates the vendor quote as selected and sets the job's vendor.
    Returns success status and redirect URL.
    """
    try:
        data = json.loads(request.body)
        vendor_quote_id = data.get('vendor_quote_id')
        
        if not vendor_quote_id:
            return JsonResponse({
                'success': False,
                'message': 'Vendor quote ID is required'
            }, status=400)
        
        vendor_quote = get_object_or_404(VendorQuote, id=vendor_quote_id)
        
        
        vendor_quote.selected = True
        vendor_quote.save()
        
        # Unselect other quotes for this job
        VendorQuote.objects.filter(
            job=vendor_quote.job
        ).exclude(
            id=vendor_quote_id
        ).update(selected=False)
        
        # Update job status and selected vendor
        job = vendor_quote.job
        job.status = 'vendor_selected'
        job.selected_vendor = vendor_quote.vendor
        job.selected_vendor_quote = vendor_quote
        job.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Vendor selected successfully',
            'redirect_url': f'/procurement/purchase-order/{job.id}/'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def quality_control_list(request):
    """List of QC Inspections"""
    inspections = QCInspection.objects.all().order_by('-created_at')
    return render(request, 'quality_control.html', {'inspections': inspections})

@login_required
def vendor_profile(request, vendor_id):
    """Detailed vendor profile page showing all vendor information."""
    vendor = get_object_or_404(Vendor, id=vendor_id)
    
    # Get vendor's jobs
    vendor_quotes = VendorQuote.objects.filter(vendor=vendor).select_related('job')
    job_stages = vendor.job_stages.all().select_related('job')
    
    # Statistics
    total_jobs = vendor_quotes.count()
    completed_jobs = vendor_quotes.filter(job__status='Completed').count()
    
    context = {
        'vendor': vendor,
        'vendor_quotes': vendor_quotes,
        'job_stages': job_stages,
        'total_jobs': total_jobs,
        'completed_jobs': completed_jobs,
        'current_view': 'vendor_profile',
    }
    
    return render(request, 'vendor_profile.html', context)

@login_required
def vendor_list(request):
    """Vendor management page - list all vendors and their process links."""
    from clientapp.models import Process
    
    vendors = Vendor.objects.all().order_by('-vps_score_value', 'name')
    
    # Get all active processes for the services section
    processes = Process.objects.filter(status='active').order_by('process_name')
    
    process_links = (
        ProcessVendor.objects.select_related('process')
        .values(
            'vendor_name',
            'vendor_id',
            'process__process_id',
            'process__process_name',
            'minimum_order',
            'standard_lead_time',
            'rush_lead_time',
        )
        .order_by('vendor_name', 'process__process_name')
    )
    
    context = {
        'current_view': 'vendor_list',
        'vendors': vendors,
        'processes': processes,
        'process_links': process_links,
    }
    return render(request, 'vendors_list.html', context)


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from .models import Process, ProcessTier, ProcessVariable, ProcessVendor, Vendor, VendorTierPricing


@login_required
def process_list(request):
    """Display list of all processes with filtering"""
    processes = Process.objects.all()  
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        processes = processes.filter(
            Q(process_name__icontains=search_query) |  
            Q(process_id__icontains=search_query)
        )
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        processes = processes.filter(category=category)
    
    # Filter by pricing type
    pricing_type = request.GET.get('pricing_type')
    if pricing_type:
        processes = processes.filter(pricing_type=pricing_type)  
    
    # Count by type
    total_processes = processes.count()
    tier_based_count = processes.filter(pricing_type='tier').count()
    formula_based_count = processes.filter(pricing_type='formula').count()
    outsourced_count = processes.filter(category='outsourced').count()
    in_house_count = processes.filter(category='in_house').count()
    
    context = {
        'processes': processes,
        'search_query': search_query,
        'total_processes': total_processes,
        'tier_based_count': tier_based_count,
        'formula_based_count': formula_based_count,
        'outsourced_count': outsourced_count,
        'in_house_count': in_house_count,
    }
    
    return render(request, 'process_list.html', context)


@login_required
def process_detail(request, process_id):
    """Display read-only process details with all variables/tiers"""
    process = get_object_or_404(Process, process_id=process_id)
    
    context = {
        'process': process,
        'tiers': process.tiers.all() if process.pricing_type == 'tier' else [],
        'variables': process.variables.all() if process.pricing_type == 'formula' else [],
        'process_vendors': process.process_vendors.all(),
    }
    return render(request, 'process_detail.html', context)


@login_required
def process_create(request):
    """
    Screen 2: Process Editor - Create new process
    Handles both GET (show form) and POST (save data)
    """
    if request.method == 'POST':
        return handle_process_save(request, process=None)

    vendors = Vendor.objects.filter(active=True).order_by('name')
    
    # Empty form
    context = {
        'mode': 'create',
        'process': None,
        'vendors': vendors
    }
    return render(request, 'process_create.html', context)


@login_required
def process_edit(request, process_id):
    """Edit existing process"""
    process = get_object_or_404(Process, process_id=process_id)
    
    if request.method == 'POST':
        return handle_process_save(request, process=process)
    
    # Show form with existing data
    available_vendors = Vendor.objects.filter(active=True).order_by('name')
    context = {
        'mode': 'edit',
        'process': process,
        'tiers': list(process.tiers.all().values()),
        'variables': list(process.variables.all().values()),
        # Choices for the vendor dropdowns
        'vendors': available_vendors,
        # Existing vendor links for this process
        'process_vendors': process.process_vendors.all(),
    }
    return render(request, 'process_create.html', context)


@transaction.atomic

def handle_process_save(request, process=None):
    """
    Handle POST data for creating/updating a process
    This is the core function that processes the form submission
    """
    import logging
    from decimal import Decimal
    
    logger = logging.getLogger(__name__)
    
    data = request.POST
    action = data.get('action', 'draft')  

    # Create or update main process
    if process is None:
        process = Process()
        process.created_by = request.user

    # Update basic fields
    process.process_name = data.get('process_name')
    process.description = data.get('description', '')
    process.category = data.get('category')
    process.standard_lead_time = int(data.get('standard_lead_time', 5))

    # Pricing method
    pricing_method = data.get('pricing_method', 'tier')

    if pricing_method == 'formula':
        process.pricing_type = 'formula'
        process.unit_of_measure = None
    else:
        process.pricing_type = 'tier'
        process.unit_of_measure = data.get('unit_of_measure', 'per_piece')

    # Approval settings
    process.approval_type = data.get('approval_settings', 'auto_approve')

    # Status
    process.status = 'active' if action == 'activate' else 'draft'

    process.save()

    # ===== SAVE TIER-BASED PRICING =====
    if process.pricing_type == 'tier':
        process.tiers.all().delete()

        tier_num = 1
        while f'tier{tier_num}_from' in data:
            ProcessTier.objects.create(
                process=process,
                tier_number=tier_num,
                quantity_from=int(data.get(f'tier{tier_num}_from', 0)),
                quantity_to=int(data.get(f'tier{tier_num}_to', 0)),
                price=float(data.get(f'tier{tier_num}_price', 0)),
                cost=float(data.get(f'tier{tier_num}_cost', 0)),
            )
            tier_num += 1

    # ===== SAVE FORMULA-BASED PRICING =====
    if process.pricing_type == 'formula':
        process.variables.all().delete()

        base_cost = data.get('base_cost', 0)
        if base_cost:
            process.base_cost = Decimal(str(base_cost))
        process.save()

        var_num = 1
        while f'variable{var_num}_name' in data:
            var_name = data.get(f'variable{var_num}_name', '').strip()

            if var_name:
                var_type = data.get(f'variable{var_num}_type', 'number') 
                var_unit = data.get(f'variable{var_num}_unit', '').strip()
                var_price = data.get(f'variable{var_num}_price', 0)
                var_rate = data.get(f'variable{var_num}_rate', 1.0)
                
                # Only get value for number type
                var_value = None
                if var_type == 'number':
                    var_value = data.get(f'variable{var_num}_value', 0)

                try:
                    ProcessVariable.objects.create(
                        process=process,
                        variable_name=var_name,
                        variable_type=var_type,  # NEW
                        unit=var_unit,
                        variable_value=Decimal(str(var_value)) if var_value else None,
                        price=Decimal(str(var_price)),
                        rate=Decimal(str(var_rate)),
                        order=var_num - 1
                    )
                except (ValueError, TypeError, decimal.InvalidOperation) as e:
                    logger.warning(f"Error saving variable {var_name}: {e}")

            var_num += 1

    #Save Vendors
    process.process_vendors.all().delete()

    # Vendor 1 
    vendor_pk = data.get('vendor1_id')
    if vendor_pk:
        try:
            vendor_obj = Vendor.objects.get(pk=vendor_pk)

            formula_rates = None
            if process.pricing_type == 'formula':
                formula_rates = {
                    'base_rate': float(data.get('vendor1_base_rate', 0) or 0),
                    'rate_per_unit': float(data.get('vendor1_rate_per_unit', 0) or 0),
                    'setup_fee': float(data.get('vendor1_setup_fee', 0) or 0),
                }

            ProcessVendor.objects.create(
                process=process,
                vendor_name=vendor_obj.name,
                vendor_id=data.get(
                    'vendor1_vendor_id',
                    f"VND-{str(vendor_obj.id).zfill(3)}"
                ),
                vps_score=vendor_obj.vps_score_value,
                priority='preferred',
                rush_enabled=data.get('vendor1_rush_enabled') == 'on',
                rush_fee_percentage=float(data.get('vendor1_rush_fee', 0) or 0),
                rush_threshold_days=int(data.get('vendor1_rush_threshold', 3) or 3),
                minimum_order=float(data.get('vendor1_min_order', 0) or 0),
                standard_lead_time=int(data.get('vendor1_standard_days', 5) or 5),
                rush_lead_time=int(data.get('vendor1_rush_days', 2) or 2),
                notes=data.get('vendor1_notes', ''),
                formula_rates=formula_rates,
            )
        except Vendor.DoesNotExist:
            pass

    # Vendor 2 
    vendor2_pk = data.get('vendor2_id')
    if vendor2_pk:
        try:
            vendor2_obj = Vendor.objects.get(pk=vendor2_pk)

            ProcessVendor.objects.create(
                process=process,
                vendor_name=vendor2_obj.name,
                vendor_id=data.get(
                    'vendor2_vendor_id',
                    f"VND-{str(vendor2_obj.id).zfill(3)}"
                ),
                vps_score=vendor2_obj.vps_score_value,
                priority='alternative',
                rush_enabled=data.get('vendor2_rush_enabled') == 'on',
                rush_fee_percentage=float(data.get('vendor2_rush_fee', 0) or 0),
                rush_threshold_days=int(data.get('vendor2_rush_threshold', 3) or 3),
                minimum_order=float(data.get('vendor2_min_order', 0) or 0),
                standard_lead_time=int(data.get('vendor2_standard_days', 5) or 5),
                rush_lead_time=int(data.get('vendor2_rush_days', 2) or 2),
                notes=data.get('vendor2_notes', ''),
                base_rate=float(data.get('vendor2_base_rate', 0) or 0),
                rate_per_unit=float(data.get('vendor2_rate_per_unit', 0) or 0),
                setup_fee=float(data.get('vendor2_setup_fee', 0) or 0),
            )
        except Vendor.DoesNotExist:
            pass

    # Vendor 3
    vendor3_pk = data.get('vendor3_id')
    if vendor3_pk:
        try:
            vendor3_obj = Vendor.objects.get(pk=vendor3_pk)

            ProcessVendor.objects.create(
                process=process,
                vendor_name=vendor3_obj.name,
                vendor_id=data.get(
                    'vendor3_vendor_id',
                    f"VND-{str(vendor3_obj.id).zfill(3)}"
                ),
                vps_score=vendor3_obj.vps_score_value,
                priority='backup',
                rush_enabled=data.get('vendor3_rush_enabled') == 'on',
                rush_fee_percentage=float(data.get('vendor3_rush_fee', 0) or 0),
                rush_threshold_days=int(data.get('vendor3_rush_threshold', 3) or 3),
                minimum_order=float(data.get('vendor3_min_order', 0) or 0),
                standard_lead_time=int(data.get('vendor3_standard_days', 5) or 5),
                rush_lead_time=int(data.get('vendor3_rush_days', 2) or 2),
                notes=data.get('vendor3_notes', ''),
                base_rate=float(data.get('vendor3_base_rate', 0) or 0),
                rate_per_unit=float(data.get('vendor3_rate_per_unit', 0) or 0),
                setup_fee=float(data.get('vendor3_setup_fee', 0) or 0),
            )
        except Vendor.DoesNotExist:
            pass

    #  SUCCESS MESSAGE
    if action == 'activate':
        messages.success(
            request,
            f'Process "{process.process_name}" has been activated!'
        )
    else:
        messages.success(
            request,
            f'Process "{process.process_name}" saved as draft.'
        )

    return redirect('process_list')


# AJAX ENDPOINTS

@login_required
def ajax_generate_process_id(request):
    """Auto-generate Process ID from name (called via AJAX)"""
    name = request.GET.get('name', '')
    if name:
        temp_process = Process(process_name=name)
        process_id = temp_process.generate_process_id()
        return JsonResponse({'process_id': process_id})
    return JsonResponse({'process_id': ''})


@login_required
def ajax_calculate_margin(request):
    """Calculate margin from price and cost (called via AJAX)"""
    try:
        price = float(request.GET.get('price', 0))
        cost = float(request.GET.get('cost', 0))
        
        if price > 0:
            margin_amount = price - cost
            margin_percentage = (margin_amount / price) * 100
            
            # Determine status
            if margin_percentage >= 25:
                status = 'above'
                color = 'green'
                message = 'Above target (25%)'
            elif margin_percentage >= 15:
                status = 'on_target'
                color = 'yellow'
                message = 'On target'
            else:
                status = 'below'
                color = 'red'
                message = 'Below target'
            
            return JsonResponse({
                'margin_amount': round(margin_amount, 2),
                'margin_percentage': round(margin_percentage, 2),
                'status': status,
                'color': color,
                'message': message,
            })
    except Exception as e:
        return JsonResponse({'error': str(e)})
    
    return JsonResponse({'error': 'Invalid data'})

@login_required
@require_POST
def ajax_create_vendor_comprehensive(request):
    """Create or update a Vendor with all fields and return it for dropdowns."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        # Get required fields
        name = (payload.get('name') or '').strip()
        email = (payload.get('email') or '').strip()
        phone = (payload.get('phone') or '').strip()
        
        if not name:
            return JsonResponse({
                'success': False, 
                'message': 'Vendor name is required.'
            }, status=400)
        
        if not email:
            return JsonResponse({
                'success': False, 
                'message': 'Email is required.'
            }, status=400)
        
        if not phone:
            return JsonResponse({
                'success': False, 
                'message': 'Phone is required.'
            }, status=400)
        
        # Check if editing existing vendor
        vendor_id = payload.get('vendor_id')
        is_editing = vendor_id and str(vendor_id).strip()
        
        # Get all vendor fields from payload
        contact_person = (payload.get('contact_person') or '').strip()
        business_address = (payload.get('business_address') or payload.get('address') or '').strip()
        tax_pin = (payload.get('tax_pin') or '').strip()
        payment_terms = payload.get('payment_terms', '')
        payment_method = payload.get('payment_method', '')
        services = payload.get('services', '')  
        specialization = (payload.get('specialization') or '').strip()
        minimum_order = float(payload.get('minimum_order', 0) or 0)
        lead_time = (payload.get('lead_time') or '').strip()
        rush_capable = payload.get('rush_capable', False)
        quality_rating = payload.get('quality_rating', '')
        reliability_rating = payload.get('reliability_rating', '')
        vps_score_value = float(payload.get('vps_score_value', 5.0))
        rating = float(payload.get('rating', 4.0))
        recommended = payload.get('recommended', False)
        
        if is_editing:
            # Update existing vendor
            try:
                vendor = Vendor.objects.get(id=vendor_id)
                vendor.name = name
                vendor.contact_person = contact_person
                vendor.email = email
                vendor.phone = phone
                vendor.business_address = business_address
                vendor.tax_pin = tax_pin
                vendor.payment_terms = payment_terms
                vendor.payment_method = payment_method
                vendor.services = services
                vendor.specialization = specialization
                vendor.minimum_order = minimum_order
                vendor.lead_time = lead_time
                vendor.rush_capable = rush_capable
                vendor.quality_rating = quality_rating
                vendor.reliability_rating = reliability_rating
                vendor.vps_score_value = vps_score_value
                vendor.rating = rating
                vendor.recommended = recommended
                vendor.save()
                
                return JsonResponse({
                    'success': True,
                    'id': vendor.id,
                    'name': vendor.name,
                    'vps_score_value': str(vendor.vps_score_value),
                    'rating': str(vendor.rating),
                    'message': f'Vendor "{vendor.name}" updated successfully!'
                })
            except Vendor.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Vendor not found.'
                }, status=404)
        else:
            # Create new vendor
            vendor = Vendor.objects.create(
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                business_address=business_address,
                tax_pin=tax_pin,
                payment_terms=payment_terms,
                payment_method=payment_method,
                services=services,
                specialization=specialization,
                minimum_order=minimum_order,
                lead_time=lead_time,
                rush_capable=rush_capable,
                quality_rating=quality_rating,
                reliability_rating=reliability_rating,
                vps_score_value=vps_score_value,
                rating=rating,
                recommended=recommended,
                active=True,
            )
            
            return JsonResponse({
                'success': True,
                'id': vendor.id,
                'name': vendor.name,
                'vps_score_value': str(vendor.vps_score_value),
                'rating': str(vendor.rating),
                'message': f'Vendor "{vendor.name}" created successfully!'
            })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in ajax_create_vendor: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Invalid JSON data: ' + str(e)
        }, status=400)
    except ValueError as e:
        logger.error(f"Value error in ajax_create_vendor: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Invalid number format: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Unexpected error in ajax_create_vendor: {error_msg}\n{error_traceback}")
        print(f"ERROR in ajax_create_vendor: {error_msg}")
        print(f"Traceback:\n{error_traceback}")
        return JsonResponse({
            'success': False, 
            'message': f'Error creating vendor: {error_msg}'
        }, status=500)

def delivery_list(request):
    """Display list of all deliveries"""

    return render(request, 'delivery.html')


@login_required
@group_required('Account Manager')
def get_product_price(request, product_id):
    """API endpoint to get product price using centralized pricing resolver"""
    from clientapp.models import resolve_unit_price
    from decimal import Decimal
    
    try:
        product = Product.objects.get(id=product_id)
        
        # Use centralized pricing resolver (this already handles fallback to ProductPricing)
        unit_price = resolve_unit_price(product)
        
        # Get base_price for display (use resolved price if base_price is not set)
        base_price = product.base_price
        if (base_price is None or base_price == 0) and hasattr(product, 'pricing'):
            # If base_price not set, calculate from ProductPricing.base_cost with margin
            if product.pricing.base_cost:
                cost = product.pricing.base_cost
                margin = product.pricing.return_margin if hasattr(product.pricing, 'return_margin') else Decimal('30')
                base_price = cost * (Decimal('1') + (margin / Decimal('100')))
        
        return JsonResponse({
            'success': True,
            'id': product.id,
            'name': product.name,
            'internal_code': product.internal_code,
            'customization_level': product.customization_level,
            'base_price': float(base_price) if base_price else None,
            'unit_price': float(unit_price) if unit_price else 0,
            'has_costing_process': product.has_costing_process(),
            'is_published': product.status == 'published' and product.is_visible
        })
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
def api_product_catalog(request):
    """Product catalog API endpoint - returns pricing metadata for product selection in forms"""
    from clientapp.models import resolve_unit_price
    
    try:
        # Return all active products
        products = Product.objects.filter(
            status__in=['draft', 'published']  # exclude archived
        ).select_related('pricing').order_by('name')
        
        # Apply search filter 
        search = request.GET.get('search', '').strip()
        if search:
            products = products.filter(
                Q(name__icontains=search) | 
                Q(internal_code__icontains=search)
            )
        
        # Build response with pricing metadata
        results = []
        for product in products:
            unit_price = resolve_unit_price(product)
            results.append({
                'id': product.id,
                'name': product.name,
                'internal_code': product.internal_code,
                'customization_level': product.customization_level,
                'base_price': float(product.base_price) if product.base_price else None,
                'unit_price': float(unit_price),
                'has_costing_process': product.has_costing_process(),
            })
        
        return JsonResponse({
            'success': True,
            'count': len(results),
            'products': results
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@require_POST
def ajax_create_vendor(request):
    """Create or update a Vendor with full field support - handles both Process editor and Vendor portal."""
    try:
        payload = json.loads(request.body.decode('utf-8'))
        
        # Get required fields - these are mandatory
        name = (payload.get('name') or '').strip()
        email = (payload.get('email') or '').strip()
        phone = (payload.get('phone') or '').strip()
        
        if not name:
            return JsonResponse({
                'success': False, 
                'message': 'Vendor name is required.'
            }, status=400)

        if not email:
            return JsonResponse({
                'success': False, 
                'message': 'Email is required.'
            }, status=400)

        if not phone:
            return JsonResponse({
                'success': False, 
                'message': 'Phone is required.'
            }, status=400)
        
        # Check if editing existing vendor
        vendor_id = payload.get('vendor_id')
        is_editing = vendor_id and str(vendor_id).strip()
        
        # Get all vendor fields from payload with sensible defaults
        contact_person = (payload.get('contact_person') or '').strip()
        business_address = (payload.get('business_address') or payload.get('address') or '').strip()
        tax_pin = (payload.get('tax_pin') or '').strip()
        payment_terms = payload.get('payment_terms', '')
        payment_method = payload.get('payment_method', '')
        services = payload.get('services', '')  
        specialization = (payload.get('specialization') or '').strip()
        minimum_order = float(payload.get('minimum_order', 0) or 0)
        lead_time = (payload.get('lead_time') or '').strip()
        rush_capable = payload.get('rush_capable', False)
        quality_rating = payload.get('quality_rating', '')
        reliability_rating = payload.get('reliability_rating', '')
        vps_score_value = float(payload.get('vps_score_value', 5.0) or 5.0)
        rating = float(payload.get('rating', 4.0) or 4.0)
        recommended = payload.get('recommended', False)
        
        if is_editing:
            # Update existing vendor
            try:
                vendor = Vendor.objects.get(id=vendor_id)
                vendor.name = name
                vendor.contact_person = contact_person
                vendor.email = email
                vendor.phone = phone
                vendor.business_address = business_address
                vendor.tax_pin = tax_pin
                vendor.payment_terms = payment_terms
                vendor.payment_method = payment_method
                vendor.services = services
                vendor.specialization = specialization
                vendor.minimum_order = minimum_order
                vendor.lead_time = lead_time
                vendor.rush_capable = rush_capable
                vendor.quality_rating = quality_rating
                vendor.reliability_rating = reliability_rating
                vendor.vps_score_value = vps_score_value
                vendor.rating = rating
                vendor.recommended = recommended
                vendor.save()
                
                return JsonResponse({
                    'success': True,
                    'id': vendor.id,
                    'name': vendor.name,
                    'vps_score_value': str(vendor.vps_score_value),
                    'rating': str(vendor.rating),
                    'message': f'Vendor "{vendor.name}" updated successfully!'
                })
            except Vendor.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Vendor not found.'
                }, status=404)
        else:
            # Create new vendor
            vendor = Vendor.objects.create(
                name=name,
                contact_person=contact_person,
                email=email,
                phone=phone,
                business_address=business_address,
                tax_pin=tax_pin,
                payment_terms=payment_terms,
                payment_method=payment_method,
                services=services,
                specialization=specialization,
                minimum_order=minimum_order,
                lead_time=lead_time,
                rush_capable=rush_capable,
                quality_rating=quality_rating,
                reliability_rating=reliability_rating,
                vps_score_value=vps_score_value,
                rating=rating,
                recommended=recommended,
                active=True,
            )
            
            return JsonResponse({
                'success': True,
                'id': vendor.id,
                'name': vendor.name,
                'vps_score_value': str(vendor.vps_score_value),
                'rating': str(vendor.rating),
                'message': f'Vendor "{vendor.name}" created successfully!'
            })
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in ajax_create_vendor: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': 'Invalid JSON data: ' + str(e)
        }, status=400)
    except ValueError as e:
        logger.error(f"Value error in ajax_create_vendor: {str(e)}")
        return JsonResponse({
            'success': False, 
            'message': f'Invalid number format: {str(e)}'
        }, status=400)
    except Exception as e:
        import traceback
        error_msg = str(e)
        error_traceback = traceback.format_exc()
        logger.error(f"Unexpected error in ajax_create_vendor: {error_msg}\n{error_traceback}")
        print(f"ERROR in ajax_create_vendor: {error_msg}")
        print(f"Traceback:\n{error_traceback}")
        return JsonResponse({
            'success': False, 
            'message': f'Error creating vendor: {error_msg}'
        }, status=500)


# Process Helpers

def import_process_variables_to_product(process, product):
    """
    Import variables from a Process to a Product
    Returns the number of variables imported
    """
    imported_count = 0
    
    if process.pricing_type == 'formula':
        # For formula-based pricing, import formula variables
        process_variables = process.variables.all()
        
        for pv in process_variables:
            # Check if variable already exists
            existing = ProductVariable.objects.filter(
                product=product,
                name=pv.variable_name
            ).first()
            
            if not existing:
                # Create new product variable
                ProductVariable.objects.create(
                    product=product,
                    name=pv.variable_name,
                    variable_type='required',
                    pricing_type='increment',
                    source_process_variable=pv,
                    display_order=pv.order
                )
                imported_count += 1
                
    elif process.pricing_type == 'tier':
        # For tier-based pricing, import quantity as a variable
        quantity_var, created = ProductVariable.objects.get_or_create(
            product=product,
            name='Quantity',
            defaults={
                'variable_type': 'required',
                'pricing_type': 'fixed',
                'display_order': 0
            }
        )
        
        if created:
            # Create options from process tiers
            tiers = process.tiers.all().order_by('tier_number')
            for i, tier in enumerate(tiers):
                ProductVariableOption.objects.create(
                    variable=quantity_var,
                    name=f"{tier.quantity_from}-{tier.quantity_to} pieces",
                    display_order=i,
                    price_modifier=tier.price
                )
            imported_count += 1
    
    return imported_count


def ajax_process_variables(request, process_id):
    """
    AJAX endpoint to fetch process variables
    """
    try:
        process = Process.objects.get(id=process_id)
        
        variables_data = []
        
        if process.pricing_type == 'formula':
            for var in process.variables.all():
                variables_data.append({
                    'id': var.id,
                    'name': var.variable_name,
                    'type': var.variable_type,
                    'unit': var.unit,
                    'min_value': str(var.min_value) if var.min_value else None,
                    'max_value': str(var.max_value) if var.max_value else None,
                    'default_value': str(var.default_value) if var.default_value else None,
                    'description': var.description
                })
        elif process.pricing_type == 'tier':
            # Return tier information
            for tier in process.tiers.all():
                variables_data.append({
                    'tier_number': tier.tier_number,
                    'quantity_from': tier.quantity_from,
                    'quantity_to': tier.quantity_to,
                    'cost': str(tier.cost),
                    'price': str(tier.price)
                })
        
        return JsonResponse({
            'success': True,
            'pricing_type': process.pricing_type,
            'variables': variables_data
        })
        
    except Process.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Process not found'
        }, status=404)



from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum, Avg, Q
from datetime import datetime, timedelta
from decimal import Decimal

@staff_member_required
def admin_dashboard_index(request):
    """Main admin dashboard with real-time statistics"""
    today = timezone.now().date()
    this_month_start = today.replace(day=1)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    this_week_start = today - timedelta(days=today.weekday())
    
    # Calculate KPIs
    total_clients = Client.objects.filter(status='Active').count()
    quotes_this_month = Quote.objects.filter(created_at__gte=this_month_start).values('quote_id').distinct().count()
    jobs_in_production = Job.objects.filter(status__in=['pending', 'in_progress']).count()
    
    # Revenue this month
    monthly_revenue = Quote.objects.filter(
        status='Approved',
        approved_at__gte=this_month_start
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Pending approvals
    pending_approvals = Quote.objects.filter(
        production_status='pending'
    ).values('quote_id').distinct().count()
    
    # Overdue jobs
    overdue_jobs = Job.objects.filter(
        expected_completion__lt=today,
        status__in=['pending', 'in_progress']
    ).count()
    
    # Completed this week
    completed_this_week = Job.objects.filter(
        status='completed',
        actual_completion__gte=this_week_start
    ).count()
    
    # Pending payments
    pending_payments = LPO.objects.filter(
        status__in=['approved', 'in_production']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    
    # Vendor performance
    avg_vendor_score = Vendor.objects.filter(active=True).aggregate(
        avg=Avg('vps_score_value')
    )['avg'] or 0
    
    # Profit margin calculation
    approved_quotes = Quote.objects.filter(status='Approved', production_cost__isnull=False)
    total_revenue_for_margin = approved_quotes.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_cost_for_margin = approved_quotes.aggregate(Sum('production_cost'))['production_cost__sum'] or 0
    profit_margin = ((total_revenue_for_margin - total_cost_for_margin) / total_revenue_for_margin * 100) if total_revenue_for_margin > 0 else 0
    
    # Growth calculations (compare to last month)
    last_month_clients = Client.objects.filter(
        status='Active',
        created_at__gte=last_month_start,
        created_at__lt=this_month_start
    ).count()
    clients_growth = ((total_clients - last_month_clients) / last_month_clients * 100) if last_month_clients > 0 else 0
    
    # Recent alerts
    recent_alerts = SystemAlert.objects.filter(
        is_active=True,
        is_dismissed=False
    ).order_by('-created_at')[:5]
    
    # Recent activity
    recent_activity = ActivityLog.objects.select_related(
        'client', 'created_by'
    ).order_by('-created_at')[:10]

     # 1. Revenue Trend (Last 6 Months)
    revenue_trend_data = []
    revenue_labels = []
    for i in range(5, -1, -1):
        month_date = today.replace(day=1) - timedelta(days=i*30)
        # First Day of the month
        m_start = month_date.replace(day=1)
        # End of that month
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year+1, month=1, day=1) - timedelta(days=1)
        else:
            m_end = m_start.replace(month=m_start.month+1, day=1) - timedelta(days=1)
            
        rev = Quote.objects.filter(
            status='Approved',
            approved_at__gte=m_start,
            approved_at__lte=m_end
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        revenue_trend_data.append(float(rev))
        revenue_labels.append(m_start.strftime('%b'))

    # 2. Production by Category 
    job_types = Job.objects.values('job_type').annotate(count=Count('id')).order_by('-count')
    category_labels = [item['job_type'].replace('_', ' ').title() for item in job_types]
    category_data = [item['count'] for item in job_types]
    if not category_data: # Fallback if no data
        category_labels = ['No Data']
        category_data = [0]

    # 3. Weekly Jobs Overview 
    weekly_labels = []
    completed_data = []
    in_progress_data = []
    delayed_data = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        weekly_labels.append(day.strftime('%a'))
        
        # Completed on this day
        completed = Job.objects.filter(
            status='completed',
            actual_completion=day
        ).count()
        completed_data.append(completed)
        
        # In Progress (Active on this day)
        in_progress = Job.objects.filter(
            status__in=['in_progress', 'pending'],
            created_at__date__lte=day
        ).count()
        in_progress_data.append(in_progress)
        
        # Delayed (Overdue as of this day)
        delayed = Job.objects.filter(
            status__in=['in_progress', 'pending'],
            expected_completion__lt=day
        ).count()
        delayed_data.append(delayed)
    
    context = {
        'total_clients': total_clients,
        'clients_growth': round(clients_growth, 1),
        'quotes_this_month': quotes_this_month,
        'quotes_growth': 8, 
        'jobs_in_production': jobs_in_production,
        'monthly_revenue': monthly_revenue,
        'revenue_growth': 12,  
        'pending_approvals': pending_approvals,
        'overdue_jobs': overdue_jobs,
        'overdue_change': -2,
        'completed_this_week': completed_this_week,
        'completed_growth': 15,
        'pending_payments': pending_payments,
        'avg_vendor_score': round(avg_vendor_score, 1),
        'vendor_score_change': 3,
        'profit_margin': round(profit_margin, 1),
        'unread_alerts': recent_alerts.count(),
        'recent_alerts': recent_alerts,
        'recent_activity': recent_activity,

        # Chart Data (JSON)
        'revenue_labels': json.dumps(revenue_labels),
        'revenue_data': json.dumps(revenue_trend_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'weekly_labels': json.dumps(weekly_labels),
        'weekly_completed': json.dumps(completed_data),
        'weekly_in_progress': json.dumps(in_progress_data),
        'weekly_delayed': json.dumps(delayed_data),
    }
    
    
    return render(request, 'admin/index.html', context)


# Add CRUD views 
@staff_member_required
def admin_clients_list(request):
    """List all clients with filters"""
    from django.contrib.auth.models import Group
    
    clients = Client.objects.all().order_by('-created_at')
    
    # Apply filters
    status_filter = request.GET.get('status')
    if status_filter:
        clients = clients.filter(status=status_filter)
    
    search = request.GET.get('search', '').strip()
    if search:
        clients = clients.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(client_id__icontains=search)
        )
    
    # Get account managers for the dropdown
    account_managers = User.objects.filter(groups__name='Account Manager').order_by('first_name')
    
    context = {
        'clients': clients,
        'status_filter': status_filter,
        'search': search,
        'account_managers': account_managers,
    }
    return render(request, 'admin/clients_list.html', context)


@staff_member_required
def admin_quotes_list(request):
    """List all quotes"""
    quotes = Quote.objects.select_related('client', 'lead').order_by('-created_at')
    
    context = {'quotes': quotes}
    return render(request, 'admin/quotes_list.html', context)


@staff_member_required
def admin_jobs_list(request):
    """List all jobs"""
    jobs = Job.objects.select_related('client').order_by('-created_at')
    
    context = {'jobs': jobs}
    return render(request, 'admin/jobs_list.html', context)


@staff_member_required
def admin_products_list(request):
    """List all products"""
    products = Product.objects.all().order_by('-created_at')
    
    context = {'products': products}
    return render(request, 'admin/products_list.html', context)


@staff_member_required
def admin_vendors_list(request):
    """List all vendors"""
    vendors = Vendor.objects.all().order_by('-vps_score_value')
    
    context = {'vendors': vendors}
    return render(request, 'admin/vendors_list.html', context)


# API Endpoints for Admin Dashboard CRUD Operations
@staff_member_required
@require_POST
def api_admin_create_client(request):
    """Create a new client via API"""
    try:
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        status = request.POST.get('status', 'Active')
        
        if not name or not email:
            return JsonResponse({'success': False, 'message': 'Name and email are required'}, status=400)
        
        # Check if email already exists
        if Client.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Email already exists'}, status=400)
        
        client = Client.objects.create(
            name=name,
            email=email,
            phone=phone,
            status=status
        )
        
        # Log activity
        ActivityLog.objects.create(
            activity_type='Client Created',
            title=f'New client {name} created',
            description=f'Client {name} was created by admin',
            client=client,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Client created successfully',
            'client_id': client.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@staff_member_required
def admin_leads_list(request):
    """List all leads for admin"""
    leads = Lead.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status')
    if status_filter:
        leads = leads.filter(status=status_filter)

    search = request.GET.get('search', '').strip()
    if search:
        leads = leads.filter(
            Q(lead_name__icontains=search) |
            Q(email__icontains=search) |
            Q(company_name__icontains=search)
        )

    context = {'leads': leads, 'status_filter': status_filter, 'search': search}
    return render(request, 'admin/leads_list.html', context)


@staff_member_required
def admin_processes_list(request):
    processes = Process.objects.all().order_by('-created_at')
    context = {'processes': processes}
    return render(request, 'admin/processes_list.html', context)


@staff_member_required
def admin_qc_list(request):
    qcs = QCInspection.objects.select_related('job').order_by('-created_at')
    context = {'qcs': qcs}
    return render(request, 'admin/qc_list.html', context)


@staff_member_required
def admin_deliveries_list(request):
    deliveries = Delivery.objects.select_related('job').order_by('-created_at')
    context = {'deliveries': deliveries}
    return render(request, 'admin/deliveries_list.html', context)


@staff_member_required
def admin_lpos_list(request):
    lpos = LPO.objects.select_related('client').order_by('-created_at')
    context = {'lpos': lpos}
    return render(request, 'admin/lpos_list.html', context)


@staff_member_required
def admin_payments_list(request):
    payments = Payment.objects.select_related('client').order_by('-created_at')
    context = {'payments': payments}
    return render(request, 'admin/payments_list.html', context)


@staff_member_required
def admin_analytics(request):
    """
    Enhanced Analytics View
    Aggregates data from various helper functions in admin_dashboard.py
    """
    from .admin_dashboard import (
        get_dashboard_stats, 
        get_sales_performance_trend,
        get_profit_margin_data, 
        get_outstanding_receivables,
        get_payment_collection_rate, 
        get_staff_performance,
        get_time_based_insights, 
        get_top_products,
        get_order_status_distribution
    )
    import json
    
    # Fetch all analytics data
    context = {
        'title': 'Analytics Overview',
        'dashboard_stats': get_dashboard_stats(),
        'sales_trend': json.dumps(get_sales_performance_trend(months=12), default=str),
        'order_distribution': json.dumps(get_order_status_distribution()),
        'profit_margins': get_profit_margin_data(),
        'receivables': get_outstanding_receivables(),
        'collection_rate': get_payment_collection_rate(),
        'staff_performance': get_staff_performance(),
        'time_insights': get_time_based_insights(),
        'top_products': get_top_products(limit=10),
    }
    return render(request, 'admin/analytics.html', context)



from .models import SystemSetting

@staff_member_required
def admin_settings(request):
    """
    System Settings View with Persistence
    """
    # Define default settings
    default_settings = {
        'site_title': 'Print Duka MIS',
        'support_email': 'support@printduka.com',
        'currency': 'KES',
        'timezone': 'Africa/Nairobi',
        'maintenance_mode': 'False',
        'allow_registration': 'True',
        'email_on_order': 'True',
        'email_on_quote': 'True',
        'daily_digest': 'False',
    }

    if request.method == 'POST':
        try:
            
            for key, value in request.POST.items():
                if key in default_settings:
                    SystemSetting.objects.update_or_create(
                        key=key,
                        defaults={'value': value}
                    )
            
            # Handle chrchboxes
            checkbox_settings = ['maintenance_mode', 'allow_registration', 'email_on_order', 'email_on_quote', 'daily_digest']
            for key in checkbox_settings:
                if key not in request.POST:
                    SystemSetting.objects.update_or_create(
                        key=key,
                        defaults={'value': 'False'}
                    )
            
            messages.success(request, 'System settings updated successfully.')
        except Exception as e:
            messages.error(request, f'Error saving settings: {str(e)}')
            
        return redirect('admin_settings')
        
    # Load current settings from DB, falling back to defaults
    current_settings = default_settings.copy()
    db_settings = SystemSetting.objects.filter(key__in=default_settings.keys())
    for setting in db_settings:
        current_settings[setting.key] = setting.value

    def to_bool(val):
        return str(val).lower() == 'true'

    context = {
        'title': 'System Settings',
        'system_settings': {
            'site_title': current_settings['site_title'],
            'support_email': current_settings['support_email'],
            'currency': current_settings['currency'],
            'timezone': current_settings['timezone'],
            'maintenance_mode': to_bool(current_settings['maintenance_mode']),
            'allow_registration': to_bool(current_settings['allow_registration']),
        },
        'notification_settings': {
            'email_on_order': to_bool(current_settings['email_on_order']),
            'email_on_quote': to_bool(current_settings['email_on_quote']),
            'daily_digest': to_bool(current_settings['daily_digest']),
        }
    }
    return render(request, 'admin/settings.html', context)

@staff_member_required
def admin_users_list(request):
    """List all users and groups for admin management"""
    from django.contrib.auth.models import Group
    
    users = User.objects.all().order_by('username')
    groups = Group.objects.all().order_by('name')
    
    context = {
        'users': users,
        'groups': groups,
    }
    return render(request, 'admin/users_list.html', context)




@staff_member_required
def admin_alerts_list(request):
    alerts = SystemAlert.objects.filter(is_active=True).order_by('-created_at')
    context = {'alerts': alerts}
    return render(request, 'admin/alerts_list.html', context)


@staff_member_required
@require_POST
def api_admin_update_client(request, client_id):
    """Update an existing client via API"""
    try:
        client = get_object_or_404(Client, id=client_id)
        
        client.name = request.POST.get('name', client.name)
        client.email = request.POST.get('email', client.email)
        client.phone = request.POST.get('phone', client.phone)
        client.status = request.POST.get('status', client.status)
        
        client.save()
        
        # Log activity
        ActivityLog.objects.create(
            activity_type='Client Updated',
            title=f'Client {client.name} updated',
            description=f'Client {client.name} was updated by admin',
            client=client,
            created_by=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Client updated successfully',
            'client_id': client.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@staff_member_required
@require_POST
def api_admin_delete_client(request, client_id):
    """Delete a client via API"""
    try:
        client = get_object_or_404(Client, id=client_id)
        
        # Log activity before deletion
        ActivityLog.objects.create(
            activity_type='Client Deleted',
            title=f'Client {client.name} deleted',
            description=f'Client {client.name} was deleted by admin',
            client=client,
            created_by=request.user
        )
        
        client_name = client.name
        client.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Client {client_name} deleted successfully'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@staff_member_required
def api_admin_dashboard_data(request):
    """API endpoint for real-time dashboard data polling with real data"""
    from .admin_dashboard import get_dashboard_stats
    
    try:
        stats = get_dashboard_stats()
        
        today = timezone.now().date()
        
        # Revenue Trend
        revenue_trend = []
        current_date = today.replace(day=1) 
        
        for i in range(5, -1, -1):
            # Calculate month start and end
            if i == 0:
                month_start = current_date
                month_end = today
            else:
                # 
                temp_date = current_date
                for _ in range(i):
                    temp_date = temp_date - timedelta(days=1)
                    temp_date = temp_date.replace(day=1)
                month_start = temp_date
                # Get last day of month
                next_month = month_start + timedelta(days=32)
                month_end = (next_month.replace(day=1) - timedelta(days=1))
            
            # Sum revenue from approved quotes and completed LPOs
            quote_revenue = Quote.objects.filter(
                status__in=['Approved', 'Completed'],
                approved_at__gte=month_start,
                approved_at__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            lpo_revenue = LPO.objects.filter(
                status__in=['approved', 'completed'],
                created_at__gte=month_start,
                created_at__lte=month_end
            ).aggregate(total=Sum('total_amount'))['total'] or 0
            
            monthly_total = float(quote_revenue or 0) + float(lpo_revenue or 0)
            revenue_trend.append(monthly_total)
        
       
        # Get product counts by category or type
        from .models import Product, ProductTag, JobProduct
        
        category_data = []
        category_labels = []
        
        # If products have tags or categories, group by them
        product_counts = Product.objects.values(
            'product_category'  # Or use tags if available
        ).annotate(count=Count('id')).order_by('-count')[:5]
        
        if product_counts.exists():
            for item in product_counts:
                category = item.get('product_category', 'Uncategorized')
                category_labels.append(category)
                category_data.append(item['count'])
        else:
            # Fallback: get production by job types/products in recent jobs
            job_products = JobProduct.objects.filter(
                job__created_at__gte=today - timedelta(days=30)
            ).values('product__name').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            if job_products.exists():
                for item in job_products:
                    category_labels.append(item['product__name'])
                    category_data.append(item['count'])
            else:
                # Last fallback: use generic data
                category_labels = ['Products', 'Services', 'Other']
                category_data = [Product.objects.count(), 0, 0]
        
        production_by_category = category_data if category_data else [1, 1, 1]
        
        # Weekly JObs
        weekly_jobs = {
            'completed': [],
            'in_progress': [],
            'delayed': []
        }
        
        # Get job counts for last 6 days by status
        for i in range(5, -1, -1):
            day = today - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            
            completed_count = Job.objects.filter(
                status__in=['completed', 'Completed', 'done', 'Done'],
                updated_at__date=day
            ).count()
            
            in_progress_count = Job.objects.filter(
                status__in=['in_progress', 'In Progress', 'pending', 'Pending'],
                updated_at__date=day
            ).count()
            
            # For delayed jobs, check if they have exceeded deadline
            overdue_count = Job.objects.filter(
                status__in=['in_progress', 'In Progress', 'pending', 'Pending'],
                deadline__lt=day,
                updated_at__date=day
            ).count()
            
            weekly_jobs['completed'].append(completed_count)
            weekly_jobs['in_progress'].append(in_progress_count)
            weekly_jobs['delayed'].append(overdue_count)
        
        # Calculate KPIs
        # Total clients
        total_clients = Client.objects.count()
        
        # Quotes this month
        quotes_this_month = Quote.objects.filter(
            created_at__gte=today.replace(day=1)
        ).count()
        
        # Jobs in production
        jobs_in_production = Job.objects.filter(
            status__in=['in_progress', 'In Progress', 'pending', 'Pending']
        ).count()
        
        # Monthly revenue
        monthly_start = today.replace(day=1)
        monthly_revenue = Quote.objects.filter(
            status__in=['Approved', 'Completed'],
            approved_at__gte=monthly_start
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_revenue_lpo = LPO.objects.filter(
            created_at__gte=monthly_start,
            status__in=['approved', 'completed']
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_revenue = float(monthly_revenue or 0) + float(monthly_revenue_lpo or 0)
        
        # Pending approvals
        pending_approvals = Quote.objects.filter(
            status__in=['Pending', 'pending', 'Draft', 'draft']
        ).count()
        
        # Overdue jobs
        overdue_jobs = Job.objects.filter(
            status__in=['in_progress', 'In Progress', 'pending', 'Pending'],
            deadline__lt=today
        ).count()
        
        return JsonResponse({
            'success': True,
            'total_clients': total_clients,
            'quotes_this_month': quotes_this_month,
            'jobs_in_production': jobs_in_production,
            'monthly_revenue': monthly_revenue,
            'pending_approvals': pending_approvals,
            'overdue_jobs': overdue_jobs,
            'revenue_trend': revenue_trend,
            'production_by_category': production_by_category,
            'weekly_jobs': weekly_jobs
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# Add this import at the top if not present
from .models import ActivityLog

@staff_member_required
def admin_activity_list(request):
    """List all activity logs"""
    activities = ActivityLog.objects.select_related('client', 'created_by').order_by('-created_at')
    
    # Optional: Add filtering
    activity_type = request.GET.get('type')
    if activity_type:
        activities = activities.filter(activity_type=activity_type)
        
    search = request.GET.get('search')
    if search:
        activities = activities.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) |
            Q(client__name__icontains=search)
        )
        
    paginator = Paginator(activities, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'activity_type': activity_type,
        'search': search
    }
    return render(request, 'admin/activity_list.html', context)

# Production Team Settings
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from datetime import timedelta


@login_required
def production_settings(request):
    """View for Production Team Settings"""
    # You can add logic here to save settings if needed
    if request.method == 'POST':
        # Handle form submission here
        messages.success(request, 'Settings updated successfully.')
        return redirect('production_settings')
        
    context = {
        'title': 'Production Settings',
        'user': request.user,
    }
    return render(request, 'production_settings.html', context)

@login_required
def production_analytics(request):
    """View for Production Team Analytics"""
    # Calculate date ranges
    today = timezone.now()
    thirty_days_ago = today - timedelta(days=30)
    
    # Fetch relevant jobs
    all_jobs = Job.objects.all() # Filter by production team if needed
    recent_jobs = all_jobs.filter(created_at__gte=thirty_days_ago)
    
    # Calculate KPIs
    total_jobs_month = recent_jobs.count()
    completed_jobs = recent_jobs.filter(status='completed').count()
    
    # Calculate On-Time Rate (Example logic)
    on_time_jobs = recent_jobs.filter(status='completed', actual_completion__lte=F('expected_completion')).count()

    on_time_rate = (on_time_jobs / completed_jobs * 100) if completed_jobs > 0 else 100
    
    # Calculate Average Lead Time
   
    avg_lead_time = 3.5 # Days
    
    context = {
        'title': 'Production Analytics',
        'total_jobs_month': total_jobs_month,
        'completion_rate': (completed_jobs / total_jobs_month * 100) if total_jobs_month > 0 else 0,
        'on_time_rate': on_time_rate,
        'avg_lead_time': avg_lead_time,
        'recent_jobs': recent_jobs.order_by('-created_at')[:5],
    }
    return render(request, 'production_analytics.html', context)



# ============================================================================
# VENDOR PORTAL VIEWSETS
# ============================================================================

from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .permissions import IsProductionTeam
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from .models import Vendor, PurchaseOrder, VendorInvoice, User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .models import (
    PurchaseOrder,
    VendorInvoice,
    PurchaseOrderProof,
    PurchaseOrderIssue,
    PurchaseOrderNote,
    MaterialSubstitutionRequest,
    Vendor,
    QCInspection,
    JobVendorStage,
    VendorCapacityAlert,
    POSMilestone,
    MaterialSubstitutionApproval,
    InvoiceHold,
    SLAEscalation,
    ProgressUpdateBatch,
    QCProofLink,
    VPSRecalculationLog,
    CustomerNotification,
    DeadlineCalculation,
)
from .vendor_portal_serializers import (
    PurchaseOrderSerializer,
    VendorInvoiceSerializer,
    PurchaseOrderProofSerializer,
    PurchaseOrderIssueSerializer,
    PurchaseOrderNoteSerializer,
    MaterialSubstitutionRequestSerializer,
    VendorPerformanceSerializer,
)
from .api_serializers import (
    VendorCapacityAlertSerializer,
    POSMilestoneSerializer,
    MaterialSubstitutionApprovalSerializer,
    InvoiceHoldSerializer,
    SLAEscalationSerializer,
    ProgressUpdateBatchSerializer,
    QCProofLinkSerializer,
    VPSRecalculationLogSerializer,
    CustomerNotificationSerializer,
    DeadlineCalculationSerializer,
)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Purchase Orders.
    Vendors can view their POs and update status/milestones.
    """
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vendor', 'status', 'milestone', 'job']
    search_fields = ['po_number', 'product_type', 'job__job_number']
    ordering_fields = ['created_at', 'required_by', 'status']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Filter POs based on user role:
        - Vendors see only their POs
        - Production team sees all POs
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Filter by vendor if vendor_id is provided
        vendor_id = self.request.query_params.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        return queryset.select_related('job', 'vendor', 'job__client')
    
    @action(detail=True, methods=['post'])
    def accept(self, request, pk=None):
        """Vendor accepts the purchase order"""
        po = self.get_object()
        po.vendor_accepted = True
        po.vendor_accepted_at = timezone.now()
        po.status = 'in_production'
        po.milestone = 'in_production'
        po.save()
        
        return Response({
            'status': 'success',
            'message': 'Purchase order accepted',
            'po_number': po.po_number
        })
    
    @action(detail=True, methods=['post'])
    def update_milestone(self, request, pk=None):
        """Update PO milestone"""
        po = self.get_object()
        milestone = request.data.get('milestone')
        notes = request.data.get('notes', '')
        
        if milestone not in dict(PurchaseOrder.MILESTONE_CHOICES):
            return Response(
                {'error': 'Invalid milestone'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        po.milestone = milestone
        if notes:
            po.vendor_notes = notes
        
        # Auto-update status based on milestone
        milestone_status_map = {
            'awaiting_acceptance': 'new',
            'in_production': 'in_production',
            'quality_check': 'quality_check',
            'completed': 'completed',
        }
        po.status = milestone_status_map.get(milestone, po.status)
        
        po.save()
        
        return Response({
            'status': 'success',
            'message': 'Milestone updated',
            'milestone': po.milestone,
            'po_status': po.status
        })
    
    @action(detail=True, methods=['post'])
    def acknowledge_assets(self, request, pk=None):
        """Mark assets as acknowledged"""
        po = self.get_object()
        po.assets_acknowledged = True
        po.assets_acknowledged_at = timezone.now()
        po.save()
        
        return Response({
            'status': 'success',
            'message': 'Assets acknowledged'
        })
    
    @action(detail=False, methods=['get'])
    def vendor_dashboard(self, request):
        """Get vendor dashboard statistics"""
        vendor_id = request.query_params.get('vendor_id')
        if not vendor_id:
            return Response(
                {'error': 'vendor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def coordination_jobs(self, request, pk=None):
        """Get related POs in the same coordination group"""
        po = self.get_object()
        if po.coordination_group:
            related_pos = PurchaseOrder.objects.filter(
                coordination_group=po.coordination_group
            ).exclude(id=po.id)
            serializer = self.get_serializer(related_pos, many=True)
            return Response(serializer.data)
        return Response([])


class VendorInvoiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor Invoices.
    Vendors can create and submit invoices for completed work.
    """
    queryset = VendorInvoice.objects.all()
    serializer_class = VendorInvoiceSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['vendor', 'status', 'purchase_order', 'job']
    search_fields = ['invoice_number', 'vendor_invoice_ref']
    ordering_fields = ['created_at', 'invoice_date', 'due_date', 'total_amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter invoices by vendor"""
        user = self.request.user
        queryset = super().get_queryset()
        
        vendor_id = self.request.query_params.get('vendor_id', None)
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
        
        return queryset.select_related('vendor', 'purchase_order', 'job')
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit invoice for review"""
        invoice = self.get_object()
        
        if invoice.status != 'draft':
            return Response(
                {'error': 'Only draft invoices can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'submitted'
        invoice.submitted_at = timezone.now()
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'Invoice submitted for review',
            'invoice_number': invoice.invoice_number
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve invoice (Production Team only)"""
        invoice = self.get_object()
        
        if invoice.status != 'submitted':
            return Response(
                {'error': 'Only submitted invoices can be approved'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'approved'
        invoice.approved_at = timezone.now()
        invoice.approved_by = request.user
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'Invoice approved',
            'invoice_number': invoice.invoice_number
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject invoice with reason"""
        invoice = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.status = 'rejected'
        invoice.rejection_reason = reason
        invoice.save()
        
        return Response({
            'status': 'success',
            'message': 'Invoice rejected',
            'invoice_number': invoice.invoice_number
        })


class PurchaseOrderProofViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order Proofs"""
    queryset = PurchaseOrderProof.objects.all()
    serializer_class = PurchaseOrderProofSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'status']
    ordering_fields = ['submitted_at']
    ordering = ['-submitted_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve proof"""
        proof = self.get_object()
        proof.status = 'approved'
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.save()
        
        return Response({'status': 'success', 'message': 'Proof approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject proof with reason"""
        proof = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proof.status = 'rejected'
        proof.rejection_reason = reason
        proof.reviewed_by = request.user
        proof.reviewed_at = timezone.now()
        proof.save()
        
        return Response({'status': 'success', 'message': 'Proof rejected'})


class PurchaseOrderIssueViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order Issues"""
    queryset = PurchaseOrderIssue.objects.all()
    serializer_class = PurchaseOrderIssueSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'issue_type', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve issue"""
        issue = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        issue.status = 'resolved'
        issue.resolution_notes = resolution_notes
        issue.resolved_by = request.user
        issue.resolved_at = timezone.now()
        issue.save()
        
        return Response({'status': 'success', 'message': 'Issue resolved'})


class PurchaseOrderNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for Purchase Order Notes"""
    queryset = PurchaseOrderNote.objects.all()
    serializer_class = PurchaseOrderNoteSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'category']
    ordering_fields = ['created_at']
    ordering = ['created_at']
    
    def perform_create(self, serializer):
        """Set sender to current user"""
        serializer.save(sender=self.request.user)


class MaterialSubstitutionRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for Material Substitution Requests"""
    queryset = MaterialSubstitutionRequest.objects.all()
    serializer_class = MaterialSubstitutionRequestSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['purchase_order', 'status']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve substitution request"""
        sub_request = self.get_object()
        sub_request.status = 'approved'
        sub_request.reviewed_by = request.user
        sub_request.reviewed_at = timezone.now()
        sub_request.save()
        
        return Response({'status': 'success', 'message': 'Substitution request approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject substitution request"""
        sub_request = self.get_object()
        reason = request.data.get('reason', '')
        
        if not reason:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        sub_request.status = 'rejected'
        sub_request.rejection_reason = reason
        sub_request.reviewed_by = request.user
        sub_request.reviewed_at = timezone.now()
        sub_request.save()
        
        return Response({'status': 'success', 'message': 'Substitution request rejected'})


class VendorPerformanceViewSet(viewsets.ViewSet):
    """
    ViewSet for Vendor Performance Analytics.
    Provides performance metrics and scorecard data.
    """
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def scorecard(self, request):
        """Get vendor performance scorecard"""
        vendor_id = request.query_params.get('vendor_id')
        if not vendor_id:
            return Response(
                {'error': 'vendor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response(
                {'error': 'Vendor not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate performance metrics
        performance_data = vendor.calculate_vps()
        
        # On-time delivery rate
        stages = JobVendorStage.objects.filter(
            vendor=vendor,
            status='completed',
            actual_completion__isnull=False
        )
        total_stages = stages.count()
        on_time_stages = sum(1 for stage in stages if stage.is_on_time)
        on_time_rate = (on_time_stages / total_stages * 100) if total_stages > 0 else 0
        
        # Average turnaround time
        completed_pos = PurchaseOrder.objects.filter(
            vendor=vendor,
            status='completed',
            actual_completion__isnull=False
        )
        avg_turnaround = 0
        if completed_pos.exists():
            turnaround_times = [
                (po.actual_completion - po.created_at.date()).days
                for po in completed_pos
            ]
            avg_turnaround = sum(turnaround_times) / len(turnaround_times)
        
        # Cost per job
        total_cost = PurchaseOrder.objects.filter(vendor=vendor).aggregate(
            Sum('total_cost')
        )['total_cost__sum'] or 0
        total_jobs = PurchaseOrder.objects.filter(vendor=vendor).count()
        cost_per_job = (total_cost / total_jobs) if total_jobs > 0 else 0
        
        # Defect rate (from QC inspections)
        qc_inspections = QCInspection.objects.filter(vendor=vendor)
        total_qc = qc_inspections.count()
        failed_qc = qc_inspections.filter(status__in=['failed', 'rework']).count()
        defect_rate = (failed_qc / total_qc * 100) if total_qc > 0 else 0
        
        # Additional metrics
        total_pos_offered = PurchaseOrder.objects.filter(vendor=vendor).count()
        accepted_pos = PurchaseOrder.objects.filter(vendor=vendor, vendor_accepted=True).count()
        acceptance_rate = (accepted_pos / total_pos_offered * 100) if total_pos_offered > 0 else 0
        
        # Response time (avg hours to accept PO)
        accepted_pos_with_time = PurchaseOrder.objects.filter(
            vendor=vendor, 
            vendor_accepted=True,
            vendor_accepted_at__isnull=False
        )
        response_times = [
            (po.vendor_accepted_at - po.created_at).total_seconds() / 3600
            for po in accepted_pos_with_time
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Ghosting incidents (POs accepted but no activity for >48hrs)
        ghosting_incidents = PurchaseOrder.objects.filter(
            vendor=vendor,
            vendor_accepted=True,
            updated_at__lt=timezone.now() - timedelta(hours=48),
            status='in_production'
        ).count()
        
        # Decline rate
        declined_pos = PurchaseOrder.objects.filter(vendor=vendor, status='cancelled').count()
        decline_rate = (declined_pos / total_pos_offered * 100) if total_pos_offered > 0 else 0
        
        # Performance insights
        insights = []
        
        if performance_data['qc_pass_rate'] >= 95:
            insights.append({
                'type': 'positive',
                'icon': 'check-circle',
                'title': 'Strong QC Track Record',
                'description': f"Maintained {performance_data['qc_pass_rate']:.1f}% QC pass rate over 90 days - {total_qc} inspections"
            })
        
        if on_time_rate < 85:
            insights.append({
                'type': 'warning',
                'icon': 'alert-triangle',
                'title': 'Attention Needed: On-Time Delivery',
                'description': f"On-time rate at {on_time_rate:.1f}% - target is 85%+"
            })
        
        if defect_rate > 5:
            insights.append({
                'type': 'negative',
                'icon': 'x-circle',
                'title': 'Quality Concerns: Too Many Defects',
                'description': f"Defect rate at {defect_rate:.1f}% - {failed_qc} failed out of {total_qc} inspections"
            })
        
        # Build response
        scorecard_data = {
            'overall_score': int(vendor.vps_score_value),
            'tax_status': 'Compliant with tax filing' if vendor.tax_pin else 'No tax info',
            'certifications': ['Certified Vendor'] if vendor.recommended else [],
            
            # Metrics
            'on_time_rate': round(on_time_rate, 1),
            'quality_score': round(performance_data['qc_pass_rate'], 1),
            'avg_turnaround': round(avg_turnaround, 1),
            'defect_rate': round(defect_rate, 1),
            'cost_per_job': round(cost_per_job, 2),
            'acceptance_rate': round(acceptance_rate, 1),
            'response_time': round(avg_response_time, 1),
            'ghosting_incidents': ghosting_incidents,
            'decline_rate': round(decline_rate, 1),
            
            # Insights
            'insights': insights,
        }
        
        serializer = VendorPerformanceSerializer(scorecard_data)
        return Response(serializer.data)


# =====================================
# NEW: BACKEND GAPS - VIEWSETS
# =====================================

class VendorCapacityAlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Vendor Capacity Alerts.
    Provides alerting system for vendor capacity thresholds.
    """
    queryset = VendorCapacityAlert.objects.all()
    serializer_class = VendorCapacityAlertSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    def get_queryset(self):
        """Filter by vendor or get all for PT"""
        qs = VendorCapacityAlert.objects.all()
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            qs = qs.filter(vendor_id=vendor_id)
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            qs = qs.filter(alert_type=alert_type)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert"""
        alert = self.get_object()
        alert.status = 'acknowledged'
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = request.user
        alert.save()
        return Response({'status': 'alert acknowledged'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve an alert"""
        alert = self.get_object()
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'status': 'alert resolved'})
    
    @action(detail=False, methods=['post'])
    def check_capacity(self, request):
        """Check and create alerts for vendor capacity"""
        from django.db.models import Count
        
        vendors = Vendor.objects.all()
        alerts_created = 0
        
        for vendor in vendors:
            # Get active jobs
            active_pos = PurchaseOrder.objects.filter(
                vendor=vendor,
                status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
            ).count()
            
            # Calculate capacity
            vendor_capacity = getattr(vendor, 'max_concurrent_jobs', 10)
            utilization = (active_pos / vendor_capacity) * 100 if vendor_capacity > 0 else 0
            
            # Check thresholds
            if utilization >= 100:
                alert, created = VendorCapacityAlert.objects.get_or_create(
                    vendor=vendor,
                    alert_type='capacity_critical',
                    status='active',
                    defaults={'message': f'Vendor at {utilization:.0f}% capacity', 'severity': 3}
                )
                if created:
                    alerts_created += 1
            elif utilization >= 80:
                alert, created = VendorCapacityAlert.objects.get_or_create(
                    vendor=vendor,
                    alert_type='capacity_warning',
                    status='active',
                    defaults={'message': f'Vendor at {utilization:.0f}% capacity', 'severity': 2}
                )
                if created:
                    alerts_created += 1
        
        return Response({'alerts_created': alerts_created})


class POSMilestoneViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Purchase Order Milestones.
    Tracks milestone progress and sends alerts.
    """
    queryset = POSMilestone.objects.all()
    serializer_class = POSMilestoneSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by purchase order"""
        qs = POSMilestone.objects.all()
        po_id = self.request.query_params.get('po_id')
        if po_id:
            qs = qs.filter(purchase_order_id=po_id)
        return qs
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark milestone as complete"""
        milestone = self.get_object()
        milestone.completed = True
        milestone.completed_at = timezone.now()
        milestone.completed_on_time = milestone.target_date >= timezone.now().date()
        milestone.save()
        return Response({'status': 'milestone completed'})
    
    @action(detail=False, methods=['post'])
    def check_approaching(self, request):
        """Check for approaching milestones and send alerts"""
        from django.utils import timezone
        
        # Get milestones due within 3 days
        three_days_ahead = timezone.now().date() + timedelta(days=3)
        approaching = POSMilestone.objects.filter(
            target_date__lte=three_days_ahead,
            target_date__gte=timezone.now().date(),
            completed=False,
            alert_sent=False
        )
        
        alerts_sent = 0
        for milestone in approaching:
            # Create alert for approaching milestone
            alert, created = VendorCapacityAlert.objects.get_or_create(
                vendor=milestone.purchase_order.vendor,
                purchase_order=milestone.purchase_order,
                alert_type='deadline_approaching',
                status='active',
                defaults={
                    'message': f'{milestone.get_milestone_type_display()} due {milestone.target_date}',
                    'severity': 2
                }
            )
            
            milestone.alert_sent = True
            milestone.alert_sent_at = timezone.now()
            milestone.save()
            
            if created:
                alerts_sent += 1
        
        return Response({'alerts_sent': alerts_sent})


class MaterialSubstitutionApprovalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Material Substitution Approvals.
    Handles approval workflow and cost impact calculations.
    """
    queryset = MaterialSubstitutionApproval.objects.all()
    serializer_class = MaterialSubstitutionApprovalSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by PO or status"""
        qs = MaterialSubstitutionApproval.objects.all()
        po_id = self.request.query_params.get('po_id')
        if po_id:
            qs = qs.filter(purchase_order_id=po_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(approval_status=status_filter)
        return qs
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve material substitution"""
        substitution = self.get_object()
        substitution.approval_status = 'approved'
        substitution.approval_notes = request.data.get('notes', '')
        substitution.approved_by = request.user
        substitution.approved_at = timezone.now()
        substitution.save()
        return Response({'status': 'substitution approved'})
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject material substitution"""
        substitution = self.get_object()
        substitution.approval_status = 'rejected'
        substitution.approval_notes = request.data.get('notes', '')
        substitution.approved_by = request.user
        substitution.approved_at = timezone.now()
        substitution.save()
        return Response({'status': 'substitution rejected'})
    
    @action(detail=True, methods=['get'])
    def cost_impact(self, request, pk=None):
        """Get cost impact of substitution"""
        substitution = self.get_object()
        return Response({
            'original_cost': str(substitution.original_cost),
            'substitute_cost': str(substitution.substitute_cost),
            'cost_difference': str(substitution.cost_difference),
            'cost_impact_percentage': round(substitution.cost_impact_percentage, 2),
            'vendor': substitution.purchase_order.vendor.name
        })


class InvoiceHoldViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Invoice Holds.
    Tracks holds and reasons for invoices.
    """
    queryset = InvoiceHold.objects.all()
    serializer_class = InvoiceHoldSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['post'])
    def hold_invoice(self, request):
        """Place a hold on an invoice"""
        invoice_id = request.data.get('invoice_id')
        hold_reason = request.data.get('hold_reason')
        hold_details = request.data.get('hold_details', '')
        
        try:
            invoice = VendorInvoice.objects.get(id=invoice_id)
        except VendorInvoice.DoesNotExist:
            return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)
        
        hold, created = InvoiceHold.objects.get_or_create(
            invoice=invoice,
            defaults={
                'hold_reason': hold_reason,
                'hold_details': hold_details,
                'held_by': request.user
            }
        )
        
        return Response({'status': 'invoice hold created' if created else 'invoice already on hold'})
    
    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release a hold on an invoice"""
        hold = self.get_object()
        hold.released = True
        hold.released_at = timezone.now()
        hold.released_by = request.user
        hold.save()
        return Response({'status': 'invoice hold released'})


# =====================================
# PHASE 2: PT DASHBOARD
# =====================================

class PTDashboardViewSet(viewsets.ViewSet):
    """
    ViewSet for Production Team Dashboard.
    Returns comprehensive metrics on vendor workload, job status, performance.
    """
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['get'], url_path='overview')
    def overview(self, request):
        """Get PT dashboard overview with vendor metrics and job status"""
        from django.utils import timezone
        from datetime import timedelta
        from django.db.models import Count, Q, Avg
        
        now = timezone.now()
        
        # ===== VENDOR WORKLOAD =====
        vendors = Vendor.objects.all().annotate(
            active_jobs=Count('purchase_orders', filter=Q(
                purchase_orders__status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
            )),
            total_jobs=Count('purchase_orders'),
            on_time_rate=Avg('vendorperformancescore__on_time_percentage', filter=Q(
                vendorperformancescore__updated_at__gte=now - timedelta(days=30)
            ))
        )
        
        vendor_workload = []
        for vendor in vendors:
            capacity = getattr(vendor, 'max_concurrent_jobs', 10)
            utilization = round((vendor.active_jobs / capacity) * 100, 1) if capacity > 0 else 0
            
            # Check for capacity alerts
            has_warning = VendorCapacityAlert.objects.filter(
                vendor=vendor,
                alert_type='capacity_warning',
                status='active'
            ).exists()
            
            has_critical = VendorCapacityAlert.objects.filter(
                vendor=vendor,
                alert_type='capacity_critical',
                status='active'
            ).exists()
            
            vendor_workload.append({
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'active_jobs': vendor.active_jobs,
                'total_jobs': vendor.total_jobs,
                'capacity': capacity,
                'utilization_percent': utilization,
                'capacity_warning': has_warning,
                'capacity_critical': has_critical,
                'on_time_rate': vendor.on_time_rate or 0,
                'status': 'critical' if has_critical else ('warning' if has_warning else 'healthy')
            })
        
        # ===== JOB STATUS SUMMARY =====
        all_pos = PurchaseOrder.objects.all()
        
        job_status = {
            'total_active': all_pos.filter(
                status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
            ).count(),
            'new_pending': all_pos.filter(status='NEW').count(),
            'in_production': all_pos.filter(status='IN_PRODUCTION').count(),
            'awaiting_approval': all_pos.filter(status='AWAITING_APPROVAL').count(),
            'completed': all_pos.filter(status='COMPLETED').count(),
            'total': all_pos.count()
        }
        
        # ===== OVERDUE JOBS =====
        overdue_jobs = all_pos.filter(
            due_date__lt=now,
            status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
        ).count()
        
        # ===== APPROACHING DEADLINES (within 3 days) =====
        approaching_deadline_time = now + timedelta(days=3)
        approaching_jobs = all_pos.filter(
            due_date__lte=approaching_deadline_time,
            due_date__gte=now,
            status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
        ).count()
        
        # ===== MILESTONE PROGRESS =====
        approaching_milestones = POSMilestone.objects.filter(
            target_date__lte=approaching_deadline_time,
            target_date__gte=now.date(),
            completed=False,
            alert_sent=False
        ).count()
        
        # ===== MATERIAL SUBSTITUTIONS =====
        pending_substitutions = MaterialSubstitutionApproval.objects.filter(
            approval_status='pending'
        ).count()
        
        approved_substitutions = MaterialSubstitutionApproval.objects.filter(
            approval_status='approved',
            customer_notified=False
        ).count()
        
        # ===== INVOICE HOLDS =====
        active_holds = InvoiceHold.objects.filter(
            released=False
        ).count()
        
        # ===== ALERTS SUMMARY =====
        active_alerts = VendorCapacityAlert.objects.filter(
            status='active'
        ).count()
        
        acknowledged_alerts = VendorCapacityAlert.objects.filter(
            status='acknowledged'
        ).count()
        
        # ===== PERFORMANCE METRICS =====
        completed_pos = all_pos.filter(status='COMPLETED')
        if completed_pos.exists():
            total_completed = completed_pos.count()
            on_time = completed_pos.filter(completed_on_time=True).count()
            on_time_percentage = round((on_time / total_completed) * 100, 1)
        else:
            on_time_percentage = 0
        
        # ===== ACTION ITEMS =====
        action_items = []
        
        if overdue_jobs > 0:
            action_items.append({
                'type': 'overdue_jobs',
                'priority': 'critical',
                'count': overdue_jobs,
                'message': f'{overdue_jobs} jobs are overdue'
            })
        
        if pending_substitutions > 0:
            action_items.append({
                'type': 'pending_substitutions',
                'priority': 'high',
                'count': pending_substitutions,
                'message': f'{pending_substitutions} material substitutions pending approval'
            })
        
        if active_holds > 0:
            action_items.append({
                'type': 'invoice_holds',
                'priority': 'high',
                'count': active_holds,
                'message': f'{active_holds} invoices are on hold'
            })
        
        if active_alerts > 0:
            action_items.append({
                'type': 'capacity_alerts',
                'priority': 'medium',
                'count': active_alerts,
                'message': f'{active_alerts} vendors at high capacity'
            })
        
        # ===== BUILD RESPONSE =====
        return Response({
            'timestamp': now.isoformat(),
            'summary': {
                'total_jobs': job_status['total'],
                'active_jobs': job_status['total_active'],
                'overdue_jobs': overdue_jobs,
                'approaching_deadlines': approaching_jobs,
                'on_time_completion_rate': on_time_percentage
            },
            'job_status': job_status,
            'vendor_workload': vendor_workload,
            'milestones': {
                'approaching_count': approaching_milestones,
                'alert_pending': approaching_milestones > 0
            },
            'substitutions': {
                'pending_approval': pending_substitutions,
                'awaiting_notification': approved_substitutions
            },
            'holds': {
                'active_holds': active_holds
            },
            'alerts': {
                'active_capacity_alerts': active_alerts,
                'acknowledged_alerts': acknowledged_alerts
            },
            'action_items': action_items
        })
    
    @action(detail=False, methods=['get'], url_path='vendor-status')
    def vendor_status(self, request):
        """Get real-time status for specific vendors"""
        vendor_ids = request.query_params.getlist('vendor_ids')
        
        if not vendor_ids:
            vendors = Vendor.objects.all()
        else:
            vendors = Vendor.objects.filter(id__in=vendor_ids)
        
        vendor_statuses = []
        now = timezone.now()
        
        for vendor in vendors:
            # Active jobs
            active_pos = PurchaseOrder.objects.filter(
                vendor=vendor,
                status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
            )
            
            # Overdue jobs for this vendor
            overdue = active_pos.filter(due_date__lt=now).count()
            
            # Capacity calculation
            capacity = getattr(vendor, 'max_concurrent_jobs', 10)
            utilization = round((active_pos.count() / capacity) * 100, 1) if capacity > 0 else 0
            
            # Recent performance
            performance = vendor.vendorperformancescore_set.latest('updated_at') if vendor.vendorperformancescore_set.exists() else None
            
            vendor_statuses.append({
                'vendor_id': vendor.id,
                'vendor_name': vendor.name,
                'active_jobs': active_pos.count(),
                'overdue_jobs': overdue,
                'capacity_utilization': utilization,
                'on_time_percentage': performance.on_time_percentage if performance else 0,
                'quality_score': performance.quality_score if performance else 0,
                'communication_score': performance.communication_score if performance else 0,
                'last_updated': performance.updated_at.isoformat() if performance else None
            })
        
        return Response(vendor_statuses)


class SLAEscalationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for SLA Escalations.
    Handles escalation of overdue jobs and tracks escalation workflow.
    """
    queryset = SLAEscalation.objects.all()
    serializer_class = SLAEscalationSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['post'])
    def escalate_job(self, request):
        """Escalate an overdue purchase order"""
        po_id = request.data.get('purchase_order_id')
        escalation_level = request.data.get('escalation_level', 'level_1')
        escalation_reason = request.data.get('escalation_reason', '')
        
        try:
            po = PurchaseOrder.objects.get(id=po_id)
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Purchase order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate days overdue
        now = timezone.now().date()
        days_overdue = max(0, (now - po.due_date).days)
        
        # Check if escalation already exists
        existing = SLAEscalation.objects.filter(
            purchase_order=po,
            escalation_status__in=['pending', 'notified']
        ).first()
        
        if existing:
            return Response({
                'error': 'Active escalation already exists',
                'escalation_id': existing.id
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create escalation
        escalation = SLAEscalation.objects.create(
            purchase_order=po,
            escalation_level=escalation_level,
            original_deadline=po.due_date,
            current_deadline=po.due_date,
            days_overdue=days_overdue,
            escalation_reason=escalation_reason,
            escalated_by=request.user
        )
        
        serializer = SLAEscalationSerializer(escalation)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def notify_vendor(self, request, pk=None):
        """Send escalation notification to vendor"""
        escalation = self.get_object()
        
        # Mark as notified
        escalation.mark_as_notified(notify_vendor=True)
        
        # TODO: Send email notification to vendor
        # notification_service.notify_vendor_escalation(escalation)
        
        serializer = SLAEscalationSerializer(escalation)
        return Response({
            'status': 'vendor_notified',
            'escalation': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def notify_pt(self, request, pk=None):
        """Send escalation notification to production team"""
        escalation = self.get_object()
        
        # Mark as notified
        escalation.mark_as_notified(notify_pt=True)
        
        # TODO: Send internal notification to PT
        # notification_service.notify_pt_escalation(escalation)
        
        serializer = SLAEscalationSerializer(escalation)
        return Response({
            'status': 'pt_notified',
            'escalation': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def escalate_level(self, request, pk=None):
        """Escalate to next level"""
        escalation = self.get_object()
        
        level_mapping = {
            'level_1': 'level_2',
            'level_2': 'level_3',
            'level_3': 'level_3'  # Already at max
        }
        
        next_level = level_mapping.get(escalation.escalation_level, escalation.escalation_level)
        escalation.escalation_level = next_level
        escalation.escalation_notes = request.data.get('notes', '')
        escalation.save()
        
        serializer = SLAEscalationSerializer(escalation)
        return Response({
            'status': 'escalation_level_increased',
            'escalation': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark escalation as resolved"""
        escalation = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        escalation.resolve(
            resolution_notes=resolution_notes,
            resolved_by=request.user
        )
        
        serializer = SLAEscalationSerializer(escalation)
        return Response({
            'status': 'escalation_resolved',
            'escalation': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending escalations"""
        escalations = SLAEscalation.objects.filter(
            escalation_status__in=['pending', 'notified']
        ).order_by('-escalated_at')
        
        # Filter by level if provided
        level = request.query_params.get('level')
        if level:
            escalations = escalations.filter(escalation_level=level)
        
        # Filter by vendor if provided
        vendor_id = request.query_params.get('vendor_id')
        if vendor_id:
            escalations = escalations.filter(purchase_order__vendor_id=vendor_id)
        
        serializer = SLAEscalationSerializer(escalations, many=True)
        return Response({
            'count': escalations.count(),
            'escalations': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def critical(self, request):
        """Get all critical escalations (Level 3 or > 7 days overdue)"""
        from django.db.models import Q
        
        escalations = SLAEscalation.objects.filter(
            Q(escalation_level='level_3') | Q(days_overdue__gt=7)
        ).filter(
            escalation_status__in=['pending', 'notified']
        ).order_by('-days_overdue', '-escalated_at')
        
        serializer = SLAEscalationSerializer(escalations, many=True)
        return Response({
            'count': escalations.count(),
            'critical_escalations': serializer.data
        })
    
    @action(detail=False, methods=['post'])
    def check_and_escalate(self, request):
        """Auto-escalate overdue jobs based on days overdue"""
        from django.db.models import Q
        
        now = timezone.now().date()
        escalated_count = 0
        
        # Get all overdue active POs without active escalations
        overdue_pos = PurchaseOrder.objects.filter(
            due_date__lt=now,
            status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
        ).exclude(
            sla_escalations__escalation_status__in=['pending', 'notified']
        )
        
        for po in overdue_pos:
            days_overdue = (now - po.due_date).days
            
            # Determine escalation level
            if days_overdue >= 14:
                level = 'level_3'
                reason = f'Job overdue by {days_overdue} days - Critical escalation'
            elif days_overdue >= 7:
                level = 'level_2'
                reason = f'Job overdue by {days_overdue} days - PT review required'
            else:
                level = 'level_1'
                reason = f'Job overdue by {days_overdue} days - Vendor alert'
            
            # Create escalation
            escalation = SLAEscalation.objects.create(
                purchase_order=po,
                escalation_level=level,
                original_deadline=po.due_date,
                current_deadline=po.due_date,
                days_overdue=days_overdue,
                escalation_reason=reason,
                escalated_by=request.user
            )
            escalated_count += 1
        
        return Response({
            'status': 'auto_escalation_complete',
            'escalated_count': escalated_count,
            'message': f'Escalated {escalated_count} overdue jobs'
        })


class ProgressUpdateBatchViewSet(viewsets.ModelViewSet):
    """ViewSet for batch progress updates from vendors"""
    queryset = ProgressUpdateBatch.objects.all()
    serializer_class = ProgressUpdateBatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by purchase order if provided"""
        qs = ProgressUpdateBatch.objects.all()
        po_id = self.request.query_params.get('purchase_order_id')
        if po_id:
            qs = qs.filter(purchase_order_id=po_id)
        return qs
    
    @action(detail=False, methods=['post'])
    def submit_update(self, request):
        """Submit a progress update for a purchase order"""
        po_id = request.data.get('purchase_order_id')
        percentage = request.data.get('percentage_complete')
        status = request.data.get('status', 'on_track')
        description = request.data.get('description', '')
        
        try:
            po = PurchaseOrder.objects.get(id=po_id)
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Purchase order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        update = ProgressUpdateBatch.objects.create(
            purchase_order=po,
            submitted_by=request.user,
            percentage_complete=percentage,
            status=status,
            description=description,
            notes=request.data.get('notes', '')
        )
        
        serializer = ProgressUpdateBatchSerializer(update)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def latest_by_po(self, request):
        """Get latest update for each PO"""
        from django.db.models import Max
        po_id = request.query_params.get('purchase_order_id')
        
        if po_id:
            latest = ProgressUpdateBatch.objects.filter(purchase_order_id=po_id).latest('submission_date')
            serializer = ProgressUpdateBatchSerializer(latest)
            return Response(serializer.data)
        
        return Response({'error': 'purchase_order_id required'}, status=status.HTTP_400_BAD_REQUEST)


class QCProofLinkViewSet(viewsets.ModelViewSet):
    """ViewSet for QC-Proof links"""
    queryset = QCProofLink.objects.all()
    serializer_class = QCProofLinkSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['post'])
    def link_qc_to_proof(self, request):
        """Link QC inspection to proof"""
        qc_id = request.data.get('qc_inspection_id')
        proof_id = request.data.get('proof_id')
        qc_status = request.data.get('qc_status')
        
        try:
            qc = QCInspection.objects.get(id=qc_id)
            proof = PurchaseOrderProof.objects.get(id=proof_id)
        except (QCInspection.DoesNotExist, PurchaseOrderProof.DoesNotExist):
            return Response({'error': 'QC or proof not found'}, status=status.HTTP_404_NOT_FOUND)
        
        link, created = QCProofLink.objects.get_or_create(
            qc_inspection=qc,
            proof=proof,
            defaults={
                'qc_status': qc_status,
                'qc_notes': request.data.get('qc_notes', '')
            }
        )
        
        # If QC failed, auto-hold invoice
        if qc_status == 'failed':
            po = proof.purchase_order
            try:
                invoice = po.vendor_invoices.last()
                if invoice and not hasattr(invoice, 'hold'):
                    InvoiceHold.objects.create(
                        invoice=invoice,
                        hold_reason='qc_failed',
                        hold_details=f'QC failed for {po.po_number}',
                        held_by=request.user
                    )
                    link.auto_held_invoice = True
                    link.hold_reason = 'QC failed'
                    link.save()
            except:
                pass
        
        serializer = QCProofLinkSerializer(link)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def calculate_vps_impact(self, request, pk=None):
        """Calculate VPS impact from QC result"""
        link = self.get_object()
        
        if link.qc_status == 'failed':
            adjustment = -5  # Default 5 point deduction
            vendor = link.proof.purchase_order.vendor
            
            log = VPSRecalculationLog.objects.create(
                vendor=vendor,
                trigger_type='qc_fail',
                previous_score=vendor.performance_score,
                new_score=max(0, vendor.performance_score + adjustment),
                score_change=adjustment,
                reason=f'QC failed for {link.proof.purchase_order.po_number}',
                reference_id=str(link.qc_inspection.id),
                recalculated_by=request.user
            )
            
            vendor.performance_score = log.new_score
            vendor.save()
            
            link.vps_impact_calculated = True
            link.vps_score_adjustment = adjustment
            link.save()
            
            serializer = QCProofLinkSerializer(link)
            return Response({'status': 'vps_impact_calculated', 'link': serializer.data})
        
        return Response({'error': 'Only failed QC results impact VPS'}, status=status.HTTP_400_BAD_REQUEST)


class VPSRecalculationViewSet(viewsets.ModelViewSet):
    """ViewSet for VPS recalculation"""
    queryset = VPSRecalculationLog.objects.all()
    serializer_class = VPSRecalculationLogSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['post'])
    def recalculate_vendor_vps(self, request):
        """Manually recalculate vendor VPS"""
        vendor_id = request.data.get('vendor_id')
        reason = request.data.get('reason', 'Manual recalculation')
        
        try:
            vendor = Vendor.objects.get(id=vendor_id)
        except Vendor.DoesNotExist:
            return Response({'error': 'Vendor not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Calculate new score based on recent performance
        from django.db.models import Avg
        from datetime import timedelta
        
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_perf = vendor.vendorperformancescore_set.filter(
            updated_at__gte=thirty_days_ago
        ).aggregate(
            avg_on_time=Avg('on_time_percentage'),
            avg_quality=Avg('quality_score'),
            avg_comm=Avg('communication_score')
        )
        
        new_score = (
            (recent_perf['avg_on_time'] or 0) * 0.4 +
            (recent_perf['avg_quality'] or 0) * 0.4 +
            (recent_perf['avg_comm'] or 0) * 0.2
        )
        
        old_score = vendor.performance_score
        change = new_score - old_score
        
        log = VPSRecalculationLog.objects.create(
            vendor=vendor,
            trigger_type='manual',
            previous_score=old_score,
            new_score=new_score,
            score_change=change,
            reason=reason,
            recalculated_by=request.user
        )
        
        vendor.performance_score = new_score
        vendor.save()
        
        serializer = VPSRecalculationLogSerializer(log)
        return Response(serializer.data)


class CustomerNotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for customer substitution notifications"""
    queryset = CustomerNotification.objects.all()
    serializer_class = CustomerNotificationSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['post'])
    def send_notification(self, request):
        """Send customer notification for substitution"""
        sub_id = request.data.get('substitution_id')
        method = request.data.get('method', 'email')
        
        try:
            sub = MaterialSubstitutionApproval.objects.get(id=sub_id)
        except MaterialSubstitutionApproval.DoesNotExist:
            return Response({'error': 'Substitution not found'}, status=status.HTTP_404_NOT_FOUND)
        
        message = f"""
        Material Substitution Notification
        
        Purchase Order: {sub.purchase_order.po_number}
        Original Material: {sub.original_material}
        Substitute Material: {sub.substitute_material}
        Reason: {sub.reason}
        
        Cost Impact: ${sub.cost_difference}
        Status: Approved by Production Team
        """
        
        notification = CustomerNotification.objects.create(
            substitution=sub,
            notification_method=method,
            recipient_email=sub.purchase_order.client_email if hasattr(sub.purchase_order, 'client_email') else '',
            message=message,
            subject=f'Material Substitution Approved - {sub.purchase_order.po_number}'
        )
        
        # TODO: Send actual email/SMS
        notification.status = 'sent'
        notification.sent_at = timezone.now()
        notification.save()
        
        sub.customer_notified = True
        sub.customer_notified_at = timezone.now()
        sub.save()
        
        serializer = CustomerNotificationSerializer(notification)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_acknowledged(self, request, pk=None):
        """Mark notification as acknowledged by customer"""
        notification = self.get_object()
        notification.acknowledged_at = timezone.now()
        notification.status = 'acknowledged'
        notification.save()
        
        serializer = CustomerNotificationSerializer(notification)
        return Response(serializer.data)


class DeadlineCalculationViewSet(viewsets.ModelViewSet):
    """ViewSet for deadline calculations"""
    queryset = DeadlineCalculation.objects.all()
    serializer_class = DeadlineCalculationSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam]
    
    @action(detail=False, methods=['post'])
    def calculate_deadline(self, request):
        """Calculate deadline for a PO"""
        po_id = request.data.get('purchase_order_id')
        
        try:
            po = PurchaseOrder.objects.get(id=po_id)
        except PurchaseOrder.DoesNotExist:
            return Response({'error': 'Purchase order not found'}, status=status.HTTP_404_NOT_FOUND)
        
        complexity = request.data.get('job_complexity', 'medium')
        vendor_capacity = request.data.get('vendor_capacity_available', 5)
        sla_days = request.data.get('sla_days', 14)
        
        # Calculate base deadline
        complexity_map = {'low': 3, 'medium': 7, 'high': 14}
        base_days = complexity_map.get(complexity, 7)
        
        # Adjust based on vendor capacity
        adjusted_days = base_days + max(0, (10 - vendor_capacity) * 0.5)
        
        # Calculate risk score
        risk_score = min(100, (adjusted_days / sla_days) * 100)
        
        calc, created = DeadlineCalculation.objects.update_or_create(
            purchase_order=po,
            defaults={
                'job_complexity': complexity,
                'vendor_capacity_available': vendor_capacity,
                'sla_days': sla_days,
                'base_deadline': int(base_days),
                'adjusted_deadline': int(adjusted_days),
                'risk_score': int(risk_score),
                'calculation_notes': f'Complexity: {complexity}, Vendor capacity: {vendor_capacity} days available'
            }
        )
        
        # Update PO due date if needed
        from datetime import timedelta
        new_due_date = timezone.now() + timedelta(days=int(adjusted_days))
        po.due_date = new_due_date
        po.save()
        
        serializer = DeadlineCalculationSerializer(calc)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Vendor, PurchaseOrder, ActivityLog, VendorInvoice

@login_required
def vendor_invoices(request):
    """Display list of vendor invoices"""
    try:
        vendor = request.user.vendor_profile
    except:
        return redirect('vendor_portal')
    
    # Get invoices for this vendor
    invoices = VendorInvoice.objects.filter(
        purchase_order__vendor_stage__vendor=vendor
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        invoices = invoices.filter(status=status)
    
    context = {
        'invoices': invoices,
        'status_filter': status,
        'vendor': vendor,
    }
    return render(request, 'vendor/invoices_list.html', context)

@login_required
def vendor_create_invoice(request):
    """Create new invoice - vendor"""
    try:
        vendor = request.user.vendor_profile
    except:
        return redirect('vendor_portal')
    
    context = {
        'vendor': vendor,
    }
    return render(request, 'vendor/invoice_create.html', context)

@login_required
def vendor_substitutions(request):
    """List vendor's material substitution requests"""
    try:
        vendor = request.user.vendor_profile
    except:
        return redirect('vendor_portal')
    
    # Get substitution requests for this vendor's purchase orders
    substitutions = MaterialSubstitutionRequest.objects.filter(
        purchase_order__vendor_stage__vendor=vendor
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        substitutions = substitutions.filter(status=status)
    
    context = {
        'substitutions': substitutions,
        'status_filter': status,
        'vendor': vendor,
    }
    return render(request, 'vendor/substitutions_list.html', context)

@login_required
def vendor_create_substitution(request):
    """Create new material substitution request - vendor"""
    try:
        vendor = request.user.vendor_profile
    except:
        return redirect('vendor_portal')
    
    # Get open purchase orders for this vendor
    purchase_orders = PurchaseOrder.objects.filter(
        vendor_stage__vendor=vendor,
        status__in=['NEW', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
    )
    
    context = {
        'vendor': vendor,
        'purchase_orders': purchase_orders,
    }
    return render(request, 'vendor/material_substitution_request.html', context)

@login_required
def substitution_dashboard(request):
    """Account manager view for reviewing material substitutions"""
    # Get account manager's clients
    clients = request.user.clients.all()
    
    # Get all substitution requests for these clients' vendors
    substitutions = MaterialSubstitutionRequest.objects.filter(
        purchase_order__job__client__in=clients
    ).order_by('-created_at')
    
    # Calculate stats
    stats = {
        'pending': substitutions.filter(status='pending').count(),
        'approved': substitutions.filter(status='approved').count(),
        'rejected': substitutions.filter(status='rejected').count(),
        'total': substitutions.count(),
    }
    
    context = {
        'requests': substitutions,
        'stats': stats,
    }
    return render(request, 'account_manager/material_substitution_dashboard.html', context)

@login_required
def vendor_dashboard(request):
    """Main vendor dashboard view"""
    # Get the vendor profile for the logged-in user
    try:
        vendor = request.user.vendor_profile
    except Vendor.DoesNotExist:
        # Redirect to profile creation or show error
        return redirect('create_vendor_profile')
    
    # Get all POs for this vendor
    all_pos = PurchaseOrder.objects.filter(vendor=vendor)
    
    # Categorize POs by status
    new_pos = all_pos.filter(status='NEW')
    in_production = all_pos.filter(status='IN_PRODUCTION')
    awaiting_approval = all_pos.filter(status='AWAITING_APPROVAL')
    completed = all_pos.filter(status='COMPLETED').order_by('-completed_at')[:5]
    
    # Calculate at-risk jobs
    now = timezone.now()
    at_risk = []
    
    # Jobs that are overdue
    overdue_pos = all_pos.filter(
        due_date__lt=now,
        status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
    )
    
    # Jobs with no activity in 24 hours
    no_activity_pos = all_pos.filter(
        last_activity_at__lt=now - timedelta(hours=24),
        status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
    ).exclude(id__in=overdue_pos.values_list('id', flat=True))
    
    # Combine at-risk jobs
    at_risk = list(overdue_pos) + list(no_activity_pos)
    
    # Blocked jobs
    blocked_jobs = all_pos.filter(is_blocked=True)
    
    # Calculate counts for urgent actions
    jobs_overdue = overdue_pos.count()
    jobs_at_risk = len(at_risk)
    new_pos_awaiting = new_pos.count()
    
    # Calculate action needed (new POs + overdue + at risk)
    action_needed = new_pos_awaiting + jobs_overdue + jobs_at_risk
    
    # Calculate proofs pending
    proofs_pending = awaiting_approval.count()
    
    # Get upcoming deadlines (within 48 hours)
    upcoming_deadline_time = now + timedelta(hours=48)
    upcoming_deadlines = all_pos.filter(
        due_date__lte=upcoming_deadline_time,
        due_date__gte=now,
        status__in=['ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
    ).order_by('due_date')[:5]
    
    # Get recent activities
    recent_activities = all_pos.order_by('-updated_at')[:5]
    
    # Calculate KPIs
    active_jobs = all_pos.filter(
        status__in=['NEW', 'ACCEPTED', 'IN_PRODUCTION', 'AWAITING_APPROVAL']
    ).count()
    
    # Performance metrics
    completed_pos = all_pos.filter(status='COMPLETED')
    total_completed = completed_pos.count()
    
    if total_completed > 0:
        on_time_jobs = completed_pos.filter(completed_on_time=True).count()
        on_time_rate = round((on_time_jobs / total_completed) * 100, 1)
    else:
        on_time_jobs = 0
        on_time_rate = 0
    
    issues_raised = all_pos.filter(has_issues=True).count()
    
    # Financial metrics
    pending_invoices = VendorInvoice.objects.filter(
        vendor=vendor
    ).exclude(
        status='paid'  
    ).aggregate(
        total=Sum('total_amount')  
    )['total'] or 0
    
    avg_response_time = 3.2  
    
    # Jobs this month
    first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    jobs_this_month = all_pos.filter(created_at__gte=first_day_of_month).count()
    
    context = {
        'vendor': vendor,
        
        # Urgent actions
        'jobs_overdue': jobs_overdue,
        'jobs_at_risk': jobs_at_risk,
        'new_pos_awaiting': new_pos_awaiting,
        
        # PO lists for kanban
        'new_pos': new_pos,
        'new_pos_count': new_pos.count(),
        
        'in_production': in_production,
        'in_production_count': in_production.count(),
        
        'awaiting_approval': awaiting_approval,
        'awaiting_approval_count': awaiting_approval.count(),
        
        'at_risk': at_risk,
        'at_risk_count': len(at_risk),
        
        'completed': completed,
        'completed_count': completed_pos.count(),
        
        # Blocked jobs
        'blocked_jobs': blocked_jobs,
        
        # KPIs
        'performance_score': int(vendor.performance_score),
        'total_completed': total_completed,
        'on_time_rate': on_time_rate,
        'on_time_jobs': on_time_jobs,
        'issues_raised': issues_raised,
        'active_jobs': active_jobs,
        'action_needed': action_needed,
        'proofs_pending': proofs_pending,
        'pending_invoices': pending_invoices,
        'avg_response_time': avg_response_time,
        'jobs_this_month': jobs_this_month,
        
        # Right panel
        'upcoming_deadlines': upcoming_deadlines,
        'recent_activities': recent_activities,
    }
    
    return render(request, 'vendor/dashboard.html', context)


@login_required
def completed_jobs(request):
    """View for completed jobs listing"""
    try:
        vendor = request.user.vendor_profile
    except Vendor.DoesNotExist:
        return redirect('create_vendor_profile')
    
    completed_pos = PurchaseOrder.objects.filter(
        vendor=vendor,
        status='COMPLETED'
    ).order_by('-completed_at')
    
    # Add filtering and search
    search_query = request.GET.get('search', '')
    if search_query:
        completed_pos = completed_pos.filter(
            Q(po_number__icontains=search_query) |
            Q(product_type__icontains=search_query)
        )
    
    context = {
        'vendor': vendor,
        'completed_jobs': completed_pos,
        'search_query': search_query,
    }
    
    return render(request, 'vendor/completed_jobs.html', context)


@login_required
def invoices(request):
    """View for invoices listing"""
    try:
        vendor = request.user.vendor_profile
    except Vendor.DoesNotExist:
        return redirect('create_vendor_profile')
    
    all_invoices = Invoice.objects.filter(vendor=vendor).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'paid':
        all_invoices = all_invoices.filter(is_paid=True)
    elif status_filter == 'pending':
        all_invoices = all_invoices.filter(is_paid=False)
    
    # Calculate totals
    total_pending = Invoice.objects.filter(
        vendor=vendor,
        is_paid=False
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_paid = Invoice.objects.filter(
        vendor=vendor,
        is_paid=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    context = {
        'vendor': vendor,
        'invoices': all_invoices,
        'status_filter': status_filter,
        'total_pending': total_pending,
        'total_paid': total_paid,
    }
    
    return render(request, 'vendor/invoices.html', context)


@login_required
def performance(request):
    """View for performance metrics"""
    try:
        vendor = request.user.vendor_profile
    except Vendor.DoesNotExist:
        return redirect('create_vendor_profile')
    
    all_pos = PurchaseOrder.objects.filter(vendor=vendor)
    completed_pos = all_pos.filter(status='COMPLETED')
    
    # Calculate detailed metrics
    total_completed = completed_pos.count()
    on_time_jobs = completed_pos.filter(completed_on_time=True).count()
    late_jobs = total_completed - on_time_jobs
    
    on_time_rate = round((on_time_jobs / total_completed * 100), 1) if total_completed > 0 else 0
    
    # Issues tracking
    jobs_with_issues = all_pos.filter(has_issues=True).count()
    
    # Monthly performance (last 6 months)
    monthly_data = []
    now = timezone.now()
    
    for i in range(6):
        month_start = (now - timedelta(days=30*i)).replace(day=1, hour=0, minute=0, second=0)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
        
        month_jobs = completed_pos.filter(
            completed_at__gte=month_start,
            completed_at__lte=month_end
        )
        
        monthly_data.append({
            'month': month_start.strftime('%B'),
            'total': month_jobs.count(),
            'on_time': month_jobs.filter(completed_on_time=True).count(),
        })
    
    monthly_data.reverse()
    
    context = {
        'vendor': vendor,
        'performance_score': int(vendor.performance_score),
        'total_completed': total_completed,
        'on_time_jobs': on_time_jobs,
        'late_jobs': late_jobs,
        'on_time_rate': on_time_rate,
        'jobs_with_issues': jobs_with_issues,
        'monthly_data': monthly_data,
    }
    
    return render(request, 'vendor/performance.html', context)


@login_required
def accept_po(request, po_id):
    """Accept a purchase order"""
    po = get_object_or_404(PurchaseOrder, id=po_id, vendor=request.user.vendor_profile)
    
    if po.accept_order():
        # Log activity
        ActivityLog.objects.create(
            purchase_order=po,
            activity_type='ORDER_ACCEPTED',
            description=f'Order {po.po_number} accepted by vendor',
            created_by=request.user
        )
    
    return redirect('vendor_dashboard')


@login_required
def decline_po(request, po_id):
    """Decline a purchase order"""
    po = get_object_or_404(PurchaseOrder, id=po_id, vendor=request.user.vendor_profile)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        po.status = 'CANCELLED'
        po.save()
        
        ActivityLog.objects.create(
            purchase_order=po,
            activity_type='STATUS_CHANGE',
            description=f'Order {po.po_number} declined. Reason: {reason}',
            created_by=request.user
        )
        
        return redirect('vendor_dashboard')
    
    return render(request, 'vendor/decline_po.html', {'po': po})


@login_required
def view_po_detail(request, po_id):
    """View purchase order details"""
    po = get_object_or_404(PurchaseOrder, id=po_id, vendor=request.user.vendor_profile)
    activities = po.activities.all()[:10]
    proofs = po.proofs.all()
    
    context = {
        'vendor': request.user.vendor_profile,
        'po': po,
        'activities': activities,
        'proofs': proofs,
    }
    
    return render(request, 'vendor/po_detail.html', context)

@login_required
def active_jobs(request):
    # Change VendorProfile to Vendor
    vendor = get_object_or_404(Vendor, user=request.user)
    jobs = PurchaseOrder.objects.filter(
        vendor=vendor
    ).exclude(status__in=['completed', 'cancelled'])
    
    return render(request, 'vendor/active_jobs.html', {
        'active_jobs': jobs,
        'current_view': 'active_jobs'
    })

@login_required
def completed_jobs(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    jobs = PurchaseOrder.objects.filter(vendor=vendor, status='completed')
    return render(request, 'vendor/completed_jobs.html', {
        'completed_jobs': jobs,
        'current_view': 'completed_jobs'
    })

@login_required
def invoices(request):
    vendor = get_object_or_404(Vendor, user=request.user)
    
    if request.method == 'POST':
        po_id = request.POST.get('po_id')
        po = get_object_or_404(PurchaseOrder, id=po_id, vendor=vendor)
        
        # Create invoice logic
        VendorInvoice.objects.create(
            purchase_order=po,
            vendor=vendor,
            job=po.job,
            subtotal=po.total_cost,
            total_amount=po.total_cost,
            due_date=timezone.now().date() + timezone.timedelta(days=30)
        )
        messages.success(request, f"Invoice generated for {po.po_number}")
        return redirect('invoices')

    invoices = VendorInvoice.objects.filter(vendor=vendor)
    ready_for_invoice = PurchaseOrder.objects.filter(
    vendor=vendor, 
    status='COMPLETED' 
    ).exclude(vendor_invoices__isnull=False)  
    
    return render(request, 'vendor/invoices.html', {
        'invoices': invoices,
        'ready_for_invoice': ready_for_invoice,
        'current_view': 'invoices'
    })

@login_required
def performance(request):
    return render(request, 'vendor/performance.html', {
        'on_time_rate': 95,
        'quality_score': 98,
        'avg_turnaround': 4.2,
        'current_view': 'performance'
    })

@login_required
def vendor_proofs(request):
    """QC Proofs page for vendors"""
    vendor = get_object_or_404(Vendor, user=request.user)
    
    proofs = PurchaseOrderProof.objects.filter(
        purchase_order__vendor=vendor
    ).select_related('purchase_order', 'uploaded_by').order_by('-created_at')
    
    return render(request, 'vendor/proofs_complete.html', {
        'proofs': proofs,
        'vendor': vendor,
        'current_view': 'proofs'
    })

@login_required
def accept_job(request, po_number):
    po = get_object_or_404(PurchaseOrder, po_number=po_number)
    po.vendor_accepted = True
    po.vendor_accepted_at = timezone.now()
    po.status = 'in_production'
    po.milestone = 'in_production'
    po.save()
    messages.success(request, f"Job {po_number} accepted.")
    return redirect('vendor_dashboard')

@login_required
def decline_job(request, po_number):
    po = get_object_or_404(PurchaseOrder, po_number=po_number)
    po.status = 'cancelled'
    po.save()
    messages.warning(request, f"Job {po_number} declined.")
    return redirect('vendor_dashboard')


@login_required
def client_portal_spa(request):
    """
    Serve the Client Portal SPA (Single Page Application)
    This view is protected with @login_required to ensure authentication
    Accessible to clients to view orders, messages, proofs, and analytics
    """
    # Check if user is a client portal user
    try:
        portal_user = request.user.client_portal_user
        client = portal_user.client
    except ClientPortalUser.DoesNotExist:
        messages.error(request, 'Your account is not linked to a client portal.')
        return redirect('login_redirect')
    
    # Render the SPA template
    from django.template.response import TemplateResponse
    return TemplateResponse(request, 'client/client_portal_spa.html', {
        'client': client,
        'portal_user': portal_user,
        'client_name': client.name,
        'company_name': client.company,
        'user': request.user
    })


@login_required
def vendor_portal_spa(request):
    """
    Serve the Vendor Portal SPA (Single Page Application)
    This view is protected with @login_required to ensure authentication
    """
    # Check if user belongs to a vendor
    try:
        vendor = request.user.vendor_profile
    except Vendor.DoesNotExist:
        messages.error(request, 'Your account is not linked to a vendor profile.')
        return redirect('vendor_dashboard')
    
    # Render the SPA template
    from django.template.response import TemplateResponse
    return TemplateResponse(request, 'vendor/vendor_portal_spa.html', {
        'vendor': vendor,
        'vendor_name': vendor.name,
        'user': request.user
    })


def vendor_invite_accept(request, token):
    company_name = getattr(settings, 'COMPANY_NAME', 'PrintDuka')
    user_id = cache.get(f'vendor_invite_{token}')

    if not user_id:
        return render(request, 'vendor/vendor_invite_accept.html', {
            'company_name': company_name,
            'valid': False,
        })

    user = get_object_or_404(User, id=user_id)
    vendor = getattr(user, 'vendor_profile', None)
    vendor_name = vendor.name if vendor else 'Vendor'
    contact_person = vendor.contact_person if vendor and vendor.contact_person else vendor_name

    if request.method == 'POST':
        password = request.POST.get('password', '')
        password_confirm = request.POST.get('password_confirm', '')

        if not password or password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        else:
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                messages.error(request, ' '.join(exc.messages))
            else:
                user.set_password(password)
                user.is_active = True
                user.save()
                cache.delete(f'vendor_invite_{token}')
                login(request, user)
                from django.conf import settings as django_settings
                return redirect(f'{django_settings.FRONTEND_URL}/vendors')

    return render(request, 'vendor/vendor_invite_accept.html', {
        'company_name': company_name,
        'valid': True,
        'vendor_name': vendor_name,
        'contact_person': contact_person,
    })


# ==================== MAILGUN WEBHOOKS ====================

import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

@csrf_exempt
@require_http_methods(["POST"])
def mailgun_webhook(request):
    """
    Handle Mailgun webhook events for quote email tracking
    
    Events handled:
    - opened: Email was opened by recipient
    - clicked: Email link was clicked by recipient
    - delivered: Email was delivered successfully
    - failed: Email delivery failed
    
    Requires custom variables to be sent with email:
    - v:quote_id: Quote ID in database
    - v:quote_number: Quote number for logging
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # Parse webhook data
        if request.POST:
            data = request.POST.dict()
        else:
            try:
                data = json.loads(request.body)
            except:
                data = {}
        
        # Get event details
        event_type = data.get('event')
        custom_vars = data.get('custom-variables', {})
        quote_id = custom_vars.get('quote_id')
        quote_number = custom_vars.get('quote_number', 'Unknown')
        
        logger.info(f"📩 Mailgun Webhook: event_type={event_type}, quote_id={quote_id}")
        
        # Webhooks without quote_id are not for us
        if not quote_id:
            logger.debug(f"Webhook received but no quote_id, ignoring")
            return JsonResponse({'status': 'ok'})
        
        # Get quote from database
        try:
            from .models import Quote
            quote = Quote.objects.get(id=quote_id)
        except Quote.DoesNotExist:
            logger.warning(f"Quote {quote_id} not found in database")
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            logger.error(f"Error fetching quote: {e}")
            return JsonResponse({'status': 'ok'})
        
        # Handle event types
        if event_type == 'opened':
            recipient = data.get('recipient', 'unknown')
            logger.info(f"📬 Quote {quote_number} opened by {recipient}")
            
            try:
                quote.email_opened = True
                quote.email_opened_at = timezone.now()
                quote.email_opened_by = recipient
                quote.save()
                logger.info(f"✅ Updated quote {quote_number}: marked as opened")
            except Exception as e:
                logger.error(f"Error updating quote: {e}")
        
        elif event_type == 'clicked':
            url = data.get('url', '')
            logger.info(f"🔗 Link clicked in quote {quote_number}: {url}")
            
            try:
                quote.email_clicked = True
                quote.email_clicked_at = timezone.now()
                quote.email_clicked_url = url
                quote.save()
                logger.info(f"✅ Updated quote {quote_number}: marked as clicked")
            except Exception as e:
                logger.error(f"Error updating quote: {e}")
        
        elif event_type == 'delivered':
            logger.info(f"✅ Quote {quote_number} delivered")
            
            try:
                quote.email_delivered = True
                quote.email_delivered_at = timezone.now()
                quote.save()
                logger.info(f"✅ Updated quote {quote_number}: marked as delivered")
            except Exception as e:
                logger.error(f"Error updating quote: {e}")
        
        elif event_type == 'failed':
            reason = data.get('description', 'Unknown reason')
            logger.error(f"❌ Quote {quote_number} delivery failed: {reason}")
            
            try:
                quote.email_failed = True
                quote.email_failed_reason = reason
                quote.save()
                logger.error(f"✅ Updated quote {quote_number}: marked as failed")
                
                # TODO: Send notification to AM about failed delivery
            except Exception as e:
                logger.error(f"Error updating quote: {e}")
        
        # Always return OK to Mailgun
        return JsonResponse({'status': 'ok'})
    
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Mailgun webhook error: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ============================================================================
# 🎯 PRODUCTION TEAM DASHBOARD - Gap 6.1 Implementation
# ============================================================================

@login_required
def production_team_dashboard(request):
    """
    Production Team dashboard with job overview and metrics.
    Shows PT user their assigned jobs, upcoming deadlines, vendor workload, etc.
    """
    from django.db.models import Q, Count, Sum, Avg
    from django.utils import timezone
    from datetime import timedelta, date
    
    # Check if user is in Production Team
    if not request.user.groups.filter(name='Production Team').exists() and not request.user.is_staff:
        return render(request, '403.html', {'message': 'Access denied. Production Team only.'}, status=403)
    
    # Get current user's jobs
    my_jobs = Job.objects.filter(person_in_charge=request.user).select_related('client', 'quote')
    
    # Status breakdown
    status_counts = {
        'pending': my_jobs.filter(status='pending').count(),
        'in_progress': my_jobs.filter(status='in_progress').count(),
        'on_hold': my_jobs.filter(status='on_hold').count(),
        'completed': my_jobs.filter(status='completed').count(),
        'total': my_jobs.count(),
    }
    
    # Upcoming deadlines (next 7 days)
    today = date.today()
    upcoming = my_jobs.filter(
        Q(expected_completion__gte=today) & Q(expected_completion__lte=today + timedelta(days=7)),
        status__in=['pending', 'in_progress']
    ).order_by('expected_completion')
    
    # Overdue jobs
    overdue = my_jobs.filter(
        expected_completion__lt=today,
        status__in=['pending', 'in_progress']
    ).order_by('expected_completion')
    
    # Jobs by priority
    priority_counts = {
        'high': my_jobs.filter(priority='high', status__in=['pending', 'in_progress']).count(),
        'normal': my_jobs.filter(priority='normal', status__in=['pending', 'in_progress']).count(),
        'urgent': my_jobs.filter(priority='urgent', status__in=['pending', 'in_progress']).count(),
    }
    
    # Vendor stages assigned (getting active vendor work)
    vendor_stages = JobVendorStage.objects.filter(
        status__in=['sent_to_vendor', 'in_production']
    ).select_related('job', 'vendor').order_by('-created_at')[:10]
    
    # Active vendors (who are we working with)
    active_vendors = Vendor.objects.filter(
        job_vendor_stages__status__in=['sent_to_vendor', 'in_production']
    ).distinct().annotate(
        active_stages=Count('job_vendor_stages', filter=Q(job_vendor_stages__status__in=['sent_to_vendor', 'in_production']))
    )[:8]
    
    # Calculate productivity metrics
    completed_this_week = my_jobs.filter(
        status='completed',
        actual_completion__gte=today - timedelta(days=7),
        actual_completion__lte=today
    ).count()
    
    # On-time completion rate
    completed_jobs = my_jobs.filter(status='completed', actual_completion__isnull=False)
    on_time_count = completed_jobs.filter(actual_completion__lte=models.F('expected_completion')).count()
    on_time_rate = (on_time_count / completed_jobs.count() * 100) if completed_jobs.count() > 0 else 0
    
    context = {
        'my_jobs': my_jobs,
        'status_counts': status_counts,
        'priority_counts': priority_counts,
        'upcoming_jobs': upcoming,
        'overdue_jobs': overdue,
        'vendor_stages': vendor_stages,
        'active_vendors': active_vendors,
        'productivity': {
            'completed_this_week': completed_this_week,
            'on_time_rate': round(on_time_rate),
            'total_completed': completed_jobs.count(),
        },
        'page_title': 'Production Team Dashboard',
        'user_name': request.user.get_full_name() or request.user.username,
    }
    
    return render(request, 'production_team_dashboard.html', context)


@login_required
def get_vendor_workload(request, vendor_id):
    """
    API endpoint to get vendor workload and capacity.
    Returns current jobs, capacity, and active stages.
    """
    try:
        vendor = Vendor.objects.get(pk=vendor_id)
        
        return JsonResponse({
            'success': True,
            'vendor': {
                'id': vendor.id,
                'name': vendor.name,
            },
            'workload': {
                'current_jobs': vendor.get_current_workload(),
                'max_capacity': vendor.max_concurrent_jobs,
                'available_capacity': vendor.get_available_capacity(),
                'utilization_percent': vendor.get_workload_percentage(),
                'is_at_capacity': vendor.is_at_capacity(),
            },
            'active_stages': list(
                vendor.job_vendor_stages.filter(
                    status__in=['sent_to_vendor', 'in_production']
                ).values('id', 'job__job_number', 'stage_name', 'status', 'progress')
            )
        })
    except Vendor.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vendor not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting vendor workload: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
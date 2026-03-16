
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta

from django.contrib.auth.models import User

from .models import (
    Client, Lead, Quote, Product, Job, Vendor, JobAttachment,
    Notification, ActivityLog, LPO, Payment, ProductionUpdate,
    ComplianceDocument, BrandAsset
)


@staff_member_required
def admin_dashboard(request):
    """Main admin dashboard view"""
    from .admin_dashboard import (
        get_dashboard_stats, get_order_status_distribution,
        get_sales_performance_trend, get_recent_orders,
        get_active_alerts, get_user_activity_logs
    )
    
    context = {
        'dashboard_stats': get_dashboard_stats(),
        'order_distribution': json.dumps(get_order_status_distribution()),
        'sales_trend': json.dumps(get_sales_performance_trend(months=6), default=str),
        'recent_orders': get_recent_orders(limit=5),
        'active_alerts': get_active_alerts(limit=5),
        'recent_activity': get_user_activity_logs(limit=10),
    }
    return render(request, 'admin/index.html', context)


@staff_member_required
def clients_list(request):
    """Display clients in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Client.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(client_id__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Clients',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/clients_list.html', context)


@staff_member_required
def leads_list(request):
    """Display leads in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    source = request.GET.get('source', '')
    page = request.GET.get('page', 1)
    
    queryset = Lead.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search) |
            Q(lead_id__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    if source:
        queryset = queryset.filter(source=source)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Leads',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'source': source,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/leads_list.html', context)


@staff_member_required
def quotes_list(request):
    """Display quotes in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Quote.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(quote_id__icontains=search) |
            Q(product_name__icontains=search) |
            Q(client__name__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-quote_date')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Quotes',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/quotes_list.html', context)


@staff_member_required
def products_list(request):
    """Display products in Django admin style"""
    search = request.GET.get('q', '')
    category = request.GET.get('category', '')
    page = request.GET.get('page', 1)
    
    queryset = Product.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(product_id__icontains=search) |
            Q(description__icontains=search)
        )
    
    if category:
        queryset = queryset.filter(product_category=category)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Products',
        'page_obj': page_obj,
        'search': search,
        'category': category,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/products_list.html', context)


@staff_member_required
def jobs_list(request):
    """Display jobs in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Job.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(job_number__icontains=search) |
            Q(quote__quote_id__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(job_status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Jobs',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/jobs_list.html', context)


@staff_member_required
def vendors_list(request):
    """Display vendors in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Vendor.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(vendor_name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(is_active=status == 'active')
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Vendors',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/vendors_list.html', context)


@staff_member_required
def processes_list(request):
    """Display processes in Django admin style"""
    search = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    
    queryset = Process.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(process_name__icontains=search) |
            Q(description__icontains=search)
        )
    
    queryset = queryset.order_by('process_name')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Processes',
        'page_obj': page_obj,
        'search': search,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/processes_list.html', context)


@staff_member_required
def qc_list(request):
    """Display QC inspections in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = ProductionUpdate.objects.filter(update_type='qc')
    
    if search:
        queryset = queryset.filter(
            Q(job__job_number__icontains=search) |
            Q(quote__quote_id__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Quality Control',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/qc_list.html', context)


@staff_member_required
def deliveries_list(request):
    """Display deliveries in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = ProductionUpdate.objects.filter(update_type='delivery')
    
    if search:
        queryset = queryset.filter(
            Q(job__job_number__icontains=search) |
            Q(quote__quote_id__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Deliveries',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/deliveries_list.html', context)


@staff_member_required
def lpos_list(request):
    """Display LPOs in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = LPO.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(lpo_number__icontains=search) |
            Q(vendor__vendor_name__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'LPOs',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/lpos_list.html', context)


@staff_member_required
def payments_list(request):
    """Display payments in Django admin style"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Payment.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(payment_id__icontains=search) |
            Q(invoice_number__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(payment_status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Payments',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/payments_list.html', context)


@staff_member_required
def analytics_view(request):
    """Display analytics in Django admin style"""
    from .admin_dashboard import (
        get_dashboard_stats, get_sales_performance_trend,
        get_profit_margin_data, get_outstanding_receivables,
        get_payment_collection_rate
    )
    
    context = {
        'title': 'Analytics',
        'dashboard_stats': get_dashboard_stats(),
        'sales_trend': json.dumps(get_sales_performance_trend(months=12), default=str),
        'profit_margins': get_profit_margin_data(),
        'receivables': get_outstanding_receivables(),
        'collection_rate': get_payment_collection_rate(),
    }
    return render(request, 'admin/analytics.html', context)


@staff_member_required
def users_list(request):
    """Display users in Django admin style"""
    search = request.GET.get('q', '')
    is_active = request.GET.get('is_active', '')
    page = request.GET.get('page', 1)
    
    queryset = User.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if is_active:
        queryset = queryset.filter(is_active=is_active == 'true')
    
    queryset = queryset.order_by('-date_joined')
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(page)
    
    context = {
        'title': 'Users',
        'page_obj': page_obj,
        'search': search,
        'is_active': is_active,
        'total_count': queryset.count(),
    }
    return render(request, 'admin/users_list.html', context)


# AJAX API ENDPOINTS FOR CRUD OPERATIONS

@staff_member_required
@require_http_methods(["GET"])
def get_object_detail(request, model_name, object_id):
    """Get object details for modal view"""
    model_map = {
        'client': Client,
        'lead': Lead,
        'quote': Quote,
        'product': Product,
        'job': Job,
        'vendor': Vendor,
        'process': Process,
        'lpo': LPO,
        'payment': Payment,
        'user': User,
    }
    
    Model = model_map.get(model_name)
    if not Model:
        return JsonResponse({'error': 'Invalid model'}, status=400)
    
    try:
        obj = Model.objects.get(pk=object_id)
        data = serialize_object(obj)
        return JsonResponse(data)
    except Model.DoesNotExist:
        return JsonResponse({'error': 'Object not found'}, status=404)


@staff_member_required
@require_http_methods(["POST"])
def create_object(request, model_name):
    """Create a new object"""
    try:
        data = json.loads(request.body)
        model_map = {
            'client': Client,
            'lead': Lead,
            'quote': Quote,
            'product': Product,
            'job': Job,
            'vendor': Vendor,
            'process': Process,
        }
        
        Model = model_map.get(model_name)
        if not Model:
            return JsonResponse({'error': 'Invalid model'}, status=400)
        
        # Create object with provided data
        obj = Model.objects.create(**clean_data(data, Model))
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f'Created {model_name}',
            object_id=obj.pk,
            object_type=model_name
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{model_name.title()} created successfully',
            'id': obj.pk
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@staff_member_required
@require_http_methods(["POST"])
def update_object(request, model_name, object_id):
    """Update an object"""
    try:
        data = json.loads(request.body)
        model_map = {
            'client': Client,
            'lead': Lead,
            'quote': Quote,
            'product': Product,
            'job': Job,
            'vendor': Vendor,
            'process': Process,
        }
        
        Model = model_map.get(model_name)
        if not Model:
            return JsonResponse({'error': 'Invalid model'}, status=400)
        
        obj = Model.objects.get(pk=object_id)
        
        # Update fields
        for key, value in clean_data(data, Model).items():
            setattr(obj, key, value)
        obj.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f'Updated {model_name}',
            object_id=obj.pk,
            object_type=model_name
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{model_name.title()} updated successfully'
        })
    except Model.DoesNotExist:
        return JsonResponse({'error': 'Object not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@staff_member_required
@require_http_methods(["POST"])
def delete_object(request, model_name, object_id):
    """Delete an object"""
    try:
        model_map = {
            'client': Client,
            'lead': Lead,
            'quote': Quote,
            'product': Product,
            'job': Job,
            'vendor': Vendor,
            'process': Process,
        }
        
        Model = model_map.get(model_name)
        if not Model:
            return JsonResponse({'error': 'Invalid model'}, status=400)
        
        obj = Model.objects.get(pk=object_id)
        obj_id = obj.pk
        obj.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            action=f'Deleted {model_name}',
            object_id=obj_id,
            object_type=model_name
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{model_name.title()} deleted successfully'
        })
    except Model.DoesNotExist:
        return JsonResponse({'error': 'Object not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# HELPER FUNCTIONS

def serialize_object(obj):
    """Serialize model object to dict for JSON response"""
    from django.core.serializers import serialize
    import json as json_lib
    
    serialized = serialize('json', [obj])
    return json_lib.loads(serialized)[0]['fields']


def clean_data(data, model):
    """Clean and validate data before saving to model"""
    # Only include fields that exist in the model
    valid_fields = {f.name for f in model._meta.get_fields()}
    return {k: v for k, v in data.items() if k in valid_fields}



#CRUD operations for processes and vendors

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.urls import reverse

from .models import Vendor
from .forms import VendorForm


# ==================== VENDORS CRUD ====================

@staff_member_required
def admin_vendor_detail(request, pk):
    """View/Edit a vendor"""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    if request.method == 'POST':
        form = VendorForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, f'Vendor "{vendor.name}" updated successfully')
            return redirect('admin_vendor_detail', pk=vendor.pk)
    else:
        form = VendorForm(instance=vendor)
    
    context = {
        'object': vendor,
        'form': form,
        'title': f'Edit Vendor: {vendor.name}',
        'model_name': 'vendor',
    }
    return render(request, 'admin/detail_view.html', context)


@staff_member_required
def admin_vendor_add(request):
    """Add a new vendor"""
    if request.method == 'POST':
        form = VendorForm(request.POST)
        if form.is_valid():
            vendor = form.save()
            messages.success(request, f'Vendor "{vendor.name}" created successfully')
            return redirect('admin_vendor_detail', pk=vendor.pk)
    else:
        form = VendorForm()
    
    context = {
        'form': form,
        'title': 'Add Vendor',
        'is_add': True,
        'model_name': 'vendor',
    }
    return render(request, 'admin/detail_view.html', context)


@staff_member_required
def admin_vendor_delete(request, pk):
    """Delete a vendor"""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    if request.method == 'POST':
        vendor_name = vendor.name
        vendor.delete()
        messages.success(request, f'Vendor "{vendor_name}" deleted successfully')
        return redirect('admin_vendors_list')
    
    context = {
        'object': vendor,
        'title': f'Delete Vendor: {vendor.name}',
        'model_name': 'vendor',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== PROCESSES CRUD ====================

@staff_member_required
def admin_process_detail(request, pk):
    """View/Edit a process"""
    process = get_object_or_404(Process, pk=pk)
    
    if request.method == 'POST':
        form = ProcessForm(request.POST, instance=process)
        if form.is_valid():
            form.save()
            messages.success(request, f'Process "{process.process_name}" updated successfully')
            return redirect('admin_process_detail', pk=process.pk)
    else:
        form = ProcessForm(instance=process)
    
    context = {
        'object': process,
        'form': form,
        'title': f'Edit Process: {process.process_name}',
        'model_name': 'process',
    }
    return render(request, 'admin/detail_view.html', context)


@staff_member_required
def admin_process_add(request):
    """Add a new process"""
    if request.method == 'POST':
        form = ProcessForm(request.POST)
        if form.is_valid():
            process = form.save()
            messages.success(request, f'Process "{process.process_name}" created successfully')
            return redirect('admin_process_detail', pk=process.pk)
    else:
        form = ProcessForm()
    
    context = {
        'form': form,
        'title': 'Add Process',
        'is_add': True,
        'model_name': 'process',
    }
    return render(request, 'admin/detail_view.html', context)


@staff_member_required
def admin_process_delete(request, pk):
    """Delete a process"""
    process = get_object_or_404(Process, pk=pk)
    
    if request.method == 'POST':
        process_name = process.process_name
        process.delete()
        messages.success(request, f'Process "{process_name}" deleted successfully')
        return redirect('admin_processes_list')
    
    context = {
        'object': process,
        'title': f'Delete Process: {process.process_name}',
        'model_name': 'process',
    }
    return render(request, 'admin/delete_confirm.html', context)
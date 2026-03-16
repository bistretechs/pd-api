"""
Admin CRUD Operations - Django Admin
Implements full CRUD functionality (List, Detail, Add, Edit, Delete) for each model
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.http import JsonResponse
from django.db.models import Q, Count
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.core.exceptions import PermissionDenied

from .models import (
    Client, Lead, Quote, Product, Job, Vendor, LPO,
    Payment, AuditLog
)
from django.contrib.auth.models import User, Group, Permission
from .forms import (
    ClientForm, LeadForm, QuoteForm, ProductForm, VendorForm,
    LPO_Form, PaymentForm, UserForm, JobForm,
    AdminClientForm, AdminProductForm
)

def log_admin_action(request, action, model_obj, details=''):
    """Helper to create audit log entry"""
    try:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
            
        AuditLog.objects.create(
            user=request.user,
            action=action,
            model_name=model_obj._meta.model_name,
            object_id=str(model_obj.pk),
            object_repr=str(model_obj)[:200],
            details=details,
            ip_address=ip
        )
    except Exception as e:
        # if logging fails, print error message
        print(f"Audit log failed: {e}")


# ==================== CLIENTS ====================

@permission_required('clientapp.view_client', raise_exception=True)
def admin_clients_list(request):
    """Display all clients in admin list view"""
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
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Clients',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_client_add'),
        'model_name': 'client',
    }
    return render(request, 'admin/clients_list.html', context)


@permission_required('clientapp.change_client', raise_exception=True)
def admin_client_detail(request, pk):
    """View/Edit a client"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        form = AdminClientForm(request.POST, instance=client)
        if form.is_valid():
            client = form.save()
            log_admin_action(request, 'UPDATE', client, 'Updated client details')
            messages.success(request, f'Client "{client.name}" updated successfully')
            return redirect('admin_client_detail', pk=client.pk)
    else:
        form = AdminClientForm(instance=client)
    
    context = {
        'object': client,
        'form': form,
        'title': f'Edit Client: {client.name}',
        'model_name': 'client',
        'model_name_plural': 'Clients',
        'list_url': reverse('admin_clients_list'),
        'delete_url': reverse('admin_client_delete', args=[client.pk]),
    }
    return render(request, 'admin/enhanced_form_view.html', context)


@permission_required('clientapp.add_client', raise_exception=True)
def admin_client_add(request):
    """Add a new client"""
    if request.method == 'POST':
        form = AdminClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.onboarded_by = request.user
            client.save()
            log_admin_action(request, 'CREATE', client, 'Created new client')
            messages.success(request, f'Client "{client.name}" created successfully')
            return redirect('admin_client_detail', pk=client.pk)
    else:
        form = AdminClientForm()
    
    context = {
        'form': form,
        'title': 'Add Client',
        'is_add': True,
        'model_name': 'client',
        'model_name_plural': 'Clients',
        'list_url': reverse('admin_clients_list'),
    }
    return render(request, 'admin/enhanced_form_view.html', context)


@permission_required('clientapp.delete_client', raise_exception=True)
def admin_client_delete(request, pk):
    """Delete a client"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        client_name = client.name
        log_admin_action(request, 'DELETE', client, 'Deleted client')
        client.delete()
        messages.success(request, f'Client "{client_name}" deleted successfully')
        return redirect('admin_clients_list')
    
    context = {
        'object': client,
        'title': f'Delete Client: {client.name}',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== LEADS ====================

@permission_required('clientapp.view_lead', raise_exception=True)
def admin_leads_list(request):
    """Display all leads in admin list view"""
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
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Leads',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'source': source,
        'total_count': queryset.count(),
        'add_url': reverse('admin_lead_add'),
        'model_name': 'lead',
    }
    return render(request, 'admin/leads_list.html', context)


@permission_required('clientapp.change_lead', raise_exception=True)
def admin_lead_detail(request, pk):
    """View/Edit a lead"""
    lead = get_object_or_404(Lead, pk=pk)
    
    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            lead = form.save()
            log_admin_action(request, 'UPDATE', lead, 'Updated lead details')
            messages.success(request, f'Lead "{lead.name}" updated successfully')
            return redirect('admin_lead_detail', pk=lead.pk)
    else:
        form = LeadForm(instance=lead)
    
    context = {
        'object': lead,
        'form': form,
        'title': f'Edit Lead: {lead.name}',
        'model_name': 'lead',
        'model_name_plural': 'Leads',
        'list_url': reverse('admin_leads_list'),
        'delete_url': reverse('admin_lead_delete', args=[lead.pk]),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.add_lead', raise_exception=True)
def admin_lead_add(request):
    """Add a new lead"""
    if request.method == 'POST':
        form = LeadForm(request.POST)
        if form.is_valid():
            lead = form.save(commit=False)
            lead.created_by = request.user
            lead.save()
            log_admin_action(request, 'CREATE', lead, 'Created new lead')
            messages.success(request, f'Lead "{lead.name}" created successfully')
            return redirect('admin_lead_detail', pk=lead.pk)
    else:
        form = LeadForm()
    
    context = {
        'form': form,
        'title': 'Add Lead',
        'is_add': True,
        'model_name': 'lead',
        'model_name_plural': 'Leads',
        'list_url': reverse('admin_leads_list'),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.delete_lead', raise_exception=True)
def admin_lead_delete(request, pk):
    """Delete a lead"""
    lead = get_object_or_404(Lead, pk=pk)
    
    if request.method == 'POST':
        lead_name = lead.name
        log_admin_action(request, 'DELETE', lead, 'Deleted lead')
        lead.delete()
        messages.success(request, f'Lead "{lead_name}" deleted successfully')
        return redirect('admin_leads_list')
    
    context = {
        'object': lead,
        'title': f'Delete Lead: {lead.name}',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== QUOTES ====================

@permission_required('clientapp.view_quote', raise_exception=True)
def admin_quotes_list(request):
    """Display all quotes in admin list view"""
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
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Quotes',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_quote_add'),
        'model_name': 'quote',
    }
    return render(request, 'admin/quotes_list.html', context)


@permission_required('clientapp.change_quote', raise_exception=True)
def admin_quote_detail(request, pk):
    """View/Edit a quote"""
    quote = get_object_or_404(Quote, pk=pk)
    
    if request.method == 'POST':
        form = QuoteForm(request.POST, instance=quote)
        if form.is_valid():
            quote = form.save()
            log_admin_action(request, 'UPDATE', quote, 'Updated quote details')
            messages.success(request, f'Quote "{quote.quote_id}" updated successfully')
            return redirect('admin_quote_detail', pk=quote.pk)
    else:
        form = QuoteForm(instance=quote)
    
    context = {
        'object': quote,
        'form': form,
        'title': f'Edit Quote: {quote.quote_id}',
        'model_name': 'quote',
        'model_name_plural': 'Quotes',
        'list_url': reverse('admin_quotes_list'),
        'delete_url': reverse('admin_quote_delete', args=[quote.pk]),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.add_quote', raise_exception=True)
def admin_quote_add(request):
    """Add a new quote"""
    if request.method == 'POST':
        form = QuoteForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.created_by = request.user
            quote.save()
            log_admin_action(request, 'CREATE', quote, 'Created new quote')
            messages.success(request, f'Quote "{quote.quote_id}" created successfully')
            return redirect('admin_quote_detail', pk=quote.pk)
    else:
        form = QuoteForm()
    
    context = {
        'form': form,
        'title': 'Add Quote',
        'is_add': True,
        'model_name': 'quote',
        'model_name_plural': 'Quotes',
        'list_url': reverse('admin_quotes_list'),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.delete_quote', raise_exception=True)
def admin_quote_delete(request, pk):
    """Delete a quote"""
    quote = get_object_or_404(Quote, pk=pk)
    
    if request.method == 'POST':
        quote_id = quote.quote_id
        log_admin_action(request, 'DELETE', quote, 'Deleted quote')
        quote.delete()
        messages.success(request, f'Quote "{quote_id}" deleted successfully')
        return redirect('admin_quotes_list')
    
    context = {
        'object': quote,
        'title': f'Delete Quote: {quote.quote_id}',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== PRODUCTS ====================

@permission_required('clientapp.view_product', raise_exception=True)
def admin_products_list(request):
    """Display all products in admin list view"""
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
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Products',
        'page_obj': page_obj,
        'search': search,
        'category': category,
        'total_count': queryset.count(),
        'add_url': reverse('admin_product_add'),
        'model_name': 'product',
    }
    return render(request, 'admin/products_list.html', context)


@permission_required('clientapp.change_product', raise_exception=True)
def admin_product_detail(request, pk):
    """View/Edit a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        form = AdminProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            log_admin_action(request, 'UPDATE', product, 'Updated product details')
            messages.success(request, f'Product "{product.name}" updated successfully')
            return redirect('admin_product_detail', pk=product.pk)
    else:
        form = AdminProductForm(instance=product)
    
    context = {
        'object': product,
        'form': form,
        'title': f'Edit Product: {product.name}',
        'model_name': 'product',
        'model_name_plural': 'Products',
        'list_url': reverse('admin_products_list'),
        'delete_url': reverse('admin_product_delete', args=[product.pk]),
    }
    return render(request, 'admin/enhanced_form_view.html', context)


@permission_required('clientapp.add_product', raise_exception=True)
def admin_product_add(request):
    """Add a new product"""
    if request.method == 'POST':
        form = AdminProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f'Product "{product.name}" created successfully')
            return redirect('admin_product_detail', pk=product.pk)
    else:
        form = AdminProductForm()
    
    context = {
        'form': form,
        'title': 'Add Product',
        'is_add': True,
        'model_name': 'product',
        'model_name_plural': 'Products',
        'list_url': reverse('admin_products_list'),
    }
    return render(request, 'admin/enhanced_form_view.html', context)


@permission_required('clientapp.delete_product', raise_exception=True)
def admin_product_delete(request, pk):
    """Delete a product"""
    product = get_object_or_404(Product, pk=pk)
    
    if request.method == 'POST':
        product_name = product.name
        log_admin_action(request, 'DELETE', product, 'Deleted product')
        product.delete()
        messages.success(request, f'Product "{product_name}" deleted successfully')
        return redirect('admin_products_list')
    
    context = {
        'object': product,
        'title': f'Delete Product: {product.name}',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== JOBS ====================

@permission_required('clientapp.view_job', raise_exception=True)
def admin_jobs_list(request):
    """Display all jobs in admin list view"""
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
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Jobs',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_job_add'),
        'model_name': 'job',
    }
    return render(request, 'admin/jobs_list.html', context)


@permission_required('clientapp.add_job', raise_exception=True)
def admin_job_add(request):
    """Add a new job"""
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            job.save()
            log_admin_action(request, 'CREATE', job, 'Created new job')
            messages.success(request, f'Job "{job.job_number}" created successfully')
            return redirect('admin_jobs_list')
    else:
        form = JobForm()
    
    context = {
        'form': form,
        'title': 'Add Job',
        'is_add': True,
        'model_name': 'job',
        'model_name_plural': 'Jobs',
        'list_url': reverse('admin_jobs_list'),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.change_job', raise_exception=True)
def admin_job_detail(request, pk):
    """View/Edit a job"""
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        form = JobForm(request.POST, request.FILES, instance=job)
        if form.is_valid():
            job = form.save()
            log_admin_action(request, 'UPDATE', job, 'Updated job details')
            messages.success(request, f'Job "{job.job_number}" updated successfully')
            return redirect('admin_jobs_list')
    else:
        form = JobForm(instance=job)
    
    context = {
        'form': form,
        'object': job,
        'title': f'Edit Job: {job.job_number}',
        'is_add': False,
        'model_name': 'job',
        'model_name_plural': 'Jobs',
        'list_url': reverse('admin_jobs_list'),
        'delete_url': reverse('admin_job_delete', args=[job.pk]),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.delete_job', raise_exception=True)
def admin_job_delete(request, pk):
    """Delete a job"""
    job = get_object_or_404(Job, pk=pk)
    
    if request.method == 'POST':
        job_number = job.job_number
        log_admin_action(request, 'DELETE', job, 'Deleted job')
        job.delete()
        messages.success(request, f'Job "{job_number}" deleted successfully')
        return redirect('admin_jobs_list')
    
    context = {
        'object': job,
        'title': f'Delete Job: {job.job_number}',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== VENDORS ====================

@permission_required('clientapp.view_vendor', raise_exception=True)
def admin_vendors_list(request):
    """Display all vendors in admin list view"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Vendor.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(name__icontains=search) |
            Q(email__icontains=search) |
            Q(phone__icontains=search)
        )
    
    if status == 'active':
        queryset = queryset.filter(active=True)
    elif status == 'inactive':
        queryset = queryset.filter(active=False)
    
    queryset = queryset.order_by('name')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Vendors',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_vendor_add'),
        'model_name': 'vendor',
    }
    return render(request, 'admin/vendors_list.html', context)


@permission_required('clientapp.add_vendor', raise_exception=True)
def admin_vendor_add(request):
    """Add a new vendor"""
    if request.method == 'POST':
        form = VendorForm(request.POST, request.FILES)
        if form.is_valid():
            vendor = form.save()
            log_admin_action(request, 'CREATE', vendor, 'Created new vendor')
            messages.success(request, f'Vendor "{vendor.name}" created successfully')
            return redirect('admin_vendors_list')
    else:
        form = VendorForm()
    
    context = {
        'form': form,
        'title': 'Add Vendor',
        'is_add': True,
        'model_name': 'vendor',
        'model_name_plural': 'Vendors',
        'list_url': reverse('admin_vendors_list'),
    }
    return render(request, 'admin/form_view.html', context)


@permission_required('clientapp.change_vendor', raise_exception=True)
def admin_vendor_detail(request, pk):
    """View/Edit a vendor"""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    if request.method == 'POST':
        form = VendorForm(request.POST, request.FILES, instance=vendor)
        if form.is_valid():
            vendor = form.save()
            log_admin_action(request, 'UPDATE', vendor, 'Updated vendor details')
            messages.success(request, f'Vendor "{vendor.name}" updated successfully')
            return redirect('admin_vendors_list')
    else:
        form = VendorForm(instance=vendor)
    
    context = {
        'form': form,
        'object': vendor,
        'title': f'Edit Vendor: {vendor.name}',
        'is_add': False,
        'model_name': 'vendor',
        'model_name_plural': 'Vendors',
        'list_url': reverse('admin_vendors_list'),
        'delete_url': reverse('admin_vendor_delete', args=[vendor.pk]),
    }
    return render(request, 'admin/form_view.html', context)



@permission_required('clientapp.delete_vendor', raise_exception=True)
def admin_vendor_delete(request, pk):
    """Delete a vendor"""
    vendor = get_object_or_404(Vendor, pk=pk)
    
    if request.method == 'POST':
        vendor_name = vendor.name
        log_admin_action(request, 'DELETE', vendor, 'Deleted vendor')
        vendor.delete()
        messages.success(request, f'Vendor "{vendor_name}" deleted successfully')
        return redirect('admin_vendors_list')
    
    context = {
        'object': vendor,
        'title': f'Delete Vendor: {vendor.name}',
    }
    return render(request, 'admin/delete_confirm.html', context)



# ==================== PROCESSES ====================

@permission_required('clientapp.view_process', raise_exception=True)
def admin_processes_list(request):
    """Display all processes in admin list view"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Process.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(process_code__icontains=search) |
            Q(process_name__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(is_active=status.lower() == 'active')
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Processes',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_process_add'),
        'model_name': 'process',
    }
    return render(request, 'admin/processes_list.html', context)


@permission_required('clientapp.change_process', raise_exception=True)
def admin_process_detail(request, pk):
    """View/Edit a process"""
    process = get_object_or_404(Process, pk=pk)
    
    if request.method == 'POST':
        form = AdminProcessForm(request.POST, instance=process)
        if form.is_valid():
            process = form.save()
            log_admin_action(request, 'UPDATE', process, 'Updated process details')
            messages.success(request, f'Process "{process.process_name}" updated successfully')
            return redirect('admin_process_detail', pk=process.pk)
    else:
        form = AdminProcessForm(instance=process)
    
    context = {
        'object': process,
        'form': form,
        'title': f'Edit Process: {process.process_name}',
        'model_name': 'process',
        'model_name_plural': 'Processes',
        'list_url': reverse('admin_processes_list'),
        'delete_url': reverse('admin_process_delete', args=[process.pk]),
    }
    return render(request, 'admin/enhanced_form_view.html', context)


@permission_required('clientapp.add_process', raise_exception=True)
def admin_process_add(request):
    """Add a new process"""
    if request.method == 'POST':
        form = AdminProcessForm(request.POST)
        if form.is_valid():
            process = form.save()
            log_admin_action(request, 'CREATE', process, 'Created new process')
            messages.success(request, f'Process "{process.process_name}" created successfully')
            return redirect('admin_process_detail', pk=process.pk)
    else:
        form = AdminProcessForm()
    
    context = {
        'form': form,
        'title': 'Add Process',
        'is_add': True,
        'model_name': 'process',
        'model_name_plural': 'Processes',
        'list_url': reverse('admin_processes_list'),
    }
    return render(request, 'admin/enhanced_form_view.html', context)


@permission_required('clientapp.delete_process', raise_exception=True)
def admin_process_delete(request, pk):
    """Delete a process"""
    process = get_object_or_404(Process, pk=pk)
    
    if request.method == 'POST':
        process_name = process.process_name
        log_admin_action(request, 'DELETE', process, 'Deleted process')
        process.delete()
        messages.success(request, f'Process "{process_name}" deleted successfully')
        return redirect('admin_processes_list')
    
    context = {
        'object': process,
        'title': f'Delete Process: {process.process_name}',
    }
    return render(request, 'admin/delete_confirm.html', context)



# ==================== LPOS ====================

@permission_required('clientapp.view_lpo', raise_exception=True)
def admin_lpos_list(request):
    """Display all LPOs in admin list view"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = LPO.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(lpo_number__icontains=search) |
            Q(client__name__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'LPOs',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_lpo_add'),
        'model_name': 'lpo',
    }
    return render(request, 'admin/lpos_list.html', context)


@permission_required('clientapp.change_lpo', raise_exception=True)
def admin_lpo_detail(request, pk):
    """View/Edit an LPO"""
    lpo = get_object_or_404(LPO, pk=pk)
    
    if request.method == 'POST':
        form = LPO_Form(request.POST, instance=lpo)
        if form.is_valid():
            lpo = form.save()
            log_admin_action(request, 'UPDATE', lpo, 'Updated LPO details')
            messages.success(request, f'LPO "{lpo.lpo_number}" updated successfully')
            return redirect('admin_lpo_detail', pk=lpo.pk)
    else:
        from .forms import LPO_Form
        form = LPO_Form(instance=lpo)
    
    context = {
        'object': lpo,
        'form': form,
        'title': f'Edit LPO: {lpo.lpo_number}',
        'model_name': 'lpo',
    }
    return render(request, 'admin/detail_view.html', context)


@permission_required('clientapp.add_lpo', raise_exception=True)
def admin_lpo_add(request):
    """Add a new LPO"""
    from .forms import LPO_Form
    
    if request.method == 'POST':
        form = LPO_Form(request.POST)
        if form.is_valid():
            lpo = form.save(commit=False)
            lpo.created_by = request.user
            lpo.save()
            log_admin_action(request, 'CREATE', lpo, 'Created new LPO')
            messages.success(request, f'LPO "{lpo.lpo_number}" created successfully')
            return redirect('admin_lpo_detail', pk=lpo.pk)
    else:
        form = LPO_Form()
    
    context = {
        'form': form,
        'title': 'Add LPO',
        'is_add': True,
        'model_name': 'lpo',
    }
    return render(request, 'admin/detail_view.html', context)


@permission_required('clientapp.delete_lpo', raise_exception=True)
def admin_lpo_delete(request, pk):
    """Delete an LPO"""
    lpo = get_object_or_404(LPO, pk=pk)
    
    if request.method == 'POST':
        lpo_number = lpo.lpo_number
        log_admin_action(request, 'DELETE', lpo, 'Deleted LPO')
        lpo.delete()
        messages.success(request, f'LPO "{lpo_number}" deleted successfully')
        return redirect('admin_lpos_list')
    
    context = {
        'object': lpo,
        'title': f'Delete LPO: {lpo.lpo_number}',
        'model_name': 'lpo',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== PAYMENTS ====================

@permission_required('clientapp.view_payment', raise_exception=True)
def admin_payments_list(request):
    """Display all payments in admin list view"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    queryset = Payment.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(payment_id__icontains=search) |
            Q(client__name__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Payments',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'add_url': reverse('admin_payment_add'),
        'model_name': 'payment',
    }
    return render(request, 'admin/payments_list.html', context)


@permission_required('clientapp.change_payment', raise_exception=True)
def admin_payment_detail(request, pk):
    """View/Edit a payment"""
    payment = get_object_or_404(Payment, pk=pk)
    
    if request.method == 'POST':
        from .forms import PaymentForm
        form = PaymentForm(request.POST, instance=payment)
        if form.is_valid():
            payment = form.save()
            log_admin_action(request, 'UPDATE', payment, 'Updated payment details')
            messages.success(request, f'Payment "{payment.payment_id}" updated successfully')
            return redirect('admin_payment_detail', pk=payment.pk)
    else:
        from .forms import PaymentForm
        form = PaymentForm(instance=payment)
    
    context = {
        'object': payment,
        'form': form,
        'title': f'Edit Payment: {payment.payment_id}',
        'model_name': 'payment',
    }
    return render(request, 'admin/detail_view.html', context)


@permission_required('clientapp.add_payment', raise_exception=True)
def admin_payment_add(request):
    """Add a new payment"""
    from .forms import PaymentForm
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save()
            log_admin_action(request, 'CREATE', payment, 'Created new payment')
            messages.success(request, f'Payment "{payment.payment_id}" created successfully')
            return redirect('admin_payment_detail', pk=payment.pk)
    else:
        form = PaymentForm()
    
    context = {
        'form': form,
        'title': 'Add Payment',
        'is_add': True,
        'model_name': 'payment',
    }
    return render(request, 'admin/detail_view.html', context)


@permission_required('clientapp.delete_payment', raise_exception=True)
def admin_payment_delete(request, pk):
    """Delete a payment"""
    payment = get_object_or_404(Payment, pk=pk)
    
    if request.method == 'POST':
        payment_id = payment.payment_id
        log_admin_action(request, 'DELETE', payment, 'Deleted payment')
        payment.delete()
        messages.success(request, f'Payment "{payment_id}" deleted successfully')
        return redirect('admin_payments_list')
    
    context = {
        'object': payment,
        'title': f'Delete Payment: {payment.payment_id}',
        'model_name': 'payment',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== USERS ====================

@permission_required('auth.view_user', raise_exception=True)
def admin_users_list(request):
    """Display all users in admin list view with group info"""
    search = request.GET.get('q', '')
    is_staff = request.GET.get('is_staff', '')
    group_filter = request.GET.get('group', '')
    page = request.GET.get('page', 1)
    
    queryset = User.objects.all().prefetch_related('groups')
    
    if search:
        queryset = queryset.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    
    if is_staff:
        queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
    
    if group_filter:
        queryset = queryset.filter(groups__id=group_filter)
    
    queryset = queryset.order_by('-date_joined')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    # Get all groups for filter dropdown
    all_groups = Group.objects.all().order_by('name')
    
    context = {
        'title': 'Users',
        'page_obj': page_obj,
        'search': search,
        'is_staff': is_staff,
        'is_staff_true_selected': 'selected' if is_staff == 'true' else '',
        'is_staff_false_selected': 'selected' if is_staff == 'false' else '',
        'group_filter': group_filter,
        'all_groups': all_groups,
        'total_count': queryset.count(),
        'add_url': reverse('admin_user_add'),
        'groups_url': reverse('admin_groups_list'),
        'model_name': 'user',
    }
    return render(request, 'admin/users_list.html', context)


@permission_required('auth.change_user', raise_exception=True)
def admin_user_detail(request, pk):
    """View/Edit a user with group assignment"""
    user_obj = get_object_or_404(User, pk=pk)
    all_groups = Group.objects.all().order_by('name')
    
    if request.method == 'POST':
        # Handle form submission
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        is_staff = request.POST.get('is_staff') == 'on'
        is_active = request.POST.get('is_active') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        new_password = request.POST.get('password')
        selected_groups = request.POST.getlist('groups')
        
        # Update user fields
        user_obj.username = username
        user_obj.email = email
        user_obj.first_name = first_name
        user_obj.last_name = last_name
        user_obj.is_staff = is_staff
        user_obj.is_active = is_active
        user_obj.is_superuser = is_superuser
        
        if new_password:
            user_obj.set_password(new_password)
        
        user_obj.save()
        
        # Update groups
        user_obj.groups.clear()
        for group_id in selected_groups:
            try:
                group = Group.objects.get(pk=group_id)
                user_obj.groups.add(group)
            except Group.DoesNotExist:
                pass
        
        log_admin_action(request, 'UPDATE', user_obj, 'Updated user details')
        messages.success(request, f'User "{user_obj.username}" updated successfully')
        return redirect('admin_user_detail', pk=user_obj.pk)
    
    # Get list of group IDs for this user
    user_group_ids = list(user_obj.groups.values_list('id', flat=True))
    
    # Add checked attribute to each group
    groups_with_checked = []
    for grp in all_groups:
        grp.checked = 'checked' if grp.id in user_group_ids else ''
        groups_with_checked.append(grp)
    
    context = {
        'object': user_obj,
        'user_obj': user_obj,
        'all_groups': groups_with_checked,
        'user_group_ids': user_group_ids,
        'is_active_checked': 'checked' if user_obj.is_active else '',
        'is_staff_checked': 'checked' if user_obj.is_staff else '',
        'is_superuser_checked': 'checked' if user_obj.is_superuser else '',
        'title': f'Edit User: {user_obj.username}',
        'model_name': 'user',
        'model_name_plural': 'Users',
        'list_url': reverse('admin_users_list'),
        'delete_url': reverse('admin_user_delete', args=[user_obj.pk]),
    }
    return render(request, 'admin/user_form.html', context)

@permission_required('auth.add_user', raise_exception=True)
def admin_user_add(request):
    """Add a new user with group assignment"""
    all_groups = Group.objects.all().order_by('name')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        is_staff = request.POST.get('is_staff') == 'on'
        # Fix: Check if 'is_active' is present in POST data
        is_active = request.POST.get('is_active') == 'on'
        is_superuser = request.POST.get('is_superuser') == 'on'
        selected_groups = request.POST.getlist('groups')
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists')
        elif not password:
            messages.error(request, 'Password is required')
        else:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff,
                is_active=is_active,
                is_superuser=is_superuser
            )
            
            # Assign groups
            for group_id in selected_groups:
                try:
                    group = Group.objects.get(pk=group_id)
                    user.groups.add(group)
                except Group.DoesNotExist:
                    pass
            
            log_admin_action(request, 'CREATE', user, 'Created new user')
            messages.success(request, f'User "{user.username}" created successfully')
            return redirect('admin_user_detail', pk=user.pk)
    
    # Add checked attribute to each group- but not for new users
    groups_with_checked = []
    for grp in all_groups:
        grp.checked = ''
        groups_with_checked.append(grp)
    
    context = {
        'all_groups': groups_with_checked,
        'user_group_ids': [],
        'is_active_checked': 'checked',  # Default to active for new users
        'is_staff_checked': '',
        'is_superuser_checked': '',
        'title': 'Add User',
        'is_add': True,
        'model_name': 'user',
        'model_name_plural': 'Users',
        'list_url': reverse('admin_users_list'),
    }
    return render(request, 'admin/user_form.html', context)

@permission_required('auth.delete_user', raise_exception=True)
def admin_user_delete(request, pk):
    """Delete a user"""
    user_obj = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        username = user_obj.username
        log_admin_action(request, 'DELETE', user_obj, 'Deleted user')
        user_obj.delete()
        messages.success(request, f'User "{username}" deleted successfully')
        return redirect('admin_users_list')
    
    context = {
        'object': user_obj,
        'title': f'Delete User: {user_obj.username}',
    }
    return render(request, 'admin/delete_confirm.html', context)


# ==================== GROUPS ====================

@permission_required('auth.view_group', raise_exception=True)
def admin_groups_list(request):
    """Display all groups (roles)"""
    search = request.GET.get('q', '')
    page = request.GET.get('page', 1)
    
    queryset = Group.objects.all().annotate(user_count=Count('user'))
    
    if search:
        queryset = queryset.filter(name__icontains=search)
    
    queryset = queryset.order_by('name')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Groups / Roles',
        'page_obj': page_obj,
        'search': search,
        'total_count': queryset.count(),
        'add_url': reverse('admin_group_add'),
        'model_name': 'group',
    }
    return render(request, 'admin/groups_list.html', context)


@permission_required('auth.change_group', raise_exception=True)
def admin_group_detail(request, pk):
    """View/Edit a group with permission assignment"""
    group = get_object_or_404(Group, pk=pk)
    all_permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label', 'codename')
    group_users = group.user_set.all()
    
    if request.method == 'POST':
        name = request.POST.get('name')
        selected_permissions = request.POST.getlist('permissions')
        
        group.name = name
        group.save()
        
        # Update permissions
        group.permissions.clear()
        for perm_id in selected_permissions:
            try:
                perm = Permission.objects.get(pk=perm_id)
                group.permissions.add(perm)
            except Permission.DoesNotExist:
                pass
        
        log_admin_action(request, 'UPDATE', group, 'Updated group details')
        messages.success(request, f'Group "{group.name}" updated successfully')
        return redirect('admin_group_detail', pk=group.pk)
    
    # Get list of permission IDs for this group
    group_permission_ids = list(group.permissions.values_list('id', flat=True))
    
    context = {
        'object': group,
        'group': group,
        'all_permissions': all_permissions,
        'group_users': group_users,
        'group_permission_ids': group_permission_ids,
        'title': f'Edit Group: {group.name}',
        'model_name': 'group',
        'model_name_plural': 'Groups',
        'list_url': reverse('admin_groups_list'),
        'delete_url': reverse('admin_group_delete', args=[group.pk]),
    }
    return render(request, 'admin/group_form.html', context)


@permission_required('auth.add_group', raise_exception=True)
def admin_group_add(request):
    """Add a new group"""
    all_permissions = Permission.objects.all().select_related('content_type').order_by('content_type__app_label', 'codename')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        selected_permissions = request.POST.getlist('permissions')
        
        if Group.objects.filter(name=name).exists():
            messages.error(request, 'Group with this name already exists')
        else:
            group = Group.objects.create(name=name)
            
            for perm_id in selected_permissions:
                try:
                    perm = Permission.objects.get(pk=perm_id)
                    group.permissions.add(perm)
                except Permission.DoesNotExist:
                    pass
            
            messages.success(request, f'Group "{group.name}" created successfully')
            return redirect('admin_group_detail', pk=group.pk)
    
    context = {
        'all_permissions': all_permissions,
        'group_permission_ids': [],
        'title': 'Add Group',
        'is_add': True,
        'model_name': 'group',
        'model_name_plural': 'Groups',
        'list_url': reverse('admin_groups_list'),
    }
    return render(request, 'admin/group_form.html', context)


@permission_required('auth.delete_group', raise_exception=True)
def admin_group_delete(request, pk):
    """Delete a group"""
    group = get_object_or_404(Group, pk=pk)
    
    if request.method == 'POST':
        group_name = group.name
        log_admin_action(request, 'DELETE', group, 'Deleted group')
        group.delete()
        messages.success(request, f'Group "{group_name}" deleted successfully')
        return redirect('admin_groups_list')
    
    context = {
        'object': group,
        'title': f'Delete Group: {group.name}',
        'model_name': 'group',  
    }
    return render(request, 'admin/delete_confirm.html', context)

# ==================== VIEW-ONLY LIST VIEWS ====================

@permission_required('clientapp.view_qcinspection', raise_exception=True)
def admin_qc_list(request):
    """Display all QC records (view only)"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    from .models import QCInspection
    queryset = QCInspection.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(qc_id__icontains=search) |
            Q(job__job_number__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'QC Records',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'model_name': 'qcinspection',
    }
    return render(request, 'admin/qc_list.html', context)


@permission_required('clientapp.view_delivery', raise_exception=True)
def admin_deliveries_list(request):
    """Display all deliveries (view only)"""
    search = request.GET.get('q', '')
    status = request.GET.get('status', '')
    page = request.GET.get('page', 1)
    
    from .models import Delivery
    queryset = Delivery.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(delivery_id__icontains=search) |
            Q(job__job_number__icontains=search)
        )
    
    if status:
        queryset = queryset.filter(status=status)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'Deliveries',
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_count': queryset.count(),
        'model_name': 'delivery',
    }
    return render(request, 'admin/deliveries_list.html', context)


@permission_required('clientapp.view_alert', raise_exception=True)
def admin_alerts_list(request):
    """Display all system alerts (view only)"""
    search = request.GET.get('q', '')
    severity = request.GET.get('severity', '')
    page = request.GET.get('page', 1)
    
    from .models import Alert
    queryset = Alert.objects.all()
    
    if search:
        queryset = queryset.filter(
            Q(message__icontains=search) |
            Q(alert_type__icontains=search)
        )
    
    if severity:
        queryset = queryset.filter(severity=severity)
    
    queryset = queryset.order_by('-created_at')
    paginator = Paginator(queryset, 25)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
    
    context = {
        'title': 'System Alerts',
        'page_obj': page_obj,
        'search': search,
        'severity': severity,
        'total_count': queryset.count(),
        'model_name': 'alert',
    }
    return render(request, 'admin/alerts_list.html', context)


@permission_required('clientapp.view_auditlog', raise_exception=True)
def admin_audit_logs(request):
    """Display audit logs"""
    search = request.GET.get('q', '')
    action = request.GET.get('action', '')
    model = request.GET.get('model', '')
    page = request.GET.get('page', 1)
    
    queryset = AuditLog.objects.all().select_related('user')
    
    if search:
        queryset = queryset.filter(
            Q(user__username__icontains=search) |
            Q(object_repr__icontains=search) |
            Q(details__icontains=search)
        )
    
    if action:
        queryset = queryset.filter(action=action)
        
    if model:
        queryset = queryset.filter(model_name=model)
    
    queryset = queryset.order_by('-timestamp')
    paginator = Paginator(queryset, 50)
    
    try:
        page_obj = paginator.page(page)
    except (EmptyPage, PageNotAnInteger):
        page_obj = paginator.page(1)
        
    # Get unique model names for filter
    model_names = AuditLog.objects.values_list('model_name', flat=True).distinct().order_by('model_name')
    
    context = {
        'title': 'Audit Logs',
        'page_obj': page_obj,
        'search': search,
        'action': action,
        'model': model,
        'model_names': model_names,
        'total_count': queryset.count(),
        'model_name': 'auditlog',
    }
    return render(request, 'admin/audit_logs.html', context)


@staff_member_required
@require_http_methods(["POST"])
def admin_bulk_action(request):
    """Handle bulk actions for admin lists"""
    model_name = request.POST.get('model_name')
    action = request.POST.get('action')
    selected_ids = request.POST.getlist('selected_ids')
    
    if not selected_ids:
        messages.warning(request, 'No items selected')
        return redirect(request.META.get('HTTP_REFERER', '/admin-dashboard/'))
    
    # Map model_name to Model Class
    from .models import (
        Client, Lead, Quote, Product, Job, Vendor, Process, LPO,
        Payment, QCInspection, Delivery, Alert
    )
    from django.contrib.auth.models import User, Group
    
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
        'group': Group,
        'qcinspection': QCInspection,
        'delivery': Delivery,
        'alert': Alert
    }
    
    ModelClass = model_map.get(model_name)
    if not ModelClass:
        messages.error(request, 'Invalid model')
        return redirect(request.META.get('HTTP_REFERER', '/admin-dashboard/'))
    
    # Determine app label
    app_label = 'clientapp'
    if model_name in ['user', 'group']:
        app_label = 'auth'
        
    if action == 'delete':
        # Check delete permission
        perm = f'{app_label}.delete_{model_name}'
        if not request.user.has_perm(perm):
            raise PermissionDenied(f"You do not have permission to delete {model_name}s")
            
        # Perform delete
        count, _ = ModelClass.objects.filter(pk__in=selected_ids).delete()
        messages.success(request, f'Successfully deleted {count} {model_name}(s)')
        
    return redirect(request.META.get('HTTP_REFERER', '/admin-dashboard/'))


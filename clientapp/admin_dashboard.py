#Admin dashboard all reports

from django.db.models import Count, Sum, Q, Avg, F
from django.db.models.functions import TruncMonth
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta
from decimal import Decimal


def get_dashboard_stats():
    """
    Calculate dashboard statistics
    Returns dict with metrics for dashboard cards
    """
    from .models import Client, Lead, Quote, Product, Job, LPO
    
    # Get date 30 days ago for trend calculations
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Calculate totals
    total_clients = Client.objects.count()
    active_leads = Lead.objects.filter(
        status__in=['New', 'Contacted', 'Qualified']
    ).count()
    pending_orders = LPO.objects.filter(status='pending').count()
    active_jobs = Job.objects.filter(
        status__in=['in_progress', 'pending']
    ).count()
    total_products = Product.objects.filter(status='published').count()
    
    # Calculate revenue
    total_revenue = LPO.objects.filter(
        status__in=['approved', 'in_production', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Calculate trends (new in last 30 days)
    new_clients_trend = Client.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    new_leads_trend = Lead.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    new_orders_trend = LPO.objects.filter(
        created_at__gte=thirty_days_ago
    ).count()
    
    revenue_trend = LPO.objects.filter(
        created_at__gte=thirty_days_ago,
        status__in=['approved', 'in_production', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    stats = {
        'total_clients': total_clients,
        'active_leads': active_leads,
        'pending_orders': pending_orders,
        'active_jobs': active_jobs,
        'total_products': total_products,
        'total_revenue': total_revenue,
        
        # Trends
        'new_clients_trend': new_clients_trend,
        'new_leads_trend': new_leads_trend,
        'new_orders_trend': new_orders_trend,
        'revenue_trend': revenue_trend,
    }
    
    return stats


def get_quote_status_distribution():
    """
    Get quote status distribution for pie chart
    Returns list of dicts with status and count
    """
    from .models import Quote
    
    distribution = Quote.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return list(distribution)


def get_order_status_distribution():
    """
    Get LPO order status distribution for donut chart
    """
    from .models import LPO
    
    distribution = LPO.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return list(distribution)


def get_production_status_data():
    """
    Get production status data for bar chart
    """
    from .models import Quote
    
    distribution = Quote.objects.values('production_status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    return list(distribution)


def get_sales_performance_trend(months=6):
    """
    Get sales performance for the last N months
    Returns monthly revenue data
    """
    from .models import LPO
    
    start_date = datetime.now() - timedelta(days=months*30)
    
    monthly_sales = LPO.objects.filter(
        created_at__gte=start_date,
        status__in=['approved', 'in_production', 'completed']
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    ).order_by('month')
    
    return list(monthly_sales)


def get_recent_orders(limit=10):
    """
    Get recent orders-LPO for dashboard
    """
    from .models import LPO
    
    return LPO.objects.select_related(
        'client', 'created_by'
    ).order_by('-created_at')[:limit]


def get_recent_activity(limit=10):
    """
    Get recent activity logs for dashboard
    """
    from .models import ActivityLog
    
    return ActivityLog.objects.select_related(
        'client', 'created_by'
    ).order_by('-created_at')[:limit]


def get_top_products(limit=10):
    """
    Get top selling products based on quote data
    """
    from .models import Quote
    
    # Group by product_name and sum quantities
    top_products = Quote.objects.filter(
        status='approved'
    ).values('product_name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('-total_revenue')[:limit]
    
    return list(top_products)


def get_top_clients(limit=10):
    """
    Get top clients by revenue
    """
    from .models import Client, LPO
    
    top_clients = Client.objects.annotate(
        total_orders=Count('lpos'),
        total_revenue=Sum('lpos__total_amount', filter=Q(
            lpos__status__in=['approved', 'in_production', 'completed']
        ))
    ).filter(
        total_revenue__isnull=False
    ).order_by('-total_revenue')[:limit]
    
    return list(top_clients)


def get_revenue_by_category():
    """
    Get revenue breakdown by product category
    """
    from .models import Quote, ProductCategory
    
    
    category_revenue = Quote.objects.filter(
        status='approved'
    ).values('product_name').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    ).order_by('-revenue')[:5]
    
    return list(category_revenue)


def get_conversion_metrics():
    """
    Calculate lead-to-client conversion metrics
    """
    from .models import Lead, Client, Quote
    
    total_leads = Lead.objects.count()
    converted_leads = Lead.objects.filter(status='Converted').count()
    
    total_quotes = Quote.objects.count()
    approved_quotes = Quote.objects.filter(status='approved').count()
    
    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0
    quote_approval_rate = (approved_quotes / total_quotes * 100) if total_quotes > 0 else 0
    
    return {
        'lead_conversion_rate': round(conversion_rate, 2),
        'quote_approval_rate': round(quote_approval_rate, 2),
        'total_leads': total_leads,
        'converted_leads': converted_leads,
        'total_quotes': total_quotes,
        'approved_quotes': approved_quotes,
    }


def get_average_order_value():
    """
    Calculate average order value
    """
    from .models import LPO
    
    avg_order = LPO.objects.filter(
        status__in=['approved', 'in_production', 'completed']
    ).aggregate(
        avg_value=Avg('total_amount')
    )['avg_value'] or Decimal('0.00')
    
    return round(avg_order, 2)

def get_active_alerts(limit=10):
    """
    Get active system alerts for admin dashboard
    """
    from .models import SystemAlert
    
    return SystemAlert.objects.filter(
        is_active=True,
        is_dismissed=False,
        visible_to_admins=True
    ).select_related(
        'created_by', 'related_client', 'related_quote'
    ).order_by('-severity', '-created_at')[:limit]


def get_user_activity_logs(limit=20):
    """
    Get recent user activity for admin dashboard
    """
    from .models import ActivityLog
    
    return ActivityLog.objects.select_related(
        'client', 'created_by', 'related_quote'
    ).order_by('-created_at')[:limit]


def get_top_selling_products(limit=10):
    """
    Get top selling products based on quotes
    """
    from .models import Quote
    from django.db.models import Count, Sum
    
    top_products = Quote.objects.filter(
        status='approved'
    ).values('product_name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_amount'),
        order_count=Count('id')
    ).order_by('-total_revenue')[:limit]
    
    return list(top_products)


def get_profit_margin_data():
    """
    Calculate profit margins by category or product
    """
    from .models import Quote
    from django.db.models import Sum, Avg, F
    
    # Calculate average margins
    margin_data = Quote.objects.filter(
        status='approved'
    ).aggregate(
        avg_markup=Avg(F('total_amount') - F('production_cost')),
        total_revenue=Sum('total_amount'),
        total_cost=Sum('production_cost')
    )
    
    if margin_data['total_revenue'] and margin_data['total_cost']:
        margin_data['overall_margin'] = (
            (margin_data['total_revenue'] - margin_data['total_cost']) / 
            margin_data['total_revenue'] * 100
        )
    else:
        margin_data['overall_margin'] = 0
    
    return margin_data


def create_low_stock_alerts():
    """
    Check inventory and create alerts for low stock
    """
    from .models import SystemAlert
    
    pass


def create_quote_expiry_alerts():
    """
    Check for quotes expiring soon and create alerts
    """
    from .models import Quote, SystemAlert
    from datetime import date, timedelta
    
    # Get quotes expiring in next 3 days
    expiring_soon = Quote.objects.filter(
        status='Draft',
        valid_until__lte=date.today() + timedelta(days=3),
        valid_until__gte=date.today()
    )
    
    for quote in expiring_soon:
        # Check if alert already exists
        existing = SystemAlert.objects.filter(
            alert_type='quote_expired',
            related_quote=quote,
            is_active=True
        ).exists()
        
        if not existing:
            SystemAlert.objects.create(
                alert_type='quote_expired',
                severity='medium',
                title=f'Quote {quote.quote_id} Expiring Soon',
                message=f'Quote for {quote.client or quote.lead} expires on {quote.valid_until}',
                link=f'/admin/clientapp/quote/{quote.id}/change/',
                related_quote=quote,
                related_client=quote.client
            )

#FEATURE 1: OUTSTANDING RECEIVABLES

def get_outstanding_receivables():
    """
    Calculate outstanding receivables and aging report
    """
    from .models import LPO, Payment
    from django.db.models import Sum, Q, F
    from datetime import date, timedelta
    
    # Get all approved/completed LPOs that haven't been fully paid
    unpaid_lpos = LPO.objects.filter(
        status__in=['approved', 'in_production', 'completed']
    ).annotate(
        paid_amount=Sum('payments__amount', filter=Q(payments__status='completed'))
    ).annotate(
        balance=F('total_amount') - F('paid_amount')
    ).filter(
        Q(paid_amount__isnull=True) | Q(balance__gt=0)
    )
    
    total_receivables = Decimal('0.00')
    current = Decimal('0.00')  # 0-30 days
    days_30_60 = Decimal('0.00')
    days_60_90 = Decimal('0.00')
    over_90 = Decimal('0.00')
    
    today = date.today()
    
    for lpo in unpaid_lpos:
        balance = lpo.total_amount - (lpo.paid_amount or Decimal('0.00'))
        total_receivables += balance
        
        # Calculate days overdue based on created_at or approved_at
        invoice_date = lpo.approved_at.date() if lpo.approved_at else lpo.created_at.date()
        days_old = (today - invoice_date).days
        
        if days_old <= 30:
            current += balance
        elif days_old <= 60:
            days_30_60 += balance
        elif days_old <= 90:
            days_60_90 += balance
        else:
            over_90 += balance
    
    overdue_total = days_30_60 + days_60_90 + over_90
    overdue_percentage = (overdue_total / total_receivables * 100) if total_receivables > 0 else 0
    
    return {
        'total_receivables': total_receivables,
        'overdue_amount': overdue_total,
        'overdue_percentage': round(overdue_percentage, 1),
        'current': current,
        'days_30_60': days_30_60,
        'days_60_90': days_60_90,
        'over_90': over_90,
        'unpaid_invoices_count': unpaid_lpos.count(),
    }


def get_recent_payments(limit=5):
    """
    Get recent payments
    """
    from .models import Payment
    
    return Payment.objects.select_related(
        'lpo', 'lpo__client', 'recorded_by'
    ).filter(status='completed').order_by('-payment_date')[:limit]


def get_payment_collection_rate():
    """
    Calculate payment collection efficiency
    """
    from .models import LPO, Payment
    from django.db.models import Sum, Count
    from datetime import date, timedelta
    
    # Last 90 days
    ninety_days_ago = date.today() - timedelta(days=90)
    
    # Total invoiced
    total_invoiced = LPO.objects.filter(
        approved_at__gte=ninety_days_ago,
        status__in=['approved', 'in_production', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    # Total collected
    total_collected = Payment.objects.filter(
        payment_date__gte=ninety_days_ago,
        status='completed'
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0
    
    # Average days to payment
    paid_lpos = LPO.objects.filter(
        approved_at__gte=ninety_days_ago,
        payments__status='completed'
    ).distinct()
    
    total_days = 0
    count = 0
    for lpo in paid_lpos:
        first_payment = lpo.payments.filter(status='completed').order_by('payment_date').first()
        if first_payment and lpo.approved_at:
            days = (first_payment.payment_date - lpo.approved_at.date()).days
            total_days += days
            count += 1
    
    avg_days_to_payment = total_days / count if count > 0 else 0
    
    return {
        'collection_rate': round(collection_rate, 1),
        'avg_days_to_payment': round(avg_days_to_payment, 1),
        'total_invoiced': total_invoiced,
        'total_collected': total_collected,
    }


# FEATURE 6: STAFF PERFORMANCE 

def get_staff_performance():
    """
    Calculate staff performance metrics
    """
    from .models import Quote, LPO
    from django.contrib.auth.models import User
    from django.db.models import Sum, Count, Avg, Q
    from datetime import date, timedelta
    
    thirty_days_ago = date.today() - timedelta(days=30)
    
    # Sales Rep Performance (Account Managers)
    sales_reps = User.objects.filter(
        groups__name='Account Manager'
    ).annotate(
        
        total_quotes=Count('quotes_created', filter=Q(
            quotes_created__created_at__gte=thirty_days_ago
        )),
        quotes_won=Count('quotes_created', filter=Q(
            quotes_created__status='Approved',
            quotes_created__created_at__gte=thirty_days_ago
        )),
        total_revenue=Sum('quotes_created__total_amount', filter=Q(
            quotes_created__status='Approved',
            quotes_created__created_at__gte=thirty_days_ago
        ))
    ).order_by('-total_revenue')[:5]
    
    sales_leaderboard = []
    for rep in sales_reps:
        
        win_rate = (rep.quotes_won / rep.total_quotes * 100) if rep.total_quotes > 0 else 0
        avg_deal = (rep.total_revenue / rep.quotes_won) if rep.quotes_won and rep.quotes_won > 0 else 0
        
        sales_leaderboard.append({
            'name': rep.get_full_name() or rep.username,
            'revenue': rep.total_revenue or Decimal('0.00'),
            'deals_closed': rep.quotes_won,
            'win_rate': round(win_rate, 1),
            'avg_deal_size': avg_deal,
        })
    
    # Production Team Performance (unchanged)
    production_staff = User.objects.filter(
        groups__name='Production Team'
    ).annotate(
        jobs_completed=Count('lpos_created', filter=Q(
            lpos_created__status='completed',
            lpos_created__created_at__gte=thirty_days_ago
        ))
    ).order_by('-jobs_completed')[:5]
    
    production_leaderboard = []
    for staff in production_staff:
        production_leaderboard.append({
            'name': staff.get_full_name() or staff.username,
            'jobs_completed': staff.jobs_completed,
        })
    
    return {
        'sales_leaderboard': sales_leaderboard,
        'production_leaderboard': production_leaderboard,
    }


# TIME-BASED INSIGHTS

def get_time_based_insights():
    """
    Calculate time-based comparisons and trends
    """
    from .models import Quote, LPO, Client, Lead
    from django.db.models import Sum, Count
    from datetime import date, timedelta, datetime
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    last_week_start = week_start - timedelta(days=7)
    last_week_end = week_start - timedelta(days=1)
    month_start = today.replace(day=1)
    
    # Last month
    if month_start.month == 1:
        last_month_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        last_month_start = month_start.replace(month=month_start.month - 1)
    last_month_end = month_start - timedelta(days=1)
    
    # Today vs Yesterday
    today_revenue = LPO.objects.filter(
        created_at__date=today,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    yesterday_revenue = LPO.objects.filter(
        created_at__date=yesterday,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    daily_change = ((today_revenue - yesterday_revenue) / yesterday_revenue * 100) if yesterday_revenue > 0 else 0
    
    # This Week vs Last Week
    this_week_revenue = LPO.objects.filter(
        created_at__date__gte=week_start,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    last_week_revenue = LPO.objects.filter(
        created_at__date__gte=last_week_start,
        created_at__date__lte=last_week_end,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    weekly_change = ((this_week_revenue - last_week_revenue) / last_week_revenue * 100) if last_week_revenue > 0 else 0
    
    # This Month vs Last Month
    this_month_revenue = LPO.objects.filter(
        created_at__date__gte=month_start,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    last_month_revenue = LPO.objects.filter(
        created_at__date__gte=last_month_start,
        created_at__date__lte=last_month_end,
        status__in=['approved', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    monthly_change = ((this_month_revenue - last_month_revenue) / last_month_revenue * 100) if last_month_revenue > 0 else 0
    
    # Peak Days Analysis (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    daily_orders = LPO.objects.filter(
        created_at__date__gte=thirty_days_ago
    ).extra(select={'day': 'date(created_at)'}).values('day').annotate(
        count=Count('id')
    ).order_by('-count')[:3]
    
    busiest_days = [{'date': item['day'], 'orders': item['count']} for item in daily_orders]
    
    return {
        'today_revenue': today_revenue,
        'yesterday_revenue': yesterday_revenue,
        'daily_change': round(daily_change, 1),
        'daily_change_abs': abs(round(daily_change, 1)),  
        'this_week_revenue': this_week_revenue,
        'last_week_revenue': last_week_revenue,
        'weekly_change': round(weekly_change, 1),
        'weekly_change_abs': abs(round(weekly_change, 1)),
        'this_month_revenue': this_month_revenue,
        'last_month_revenue': last_month_revenue,
        'monthly_change': round(monthly_change, 1),
        'monthly_change_abs': abs(round(monthly_change, 1)),
        'busiest_days': busiest_days,
    }
    
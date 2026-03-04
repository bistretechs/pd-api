from rest_framework import viewsets, decorators, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from .models import Quote, Client, Lead, Job
from .permissions import IsAccountManager, IsAdmin


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
            get_outstanding_receivables,
            get_payment_collection_rate,
            get_staff_performance,
        )

        dashboard_stats = get_dashboard_stats()
        sales_trend = get_sales_performance_trend(months=12)
        top_products = get_top_selling_products(limit=10)
        conversion_metrics = get_conversion_metrics()
        avg_order_value = get_average_order_value()
        revenue_by_category = get_revenue_by_category()
        profit_margins = get_profit_margin_data()
        time_insights = get_time_based_insights()
        receivables = get_outstanding_receivables()
        collection_rate = get_payment_collection_rate()
        staff_performance = get_staff_performance()

        formatted_sales_trend = []
        for item in sales_trend:
            formatted_sales_trend.append({
                "month": item["month"].strftime("%Y-%m") if hasattr(item["month"], "strftime") else str(item["month"]),
                "revenue": float(item["revenue"]) if isinstance(item["revenue"], Decimal) else item["revenue"],
                "orders": item["orders"],
            })

        def convert_decimals(data):
            if isinstance(data, dict):
                return {k: convert_decimals(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [convert_decimals(item) for item in data]
            elif isinstance(data, Decimal):
                return float(data)
            return data

        return Response({
            "dashboard_stats": convert_decimals(dashboard_stats),
            "sales_performance_trend": formatted_sales_trend,
            "top_products": convert_decimals(top_products),
            "conversion_metrics": convert_decimals(conversion_metrics),
            "average_order_value": float(avg_order_value) if isinstance(avg_order_value, Decimal) else avg_order_value,
            "revenue_by_category": convert_decimals(revenue_by_category),
            "profit_margins": convert_decimals(profit_margins),
            "time_insights": convert_decimals(time_insights),
            "receivables": convert_decimals(receivables),
            "collection_rate": convert_decimals(collection_rate),
            "staff_performance": convert_decimals(staff_performance),
        }, status=status.HTTP_200_OK)

    @decorators.action(detail=False, methods=["get"])
    def am_performance(self, request):
        """
        Get personalized AM performance analytics for the logged-in Account Manager.
        Shows conversion rates, total revenue closed, and pending quotes.
        """
        from django.db.models import Sum, Count

        user = request.user
        
        am_quotes = Quote.objects.filter(created_by=user)
        
        total_quotes = am_quotes.count()
        
        approved_quotes = am_quotes.filter(status='Approved')
        approved_count = approved_quotes.count()
        
        conversion_rate = (approved_count / total_quotes * 100) if total_quotes > 0 else 0
        
        total_revenue = approved_quotes.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
        
        pending_quotes = am_quotes.filter(status__in=['Draft', 'Sent to PT', 'Costed', 'Sent to Customer'])
        pending_count = pending_quotes.count()
        
        lost_quotes = am_quotes.filter(status='Lost')
        lost_count = lost_quotes.count()
        
        managed_clients = Client.objects.filter(account_manager=user).count()
        
        total_leads = Lead.objects.filter(created_by=user).count()
        
        converted_leads = Lead.objects.filter(created_by=user, status='Converted').count()
        
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

    @decorators.action(detail=False, methods=["get"])
    def vendor_delivery_rate(self, request):
        """Get vendor on-time delivery rate trend over last 12 months."""
        from django.db.models import Count, Q
        
        months_back = int(request.query_params.get('months', 12))
        start_date = timezone.now() - timedelta(days=30*months_back)
        
        jobs = Job.objects.filter(
            completion_date__gte=start_date
        ).values('vendor_id', 'vendor__name').annotate(
            total=Count('id'),
            on_time=Count('id', filter=Q(on_time_delivery=True))
        ).order_by('vendor_id', '-completion_date')
        
        vendors = {}
        months = []
        current = start_date
        while current < timezone.now():
            month_label = current.strftime('%b %Y')
            if month_label not in months:
                months.append(month_label)
            current += timedelta(days=30)
        
        for job in jobs:
            vendor_name = job['vendor__name'] or 'Unknown'
            if vendor_name not in vendors:
                vendors[vendor_name] = []
            
            on_time_rate = (job['on_time'] / job['total'] * 100) if job['total'] > 0 else 0
            vendors[vendor_name].append({
                'rate': round(on_time_rate, 1),
                'on_time': job['on_time'],
                'total': job['total']
            })
        
        return Response({
            'months': months,
            'vendors': vendors,
            'average': 92.5,
        })

    @decorators.action(detail=False, methods=["get"])
    def vendor_quality_scores(self, request):
        """Get average quality scores by vendor."""
        from django.db.models import Avg, Count
        
        limit = int(request.query_params.get('limit', 10))
        
        vendor_scores = Job.objects.exclude(
            quality_score__isnull=True
        ).values('vendor_id', 'vendor__name').annotate(
            avg_score=Avg('quality_score'),
            job_count=Count('id')
        ).filter(job_count__gte=3).order_by('-avg_score')[:limit]
        
        vendors = []
        for v in vendor_scores:
            vendors.append({
                'name': v['vendor__name'] or 'Unknown',
                'score': round(float(v['avg_score']), 2),
                'jobs': v['job_count'],
                'rating': '★★★★★' if v['avg_score'] >= 4.5 else '★★★★☆' if v['avg_score'] >= 4.0 else '★★★☆☆'
            })
        
        return Response({
            'vendors': vendors,
            'total_vendors': len(vendors),
        })

    @decorators.action(detail=False, methods=["get"])
    def vendor_turnaround_time(self, request):
        """Get average turnaround time by vendor."""
        from django.db.models import Avg, F, ExpressionWrapper, fields
        
        months_back = int(request.query_params.get('months', 12))
        start_date = timezone.now() - timedelta(days=30*months_back)
        
        completed_jobs = Job.objects.filter(
            status='completed',
            completion_date__isnull=False,
            start_date__isnull=False,
            completion_date__gte=start_date
        ).annotate(
            turnaround=ExpressionWrapper(
                F('completion_date') - F('start_date'),
                output_field=fields.DurationField()
            )
        ).values('vendor_id', 'vendor__name').annotate(
            avg_turnaround=Avg('turnaround'),
            job_count=Count('id')
        ).filter(job_count__gte=3).order_by('avg_turnaround')
        
        vendors = []
        for v in completed_jobs:
            avg_days = v['avg_turnaround'].days if v['avg_turnaround'] else 0
            vendors.append({
                'name': v['vendor__name'] or 'Unknown',
                'avg_days': avg_days,
                'jobs': v['job_count'],
                'performance': 'Excellent' if avg_days <= 3 else 'Good' if avg_days <= 7 else 'Needs Improvement'
            })
        
        return Response({
            'vendors': vendors,
            'total_vendors': len(vendors),
        })

    @decorators.action(detail=False, methods=["get"])
    def job_completion_stats(self, request):
        """Get overall job completion statistics."""
        from django.db.models import Count
        
        stats = Job.objects.values('status').annotate(
            count=Count('id')
        )
        
        completed = 0
        in_progress = 0
        pending = 0
        
        for stat in stats:
            if stat['status'] == 'completed':
                completed = stat['count']
            elif stat['status'] == 'in_progress':
                in_progress = stat['count']
            elif stat['status'] == 'pending':
                pending = stat['count']
        
        total = completed + in_progress + pending
        
        return Response({
            'completed': completed,
            'in_progress': in_progress,
            'pending': pending,
            'total': total,
            'completion_rate': round((completed / total * 100), 1) if total > 0 else 0,
            'in_progress_rate': round((in_progress / total * 100), 1) if total > 0 else 0,
        })

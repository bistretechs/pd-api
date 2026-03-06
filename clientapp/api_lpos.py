from django.db.models import Count, Q, Sum
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_serializers import LPOSerializer
from .models import LPO
from .permissions import IsAdmin, IsAccountManager, IsProductionTeam


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class LPOViewSet(viewsets.ModelViewSet):
    queryset = LPO.objects.select_related("client", "quote", "created_by", "approved_by").all()
    serializer_class = LPOSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsAccountManager | IsProductionTeam]
    filterset_fields = {
        "status": ["exact"],
        "client": ["exact"],
        "quote": ["exact"],
        "created_at": ["gte", "lte"],
    }
    search_fields = ["lpo_number", "client__name", "quote__quote_id"]
    ordering_fields = ["created_at", "total_amount", "delivery_date"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        aggregates = queryset.aggregate(
            total_amount_sum=Sum("total_amount"),
            pending_amount_sum=Sum("total_amount", filter=Q(status="pending")),
            approved_amount_sum=Sum("total_amount", filter=Q(status="approved")),
            in_production_amount_sum=Sum("total_amount", filter=Q(status="in_production")),
            completed_amount_sum=Sum("total_amount", filter=Q(status="completed")),
            cancelled_amount_sum=Sum("total_amount", filter=Q(status="cancelled")),
            total_count=Count("id"),
            pending_count=Count("id", filter=Q(status="pending")),
            approved_count=Count("id", filter=Q(status="approved")),
            in_production_count=Count("id", filter=Q(status="in_production")),
            completed_count=Count("id", filter=Q(status="completed")),
            cancelled_count=Count("id", filter=Q(status="cancelled")),
        )

        summary = {
            "total_amount": float(aggregates["total_amount_sum"] or 0),
            "pending_amount": float(aggregates["pending_amount_sum"] or 0),
            "approved_amount": float(aggregates["approved_amount_sum"] or 0),
            "in_production_amount": float(aggregates["in_production_amount_sum"] or 0),
            "completed_amount": float(aggregates["completed_amount_sum"] or 0),
            "cancelled_amount": float(aggregates["cancelled_amount_sum"] or 0),
            "total_count": int(aggregates["total_count"] or 0),
            "pending_count": int(aggregates["pending_count"] or 0),
            "approved_count": int(aggregates["approved_count"] or 0),
            "in_production_count": int(aggregates["in_production_count"] or 0),
            "completed_count": int(aggregates["completed_count"] or 0),
            "cancelled_count": int(aggregates["cancelled_count"] or 0),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["summary"] = summary
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "summary": summary})

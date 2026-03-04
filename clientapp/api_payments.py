from drf_yasg.utils import swagger_auto_schema
from django.db.models import Count, Q, Sum
from django.utils.decorators import method_decorator
from rest_framework import viewsets
from rest_framework.response import Response

from .api_serializers import PaymentSerializer
from .models import Payment
from .permissions import IsAdmin, IsAccountManager
from rest_framework.permissions import IsAuthenticated


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Finance & Purchasing']))
class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("lpo", "lpo__client", "recorded_by").all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsAccountManager]
    filterset_fields = {
        "status": ["exact"],
        "payment_method": ["exact"],
        "lpo": ["exact"],
        "payment_date": ["gte", "lte"],
    }
    search_fields = ["reference_number", "lpo__lpo_number", "lpo__client__name"]
    ordering_fields = ["payment_date", "amount"]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        aggregates = queryset.aggregate(
            total_amount=Sum("amount"),
            completed_amount=Sum("amount", filter=Q(status="completed")),
            pending_amount=Sum("amount", filter=Q(status="pending")),
            total_count=Count("id"),
            completed_count=Count("id", filter=Q(status="completed")),
            pending_count=Count("id", filter=Q(status="pending")),
            failed_count=Count("id", filter=Q(status="failed")),
            refunded_count=Count("id", filter=Q(status="refunded")),
        )

        summary = {
            "total_amount": float(aggregates["total_amount"] or 0),
            "completed_amount": float(aggregates["completed_amount"] or 0),
            "pending_amount": float(aggregates["pending_amount"] or 0),
            "total_count": int(aggregates["total_count"] or 0),
            "completed_count": int(aggregates["completed_count"] or 0),
            "pending_count": int(aggregates["pending_count"] or 0),
            "failed_count": int(aggregates["failed_count"] or 0),
            "refunded_count": int(aggregates["refunded_count"] or 0),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["summary"] = summary
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "summary": summary})

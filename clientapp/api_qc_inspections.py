from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_serializers import QCInspectionSerializer
from .models import QCInspection
from .permissions import IsAdmin, IsProductionTeam


@method_decorator(name="list", decorator=swagger_auto_schema(tags=["Production Team"]))
@method_decorator(name="create", decorator=swagger_auto_schema(tags=["Production Team"]))
@method_decorator(name="retrieve", decorator=swagger_auto_schema(tags=["Production Team"]))
@method_decorator(name="update", decorator=swagger_auto_schema(tags=["Production Team"]))
@method_decorator(name="partial_update", decorator=swagger_auto_schema(tags=["Production Team"]))
@method_decorator(name="destroy", decorator=swagger_auto_schema(tags=["Production Team"]))
class QCInspectionViewSet(viewsets.ModelViewSet):
    queryset = QCInspection.objects.select_related(
        "job",
        "job__client",
        "job__quote",
        "vendor",
        "inspector",
    ).all()
    serializer_class = QCInspectionSerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin]
    filterset_fields = {
        "job": ["exact"],
        "vendor": ["exact"],
        "inspector": ["exact"],
        "status": ["exact"],
        "created_at": ["gte", "lte"],
    }
    search_fields = [
        "job__job_number",
        "job__quote__quote_id",
        "job__client__name",
        "vendor__name",
        "inspector__first_name",
        "inspector__last_name",
    ]
    ordering_fields = ["created_at", "inspection_date", "status", "id"]

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.vendor and instance.status in ["passed", "failed"]:
            instance.vendor.calculate_vps()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        aggregates = queryset.aggregate(
            total_count=Count("id"),
            pending_count=Count("id", filter=Q(status="pending")),
            passed_count=Count("id", filter=Q(status="passed")),
            failed_count=Count("id", filter=Q(status="failed")),
            rework_count=Count("id", filter=Q(status="rework")),
        )

        summary = {
            "total_count": int(aggregates["total_count"] or 0),
            "pending_count": int(aggregates["pending_count"] or 0),
            "passed_count": int(aggregates["passed_count"] or 0),
            "failed_count": int(aggregates["failed_count"] or 0),
            "rework_count": int(aggregates["rework_count"] or 0),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["summary"] = summary
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "summary": summary})

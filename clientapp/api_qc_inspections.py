from django.db.models import Count, Q
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_serializers import QCInspectionSerializer
from .models import Job, QCInspection
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

    def _is_admin(self, user):
        return user.is_superuser or user.groups.filter(name="Admin").exists()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if self._is_admin(user):
            return queryset

        return queryset.filter(Q(job__person_in_charge=user) | Q(inspector=user)).distinct()

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.vendor and instance.status in ["passed", "failed"]:
            instance.vendor.calculate_vps()

    @decorators.action(
        detail=False,
        methods=["post"],
        url_path="submit-for-job",
        permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin],
    )
    def submit_for_job(self, request):
        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"detail": "job_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.objects.select_related("person_in_charge").get(pk=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if not self._is_admin(user) and job.person_in_charge_id != user.id:
            return Response(
                {"detail": "You can only submit QC for jobs assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        qc_status = request.data.get("status", "pending")
        valid_statuses = {choice[0] for choice in QCInspection.INSPECTION_STATUS_CHOICES}
        if qc_status not in valid_statuses:
            return Response({"detail": "Invalid QC status."}, status=status.HTTP_400_BAD_REQUEST)

        def to_bool(value):
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.strip().lower() in {"true", "1", "yes", "on"}
            return bool(value)

        color_accuracy = to_bool(request.data.get("color_accuracy"))
        print_quality = to_bool(request.data.get("print_quality"))
        cutting_accuracy = to_bool(request.data.get("cutting_accuracy"))
        finishing_quality = to_bool(request.data.get("finishing_quality"))
        quantity_verified = to_bool(request.data.get("quantity_verified"))
        packaging_checked = to_bool(request.data.get("packaging_checked"))
        notes = request.data.get("notes", "")

        if qc_status == "passed":
            required_checks = [
                color_accuracy,
                print_quality,
                cutting_accuracy,
                finishing_quality,
                quantity_verified,
                packaging_checked,
            ]
            if not all(required_checks):
                return Response(
                    {"detail": "All QC checklist checks must be true for passed status."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        inspection = QCInspection.objects.filter(job=job).order_by("-created_at").first()
        if inspection is None:
            inspection = QCInspection.objects.create(
                job=job,
                inspector=user,
                status=qc_status,
                color_accuracy=color_accuracy,
                print_quality=print_quality,
                cutting_accuracy=cutting_accuracy,
                finishing_quality=finishing_quality,
                quantity_verified=quantity_verified,
                packaging_checked=packaging_checked,
                notes=notes,
            )
        else:
            inspection.inspector = user
            inspection.status = qc_status
            inspection.color_accuracy = color_accuracy
            inspection.print_quality = print_quality
            inspection.cutting_accuracy = cutting_accuracy
            inspection.finishing_quality = finishing_quality
            inspection.quantity_verified = quantity_verified
            inspection.packaging_checked = packaging_checked
            inspection.notes = notes
            inspection.save()

        if inspection.vendor and inspection.status in ["passed", "failed"]:
            inspection.vendor.calculate_vps()

        serializer = self.get_serializer(inspection)
        return Response(
            {
                "detail": "QC submitted successfully.",
                "inspection": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

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

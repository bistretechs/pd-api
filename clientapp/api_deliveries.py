from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework import decorators, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .api_serializers import DeliverySerializer
from .models import ActivityLog, Delivery, Job, JobVendorStage, Notification, QCInspection
from .permissions import IsAdmin, IsAccountManager, IsProductionTeam


@method_decorator(name='list', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='create', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='retrieve', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='partial_update', decorator=swagger_auto_schema(tags=['Production Team']))
@method_decorator(name='destroy', decorator=swagger_auto_schema(tags=['Production Team']))
class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related(
        "job",
        "job__client",
        "job__quote",
        "qc_inspection",
        "handoff_confirmed_by",
        "created_by",
    ).all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAuthenticated, IsProductionTeam | IsAdmin | IsAccountManager]
    filterset_fields = {
        "job": ["exact"],
        "status": ["exact"],
        "staging_location": ["exact"],
        "handoff_confirmed": ["exact"],
        "mark_urgent": ["exact"],
        "created_at": ["gte", "lte"],
        "job__delivery_method": ["exact"],
    }
    search_fields = [
        "delivery_number",
        "job__job_number",
        "job__quote__quote_id",
        "job__client__name",
    ]
    ordering_fields = ["created_at", "updated_at", "delivery_number", "status"]

    def _is_admin(self, user):
        return user.is_superuser or user.groups.filter(name="Admin").exists()

    def _is_account_manager(self, user):
        return user.groups.filter(name="Account Manager").exists()

    def _is_production_team(self, user):
        return user.groups.filter(name="Production Team").exists()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if self._is_admin(user):
            return queryset

        if self._is_account_manager(user):
            return queryset.filter(job__client__account_manager=user)

        if self._is_production_team(user):
            return queryset.filter(Q(job__person_in_charge=user) | Q(created_by=user))

        return queryset.none()

    def _to_bool(self, value, default=False):
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return bool(value)

    def _parse_decimal(self, value, fallback):
        if value in (None, ""):
            return fallback
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return None

    def perform_update(self, serializer):
        instance = serializer.save()

        if instance.status == "delivered" and instance.job:
            vendor_stages = JobVendorStage.objects.filter(
                job=instance.job,
                status="completed",
            )
            vendors_updated = set()
            for stage in vendor_stages:
                if stage.vendor and stage.vendor.id not in vendors_updated:
                    if hasattr(stage.vendor, "calculate_vps"):
                        stage.vendor.calculate_vps()
                    elif hasattr(stage.vendor, "update_performance_score"):
                        stage.vendor.update_performance_score()
                    vendors_updated.add(stage.vendor.id)

    @decorators.action(
        detail=False,
        methods=["get"],
        url_path="handoff-queue",
        permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin],
    )
    def handoff_queue(self, request):
        user = request.user
        jobs_queryset = Job.objects.select_related("client", "quote", "person_in_charge")

        if not self._is_admin(user):
            jobs_queryset = jobs_queryset.filter(person_in_charge=user)

        jobs_queryset = jobs_queryset.exclude(delivery__handoff_confirmed=True).filter(
            status__in=["in_progress", "on_hold", "completed"]
        )

        search_query = request.query_params.get("search", "").strip()
        if search_query:
            jobs_queryset = jobs_queryset.filter(
                Q(job_number__icontains=search_query)
                | Q(job_name__icontains=search_query)
                | Q(product__icontains=search_query)
                | Q(client__name__icontains=search_query)
            )

        jobs_queryset = jobs_queryset.order_by("expected_completion", "-created_at")

        results = []
        ready_count = 0
        blocked_count = 0

        for job in jobs_queryset:
            latest_qc = QCInspection.objects.filter(job=job).order_by("-created_at").first()
            existing_delivery = getattr(job, "delivery", None)

            qc_status = latest_qc.status if latest_qc else None
            is_ready_for_handoff = qc_status == "passed"
            if is_ready_for_handoff:
                ready_count += 1
            else:
                blocked_count += 1

            results.append(
                {
                    "job_id": job.id,
                    "job_number": job.job_number,
                    "job_name": job.job_name,
                    "client_name": job.client.name if job.client else None,
                    "product": job.product,
                    "quantity": job.quantity,
                    "job_status": job.status,
                    "expected_completion": job.expected_completion,
                    "quote_id": job.quote.quote_id if job.quote else None,
                    "person_in_charge_id": job.person_in_charge_id,
                    "qc_status": qc_status,
                    "qc_checked_at": latest_qc.created_at if latest_qc else None,
                    "qc_inspection_id": latest_qc.id if latest_qc else None,
                    "qc_notes": latest_qc.notes if latest_qc else "",
                    "qc_color_accuracy": latest_qc.color_accuracy if latest_qc else False,
                    "qc_print_quality": latest_qc.print_quality if latest_qc else False,
                    "qc_cutting_accuracy": latest_qc.cutting_accuracy if latest_qc else False,
                    "qc_finishing_quality": latest_qc.finishing_quality if latest_qc else False,
                    "qc_quantity_verified": latest_qc.quantity_verified if latest_qc else False,
                    "qc_packaging_checked": latest_qc.packaging_checked if latest_qc else False,
                    "is_ready_for_handoff": is_ready_for_handoff,
                    "existing_delivery_id": existing_delivery.id if existing_delivery else None,
                    "existing_staging_location": existing_delivery.staging_location if existing_delivery else None,
                    "existing_mark_urgent": existing_delivery.mark_urgent if existing_delivery else False,
                }
            )

        return Response(
            {
                "count": len(results),
                "ready_count": ready_count,
                "blocked_count": blocked_count,
                "results": results,
            }
        )

    @decorators.action(
        detail=False,
        methods=["post"],
        url_path="complete-handoff",
        permission_classes=[IsAuthenticated, IsProductionTeam | IsAdmin],
    )
    def complete_handoff(self, request):
        user = request.user
        job_id = request.data.get("job_id")

        if not job_id:
            return Response({"detail": "job_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job = Job.objects.select_related("client", "quote", "person_in_charge").get(pk=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        is_admin = self._is_admin(user)
        if not is_admin and job.person_in_charge_id != user.id:
            return Response(
                {"detail": "You can only hand over jobs assigned to you."},
                status=status.HTTP_403_FORBIDDEN,
            )

        latest_qc = QCInspection.objects.filter(job=job).order_by("-created_at").first()
        if not is_admin and (latest_qc is None or latest_qc.status != "passed"):
            return Response(
                {"detail": "QC must be passed before handoff."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_delivery = getattr(job, "delivery", None)
        if existing_delivery and existing_delivery.handoff_confirmed and not is_admin:
            return Response(
                {"detail": "This job has already been handed off."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        staging_location = request.data.get("staging_location", "shelf-b")
        valid_staging_locations = {choice[0] for choice in Delivery.STAGING_LOCATION_CHOICES}
        if staging_location not in valid_staging_locations:
            return Response(
                {"detail": "Invalid staging_location."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        packaging_verified = request.data.get("packaging_verified")
        if not isinstance(packaging_verified, dict):
            packaging_verified = {
                "boxes_sealed": self._to_bool(request.data.get("boxes_sealed")),
                "job_labels": self._to_bool(request.data.get("job_labels")),
                "quantity_marked": self._to_bool(request.data.get("quantity_marked")),
                "total_quantity": self._to_bool(request.data.get("total_quantity")),
                "fragile_stickers": self._to_bool(request.data.get("fragile_stickers")),
            }

        required_checks = [
            "boxes_sealed",
            "job_labels",
            "quantity_marked",
            "total_quantity",
            "fragile_stickers",
        ]
        incomplete_checks = [
            check_name for check_name in required_checks if not self._to_bool(packaging_verified.get(check_name), False)
        ]
        if incomplete_checks:
            return Response(
                {"detail": "All packaging verification checks must be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        package_photos = request.data.get("package_photos", [])
        if not isinstance(package_photos, list):
            package_photos = []

        default_locked_evp = Decimal("0")
        if job.quote and job.quote.production_cost:
            default_locked_evp = job.quote.production_cost

        locked_evp = self._parse_decimal(request.data.get("locked_evp"), default_locked_evp)
        if locked_evp is None:
            return Response({"detail": "Invalid locked_evp value."}, status=status.HTTP_400_BAD_REQUEST)

        actual_cost = self._parse_decimal(request.data.get("actual_cost"), locked_evp)
        if actual_cost is None:
            return Response({"detail": "Invalid actual_cost value."}, status=status.HTTP_400_BAD_REQUEST)

        notes_to_am = request.data.get("notes_to_am", "")
        mark_urgent = self._to_bool(request.data.get("mark_urgent"), False)
        notify_am = self._to_bool(request.data.get("notify_am"), True)
        notify_via_email = self._to_bool(request.data.get("notify_via_email"), True)

        delivery, _ = Delivery.objects.get_or_create(
            job=job,
            defaults={
                "created_by": user,
            },
        )

        delivery.qc_inspection = latest_qc
        delivery.staging_location = staging_location
        delivery.packaging_verified = packaging_verified
        delivery.package_photos = package_photos
        delivery.notes_to_am = notes_to_am
        delivery.locked_evp = locked_evp
        delivery.actual_cost = actual_cost
        delivery.handoff_confirmed = True
        delivery.handoff_confirmed_at = timezone.now()
        delivery.handoff_confirmed_by = user
        delivery.notify_am = notify_am
        delivery.notify_via_email = notify_via_email
        delivery.mark_urgent = mark_urgent
        delivery.status = "staged"
        delivery.save()

        job.status = "completed"
        if not job.actual_completion:
            job.actual_completion = timezone.now().date()
        job.save(update_fields=["status", "actual_completion", "updated_at"])

        if notify_am and job.client and job.client.account_manager:
            Notification.objects.create(
                recipient=job.client.account_manager,
                notification_type="delivery_ready",
                title=f"Job {job.job_number} ready for dispatch",
                message=f"Staged at {delivery.get_staging_location_display()}. {notes_to_am[:120]}",
                link=f"/job/{job.pk}/",
                related_job=job,
                action_url=f"/job/{job.pk}/",
                action_label="View Job",
            )

        if job.client:
            ActivityLog.objects.create(
                client=job.client,
                activity_type="Order",
                title=f"Delivery handoff complete - {job.job_number}",
                description=f"Production handed over job at {delivery.get_staging_location_display()}",
                created_by=user,
            )

        serializer = self.get_serializer(delivery)
        return Response(
            {
                "detail": "Handoff completed successfully.",
                "delivery": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        aggregates = queryset.aggregate(
            total_count=Count("id"),
            staged_count=Count("id", filter=Q(status="staged")),
            in_transit_count=Count("id", filter=Q(status="in_transit")),
            delivered_count=Count("id", filter=Q(status="delivered")),
            failed_count=Count("id", filter=Q(status="failed")),
            urgent_count=Count("id", filter=Q(mark_urgent=True)),
            handoff_confirmed_count=Count("id", filter=Q(handoff_confirmed=True)),
        )

        summary = {
            "total_count": int(aggregates["total_count"] or 0),
            "staged_count": int(aggregates["staged_count"] or 0),
            "in_transit_count": int(aggregates["in_transit_count"] or 0),
            "delivered_count": int(aggregates["delivered_count"] or 0),
            "failed_count": int(aggregates["failed_count"] or 0),
            "urgent_count": int(aggregates["urgent_count"] or 0),
            "handoff_confirmed_count": int(aggregates["handoff_confirmed_count"] or 0),
        }

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response = self.get_paginated_response(serializer.data)
            response.data["summary"] = summary
            return response

        serializer = self.get_serializer(queryset, many=True)
        return Response({"results": serializer.data, "summary": summary})

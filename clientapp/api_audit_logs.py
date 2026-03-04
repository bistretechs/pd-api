"""
Audit Logs API - Separate module to avoid modifying large api_views.py
"""
from rest_framework import viewsets, serializers, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from django.contrib.auth.models import User

from .models import AuditLog
from .permissions import IsAdmin
 

class AuditLogUserSerializer(serializers.ModelSerializer):
    """Nested serializer for user information"""
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model"""
    user = AuditLogUserSerializer(read_only=True)
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user",
            "action",
            "action_display",
            "model_name",
            "object_id",
            "object_repr",
            "details",
            "ip_address",
            "timestamp",
        ]
        read_only_fields = fields


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for AuditLog
    Provides list and retrieve operations with filtering and search
    """
    queryset = AuditLog.objects.all().select_related("user").order_by("-timestamp")
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["action", "model_name", "user"]
    search_fields = ["user__username", "object_repr", "details", "model_name"]
    ordering_fields = ["timestamp", "action", "model_name"]
    ordering = ["-timestamp"]
    
    @swagger_auto_schema(tags=["Audit Logs"])
    def list(self, request, *args, **kwargs):
        """Get paginated list of audit logs"""
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(tags=["Audit Logs"])
    def retrieve(self, request, *args, **kwargs):
        """Get single audit log detail"""
        return super().retrieve(request, *args, **kwargs)

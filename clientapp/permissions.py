from rest_framework import permissions


def _in_group(user, group_name: str) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=group_name).exists()


class IsAdmin(permissions.BasePermission):
    """Allow Admin group members or superusers."""

    def has_permission(self, request, view):
        return _in_group(request.user, "Admin")


class IsAccountManager(permissions.BasePermission):
    """Allow Account Manager group members or superusers."""

    def has_permission(self, request, view):
        return _in_group(request.user, "Account Manager")


class IsProductionTeam(permissions.BasePermission):
    """Allow Production Team group members or superusers."""

    def has_permission(self, request, view):
        return _in_group(request.user, "Production Team")


class IsCatalogEditor(permissions.BasePermission):
    """Allow Admin, Account Manager, or Production Team members."""

    def has_permission(self, request, view):
        return (
            _in_group(request.user, "Admin")
            or _in_group(request.user, "Account Manager")
            or _in_group(request.user, "Production Team")
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission: Admins/Superusers always allowed; otherwise user must own the object.
    """

    def has_object_permission(self, request, view, obj):
        if _in_group(request.user, "Admin"):
            return True
        owner = getattr(obj, "created_by", None) or getattr(obj, "owner", None)
        return owner == request.user


class IsClient(permissions.BasePermission):
    """Allow Client Portal Users - authenticated only"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Check if user has a client portal profile
        try:
            from .models import ClientPortalUser
            return ClientPortalUser.objects.filter(user=request.user, is_active=True).exists()
        except:
            return False


class IsClientOwner(permissions.BasePermission):
    """
    Object-level: Client can only access their own data
    """

    def has_object_permission(self, request, view, obj):
        from .models import ClientPortalUser
        
        try:
            portal_user = ClientPortalUser.objects.get(user=request.user, is_active=True)
        except:
            return False
        
        # Get client from object (different models have different field names)
        obj_client = getattr(obj, "client", None) or getattr(obj, "portal_user.client", None)
        
        return portal_user.client == obj_client


class IsVendor(permissions.BasePermission):
    """Allow Vendor Portal Users - vendors who have active user profile"""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Check if user is associated with an active vendor
        try:
            from .models import Vendor
            return Vendor.objects.filter(user=request.user, active=True).exists()
        except:
            return False
    
    def has_object_permission(self, request, view, obj):
        """Vendor can only access their own purchase orders"""
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            from .models import Vendor
            vendor = Vendor.objects.get(user=request.user, active=True)
            # Check if object is owned by this vendor
            if hasattr(obj, 'vendor'):
                return obj.vendor == vendor
            return False
        except:
            return False


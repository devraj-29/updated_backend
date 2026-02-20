from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "super_admin"


class CanManageNDAs(BasePermission):
    """super_admin, legal, hr can create/edit. Everyone else read-only."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.can_manage_ndas


class CanAssignNDAs(BasePermission):
    """super_admin, legal, hr, manager can assign. Others read-only."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.can_assign_ndas


class CanManagePeople(BasePermission):
    """super_admin, hr, manager can create/edit. Others read-only."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.can_manage_people


class CanManageUsers(BasePermission):
    """super_admin, hr only."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.can_manage_users

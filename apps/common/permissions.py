from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        owner = getattr(obj, "owner", None) or getattr(obj, "user", None)
        return owner == request.user


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            owner = getattr(obj, "owner", None) or getattr(obj, "user", None)
            return owner == request.user
        owner = getattr(obj, "owner", None) or getattr(obj, "user", None)
        return owner == request.user

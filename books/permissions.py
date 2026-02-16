from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow read for anyone; allow write (update/delete) only for the book's seller.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, 'seller', None) == request.user

from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        return is_verified_staff(request.user)

def is_verified_staff(user):
    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and getattr(user, "is_verified", lambda: False)()
    )

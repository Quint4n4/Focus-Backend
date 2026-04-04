from rest_framework.permissions import BasePermission, IsAuthenticated

VALID_ROLES = {'super_admin', 'admin_area', 'trabajador', 'personal'}


class IsSuperAdmin(BasePermission):
    """Solo el Super Admin puede acceder."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role == 'super_admin'
        )


class IsAdminAreaOrAbove(BasePermission):
    """Admin de Área o Super Admin."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in ('super_admin', 'admin_area')
        )


class IsWorkerOrAbove(BasePermission):
    """
    Cualquier usuario autenticado con un rol válido.
    Equivale a IsAuthenticated + tener un rol reconocido en el sistema.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in VALID_ROLES
        )


class IsOwnerOrAssignee(BasePermission):
    """
    Permite acceso si el usuario:
      - es Super Admin o Admin de Área (acceso total), o
      - es el dueño del objeto (obj.owner), o
      - está asignado al objeto (obj.assigned_to).
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.role in ('super_admin', 'admin_area'):
            return True

        # Comprobar campo owner (puede ser FK o UUID directo)
        owner = getattr(obj, 'owner', None)
        if owner is not None:
            owner_id = getattr(owner, 'pk', owner)
            if owner_id == request.user.pk:
                return True

        # Comprobar campo assigned_to
        assigned_to = getattr(obj, 'assigned_to', None)
        if assigned_to is not None:
            assignee_id = getattr(assigned_to, 'pk', assigned_to)
            if assignee_id == request.user.pk:
                return True

        return False


class IsAreaMember(BasePermission):
    """
    Super Admin: accede a cualquier área.
    Admin de Área: solo puede operar sobre objetos que pertenezcan a su área.
    Trabajador: denegado (escalar a IsOwnerOrAssignee si se necesita acceso propio).
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.role == 'super_admin':
            return True

        if request.user.role == 'admin_area':
            obj_area_id = getattr(obj, 'area_id', None)
            user_area_id = getattr(request.user, 'area_id', None)
            return obj_area_id is not None and obj_area_id == user_area_id

        return False

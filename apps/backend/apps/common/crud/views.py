"""CRUD Framework Views."""

from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from .mixins import CRUDDeleteMixin, CRUDDetailMixin, CRUDFormMixin, CRUDListMixin


class CRUDListView(CRUDListMixin, ListView):
    """Generic CRUD list view."""

    pass


class CRUDCreateView(CRUDFormMixin, CreateView):
    """Generic CRUD create view."""

    def get_permission_required(self):
        """Get required permissions."""
        config = self.get_crud_config()
        if config.create_permission:
            return [config.create_permission]
        if hasattr(self, "model") and self.model:
            return [f"{self.model._meta.app_label}.add_{self.model._meta.model_name}"]
        return []


class CRUDUpdateView(CRUDFormMixin, UpdateView):
    """Generic CRUD update view."""

    def get_permission_required(self):
        """Get required permissions."""
        config = self.get_crud_config()
        if config.update_permission:
            return [config.update_permission]
        if hasattr(self, "model") and self.model:
            return [f"{self.model._meta.app_label}.change_{self.model._meta.model_name}"]
        return []


class CRUDDetailView(CRUDDetailMixin, DetailView):
    """Generic CRUD detail view."""

    pass


class CRUDDeleteView(CRUDDeleteMixin, DeleteView):
    """Generic CRUD delete view."""

    pass

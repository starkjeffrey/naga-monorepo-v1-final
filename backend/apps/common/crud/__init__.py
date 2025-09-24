# CRUD Framework for Django
from .mixins import CRUDDeleteMixin, CRUDDetailMixin, CRUDFormMixin, CRUDListMixin
from .views import (
    CRUDCreateView,
    CRUDDeleteView,
    CRUDDetailView,
    CRUDListView,
    CRUDUpdateView,
)

__all__ = [
    "CRUDCreateView",
    "CRUDDeleteMixin",
    "CRUDDeleteView",
    "CRUDDetailMixin",
    "CRUDDetailView",
    "CRUDFormMixin",
    # Mixins
    "CRUDListMixin",
    # Views
    "CRUDListView",
    "CRUDUpdateView",
]

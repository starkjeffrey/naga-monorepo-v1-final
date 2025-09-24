"""CRUD Framework Configuration."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldConfig:
    """Configuration for a table field."""

    name: str
    verbose_name: str | None = None
    field_type: str = "text"  # text, number, boolean, date, datetime, image, foreign_key
    sortable: bool = True
    searchable: bool = False
    hidden: bool = False
    truncate: int | None = None
    format: str | None = None  # For dates, numbers, etc.
    link_url: str | None = None  # URL pattern for linking
    renderer: Callable | None = None  # Custom renderer function
    css_class: str | None = None
    export: bool = True  # Include in exports

    def __post_init__(self):
        if not self.verbose_name:
            self.verbose_name = self.name.replace("_", " ").title()


@dataclass
class CRUDConfig:
    """Main configuration for CRUD views."""

    # Display settings
    page_title: str = "Data Management"
    page_subtitle: str | None = None
    page_icon: str | None = None

    # Table settings
    fields: list[FieldConfig] = field(default_factory=list)
    default_sort_field: str = "-id"
    paginate_by: int = 25
    paginate_choices: list[int] = field(default_factory=lambda: [10, 25, 50, 100])

    # Features
    enable_search: bool = True
    enable_filters: bool = True
    enable_export: bool = True
    enable_column_toggle: bool = True
    enable_column_reorder: bool = True
    enable_bulk_actions: bool = False
    enable_detail_view: bool = True
    enable_inline_edit: bool = False

    # URLs
    list_url_name: str | None = None
    create_url_name: str | None = None
    update_url_name: str | None = None
    delete_url_name: str | None = None
    detail_url_name: str | None = None

    # Permissions
    list_permission: str | None = None
    create_permission: str | None = None
    update_permission: str | None = None
    delete_permission: str | None = None
    export_permission: str | None = None

    list_template: str = "common/crud/list.html"
    form_template: str = "common/crud/form.html"
    detail_template: str = "common/crud/detail.html"
    delete_template: str = "common/crud/delete.html"
    table_template: str = "common/crud/table.html"

    # Actions
    bulk_actions: list[dict[str, Any]] = field(default_factory=list)
    row_actions: list[dict[str, Any]] = field(default_factory=list)

    # Export settings
    export_formats: list[str] = field(default_factory=lambda: ["csv", "xlsx"])
    export_filename_prefix: str = "export"

    # Custom context
    extra_context: dict[str, Any] = field(default_factory=dict)

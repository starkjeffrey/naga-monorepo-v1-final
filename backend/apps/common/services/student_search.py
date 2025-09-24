"""
Centralized student search service for consistent search logic across the application.

This module provides optimized search functionality for StudentProfile objects,
eliminating duplicated search code and providing consistent performance optimization.
"""

from typing import Any

from django.db.models import Q, QuerySet

from apps.people.models import StudentProfile


class StudentSearchService:
    """
    Centralized service for student search operations.

    Provides consistent search logic, query optimization, and eliminates
    code duplication across different views and endpoints.
    """

    @classmethod
    def get_optimized_search_queryset(
        cls, query_params: dict[str, Any], for_list_view: bool = False, limit: int | None = None
    ) -> QuerySet[StudentProfile]:
        """
        Get optimized queryset for student search with advanced filtering.

        Args:
            query_params: Dictionary of search parameters from request.GET
            for_list_view: Whether this is for a list view (affects prefetching)
            limit: Optional limit on number of results

        Returns:
            Optimized QuerySet for StudentProfile objects
        """
        # Start with base queryset
        queryset = StudentProfile.objects.filter(is_deleted=False).select_related("person")

        # Apply search filters
        search_query = query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(student_id__startswith=search_query)  # Optimized: search by ID prefix
                | Q(person__full_name__icontains=search_query)
                | Q(person__khmer_name__icontains=search_query)
                | Q(person__school_email__icontains=search_query)
                | Q(person__personal_email__icontains=search_query)
            )

        # Status filter
        status = query_params.get("status", "").strip()
        if status:
            queryset = queryset.filter(current_status=status)

        # Add prefetching for list views
        if for_list_view:
            queryset = queryset.prefetch_related("program_enrollments__program")

        # Apply limit if specified
        if limit:
            queryset = queryset[:limit]

        return queryset

    @classmethod
    def quick_search(
        cls, search_term: str, limit: int = 20, active_only: bool = False, include_phone: bool = False
    ) -> QuerySet[StudentProfile]:
        """
        Quick search for students with optimized performance.

        Args:
            search_term: Search term to match against student fields
            limit: Maximum number of results to return
            active_only: Whether to filter by active status only
            include_phone: Whether to include phone number in search (if available)

        Returns:
            QuerySet of matching StudentProfile objects
        """
        if not search_term or len(search_term.strip()) < 2:
            return StudentProfile.objects.none()

        search_term = search_term.strip()

        # Base queryset
        queryset = StudentProfile.objects.filter(is_deleted=False)

        # Build search filters
        search_filters = Q(
            Q(student_id__startswith=search_term)  # Optimized: search by ID prefix
            | Q(person__full_name__icontains=search_term)
            | Q(person__khmer_name__icontains=search_term)
            | Q(person__school_email__icontains=search_term)
            | Q(person__personal_email__icontains=search_term)
        )

        # Add phone search if requested and available
        # Note: Person model may not have phone field - this is defensive coding
        if include_phone:
            try:
                # Check if person model has phone field
                from apps.people.models import Person

                if hasattr(Person, "phone"):
                    search_filters |= Q(person__phone__icontains=search_term)
            except Exception:
                # Silently ignore if phone field doesn't exist
                pass

        queryset = queryset.filter(search_filters)

        # Filter by active status if requested
        if active_only:
            queryset = queryset.filter(current_status__iexact="active")

        # Optimize query with related data
        queryset = queryset.select_related("person").prefetch_related("program_enrollments__program")

        # Apply limit
        return queryset[:limit]

    @classmethod
    def search_by_id_prefix(cls, id_prefix: str, limit: int = 10) -> QuerySet[StudentProfile]:
        """
        Search students by student ID prefix (most optimized search).

        Args:
            id_prefix: Prefix to match against student_id
            limit: Maximum number of results

        Returns:
            QuerySet of matching students
        """
        if not id_prefix:
            return StudentProfile.objects.none()

        return StudentProfile.objects.filter(is_deleted=False, student_id__startswith=id_prefix).select_related(
            "person"
        )[:limit]

"""URL configuration for People app."""

from django.urls import path

from .views.student_profile_adaptive import (
    StudentProfileAdaptiveByStudentIdView,
    StudentProfileAdaptiveTabByStudentIdView,
    StudentProfileAdaptiveTabView,
    StudentProfileAdaptiveView,
)
from .views.student_profile_crud import (
    StudentProfileCreateView,
    StudentProfileDeactivateView,
    StudentProfileDetailView,
    StudentProfileListView,
    StudentProfileUpdateView,
)
from .views.student_profile_mockup import (
    StudentProfileByStudentIdView,
    StudentProfileMockupView,
    StudentProfileTabByStudentIdView,
    StudentProfileTabView,
)
from .views.test_adaptive import TestAdaptiveView
from .views.test_student_adaptive import TestStudentAdaptiveView
from .views.test_student_simple import TestStudentSimpleView

app_name = "people"

urlpatterns = [
    # StudentProfile CRUD URLs
    path("students/", StudentProfileListView.as_view(), name="student-profile-list"),
    path(
        "students/add/",
        StudentProfileCreateView.as_view(),
        name="student-profile-create",
    ),
    path(
        "students/<int:pk>/",
        StudentProfileDetailView.as_view(),
        name="student-profile-detail",
    ),
    path(
        "students/<int:pk>/edit/",
        StudentProfileUpdateView.as_view(),
        name="student-profile-update",
    ),
    path(
        "students/<int:pk>/deactivate/",
        StudentProfileDeactivateView.as_view(),
        name="student-profile-deactivate",
    ),
    # Mockup URLs
    path(
        "students/<int:pk>/mockup/",
        StudentProfileMockupView.as_view(),
        name="student-profile-mockup",
    ),
    path(
        "students/<int:pk>/tab/<str:tab>/",
        StudentProfileTabView.as_view(),
        name="student-profile-tab",
    ),
    # TEST ONLY: Student ID based URLs for easier testing (not for production)
    path(
        "students/id/<int:student_id>/mockup/",
        StudentProfileByStudentIdView.as_view(),
        name="student-profile-mockup-by-id",
    ),
    path(
        "students/id/<int:student_id>/tab/<str:tab>/",
        StudentProfileTabByStudentIdView.as_view(),
        name="student-profile-tab-by-id",
    ),
    # Adaptive Navigation URLs
    path(
        "students/<int:pk>/adaptive/",
        StudentProfileAdaptiveView.as_view(),
        name="student-profile-adaptive",
    ),
    path(
        "students/<int:pk>/adaptive/tab/<str:tab>/",
        StudentProfileAdaptiveTabView.as_view(),
        name="student-profile-adaptive-tab",
    ),
    # TEST ONLY: Adaptive with Student ID
    path(
        "students/id/<int:student_id>/adaptive/",
        StudentProfileAdaptiveByStudentIdView.as_view(),
        name="student-profile-adaptive-by-id",
    ),
    path(
        "students/id/<int:student_id>/adaptive/tab/<str:tab>/",
        StudentProfileAdaptiveTabByStudentIdView.as_view(),
        name="student-profile-adaptive-tab-by-id",
    ),
    # TEST: Adaptive navigation CSS test page (no login required)
    path(
        "test-adaptive/",
        TestAdaptiveView.as_view(),
        name="test-adaptive",
    ),
    # TEST: Student profile adaptive test (no login required)
    path(
        "test-student-adaptive/",
        TestStudentAdaptiveView.as_view(),
        name="test-student-adaptive",
    ),
    path(
        "test-student-simple/",
        TestStudentSimpleView.as_view(),
        name="test-student-simple",
    ),
    # Additional student-related views can be added here
    # path('students/<int:pk>/status/', StudentStatusChangeView.as_view(), name='student-profile-status'),
    # path('students/<int:pk>/emergency-contacts/', EmergencyContactListView.as_view(), name='emergency-contacts'),
]

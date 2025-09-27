"""
Web interface forms module.

This module contains all forms for the user-facing web interface of Naga SIS.
Forms are organized by functionality:
- auth_forms: Authentication forms
- student_forms: Student management forms
- finance_forms: Financial management forms
"""

from .auth_forms import LoginForm, PasswordResetRequestForm, ProfileUpdateForm, RoleSwitchForm
from .finance_forms import InvoiceCreateForm, InvoiceSearchForm, PaymentProcessForm
from .student_forms import StudentCreateForm, StudentSearchForm, StudentUpdateForm

__all__ = [
    # Finance forms
    "InvoiceCreateForm",
    "InvoiceSearchForm",
    # Auth forms
    "LoginForm",
    "PasswordResetRequestForm",
    "PaymentProcessForm",
    "ProfileUpdateForm",
    "RoleSwitchForm",
    # Student forms
    "StudentCreateForm",
    "StudentSearchForm",
    "StudentUpdateForm",
]

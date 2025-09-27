"""
Custom authentication backend to handle email-based authentication
with the standard Django admin login form.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Authentication backend that accepts email in the username field.

    This is needed because Django's admin login form sends 'username'
    as the parameter name, but our custom User model uses email as
    the USERNAME_FIELD.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate using email address.

        The 'username' parameter will contain the email address.
        """
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        if username is None or password is None:
            return None

        try:
            # Try to fetch the user by email
            user = User.objects.get(email=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)

        return None

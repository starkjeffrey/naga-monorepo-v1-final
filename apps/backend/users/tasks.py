import dramatiq

from .models import User


@dramatiq.actor
def get_users_count():
    """A pointless Dramatiq task to demonstrate usage."""
    return User.objects.count()

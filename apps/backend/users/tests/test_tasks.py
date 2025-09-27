import pytest

from users.tasks import get_users_count
from users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_user_count():
    """A basic test to execute the get_users_count Dramatiq task."""
    batch_size = 3
    UserFactory.create_batch(batch_size)
    # Dramatiq tasks can be called directly for testing
    task_result = get_users_count()
    assert task_result == batch_size

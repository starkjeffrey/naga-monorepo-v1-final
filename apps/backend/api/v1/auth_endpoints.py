"""Authentication endpoints for staff web interface.

This module provides JWT-based authentication endpoints for the React staff interface.
"""

from datetime import UTC, datetime, timedelta

import jwt
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from ninja import Router, Schema
from ninja.errors import AuthenticationError

User = get_user_model()
router = Router(tags=["Authentication"])

# JWT Configuration
JWT_SECRET_KEY = getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7


# Schemas
class LoginSchema(Schema):
    email: str
    password: str


class TokenResponseSchema(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    user: dict


class RefreshTokenSchema(Schema):
    refresh_token: str


class UserProfileSchema(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    is_staff: bool
    is_superuser: bool
    roles: list[str]


class MessageSchema(Schema):
    message: str


def create_access_token(user_id: int) -> tuple[str, int]:
    """Create JWT access token.

    Returns:
        tuple: (token, expires_in_seconds)
    """
    expire = datetime.now(UTC) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_in = JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60

    payload = {"user_id": user_id, "exp": expire, "iat": datetime.now(UTC), "type": "access"}
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token, expires_in


def create_refresh_token(user_id: int) -> str:
    """Create JWT refresh token."""
    expire = datetime.now(UTC) + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {"user_id": user_id, "exp": expire, "iat": datetime.now(UTC), "type": "refresh"}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str | None = None) -> dict | None:
    """Verify and decode JWT token."""
    if token_type is None:
        token_type = "access"
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_roles(user) -> list[str]:
    """Get user roles for the frontend."""
    roles = []

    if user.is_superuser:
        roles.append("admin")
    if user.is_staff:
        roles.append("staff")

    # Add role based on groups
    for group in user.groups.all():
        roles.append(group.name.lower())

    # Check for specific app permissions
    if user.has_perm("finance.view_invoice"):
        roles.append("finance")
    if user.has_perm("academic.view_student"):
        roles.append("academic")

    return list(set(roles))  # Remove duplicates


@router.post("/login/", response=TokenResponseSchema)
def login(request, credentials: LoginSchema):
    """Authenticate user and return JWT tokens.

    This endpoint authenticates staff users and returns both access and refresh tokens
    for the React staff interface.
    """
    # Try authentication with email
    user = authenticate(request, username=credentials.email, password=credentials.password)

    if not user:
        # Try to find user by email and authenticate
        try:
            user_obj = User.objects.get(email=credentials.email)
            user = authenticate(request, username=user_obj.username, password=credentials.password)
        except User.DoesNotExist:
            pass

    if not user:
        raise AuthenticationError("Invalid credentials")

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Create tokens
    access_token, expires_in = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)

    # Get user roles
    roles = get_user_roles(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "full_name": user.get_full_name()
            if hasattr(user, "get_full_name")
            else f"{user.first_name} {user.last_name}",
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "roles": roles,
        },
    }


@router.post("/refresh/", response=TokenResponseSchema)
def refresh_token(request, data: RefreshTokenSchema):
    """Refresh access token using refresh token."""
    payload = verify_token(data.refresh_token, "refresh")

    if not payload:
        raise AuthenticationError("Invalid or expired refresh token")

    try:
        user = User.objects.get(id=payload["user_id"])
    except User.DoesNotExist:
        raise AuthenticationError("User not found") from None

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Create new tokens
    access_token, expires_in = create_access_token(user.id)
    new_refresh_token = create_refresh_token(user.id)

    # Get user roles
    roles = get_user_roles(user)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "user": {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "full_name": user.get_full_name()
            if hasattr(user, "get_full_name")
            else f"{user.first_name} {user.last_name}",
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "roles": roles,
        },
    }


@router.get("/profile/", response=UserProfileSchema)
def get_profile(request):
    """Get current user profile.

    This endpoint requires authentication via JWT token in the Authorization header.
    """
    # Get token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise AuthenticationError("Missing or invalid authorization header")

    token = auth_header[7:]  # Remove 'Bearer ' prefix
    payload = verify_token(token, "access")

    if not payload:
        raise AuthenticationError("Invalid or expired token")

    try:
        user = User.objects.get(id=payload["user_id"])
    except User.DoesNotExist:
        raise AuthenticationError("User not found") from None

    if not user.is_active:
        raise AuthenticationError("Account is disabled")

    # Get user roles
    roles = get_user_roles(user)

    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "roles": roles,
    }


@router.post("/logout/", response=MessageSchema)
def logout(request):
    """Logout user (client-side token removal).

    Note: This is a placeholder endpoint. In a JWT-based system,
    logout is typically handled client-side by removing the token.
    For added security, you could implement token blacklisting here.
    """
    return {"message": "Logged out successfully"}

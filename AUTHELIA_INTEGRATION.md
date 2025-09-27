# Authelia Integration with React/JWT Architecture

## 🔐 Overview

Yes, React/JWT can work seamlessly with Authelia! There are multiple integration patterns, each with different benefits.

## 🏗️ Architecture Options

### Option 1: Authelia as Primary Auth Gateway (Recommended)

```mermaid
[User] → [Authelia Portal] → [React App] → [Django API]
         ↓                    ↓             ↓
    [LDAP/OIDC]        [JWT from Authelia]  [Verify JWT]
```

**Benefits:**
- Single Sign-On (SSO) across all apps
- Centralized authentication
- 2FA/MFA handled by Authelia
- Session management by Authelia

### Option 2: Hybrid Authentication

```mermaid
[User] → [React App] → [Authelia] → [Django API]
                    ↘              ↗
                     [Direct JWT Auth]
```

**Benefits:**
- Flexibility for mobile apps
- Can bypass Authelia for API-only access
- Gradual migration path

### Option 3: Authelia Forward Auth + JWT

```mermaid
[User] → [Nginx/Traefik] → [Authelia Forward Auth] → [React App]
                                                    ↓
                                            [Django API + JWT]
```

**Benefits:**
- Zero-trust architecture
- Every request validated
- No client-side auth logic needed

## 📋 Implementation Strategies

### 1. Authelia with OIDC (OpenID Connect)

**Authelia Configuration:**
```yaml
# authelia/configuration.yml
identity_providers:
  oidc:
    enable: true
    cors:
      endpoints:
        - authorization
        - token
        - userinfo
      allowed_origins:
        - https://staff.naga.edu
    clients:
      - id: naga-staff-web
        description: Naga Staff Web Interface
        secret: '$pbkdf2-sha512$310000$...' # hashed secret
        authorization_policy: two_factor
        redirect_uris:
          - https://staff.naga.edu/callback
        scopes:
          - openid
          - profile
          - email
          - groups
        grant_types:
          - authorization_code
          - refresh_token
        response_types:
          - code
        token_endpoint_auth_method: client_secret_post
```

**React Integration:**
```tsx
// staff-web/src/services/auth.service.ts
import { UserManager, WebStorageStateStore } from 'oidc-client-ts';

const settings = {
  authority: 'https://auth.naga.edu',
  client_id: 'naga-staff-web',
  client_secret: process.env.REACT_APP_OIDC_SECRET,
  redirect_uri: 'https://staff.naga.edu/callback',
  response_type: 'code',
  scope: 'openid profile email groups',
  post_logout_redirect_uri: 'https://staff.naga.edu/',
  userStore: new WebStorageStateStore({ store: window.localStorage })
};

const userManager = new UserManager(settings);

export class AuthService {
  async login(): Promise<void> {
    await userManager.signinRedirect();
  }

  async handleCallback(): Promise<void> {
    const user = await userManager.signinRedirectCallback();
    // Convert OIDC token to internal JWT
    const response = await fetch('/api/auth/oidc-login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: user.id_token })
    });
    const { access_token } = await response.json();
    localStorage.setItem('jwt_token', access_token);
  }

  async logout(): Promise<void> {
    await userManager.signoutRedirect();
  }
}
```

### 2. Authelia Forward Authentication

**Docker Compose Setup:**
```yaml
# docker-compose.yml
services:
  authelia:
    image: authelia/authelia:latest
    container_name: authelia
    volumes:
      - ./authelia:/config
    networks:
      - naga_network
    environment:
      - TZ=Asia/Phnom_Penh
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.authelia.rule=Host(`auth.naga.edu`)"
      - "traefik.http.middlewares.authelia.forwardauth.address=http://authelia:9091/api/verify?rd=https://auth.naga.edu"
      - "traefik.http.middlewares.authelia.forwardauth.trustForwardHeader=true"
      - "traefik.http.middlewares.authelia.forwardauth.authResponseHeaders=Remote-User,Remote-Groups,Remote-Name,Remote-Email"

  traefik:
    image: traefik:v2.10
    container_name: traefik
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./traefik:/etc/traefik
    networks:
      - naga_network

  staff-web:
    image: naga-staff-web:latest
    container_name: staff-web
    networks:
      - naga_network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.staff-web.rule=Host(`staff.naga.edu`)"
      - "traefik.http.routers.staff-web.middlewares=authelia@docker"

  django-api:
    image: naga-backend:latest
    container_name: django-api
    networks:
      - naga_network
    environment:
      - AUTHELIA_HEADER_USER=Remote-User
      - AUTHELIA_HEADER_GROUPS=Remote-Groups
```

### 3. Django Backend Integration

**Update Django Authentication:**
```python
# backend/api/v1/authelia_auth.py
"""Authelia integration for Django API."""

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja import Router, Schema
from ninja.security import HttpBearer

User = get_user_model()
router = Router(tags=["Authelia Authentication"])

class AutheliaAuth(HttpBearer):
    """Authelia header authentication."""

    def authenticate(self, request, token):
        # Check Authelia headers
        remote_user = request.headers.get('Remote-User')
        remote_groups = request.headers.get('Remote-Groups', '').split(',')
        remote_email = request.headers.get('Remote-Email')

        if remote_user:
            # User authenticated by Authelia
            user, created = User.objects.get_or_create(
                username=remote_user,
                defaults={'email': remote_email}
            )

            # Update user groups based on Authelia groups
            if 'admins' in remote_groups:
                user.is_staff = True
                user.is_superuser = True
            elif 'staff' in remote_groups:
                user.is_staff = True

            user.save()
            request.authelia_groups = remote_groups
            return user

        # Fall back to JWT authentication for mobile/API clients
        if token:
            try:
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET_KEY,
                    algorithms=['HS256']
                )
                user = User.objects.get(id=payload['user_id'])
                return user
            except:
                pass

        return None

# OIDC Login endpoint for React
class OIDCLoginSchema(Schema):
    id_token: str

class TokenResponseSchema(Schema):
    access_token: str
    refresh_token: str
    user: dict

@router.post("/oidc-login/", response=TokenResponseSchema)
def oidc_login(request, data: OIDCLoginSchema):
    """Convert OIDC token from Authelia to internal JWT."""

    # Verify OIDC token with Authelia's public key
    try:
        # In production, verify with Authelia's JWKS endpoint
        payload = jwt.decode(
            data.id_token,
            options={"verify_signature": False}  # For demo only!
        )

        email = payload.get('email')
        groups = payload.get('groups', [])
        name = payload.get('name')

        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': name.split()[0] if name else '',
                'last_name': ' '.join(name.split()[1:]) if name else '',
            }
        )

        # Update permissions based on Authelia groups
        if 'admins' in groups:
            user.is_staff = True
            user.is_superuser = True
        elif 'staff' in groups:
            user.is_staff = True

        user.save()

        # Generate internal JWT
        from .auth_endpoints import create_access_token, create_refresh_token
        access_token, _ = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.get_full_name(),
                'groups': groups,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser
            }
        }
    except Exception as e:
        raise AuthenticationError(f"Invalid OIDC token: {e}")
```

### 4. React App with Authelia Protection

**App.tsx with Auth Check:**
```tsx
// staff-web/src/App.tsx
import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { AuthService } from './services/auth.service';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/Login';
import { CallbackPage } from './pages/Callback';

const authService = new AuthService();

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      // Check if we have Authelia headers (server-side rendering)
      const response = await fetch('/api/auth/me/');
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
      } else {
        // Check for stored JWT token
        const token = localStorage.getItem('jwt_token');
        if (token) {
          const profileResponse = await fetch('/api/auth/profile/', {
            headers: { 'Authorization': `Bearer ${token}` }
          });
          if (profileResponse.ok) {
            const userData = await profileResponse.json();
            setUser(userData);
          }
        }
      }
    } catch (error) {
      console.error('Auth check failed:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <ConfigProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/callback" element={<CallbackPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/*"
            element={
              user ? (
                <AppLayout user={user}>
                  <Routes>
                    {/* Protected routes */}
                  </Routes>
                </AppLayout>
              ) : (
                <Navigate to="/login" />
              )
            }
          />
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}
```

## 🔄 Authentication Flows

### Flow 1: Web Browser (Authelia Primary)
1. User visits `staff.naga.edu`
2. Traefik forwards to Authelia
3. Authelia shows login portal
4. User authenticates (with 2FA if configured)
5. Authelia sets session cookie
6. User redirected to React app
7. React app receives user info via headers
8. React requests JWT from Django for API calls

### Flow 2: Mobile App (Direct JWT)
1. Mobile app shows login screen
2. Credentials sent to `/api/auth/login/`
3. Django validates against LDAP/database
4. JWT tokens returned
5. Mobile app uses JWT for all API calls

### Flow 3: API Client (Service Account)
1. Service authenticates with Authelia API
2. Receives service token
3. Uses token for API access
4. Django validates token

## 🛡️ Security Benefits

1. **Multi-Factor Authentication**: Authelia handles TOTP, WebAuthn, Duo
2. **Single Sign-On**: One login for all services
3. **Session Management**: Centralized session control
4. **Access Control**: Fine-grained permissions via groups
5. **Audit Logging**: All auth events logged centrally
6. **Password Policies**: Enforced by Authelia
7. **Account Lockout**: Brute force protection

## 📦 Required Packages

**React:**
```json
{
  "dependencies": {
    "oidc-client-ts": "^2.4.0",
    "react-oidc-context": "^2.3.1"
  }
}
```

**Django:**
```python
# Already in pyproject.toml
PyJWT>=2.8.0
```

**Docker:**
```yaml
services:
  authelia:
    image: authelia/authelia:latest
  redis:
    image: redis:alpine  # For Authelia sessions
  postgres:
    image: postgres:18  # For Authelia data
```

## 🚀 Migration Path

### Phase 1: Setup Authelia (Week 1)
1. Deploy Authelia with Docker
2. Configure LDAP/database backend
3. Setup OIDC provider
4. Test with sample app

### Phase 2: Integrate React (Week 2)
1. Add OIDC client to React
2. Implement callback handling
3. Store tokens securely
4. Test authentication flow

### Phase 3: Update Django (Week 3)
1. Add Authelia header authentication
2. Implement OIDC token validation
3. Maintain JWT for mobile compatibility
4. Test all auth methods

### Phase 4: Production (Week 4)
1. Configure Traefik/Nginx
2. Setup SSL certificates
3. Configure 2FA policies
4. Deploy to production

## 🔧 Environment Variables

```bash
# .env.production
AUTHELIA_URL=https://auth.naga.edu
AUTHELIA_CLIENT_ID=naga-staff-web
AUTHELIA_CLIENT_SECRET=your-secret-here
AUTHELIA_REDIRECT_URI=https://staff.naga.edu/callback

# Django settings
AUTHELIA_ENABLED=True
AUTHELIA_HEADER_USER=Remote-User
AUTHELIA_HEADER_GROUPS=Remote-Groups
AUTHELIA_HEADER_EMAIL=Remote-Email

# React
REACT_APP_AUTHELIA_URL=https://auth.naga.edu
REACT_APP_OIDC_CLIENT_ID=naga-staff-web
```

## 📊 Comparison Table

| Feature | Django JWT Only | Authelia + JWT |
|---------|----------------|----------------|
| SSO | ❌ | ✅ |
| 2FA/MFA | Manual implementation | ✅ Built-in |
| LDAP Integration | Django-ldap | ✅ Native |
| Session Management | JWT expiry only | ✅ Full control |
| Password Reset | Custom | ✅ Built-in |
| Account Lockout | Custom | ✅ Built-in |
| Audit Logging | Django only | ✅ Centralized |
| Mobile Support | ✅ | ✅ |
| Complexity | Lower | Higher (but more features) |

## 🎯 Recommendation

**Use Authelia + JWT Hybrid Approach:**
- Authelia for web staff interface (SSO, 2FA)
- Direct JWT for mobile apps
- Authelia forward auth for admin tools
- OIDC for third-party integrations

This gives you enterprise-grade authentication while maintaining flexibility for different client types.

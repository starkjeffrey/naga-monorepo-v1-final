# React Staff Web Interface Architecture

## 🔍 Current State Analysis

### Existing Components

#### 1. **Backend API** (`/backend/api/`)
- **Framework**: Django Ninja
- **Base URL**: `/api/`
- **Version**: v1.0.0
- **Existing Endpoints**:
  - `/api/health/` - System health check
  - `/api/info/` - API information
  - `/api/grading/` - Grading endpoints
  - `/api/finance/` - Finance endpoints
  - `/api/attendance/` - Attendance endpoints

#### 2. **Authentication System**
- **Current Auth**:
  - JWT authentication class exists (`apps.mobile.auth.JWTAuth`)
  - Session-based auth for deprecated HTMX interface
- **Missing**:
  - ❌ Login endpoint for staff (JWT token generation)
  - ❌ Refresh token endpoint
  - ❌ User profile endpoint
  - ❌ Role/permissions endpoint

#### 3. **Deprecated HTMX Interface** (`/backend/apps/web_interface_deprecated/`)
- **Status**: DEPRECATED - to be replaced
- **Location**: Root path ("/")
- **Components**: Login, dashboard, sidebar, student management
- **Why deprecated**: Moving to modern React SPA architecture

## 🏗️ Proposed React Architecture

### Directory Structure
```
naga-monorepo-v1-final/
├── backend/              # Django API backend
├── frontend-vue-old/     # Legacy Vue.js app
├── mobile/               # React Native mobile app
├── staff-web/            # 🆕 NEW React Staff Interface
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.tsx      # Main layout wrapper
│   │   │   │   ├── Header.tsx         # Top navigation bar
│   │   │   │   ├── Sidebar.tsx        # Side navigation menu
│   │   │   │   └── Footer.tsx         # Footer component
│   │   │   ├── auth/
│   │   │   │   ├── LoginForm.tsx      # Login component
│   │   │   │   ├── ProtectedRoute.tsx # Route protection
│   │   │   │   └── AuthProvider.tsx   # Auth context
│   │   │   └── common/
│   │   ├── pages/
│   │   │   ├── Login.tsx              # Login page
│   │   │   ├── Dashboard.tsx          # Dashboard page
│   │   │   ├── Students/              # Student management
│   │   │   ├── Finance/               # Finance management
│   │   │   └── Academic/              # Academic management
│   │   ├── services/
│   │   │   ├── api.ts                 # API client setup
│   │   │   ├── auth.service.ts        # Authentication service
│   │   │   └── [domain].service.ts    # Domain-specific services
│   │   ├── hooks/
│   │   │   ├── useAuth.ts             # Authentication hook
│   │   │   └── useApi.ts              # API hook
│   │   ├── store/                     # State management (Zustand/Redux)
│   │   ├── types/                     # TypeScript types
│   │   ├── utils/                     # Utility functions
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts               # Vite for fast development
│   └── project.json                 # NX configuration
└── libs/shared/api-types/           # Shared TypeScript types
```

### Technology Stack
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite (fast HMR and builds)
- **Routing**: React Router v6
- **State Management**: Zustand (lightweight) or Redux Toolkit
- **UI Components**:
  - Ant Design (enterprise-ready components)
  - Tailwind CSS (utility-first styling)
- **API Client**: Axios with interceptors
- **Form Handling**: React Hook Form + Zod validation
- **Authentication**: JWT with refresh tokens
- **Testing**: Vitest + React Testing Library

## 📍 Component Locations

### 1. **Layout Components** (`staff-web/src/components/layout/`)

#### AppLayout.tsx
```tsx
// Main layout wrapper that includes header, sidebar, and content area
interface AppLayoutProps {
  children: React.ReactNode;
}

const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  // Contains:
  // - Sidebar (collapsible)
  // - Header with user info
  // - Main content area
  // - Footer
};
```

#### Sidebar.tsx
```tsx
// Navigation sidebar with role-based menu items
const Sidebar: React.FC = () => {
  // Menu structure based on user role
  // - Dashboard
  // - Students
  // - Academic
  // - Finance
  // - Reports
  // - Settings
};
```

#### Header.tsx
```tsx
// Top navigation with user profile, notifications, and quick actions
const Header: React.FC = () => {
  // Contains:
  // - Logo/Brand
  // - Search bar
  // - Notifications
  // - User profile dropdown
  // - Logout
};
```

### 2. **Authentication Flow**

#### Missing API Endpoints (Need to Create)
```python
# backend/api/v1/auth_endpoints.py (NEW FILE)

@api.post("/auth/login/", response=LoginResponse)
def login(request, credentials: LoginSchema):
    """Generate JWT token for staff login"""

@api.post("/auth/refresh/", response=TokenResponse)
def refresh_token(request, refresh: RefreshTokenSchema):
    """Refresh JWT token"""

@api.get("/auth/profile/", auth=jwt_auth, response=UserProfileSchema)
def get_profile(request):
    """Get current user profile and permissions"""

@api.post("/auth/logout/", auth=jwt_auth)
def logout(request):
    """Invalidate token (if using blacklist)"""
```

## 🚀 Implementation Steps

### Phase 1: Foundation (Week 1)
1. ✅ Fix Django settings/URLs
2. Create `staff-web` directory structure
3. Initialize React project with Vite and TypeScript
4. Configure NX for the new project
5. Set up base routing and layout components

### Phase 2: Authentication (Week 2)
1. Create JWT login endpoint in Django
2. Build login page and authentication service
3. Implement protected routes
4. Add token refresh mechanism
5. Create user context/store

### Phase 3: Core UI (Week 3)
1. Build AppLayout with sidebar and header
2. Create dashboard page
3. Implement navigation system
4. Add role-based menu rendering
5. Style with Tailwind + Ant Design

### Phase 4: Feature Migration (Weeks 4-8)
1. Student management module
2. Academic module
3. Finance module
4. Reports module
5. Settings and user preferences

## 🔐 Why Your Login Failed

Your superuser login is failing because:

1. **URL Mismatch**: The root path ("/") points to `web_interface_deprecated` which doesn't have proper authentication
2. **No API Login**: There's no JWT login endpoint for API-based authentication
3. **Session vs JWT**: The system is confused between session-based (HTMX) and token-based (API) auth

### Immediate Fix for Login
```bash
# 1. Access Django admin directly
http://localhost:8001/admin/

# 2. Or create a simple API login endpoint
cd backend
docker compose -f docker-compose.local.yml run --rm django python manage.py shell

# Create a test token manually
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.get(email='stark.jeffrey@pucsr.edu.kh')
# Generate JWT token here
```

## 📊 API Endpoints Summary

### Currently Available
- ✅ `/api/health/` - Health check
- ✅ `/api/grading/*` - Grading operations
- ✅ `/api/finance/*` - Finance operations
- ✅ `/api/attendance/*` - Attendance operations

### Need to Create
- ❌ `/api/auth/login/` - Staff login
- ❌ `/api/auth/refresh/` - Token refresh
- ❌ `/api/auth/profile/` - User profile
- ❌ `/api/people/*` - People management
- ❌ `/api/students/*` - Student operations
- ❌ `/api/enrollment/*` - Enrollment management
- ❌ `/api/academic-records/*` - Academic records

## 🎯 Next Steps

1. **Create staff-web React project**:
   ```bash
   npm create vite@latest staff-web -- --template react-ts
   cd staff-web
   npm install
   ```

2. **Add to NX workspace**:
   ```bash
   # Update nx.json and package.json
   # Create staff-web/project.json
   ```

3. **Create login endpoint**:
   ```python
   # backend/api/v1/auth_endpoints.py
   # Implement JWT token generation
   ```

4. **Build basic layout**:
   - Create AppLayout component
   - Add Sidebar with navigation
   - Implement Header with user info
   - Set up routing

## 📝 Notes

- The deprecated HTMX interface has all the UI patterns we need to replicate
- Use `/backend/apps/web_interface_deprecated/` as reference for features
- API types are shared via `/libs/shared/api-types/`
- Mobile app (`/mobile/`) uses React Native, can share some logic
- Authentication should be unified across web and mobile using JWT
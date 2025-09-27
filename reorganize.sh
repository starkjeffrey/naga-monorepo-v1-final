#!/bin/bash

# Project Reorganization Script
# This script transforms your current messy structure into a clean monorepo
# Run this from your project root directory

set -e  # Exit on any error

echo "🚀 Starting project reorganization..."
echo "⚠️  IMPORTANT: This script will move many files. Consider backing up your project first!"
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Create the new monorepo structure
log "Creating new directory structure..."

# Main directories
mkdir -p apps/backend
mkdir -p apps/staff-web
mkdir -p apps/mobile
mkdir -p shared/{types,constants,docs,api-contracts}
mkdir -p tools/{scripts,analysis,screenshots}
mkdir -p docs/{architecture,api,deployment}
mkdir -p config/{docker,ci}

# ============================================================================
# MOVE BACKEND (Django)
# ============================================================================

log "Moving Django backend..."

# Move main backend directory
if [ -d "backend" ]; then
    # Move the entire backend directory content
    mv backend/* apps/backend/ 2>/dev/null || true
    mv backend/.* apps/backend/ 2>/dev/null || true
    rmdir backend
    log "✅ Backend moved to apps/backend"
else
    warn "Backend directory not found"
fi

# ============================================================================
# MOVE STAFF-WEB (React Frontend)
# ============================================================================

log "Moving and cleaning up staff-web..."

if [ -d "staff-web" ]; then
    # Create temp directory for cleanup
    mkdir -p temp_staff_web
    
    # Move essential files first
    log "Moving essential staff-web files..."
    
    # Core config files
    [ -f "staff-web/package.json" ] && mv "staff-web/package.json" "temp_staff_web/"
    [ -f "staff-web/package-lock.json" ] && mv "staff-web/package-lock.json" "temp_staff_web/"
    [ -f "staff-web/vite.config.ts" ] && mv "staff-web/vite.config.ts" "temp_staff_web/"
    [ -f "staff-web/tsconfig.json" ] && mv "staff-web/tsconfig.json" "temp_staff_web/"
    [ -f "staff-web/tsconfig.app.json" ] && mv "staff-web/tsconfig.app.json" "temp_staff_web/"
    [ -f "staff-web/tsconfig.node.json" ] && mv "staff-web/tsconfig.node.json" "temp_staff_web/"
    [ -f "staff-web/tailwind.config.js" ] && mv "staff-web/tailwind.config.js" "temp_staff_web/"
    [ -f "staff-web/postcss.config.js" ] && mv "staff-web/postcss.config.js" "temp_staff_web/"
    [ -f "staff-web/project.json" ] && mv "staff-web/project.json" "temp_staff_web/"
    [ -f "staff-web/README.md" ] && mv "staff-web/README.md" "temp_staff_web/"
    
    # Move node_modules and public (keep as-is for now)
    [ -d "staff-web/node_modules" ] && mv "staff-web/node_modules" "temp_staff_web/"
    [ -d "staff-web/public" ] && mv "staff-web/public" "temp_staff_web/"
    
    # Clean up and reorganize src directory
    log "Reorganizing src directory structure..."
    
    mkdir -p temp_staff_web/src/{app,features,shared,api,types}
    mkdir -p temp_staff_web/src/features/{auth,students,finance,reports,enrollment,innovation,academic}
    mkdir -p temp_staff_web/src/features/{auth,students,finance,reports,enrollment,innovation,academic}/{components,pages,services}
    mkdir -p temp_staff_web/src/shared/{components,hooks,utils,constants,pages}
    
    # Move main App file (keep only the primary one)
    if [ -f "staff-web/src/App.tsx" ]; then
        mv "staff-web/src/App.tsx" "temp_staff_web/src/app/"
    fi
    
    # Move App.css and main.tsx
    [ -f "staff-web/src/App.css" ] && mv "staff-web/src/App.css" "temp_staff_web/src/app/"
    [ -f "staff-web/src/main.tsx" ] && mv "staff-web/src/main.tsx" "temp_staff_web/src/app/"
    [ -f "staff-web/src/index.css" ] && mv "staff-web/src/index.css" "temp_staff_web/src/app/"
    
    # Move assets
    [ -d "staff-web/src/assets" ] && mv "staff-web/src/assets" "temp_staff_web/src/shared/"
    
    # Reorganize components by feature
    if [ -d "staff-web/src/components" ]; then
        # Create component directories first
        mkdir -p temp_staff_web/src/features/{auth,enrollment,students,reports}/components
        mkdir -p temp_staff_web/src/shared/components/{common,ui,layout,patterns}
        
        # Move auth components
        [ -d "staff-web/src/components/auth" ] && mv "staff-web/src/components/auth" "temp_staff_web/src/features/auth/components/"
        
        # Move enrollment components
        [ -d "staff-web/src/components/enrollment" ] && mv "staff-web/src/components/enrollment" "temp_staff_web/src/features/enrollment/components/"
        
        # Move student components
        [ -d "staff-web/src/components/students" ] && mv "staff-web/src/components/students" "temp_staff_web/src/features/students/components/"
        
        # Move report components
        [ -d "staff-web/src/components/reports" ] && mv "staff-web/src/components/reports" "temp_staff_web/src/features/reports/components/"
        
        # Move common/shared components
        [ -d "staff-web/src/components/common" ] && mv "staff-web/src/components/common" "temp_staff_web/src/shared/components/"
        [ -d "staff-web/src/components/ui" ] && mv "staff-web/src/components/ui" "temp_staff_web/src/shared/components/"
        [ -d "staff-web/src/components/layout" ] && mv "staff-web/src/components/layout" "temp_staff_web/src/shared/components/"
        [ -d "staff-web/src/components/patterns" ] && mv "staff-web/src/components/patterns" "temp_staff_web/src/shared/components/"
        
        # Move remaining components to shared
        for comp in staff-web/src/components/*; do
            if [ -d "$comp" ]; then
                mv "$comp" "temp_staff_web/src/shared/components/"
            fi
        done
        
        # Move individual component files
        for comp in staff-web/src/components/*.tsx staff-web/src/components/*.ts; do
            if [ -f "$comp" ]; then
                mv "$comp" "temp_staff_web/src/shared/components/"
            fi
        done
    fi
    
    # Move pages to features
    if [ -d "staff-web/src/pages" ]; then
        # Create feature page directories first
        mkdir -p temp_staff_web/src/features/{academic,students,finance,innovation,auth,reports}/pages
        
        [ -d "staff-web/src/pages/Academic" ] && mv "staff-web/src/pages/Academic" "temp_staff_web/src/features/academic/pages/"
        [ -d "staff-web/src/pages/Students" ] && mv "staff-web/src/pages/Students" "temp_staff_web/src/features/students/pages/"
        [ -d "staff-web/src/pages/Finance" ] && mv "staff-web/src/pages/Finance" "temp_staff_web/src/features/finance/pages/"
        [ -d "staff-web/src/pages/Innovation" ] && mv "staff-web/src/pages/Innovation" "temp_staff_web/src/features/innovation/pages/"
        [ -d "staff-web/src/pages/Login" ] && mv "staff-web/src/pages/Login" "temp_staff_web/src/features/auth/pages/"
        [ -d "staff-web/src/pages/Dashboard" ] && mv "staff-web/src/pages/Dashboard" "temp_staff_web/src/shared/pages/"
        [ -d "staff-web/src/pages/reports" ] && mv "staff-web/src/pages/reports" "temp_staff_web/src/features/reports/pages/"
        
        # Move remaining pages
        for page in staff-web/src/pages/*; do
            if [ -d "$page" ] || [ -f "$page" ]; then
                mv "$page" "temp_staff_web/src/shared/pages/"
            fi
        done
    fi
    
    # Move services to features and shared
    if [ -d "staff-web/src/services" ]; then
        # Create service directories first
        mkdir -p temp_staff_web/src/features/{auth,students,finance,enrollment}/services
        
        [ -f "staff-web/src/services/auth.service.ts" ] && mv "staff-web/src/services/auth.service.ts" "temp_staff_web/src/features/auth/services/"
        [ -f "staff-web/src/services/student.service.ts" ] && mv "staff-web/src/services/student.service.ts" "temp_staff_web/src/features/students/services/"
        [ -f "staff-web/src/services/financeService.ts" ] && mv "staff-web/src/services/financeService.ts" "temp_staff_web/src/features/finance/services/"
        [ -f "staff-web/src/services/enrollment.service.ts" ] && mv "staff-web/src/services/enrollment.service.ts" "temp_staff_web/src/features/enrollment/services/"
        
        # Move remaining services to api
        for service in staff-web/src/services/*; do
            if [ -f "$service" ]; then
                mv "$service" "temp_staff_web/src/api/"
            fi
        done
        
        # Move service tests
        [ -d "staff-web/src/services/__tests__" ] && mv "staff-web/src/services/__tests__" "temp_staff_web/src/api/"
    fi
    
    # Move hooks to shared
    [ -d "staff-web/src/hooks" ] && mv "staff-web/src/hooks" "temp_staff_web/src/shared/"
    
    # Move store/state management
    if [ -d "staff-web/src/store" ]; then
        mv "staff-web/src/store" "temp_staff_web/src/shared/"
    fi
    
    # Move types
    if [ -d "staff-web/src/types" ]; then
        mv "staff-web/src/types"/* "temp_staff_web/src/types/" 2>/dev/null || true
        rmdir "staff-web/src/types" 2>/dev/null || true
    fi
    
    # Move utils
    if [ -d "staff-web/src/utils" ]; then
        mv "staff-web/src/utils"/* "temp_staff_web/src/shared/utils/" 2>/dev/null || true
        rmdir "staff-web/src/utils" 2>/dev/null || true
    fi
    
    # Move theme
    [ -d "staff-web/src/theme" ] && mv "staff-web/src/theme" "temp_staff_web/src/shared/"
    
    # Move router
    if [ -d "staff-web/src/router" ]; then
        mv "staff-web/src/router" "temp_staff_web/src/app/"
    fi
    
    # Move individual router files
    [ -f "staff-web/src/router.tsx" ] && mv "staff-web/src/router.tsx" "temp_staff_web/src/app/"
    [ -f "staff-web/src/router-simple.tsx" ] && mv "staff-web/src/router-simple.tsx" "temp_staff_web/src/app/"
    
    # Move test directory
    [ -d "staff-web/src/test" ] && mv "staff-web/src/test" "temp_staff_web/src/__tests__"
    [ -d "staff-web/src/__tests__" ] && mv "staff-web/src/__tests__" "temp_staff_web/src/"
    
    # Handle the 'x' directory (appears to be a Next.js experiment)
    if [ -d "staff-web/x" ]; then
        log "Moving experimental Next.js code to separate directory..."
        mv "staff-web/x" "temp_staff_web/experiments/nextjs"
    fi
    
    # Now move the cleaned up staff-web to final location
    mv temp_staff_web/* apps/staff-web/
    rmdir temp_staff_web
    
    # Remove old staff-web directory
    rm -rf staff-web
    
    log "✅ Staff-web reorganized and moved to apps/staff-web"
else
    warn "Staff-web directory not found"
fi

# ============================================================================
# MOVE ANALYSIS AND TOOLS FILES
# ============================================================================

log "Moving analysis and tool files..."

# Move analysis files to tools
[ -f "analyze-apps.js" ] && mv "analyze-apps.js" "tools/analysis/"
[ -f "app-analysis-report.html" ] && mv "app-analysis-report.html" "tools/analysis/"

# Move screenshot directory
[ -d "app-screenshots" ] && mv "app-screenshots" "tools/screenshots/"

# Move assets to shared
[ -d "assets" ] && mv "assets" "shared/"

# Move scripts
if [ -d "tools/scripts" ]; then
    # Keep existing scripts
    log "Existing tools/scripts directory found"
else
    mkdir -p tools/scripts
fi

# ============================================================================
# MOVE DOCUMENTATION FILES
# ============================================================================

log "Organizing documentation..."

# Move top-level markdown files to docs
[ -f "AUTHELIA_INTEGRATION.md" ] && mv "AUTHELIA_INTEGRATION.md" "docs/deployment/"
[ -f "system-overview.md" ] && mv "system-overview.md" "docs/architecture/"

# Move scattered documentation from backend to shared docs
if [ -d "apps/backend" ]; then
    # Find and move documentation files from backend
    find apps/backend -name "*.md" -not -path "*/migrations/*" -not -path "*/node_modules/*" | while read -r file; do
        # Create relative path structure in docs
        rel_path=$(echo "$file" | sed 's|apps/backend/||')
        dest_dir="docs/backend/$(dirname "$rel_path")"
        mkdir -p "$dest_dir"
        cp "$file" "$dest_dir/"
    done
    
    log "Backend documentation copied to docs/backend/"
fi

# ============================================================================
# CREATE MOBILE APP PLACEHOLDER
# ============================================================================

log "Creating mobile app structure..."

# Create basic mobile app structure (you'll populate this when you create the mobile app)
mkdir -p apps/mobile/{src,docs}
cat > apps/mobile/README.md << 'EOF'
# Mobile App

This will contain your mobile application that consumes the backend APIs.

## Planned Structure
- React Native, Flutter, or native iOS/Android
- Shared API contracts with backend
- Shared types with staff-web where applicable

## Next Steps
1. Choose mobile framework
2. Set up project structure
3. Implement API integration
4. Share types and constants with backend and staff-web
EOF

# ============================================================================
# CREATE SHARED RESOURCES
# ============================================================================

log "Setting up shared resources..."

# Create shared API contracts structure
cat > shared/api-contracts/README.md << 'EOF'
# API Contracts

This directory contains shared API contracts between backend, staff-web, and mobile apps.

## Structure
- `openapi/` - OpenAPI/Swagger specifications
- `types/` - Generated TypeScript types
- `clients/` - Generated API clients

## Usage
- Backend exports OpenAPI spec
- Frontend apps import generated types and clients
- Mobile app imports relevant types
EOF

# Create shared types
cat > shared/types/README.md << 'EOF'
# Shared Types

Common TypeScript interfaces and types used across all frontend applications.

## Guidelines
- Keep types generic and reusable
- Separate by domain (auth, students, finance, etc.)
- Use consistent naming conventions
EOF

# Create shared constants
cat > shared/constants/README.md << 'EOF'
# Shared Constants

Application constants shared between frontend applications.

## Structure
- `api.ts` - API endpoints and configuration
- `app.ts` - Application-wide constants
- `validation.ts` - Validation rules and messages
EOF

# ============================================================================
# CREATE ROOT CONFIGURATION FILES
# ============================================================================

log "Creating root configuration files..."

# Create root package.json for workspace management
cat > package.json << 'EOF'
{
  "name": "school-management-system",
  "version": "1.0.0",
  "description": "School Management System - Monorepo",
  "private": true,
  "workspaces": [
    "apps/*",
    "shared/*"
  ],
  "scripts": {
    "dev": "concurrently \"npm run dev:backend\" \"npm run dev:staff-web\"",
    "dev:backend": "cd apps/backend && python manage.py runserver",
    "dev:staff-web": "cd apps/staff-web && npm run dev",
    "build": "npm run build:staff-web",
    "build:staff-web": "cd apps/staff-web && npm run build",
    "test": "npm run test:staff-web",
    "test:staff-web": "cd apps/staff-web && npm run test",
    "lint": "npm run lint:staff-web",
    "lint:staff-web": "cd apps/staff-web && npm run lint",
    "type-check": "npm run type-check:staff-web",
    "type-check:staff-web": "cd apps/staff-web && npx tsc --noEmit"
  },
  "devDependencies": {
    "concurrently": "^8.2.2"
  },
  "engines": {
    "node": ">=18.0.0",
    "npm": ">=8.0.0"
  }
}
EOF

# Create root tsconfig.json
if [ ! -f "tsconfig.base.json" ]; then
    cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@shared/*": ["./shared/*"],
      "@backend/*": ["./apps/backend/*"],
      "@staff-web/*": ["./apps/staff-web/src/*"],
      "@mobile/*": ["./apps/mobile/src/*"]
    }
  },
  "include": ["apps/**/*", "shared/**/*"],
  "exclude": ["node_modules", "**/node_modules", "**/dist", "**/build"]
}
EOF
else
    mv tsconfig.base.json tsconfig.json
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    cat > .gitignore << 'EOF'
# Dependencies
node_modules/
*/node_modules/

# Build outputs
dist/
build/
*.tsbuildinfo

# Environment files
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.sqlite3

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Coverage
coverage/
.nyc_output

# Temporary files
tmp/
temp/
EOF
fi

# Create README for the new structure
cat > README.md << 'EOF'
# School Management System

A comprehensive school management system built with Django (backend) and React (staff-web frontend).

## 🏗️ Project Structure

```
├── apps/
│   ├── backend/          # Django backend API
│   ├── staff-web/        # React frontend for staff
│   └── mobile/           # Mobile app (planned)
├── shared/
│   ├── types/           # Shared TypeScript types
│   ├── constants/       # Shared constants
│   ├── api-contracts/   # API specifications
│   └── docs/            # Shared documentation
├── tools/
│   ├── scripts/         # Build and deployment scripts
│   ├── analysis/        # Code analysis tools
│   └── screenshots/     # App screenshots and demos
├── docs/
│   ├── architecture/    # System architecture docs
│   ├── api/            # API documentation
│   └── deployment/     # Deployment guides
└── config/
    ├── docker/         # Docker configurations
    └── ci/             # CI/CD configurations
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm or yarn

### Development Setup

1. **Install dependencies:**
   ```bash
   npm install  # Install root dependencies
   cd apps/backend && pip install -r requirements.txt
   cd ../staff-web && npm install
   ```

2. **Start development servers:**
   ```bash
   npm run dev  # Starts both backend and frontend
   ```

   Or individually:
   ```bash
   npm run dev:backend    # Django server on http://localhost:8000
   npm run dev:staff-web  # React dev server on http://localhost:5173
   ```

3. **Run tests:**
   ```bash
   npm run test  # Run all tests
   ```

## 📱 Applications

### Backend (Django)
- **Location:** `apps/backend/`
- **API:** RESTful API with DRF
- **Database:** SQLite (development), PostgreSQL (production)
- **Features:** Authentication, student management, finance, grading, etc.

### Staff Web (React)
- **Location:** `apps/staff-web/`
- **Framework:** React + TypeScript + Vite
- **UI:** Tailwind CSS + shadcn/ui
- **State:** Zustand
- **Features:** Dashboard, student management, finance, reports

### Mobile (Planned)
- **Location:** `apps/mobile/`
- **Status:** Planned for future development
- **Purpose:** Student and parent portal

## 🔗 Shared Resources

### Types
Shared TypeScript interfaces and types used across frontend applications.

### API Contracts
OpenAPI specifications and generated clients for consistent API consumption.

### Constants
Application-wide constants for URLs, validation rules, and configuration.

## 📚 Documentation

- **Architecture:** `docs/architecture/`
- **API Documentation:** `docs/api/`
- **Deployment:** `docs/deployment/`
- **Backend-specific:** `docs/backend/`

## 🛠️ Development Workflow

1. **Backend changes:** Develop in `apps/backend/`
2. **Frontend changes:** Develop in `apps/staff-web/`
3. **Shared types:** Update in `shared/types/`
4. **API contracts:** Update OpenAPI specs in `shared/api-contracts/`

## 📦 Build & Deployment

```bash
npm run build           # Build all applications
npm run build:staff-web # Build only staff-web
```

## 🧪 Testing

```bash
npm run test           # Run all tests
npm run test:staff-web # Run staff-web tests
npm run lint          # Lint all code
npm run type-check    # TypeScript type checking
```

## 🚀 Next Steps

1. **Mobile App:** Choose framework and implement mobile application
2. **API Documentation:** Generate OpenAPI specs from Django backend
3. **CI/CD:** Set up automated testing and deployment
4. **Docker:** Containerize applications for easier deployment
5. **Monitoring:** Add logging and monitoring solutions
EOF

# ============================================================================
# CLEANUP AND FINAL STEPS
# ============================================================================

log "Cleaning up remaining files..."

# Move any remaining test files
[ -f "test_login.py" ] && mv "test_login.py" "tools/scripts/"

# Move UV lock file to backend (assuming it's Python-related)
[ -f "uv.lock" ] && mv "uv.lock" "apps/backend/"

# Clean up the tree.txt file (move to tools)
[ -f "tree.txt" ] && mv "tree.txt" "tools/analysis/"

# ============================================================================
# CREATE HELPFUL SCRIPTS
# ============================================================================

log "Creating helpful development scripts..."

# Create a development setup script
cat > tools/scripts/setup-dev.sh << 'EOF'
#!/bin/bash
# Development environment setup script

echo "🚀 Setting up development environment..."

# Install root dependencies
echo "📦 Installing root dependencies..."
npm install

# Setup backend
echo "🐍 Setting up Django backend..."
cd apps/backend
if [ ! -f "venv/bin/activate" ]; then
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Run migrations
python manage.py migrate

# Create superuser if needed
echo "👤 Create a superuser for Django admin (optional):"
python manage.py createsuperuser --noinput --username admin --email admin@example.com || true

cd ../..

# Setup staff-web
echo "⚛️ Setting up React frontend..."
cd apps/staff-web
npm install
cd ../..

echo "✅ Development environment setup complete!"
echo ""
echo "🏃‍♂️ Quick start commands:"
echo "  npm run dev              # Start both backend and frontend"
echo "  npm run dev:backend      # Start only Django backend"
echo "  npm run dev:staff-web    # Start only React frontend"
echo ""
echo "🌐 Default URLs:"
echo "  Backend API: http://localhost:8000"
echo "  Staff Web:   http://localhost:5173"
echo "  Django Admin: http://localhost:8000/admin"
EOF

chmod +x tools/scripts/setup-dev.sh

# Create a build script
cat > tools/scripts/build-all.sh << 'EOF'
#!/bin/bash
# Build all applications for production

echo "🏗️ Building all applications..."

# Build staff-web
echo "⚛️ Building React frontend..."
cd apps/staff-web
npm run build
cd ../..

# Collect static files for Django
echo "🐍 Collecting Django static files..."
cd apps/backend
python manage.py collectstatic --noinput
cd ../..

echo "✅ Build complete!"
echo "📁 Built files:"
echo "  Staff Web: apps/staff-web/dist/"
echo "  Django Static: apps/backend/staticfiles/"
EOF

chmod +x tools/scripts/build-all.sh

# Update the existing update-api-types script if it exists
if [ -f "tools/scripts/update-api-types.sh" ]; then
    log "Updating existing API types script..."
    # Add note about new structure
    echo "" >> tools/scripts/update-api-types.sh
    echo "# Note: Update this script to work with the new monorepo structure" >> tools/scripts/update-api-types.sh
    echo "# Backend: apps/backend/" >> tools/scripts/update-api-types.sh
    echo "# Frontend: apps/staff-web/" >> tools/scripts/update-api-types.sh
    echo "# Shared types: shared/types/" >> tools/scripts/update-api-types.sh
fi

# ============================================================================
# FINAL VERIFICATION AND SUMMARY
# ============================================================================

log "Verifying new structure..."

# Check if key directories exist
success=true

check_dir() {
    if [ -d "$1" ]; then
        log "✅ $1 exists"
    else
        error "❌ $1 missing"
        success=false
    fi
}

check_dir "apps/backend"
check_dir "apps/staff-web"
check_dir "apps/mobile"
check_dir "shared/types"
check_dir "shared/api-contracts"
check_dir "tools/scripts"
check_dir "docs"

if [ "$success" = true ]; then
    echo ""
    echo "🎉 Project reorganization completed successfully!"
    echo ""
    echo "📋 Summary of changes:"
    echo "  ✅ Django backend moved to apps/backend/"
    echo "  ✅ React frontend reorganized and moved to apps/staff-web/"
    echo "  ✅ Created mobile app placeholder in apps/mobile/"
    echo "  ✅ Organized shared resources in shared/"
    echo "  ✅ Moved analysis tools to tools/"
    echo "  ✅ Organized documentation in docs/"
    echo "  ✅ Created monorepo configuration files"
    echo "  ✅ Created development scripts"
    echo ""
    echo "🚀 Next steps:"
    echo "  1. Run: ./tools/scripts/setup-dev.sh"
    echo "  2. Test that everything works: npm run dev"
    echo "  3. Update any hardcoded paths in your code"
    echo "  4. Update CI/CD configurations"
    echo "  5. Plan mobile app development"
    echo ""
    echo "📚 Important files to review:"
    echo "  - README.md (updated project documentation)"
    echo "  - package.json (workspace configuration)"
    echo "  - tsconfig.json (TypeScript configuration)"
    echo "  - apps/staff-web/src/ (new frontend structure)"
    echo ""
else
    error "❌ Some directories are missing. Please check the output above."
    exit 1
fi

echo "🎊 Happy coding with your new organized project structure!"
EOF

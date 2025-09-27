# NX Commands Reference for Raycast

## 🚀 Development Commands

### Run Targets
```bash
# Run specific project target
nx run <project>:<target>
nx run backend:dev
nx run frontend-vue-old:dev
nx run mobile:start

# Run multiple projects
nx run-many --target=<target> --projects=<project1>,<project2>
nx run-many --target=dev --projects=backend,frontend-vue-old --parallel
nx run-many --target=test --all --parallel

# Run with specific configuration
nx run <project>:<target>:<configuration>
nx run backend:serve:production
```

### Project Management
```bash
# List all projects
nx show projects

# Show project details
nx show project <project-name>
nx show project backend

# Show project configuration
nx show project <project-name> --web
```

## 🔍 Analysis & Information

### Dependency Graph
```bash
# Show dependency graph
nx graph

# Show dependency graph for specific project
nx graph --focus=<project-name>
nx graph --focus=backend

# Show affected projects
nx show projects --affected
nx affected:graph
```

### Project Information
```bash
# List all available targets
nx show projects --with-target=<target>
nx show projects --with-target=test

# Show project JSON configuration
nx show project <project-name>

# Print workspace configuration
nx show projects --json
```

## 🧪 Testing Commands

### Run Tests
```bash
# Run tests for all projects
nx run-many --target=test --all

# Run tests for specific projects
nx run-many --target=test --projects=backend,mobile

# Run tests with coverage
nx run <project>:test --coverage
nx run backend:test --coverage

# Run affected tests only
nx affected --target=test
nx affected:test

# Run tests in watch mode
nx run <project>:test --watch
```

### Test Utilities
```bash
# Run tests with specific pattern
nx run <project>:test --testNamePattern="<pattern>"
nx run backend:test --testNamePattern="auth"

# Run tests for specific file
nx run <project>:test <file-path>
nx run mobile:test src/components/Button.test.tsx
```

## 🔨 Build & Lint Commands

### Build
```bash
# Build all projects
nx run-many --target=build --all

# Build specific project
nx run <project>:build
nx run frontend-vue-old:build

# Build affected projects only
nx affected --target=build
nx affected:build

# Build with production configuration
nx run <project>:build --configuration=production
```

### Linting
```bash
# Lint all projects
nx run-many --target=lint --all

# Lint specific project
nx run <project>:lint
nx run backend:lint

# Lint affected projects only
nx affected --target=lint
nx affected:lint

# Auto-fix linting issues
nx run <project>:lint --fix
nx run mobile:lint --fix
```

## 📊 Cache & Performance

### Cache Management
```bash
# Clear cache
nx reset

# Show cache statistics
nx show projects --cached

# Run without cache
nx run <project>:<target> --skip-nx-cache

# Print cache directory
nx show projects --json | grep cacheDirectory
```

### Performance
```bash
# Run with timing information
nx run <project>:<target> --verbose

# Skip dependency checks
nx run <project>:<target> --skip-nx-cache

# Run in parallel
nx run-many --target=<target> --parallel --maxParallel=<number>
```

## 🎯 Affected Commands

### Show Affected
```bash
# Show affected projects
nx show projects --affected

# Show affected projects for specific target
nx affected --target=<target> --dry-run
nx affected --target=test --dry-run

# Show affected since specific commit
nx affected --base=<commit-hash>
nx affected --base=HEAD~1
```

### Run Affected
```bash
# Run target on affected projects
nx affected --target=<target>
nx affected --target=test
nx affected --target=lint
nx affected --target=build

# Run multiple targets on affected
nx affected --targets=lint,test,build
```

## 📦 Workspace Commands

### Format Code
```bash
# Format all files
nx format:write

# Check formatting
nx format:check

# Format specific files
nx format:write --files="src/**/*.ts"

# Format uncommitted files
nx format:write --uncommitted
```

### Workspace Utilities
```bash
# Print workspace configuration
nx list

# Show installed plugins
nx list --installed

# Show available plugins
nx list --available

# Print NX version
nx --version
```

## 🚀 Your Project-Specific Commands

### Backend (Django)
```bash
nx run backend:dev              # Start Django dev server
nx run backend:serve            # Start Django server
nx run backend:serve:all        # Start all backend services
nx run backend:test             # Run Python tests
nx run backend:test:docker      # Run tests in Docker
nx run backend:lint             # Ruff linting
nx run backend:format           # Format Python code
nx run backend:typecheck        # MyPy type checking
nx run backend:migrate          # Django migrations
nx run backend:shell            # Django shell
nx run backend:generate-schema  # Generate OpenAPI schema
```

### Frontend Vue (frontend-vue-old)
```bash
nx run frontend-vue-old:dev          # Start Vue dev server
nx run frontend-vue-old:build        # Build Vue app
nx run frontend-vue-old:test         # Run Vue tests
nx run frontend-vue-old:test:coverage # Run tests with coverage
nx run frontend-vue-old:lint         # ESLint
nx run frontend-vue-old:mobile:dev   # Mobile development mode
```

### Mobile (React Native)
```bash
nx run mobile:start           # Start Metro bundler
nx run mobile:dev            # Start development server
nx run mobile:android        # Run on Android
nx run mobile:ios            # Run on iOS
nx run mobile:test           # Run Jest tests
nx run mobile:lint           # ESLint for React Native
nx run mobile:typecheck      # TypeScript checking
nx run mobile:storybook      # Start Storybook
nx run mobile:build-storybook # Build Storybook
```

### API Types (Shared)
```bash
nx run api-types:build       # Build TypeScript types
nx run api-types:test        # Run type tests
nx run api-types:lint        # Lint shared types
```

## 🔧 Advanced Commands

### Custom Executors
```bash
# Run with custom executor options
nx run <project>:<target> --<option>=<value>

# Pass through arguments
nx run <project>:<target> -- --<native-option>
nx run backend:test -- --verbose
nx run mobile:android -- --variant=debug
```

### Environment & Configuration
```bash
# Run with environment variables
NX_VERBOSE_LOGGING=true nx run <project>:<target>

# Run with specific configuration
nx run <project>:<target>:production
nx run <project>:<target>:development

# Override configuration
nx run <project>:<target> --configuration=<config>
```

### Batch Operations
```bash
# Run multiple targets sequentially
nx run <project>:<target1> && nx run <project>:<target2>

# Run with different configurations
nx run-many --target=build --projects=frontend-vue-old,mobile --configuration=production

# Run with custom parallel limit
nx run-many --target=test --all --parallel --maxParallel=3
```

## 📱 Quick Commands for Daily Use

### Most Common
```bash
# Start everything for development
nx run-many --target=dev --projects=backend,frontend-vue-old --parallel

# Run all tests
nx run-many --target=test --all

# Lint everything
nx run-many --target=lint --all

# Show what's affected by changes
nx affected --target=test --dry-run

# Clear cache and reset
nx reset
```

### Project-Specific Quick Commands
```bash
# Backend development
nx run backend:dev

# Frontend development
nx run frontend-vue-old:dev

# Mobile development
nx run mobile:start
nx run mobile:android

# Run affected tests only
nx affected --target=test

# Format all code
nx format:write
```

## 💡 Tips for Raycast

1. **Create shortcuts** for the most common commands
2. **Use aliases** like `nx g` instead of `nx generate`
3. **Set up script commands** in Raycast for complex multi-step operations
4. **Use `--dry-run`** to see what would happen before running
5. **Combine with `&&`** for sequential operations
6. **Use `--parallel`** for faster execution when possible

## 🔗 Useful Flags

- `--dry-run` - Show what would happen without executing
- `--parallel` - Run targets in parallel
- `--maxParallel=N` - Limit parallel execution
- `--verbose` - Show detailed output
- `--skip-nx-cache` - Skip cache for this run
- `--configuration=<config>` - Use specific configuration
- `--projects=<list>` - Target specific projects
- `--all` - Target all projects
- `--affected` - Only target affected projects
- `--base=<ref>` - Compare against specific git reference
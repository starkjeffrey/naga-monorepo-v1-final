# Development Documentation

## 💻 Development Workflows & Standards

This directory contains development guides, environment setup, and coding standards for the Naga SIS project.

## 📁 Contents

### Environment Setup
- **dual_database_development_guide.md** - Multi-environment development strategy
- **environment_usage.md** - Environment-specific development guidelines
- **context7-setup-instructions.md** - MCP Context7 setup for Claude AI assistance

### Integration Guides
- **gl-integration-guide.md** - General Ledger integration patterns and procedures

## 🛠️ Development Standards

### Environment Management
- **Local**: Safe development with test data
- **Migration**: Legacy data processing (REAL DATA - CAUTION)
- **Staging**: Pre-production testing
- **Production**: Live system

### Code Quality Standards
- **Python**: PEP 8, Ruff formatting, type hints, comprehensive docstrings
- **TypeScript**: ESLint, Prettier, strict type checking
- **Testing**: Comprehensive coverage with pytest and Vitest
- **Architecture**: Follow clean architecture principles (see [Architecture](../architecture/))

### Git Workflow
- **Conventional Commits**: Use descriptive commit messages with emojis
- **Feature Branches**: Create from main, comprehensive testing before merge
- **Code Reviews**: Required for all changes, architectural validation
- **CI/CD**: Automated testing, security scanning, affected builds

## 🔧 Development Tools

### Monorepo Tools
- **Nx**: Affected builds, dependency graph, project management
- **Shared Libraries**: TypeScript API types, validation schemas
- **Build Optimization**: Caching, parallel execution, incremental builds

### Quality Assurance
- **Linting**: Ruff (Python), ESLint (TypeScript)
- **Type Checking**: mypy (Python), TypeScript compiler
- **Testing**: pytest (Backend), Vitest (Frontend)
- **Security**: Multi-layer scanning (CodeQL, Trivy, Snyk, TruffleHog)

## 📚 Related Documentation
- [Architecture](../architecture/) - Architectural principles and constraints
- [Operations](../operations/) - Deployment and maintenance procedures
- [API](../api/) - API development and integration guides
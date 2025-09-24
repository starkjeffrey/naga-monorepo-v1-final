# Architecture & Design Documentation

## 🏗️ System Architecture

This directory contains architectural analysis, design decisions, and system structure documentation for the Naga SIS project.

## 📁 Contents

### Core Architecture Analysis
- **dependency_analysis_20250612.md** - Critical analysis of circular dependencies from v0
  - Documents 12 circular dependency patterns to avoid
  - Provides foundation for clean architecture decisions
  - **Required reading** for all architectural decisions

### Model Documentation
- **model-diagrams/** - Comprehensive model relationship diagrams
  - System overview and inter-app relationships
  - Individual app model structures
  - Business domain modeling

### System Integrations
- **moodle_integration_architecture.md** - External LMS integration patterns
- **dynamic_sidebar_system.md** - Frontend navigation architecture

## 🎯 Key Architectural Principles

1. **Clean Architecture**: Strict separation of concerns between Django apps
2. **Single Responsibility**: Each app has one well-defined domain
3. **Dependency Direction**: Dependencies flow in one direction only
4. **Domain-Driven Design**: App boundaries reflect business domains

## ⚠️ Critical Guidelines

### Architectural Alert Triggers
- Any design resembling v0 circular dependencies
- Cross-app model imports (use signals/events instead)
- Mixed responsibilities within single apps
- Bidirectional dependencies between domains

### Decision Framework
1. **Single Responsibility Check**: Does this belong in the proposed app's domain?
2. **Clean Dependencies**: Will this create circular dependencies?
3. **Interface Design**: Can communication use events instead of direct imports?
4. **Future Maintenance**: Will this make the codebase easier to maintain?

## 📚 Related Documentation
- [Development Guides](../development/) - Implementation of architectural principles
- [Code Reviews](../code-reviews/) - Architecture validation per app
- [Migration](../migration/) - Legacy system architectural migration
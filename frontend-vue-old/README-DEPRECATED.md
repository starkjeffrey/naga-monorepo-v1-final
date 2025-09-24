# ⚠️ DEPRECATED - Vue 3 Frontend (Preserved for Reference)

This directory contains the **original Vue 3 + Quasar frontend** that was previously used in the NAGA project.

## Status: DEPRECATED ❌

**This frontend has been replaced by:**
- **React web frontend** in `/frontend/` (React + TypeScript + modern tools)
- **React Native mobile app** in `/mobile/` (React Native + TypeScript + React Native Paper)

## Historical Context

This Vue 3 frontend was built with:
- Vue 3.5.13 + Composition API
- Quasar 2.18.1 (Material Design components)
- TypeScript support
- Vite build system
- PWA capabilities with Capacitor
- Pinia for state management
- Vue Router for navigation

## Why Deprecated?

The project has moved to a **React-first architecture** to:
1. **Unify technology stack** - React for both web and mobile
2. **Reduce complexity** - Single framework instead of Vue + React Native
3. **Improve developer experience** - One mental model for all frontends
4. **Better ecosystem integration** - React has more mature mobile/web tooling

## Contents Preserved

This directory contains all the original Vue components, composables, and configuration:
- ✅ All Vue 3 components intact
- ✅ Quasar UI components
- ✅ TypeScript configurations
- ✅ Vite build configuration
- ✅ PWA/Capacitor setup
- ✅ State management with Pinia
- ✅ All original functionality

## Migration Notes

Key functionality that was migrated to React:
- **Authentication flow** → React components with Zustand
- **Dashboard interface** → React Native mobile + React web
- **Form handling** → React Hook Form or native React patterns
- **State management** → Zustand (simpler than Pinia/Vuex)
- **Routing** → React Router (web) + React Navigation (mobile)

## Future Use

This directory is kept for:
- **Reference** - Understanding original functionality
- **Gradual migration** - Components can be ported as needed
- **Backup** - Fallback if React implementation has issues
- **Learning** - Comparison between Vue and React implementations

## Do Not Use for New Development

❌ **Do not add new features to this Vue frontend**
❌ **Do not fix bugs in this deprecated version**
✅ **Refer to this code when building React equivalents**
✅ **Use as documentation for business logic**

---

**For current development, see:**
- `/frontend/` - React web application
- `/mobile/` - React Native mobile application
- `/backend/` - Django backend (unchanged)
# Class Scheduling System Design

**Created**: July 20, 2024  
**Author**: Claude Code  
**Status**: Design Complete, Implementation Partial

## Overview

This document outlines the design for a modern, user-friendly class scheduling interface for the Naga SIS. The system leverages the existing `ClassHeader`, `ClassSession`, and `ClassPart` models to provide intuitive class management capabilities.

The design focuses on creating an efficient workflow for staff members who need to:

- View and manage scheduled classes for current and future terms
- Add students to classes and manage enrollments
- Create new classes from course templates
- Monitor class capacity and waitlists
- Generate schedules and reports

## Key Design Principles

1. **Task-Focused Interface**: Separate screens for different tasks (viewing vs creating vs managing)
2. **Mobile-First Responsive**: Works seamlessly on phones, tablets, and desktops
3. **HTMX-Driven**: Real-time updates without full page reloads
4. **Progressive Enhancement**: Basic functionality works without JavaScript
5. **Reusable Components**: Building blocks that can be used across the SIS

## User Interface Structure

### 1. Dashboard View (`/scheduling/`)

- **Purpose**: Quick overview of current term classes
- **Features**:
  - Summary cards showing class counts by status
  - Quick actions for common tasks
  - Term selector (defaults to current/upcoming term)
  - Search/filter bar

### 2. Class List View (`/scheduling/classes/`)

- **Purpose**: Browse and filter all classes
- **Features**:
  - Data table with sortable columns
  - Advanced filtering (by term, status, teacher, room, time)
  - Inline status updates
  - Bulk actions (export, status change)
  - Quick view modal on row click

### 3. Class Detail View (`/scheduling/classes/{id}/`)

- **Purpose**: Complete class information and management
- **Sections**:
  - Header info (course, term, section, status)
  - Enrollment summary with quick add student
  - Sessions and parts breakdown
  - Schedule visualization
  - Teacher and room assignments
  - Action buttons (edit, copy, cancel)

### 4. Create Class Wizard (`/scheduling/classes/create/`)

- **Purpose**: Step-by-step class creation
- **Steps**:
  1. Select course and term
  2. Configure sections and capacity
  3. Set up sessions (auto-detect IEAP)
  4. Assign parts with schedule
  5. Review and create

### 5. Student Enrollment View (`/scheduling/enrollments/`)

- **Purpose**: Manage student enrollments
- **Features**:
  - Search students by ID/name
  - View student's current schedule
  - Add/drop interface with conflict checking
  - Waitlist management
  - Batch enrollment upload

### 6. Historical View (`/scheduling/archive/`)

- **Purpose**: Read-only view of past terms
- **Features**:
  - Simplified interface
  - Focus on reports and analytics
  - Grade distribution charts
  - Attendance summaries

## Component Library

### Base Components

1. **Card Component** (`components/card.html`)

   - Consistent styling for content containers
   - Variants: default, primary, success, warning, danger

2. **Data Table** (`components/data_table.html`)

   - Sortable columns
   - Pagination
   - Row selection
   - Responsive (cards on mobile)

3. **Form Elements** (`components/forms/`)

   - Text inputs with floating labels
   - Select dropdowns with search
   - Date/time pickers
   - Validation feedback

4. **Modal System** (`components/modal.html`)

   - HTMX-powered loading
   - Multiple sizes
   - Backdrop click to close
   - Keyboard navigation

5. **Alert Messages** (`components/alerts.html`)
   - Auto-dismiss options
   - Action buttons
   - Icons for different types

### Scheduling-Specific Components

1. **Term Selector** (`scheduling/components/term_selector.html`)

   - Dropdown with current/future terms
   - Shows term dates
   - Updates page content via HTMX

2. **Class Card** (`scheduling/components/class_card.html`)

   - Compact class display
   - Shows key info: code, title, enrollment
   - Status badge
   - Quick actions dropdown

3. **Schedule Grid** (`scheduling/components/schedule_grid.html`)

   - Weekly calendar view
   - Drag-and-drop support (future)
   - Conflict highlighting
   - Room availability overlay

4. **Enrollment Widget** (`scheduling/components/enrollment_widget.html`)

   - Student search
   - Add/drop buttons
   - Capacity indicator
   - Waitlist queue

5. **Teacher Assignment** (`scheduling/components/teacher_assignment.html`)
   - Teacher dropdown with availability
   - Load balancing indicator
   - Conflict warnings

## Technical Implementation

### URL Structure

```
/scheduling/                          # Dashboard
/scheduling/classes/                  # List view
/scheduling/classes/create/           # Create wizard
/scheduling/classes/{id}/             # Detail view
/scheduling/classes/{id}/edit/        # Edit form
/scheduling/classes/{id}/enrollments/ # Manage enrollments
/scheduling/enrollments/              # Student enrollment
/scheduling/enrollments/search/       # HTMX student search
/scheduling/archive/                  # Historical data
/scheduling/api/                      # HTMX endpoints
```

### HTMX Patterns

1. **Lazy Loading**: Load class details on demand
2. **Inline Editing**: Update status without page reload
3. **Live Search**: Real-time filtering as you type
4. **Infinite Scroll**: Load more results automatically
5. **Polling**: Auto-refresh enrollment counts

### Responsive Breakpoints

- Mobile: < 640px (Tailwind `sm:`)
- Tablet: 640px - 1024px (Tailwind `sm:` to `lg:`)
- Desktop: > 1024px (Tailwind `lg:` and up)

## Color Scheme

Using Tailwind's default palette:

- **Primary**: Blue-600 (actions, links)
- **Success**: Green-600 (active, enrolled)
- **Warning**: Yellow-600 (waitlist, pending)
- **Danger**: Red-600 (cancelled, conflicts)
- **Neutral**: Gray shades (backgrounds, borders)

## Accessibility

- ARIA labels on all interactive elements
- Keyboard navigation support
- Focus indicators
- Screen reader announcements for HTMX updates
- Color contrast WCAG AA compliant

## Performance Optimizations

1. **Pagination**: Load 20 items by default
2. **Caching**: Cache term and course lists
3. **Lazy Loading**: Load details only when needed
4. **Debouncing**: Search input with 300ms delay
5. **Compression**: Minimize HTML responses

## System Changes Needed

See `SYSTEM_CHANGES_NEEDED.md` for required backend modifications.

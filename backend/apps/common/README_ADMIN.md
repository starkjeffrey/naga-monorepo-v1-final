# Common App Admin Interfaces

This document describes the enhanced admin interfaces available in the common app for managing student activity logs and other common models.

## StudentActivityLog Admin

### Overview

The StudentActivityLog admin provides a comprehensive interface for viewing and filtering all student-related activities in the system. This includes enrollments, withdrawals, grade changes, overrides, and other administrative actions.

### Features

#### 1. **Enhanced List Display**

- **Colored Visibility Badges**: Quick visual identification of log visibility levels
  - Red: Staff Only
  - Green: Student Visible
  - Blue: Public
- **Activity Type Color Coding**: Different colors for different activity types
- **Tooltips**: Hover over truncated text to see full content
- **Smart Truncation**: Long descriptions are truncated with full text in tooltips

#### 2. **Advanced Filtering**

- **Date Range Filtering**: Filter by custom date ranges or use quick presets
  - Today, Yesterday
  - Last 7/30/90 days
  - This month, Last month
  - This year
- **Multi-Select Filters**:
  - Activity Types (checkboxes for multiple selection)
  - Visibility Levels
- **Text Filters**:
  - Student numbers (comma or newline separated)
  - Term name
  - Class code
  - Description search
- **Staff Filter**: Filter by who performed the action

#### 3. **Search Capabilities**

- Search across multiple fields:
  - Student number and name
  - Description
  - Class code and section
  - Program name
  - Staff username and name

#### 4. **Summary Statistics**

The change list view displays summary statistics including:

- Total number of logs
- Logs in the last 30 days
- Top 5 activity types with counts
- Visibility breakdown
- Top 5 most active students

#### 5. **Quick Filter Buttons**

Convenient buttons for common filters:

- Enrollments (green)
- Withdrawals (red)
- Grade Changes (yellow)
- Overrides (pink)
- Staff Only logs
- Student Visible logs
- Last 30 days
- Clear all filters

#### 6. **Bulk Actions**

- **Export to CSV**: Export selected logs with all relevant fields
- **Mark as Staff Only**: Bulk update visibility
- **Mark as Student Visible**: Bulk update visibility

#### 7. **Performance Optimizations**

- Uses `select_related` for efficient database queries
- Pagination set to 50 items per page
- Indexed fields for fast searching and filtering

### Usage Examples

#### Finding All Grade Changes for a Student

1. Enter the student number in the search box
2. Select "Grade Change" from the Activity Type filter
3. View results sorted by date

#### Exporting Monthly Activity Report

1. Use the date range filter to select the desired month
2. Select all records using the checkbox in the header
3. Choose "Export selected logs as CSV" from the actions dropdown
4. Click "Go"

#### Reviewing Override Actions

1. Click the "Overrides" quick filter button
2. Review the logs, noting the override reasons and who performed them
3. Use the visibility badges to ensure appropriate access levels

### Permissions

- **View**: All staff members can view logs
- **Add**: Disabled (logs are created programmatically)
- **Change**: Disabled (audit logs are immutable)
- **Delete**: Only superusers can delete logs

## SystemAuditLog Admin

### Overview

Tracks all system-wide management overrides and policy exceptions for compliance and auditing purposes.

### Features

- Read-only interface for viewing override actions
- Displays target object information
- Shows IP address and user agent for security tracking
- Comprehensive filtering by action type and user

## Holiday Admin

### Overview

Manages Cambodian national holidays and institutional holidays that affect academic scheduling.

### Features

- Bilingual support (English and Khmer names)
- Date range management for multi-day holidays
- Active/inactive status for holiday observance
- Duration calculation for multi-day holidays

## Room Admin

### Overview

Manages physical classroom and meeting room information for scheduling purposes.

### Features

- Building and room type categorization
- Equipment tracking (projector, whiteboard, computers)
- Capacity management
- Active/inactive status for availability

## JavaScript Enhancements

The admin interface includes custom JavaScript for:

- **Tooltips**: Custom tooltip implementation for better UX
- **Date Range Selector**: Automatic date calculation for quick ranges
- **Export Loading Indicator**: Visual feedback during CSV export
- **Search Enhancements**: Clear button for search field
- **Filter Persistence**: Save and restore filter states
- **Keyboard Shortcuts**:
  - Ctrl/Cmd + E: Export selected items
  - Ctrl/Cmd + F: Focus search field

## CSS Customizations

Custom styles provide:

- Colored badges for visibility levels
- Activity type color coding
- Responsive design for mobile devices
- Loading indicators
- Enhanced button styles
- Improved table readability

## Best Practices

1. **Regular Monitoring**: Review audit logs regularly for suspicious activities
2. **Export Backups**: Periodically export important logs for archival
3. **Visibility Management**: Ensure logs have appropriate visibility levels
4. **Filter Bookmarking**: Save commonly used filter combinations as bookmarks
5. **Performance**: Use specific filters to reduce result sets for better performance

## Troubleshooting

### Slow Loading

- Use more specific filters to reduce the number of records
- Check if database indexes are properly created
- Consider adjusting the pagination size

### Export Issues

- Ensure at least one record is selected before exporting
- Check browser download settings if CSV doesn't download
- For large exports, consider filtering first to reduce size

### Missing Data

- Verify that the logging is properly implemented in the source apps
- Check if the user has appropriate permissions to view all logs
- Ensure database migrations are up to date

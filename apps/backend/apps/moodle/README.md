# Moodle Integration App

This Django app provides comprehensive integration between the Naga SIS and Moodle Learning Management System (LMS).

## Features

### Core Integration

- **User Synchronization**: Automatic sync of SIS persons to Moodle users
- **Course Management**: Create and sync courses from SIS to Moodle
- **Enrollment Sync**: Real-time enrollment and unenrollment
- **Grade Sync**: Bidirectional grade synchronization (future)

### Architecture

- **Clean Dependencies**: Only imports from core SIS apps (people, curriculum, enrollment)
- **Event-Driven**: Uses Django signals for automatic synchronization
- **Background Processing**: Non-blocking operations using Dramatiq
- **Comprehensive Logging**: Full audit trail of all API interactions

## Configuration

Add to your environment variables:

```bash
# Enable/disable Moodle integration
MOODLE_ENABLED=true

# Moodle instance configuration
MOODLE_URL=https://your-moodle-site.com
MOODLE_API_TOKEN=your_webservice_token

# Sync behavior
MOODLE_AUTO_SYNC=true
MOODLE_DEFAULT_CATEGORY_ID=1
MOODLE_USERNAME_PREFIX=sis_
```

## Models

### Core Mapping Models

- `MoodleUserMapping`: Maps SIS Person to Moodle user
- `MoodleCourseMapping`: Maps SIS Course to Moodle course
- `MoodleEnrollmentMapping`: Maps SIS Enrollment to Moodle enrollment
- `MoodleGradeMapping`: Maps SIS Grade to Moodle grade (future)

### Operational Models

- `MoodleSyncStatus`: Generic sync status tracking for any SIS entity
- `MoodleAPILog`: Complete log of all Moodle API interactions

## Services

### MoodleAPIClient

Low-level Moodle Web Services API client with:

- Authentication handling
- Error categorization
- Timeout management
- Comprehensive logging

### Domain Services

- `MoodleUserService`: User creation, updates, and sync
- `MoodleCourseService`: Course management and sync
- `MoodleEnrollmentService`: Enrollment operations
- `MoodleGradeService`: Grade synchronization (future)

## Background Tasks

All synchronization operations are performed in background using Dramatiq:

- `async_sync_person_to_moodle`: Individual person sync
- `async_create_moodle_course`: Course creation
- `async_enroll_student`: Student enrollment
- `bulk_sync_users_to_moodle`: Bulk user synchronization
- `moodle_health_check`: Connectivity monitoring

## Management Commands

### moodle_sync

```bash
# Test connection
python manage.py moodle_sync test

# Sync all users (dry run)
python manage.py moodle_sync sync-users --dry-run

# Sync courses
python manage.py moodle_sync sync-courses

# Health check
python manage.py moodle_sync health-check
```

### moodle_cleanup

```bash
# Clean up old API logs and failed syncs
python manage.py moodle_cleanup

# Custom retention periods
python manage.py moodle_cleanup --api-logs-days 7 --failed-syncs-days 30
```

## API Endpoints

Internal API endpoints for monitoring and manual operations:

- `GET /api/moodle/health` - Health status
- `GET /api/moodle/sync-status` - Sync summary
- `POST /api/moodle/sync/person/{id}` - Manual person sync
- `GET /api/moodle/api-logs` - Recent API logs

## Signal Integration

Automatic synchronization is triggered by Django signals:

### Person Changes

```python
# Triggered automatically when Person is saved
person = Person.objects.create(...)  # -> Moodle user created
```

### Course Changes

```python
# Triggered automatically when Course is saved
course = Course.objects.create(...)  # -> Moodle course created
```

### Enrollment Changes

```python
# Triggered automatically when Enrollment is saved/deleted
enrollment = Enrollment.objects.create(...)  # -> Student enrolled in Moodle
enrollment.delete()  # -> Student unenrolled from Moodle
```

## Error Handling

### Retry Logic

- Failed operations are automatically retried (max 3 attempts)
- Exponential backoff between retries
- Failed syncs are logged with detailed error information

### Error Categories

- Network errors (connection issues)
- Authentication errors (invalid token)
- Validation errors (invalid data)
- Conflict errors (duplicate users/courses)

## Monitoring

### Health Checks

- API connectivity monitoring
- Sync status summaries
- Error rate tracking

### Logging

- All API calls are logged with timing information
- Comprehensive error tracking
- Sync status for every entity

## Future Enhancements

### Grade Synchronization

Once the `grading` app is implemented:

- Bidirectional grade sync
- Grade item mapping
- Gradebook integration

### Additional Features

- Bulk import from Moodle
- Selective sync by department/program
- Conflict resolution workflows
- Advanced retry strategies

## Development

### Testing

```bash
# Run Moodle app tests
pytest apps/moodle/

# Test with mock Moodle API
pytest apps/moodle/ --moodle-mock
```

### Adding New Sync Operations

1. **Extend Services**: Add new methods to appropriate service classes
2. **Create Tasks**: Add background tasks for non-blocking operations
3. **Add Signals**: Hook into relevant model changes
4. **Update Admin**: Add admin interfaces for new mappings
5. **Document**: Update this README and add management commands

### Dependencies

Required packages:

- `requests`: HTTP client for Moodle API
- `dramatiq`: Background task processing
- `django-environ`: Environment variable management

## Security Considerations

- API tokens are stored in environment variables only
- All API communications use HTTPS
- Sensitive data is not logged in API logs
- User passwords are never stored or transmitted
- Proper authentication validation on all endpoints

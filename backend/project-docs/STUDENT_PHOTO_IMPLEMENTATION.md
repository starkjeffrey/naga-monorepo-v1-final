# Student Photo Management System Implementation

## Overview
Implemented a comprehensive student photo management system with versioning, reminders, and mobile app integration for Pannasastra University of Cambodia Student Information System.

## Key Features Implemented

### 1. Photo Versioning System
- **Model**: `StudentPhoto` with full history tracking
- **Multiple photos per person** with `is_current` flag
- **Deduplication** using SHA-256 file hashing
- **Automatic thumbnail generation** (80x90px)
- **Backward compatibility** with existing `Person.photo` field

### 2. Photo Processing
- **PhotoProcessor utility class** in `apps/people/utils.py`
- **Automatic resizing** to 320x360px standard size
- **EXIF orientation handling** for proper rotation
- **File validation**: JPEG/PNG only, max 5MB, min 160x180px
- **Thumbnail generation** for efficient display

### 3. API Endpoints
- **POST `/api/students/me/photo`** - Mobile app photo upload
- **GET `/api/students/me/photos`** - Photo history retrieval
- **GET `/api/students/me/photo/current`** - Current photo retrieval
- **POST `/api/admin/photos/{id}/verify`** - Admin photo verification
- **DELETE `/api/admin/photos/{id}`** - Admin photo deletion

### 4. Reminder System
- **Automated reminders** at 30 days before expiration
- **Different schedules**: 6 months for students, 12 months for monks
- **Email notifications** with HTML and text templates
- **Admin alerts** for overdue photos
- **Dramatiq tasks** for background processing

### 5. Historical Photo Import
- **Management command**: `import_student_photos`
- **Batch processing** with configurable batch size
- **Comprehensive audit reporting**
- **Duplicate detection** and skip existing photos
- **Matches photos by student ID in filename**

### 6. Django Admin Integration
- **StudentPhotoAdmin** with full photo management
- **Inline display** in PersonAdmin
- **Photo preview** with automatic fallback to legacy photos
- **Bulk actions**: verify, send reminders, mark as current
- **Advanced filtering** by status, source, and verification

## Database Schema

```python
class StudentPhoto(AuditModel):
    person = models.ForeignKey(Person, related_name="photos")
    photo_file = models.ImageField(upload_to=student_photo_path)
    thumbnail = models.ImageField(upload_to=student_thumbnail_path)
    upload_source = models.CharField(choices=UploadSource.choices)
    upload_timestamp = models.DateTimeField(auto_now_add=True)
    is_current = models.BooleanField(default=True)
    file_hash = models.CharField(max_length=64, unique=True)
    file_size = models.IntegerField()
    width = models.IntegerField()
    height = models.IntegerField()
    original_filename = models.CharField(max_length=255)
    verified_by = models.ForeignKey(User, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_count = models.IntegerField(default=0)
    skip_reminder = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
```

## File Organization
- **Photos**: `/media/photos/students/{year}/{month}/`
- **Thumbnails**: `/media/photos/students/thumbnails/{year}/{month}/`
- **Hashed filenames** for security and deduplication

## Configuration Required

### Settings
```python
# Add to settings.py
PHOTO_ADMIN_EMAILS = ['admin@pucsr.edu.kh']  # Admin notification emails
```

### Dramatiq Schedule
```python
# Add to periodic tasks
from apps.people.tasks import check_photo_reminders

# Schedule daily at 9 AM
schedule('check_photo_reminders', cron='0 9 * * *')
```

## Usage Instructions

### 1. Run Migration
```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
```

### 2. Import Historical Photos
```bash
# Dry run first
docker compose -f docker-compose.local.yml run --rm django python manage.py import_student_photos /path/to/photos --dry-run

# Actual import
docker compose -f docker-compose.local.yml run --rm django python manage.py import_student_photos /path/to/photos
```

### 3. API Integration
The mobile app should:
1. Authenticate users with JWT token
2. POST photo to `/api/students/me/photo`
3. Handle response with photo URLs and next required date
4. Display current photo from `/api/students/me/photo/current`

### 4. Admin Usage
1. Navigate to People > Student Photos in admin
2. Use filters to find photos needing verification
3. Bulk verify photos using admin actions
4. Monitor overdue photos and send manual reminders

## Security Considerations
- Photos are stored with hashed filenames
- Original filenames preserved in database only
- File validation prevents malicious uploads
- Admin verification workflow for quality control
- JWT authentication required for API access

## Performance Optimizations
- Thumbnail generation for fast display
- SHA-256 hashing prevents duplicate storage
- Batch processing for bulk imports
- Indexed queries on common filters
- Filesystem storage for better performance than DB storage

## Future Enhancements
1. Face detection validation
2. Cloud storage backup (S3)
3. Mobile push notifications
4. QR code generation for ID cards
5. Automated quality assessment
6. Bulk photo download for ID card printing
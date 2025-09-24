"""Moodle integration constants."""

# Moodle Web Services Function Names
MOODLE_WS_FUNCTIONS = {
    # User management
    "CREATE_USER": "core_user_create_users",
    "UPDATE_USER": "core_user_update_users",
    "GET_USER": "core_user_get_users",
    "DELETE_USER": "core_user_delete_users",
    # Course management
    "CREATE_COURSE": "core_course_create_courses",
    "UPDATE_COURSE": "core_course_update_courses",
    "GET_COURSE": "core_course_get_courses",
    "DELETE_COURSE": "core_course_delete_courses",
    "GET_COURSE_CONTENTS": "core_course_get_contents",
    # Category management
    "CREATE_CATEGORY": "core_course_create_categories",
    "GET_CATEGORIES": "core_course_get_categories",
    # Enrollment management
    "ENROL_USERS": "enrol_manual_enrol_users",
    "UNENROL_USERS": "enrol_manual_unenrol_users",
    "GET_ENROLLED_USERS": "core_enrol_get_enrolled_users",
    # Grade management (future)
    "GET_GRADES": "core_grades_get_grades",
    "UPDATE_GRADES": "core_grades_update_grades",
}

# Moodle User Roles
MOODLE_ROLES = {
    "STUDENT": 5,
    "TEACHER": 3,
    "EDITING_TEACHER": 3,
    "MANAGER": 1,
    "COURSE_CREATOR": 2,
}

# Moodle User Profile Fields
MOODLE_USER_FIELDS = {
    "REQUIRED": ["username", "password", "firstname", "lastname", "email"],
    "OPTIONAL": [
        "idnumber",
        "description",
        "city",
        "country",
        "timezone",
        "lang",
        "theme",
        "mailformat",
        "maildisplay",
        "maildigest",
        "htmleditor",
        "autosubscribe",
        "trackforums",
        "calendartype",
    ],
}

# Moodle Course Fields
MOODLE_COURSE_FIELDS = {
    "REQUIRED": ["fullname", "shortname", "categoryid"],
    "OPTIONAL": [
        "idnumber",
        "summary",
        "summaryformat",
        "format",
        "showgrades",
        "newsitems",
        "startdate",
        "enddate",
        "maxbytes",
        "showreports",
        "visible",
        "groupmode",
        "groupmodeforce",
        "defaultgroupingid",
        "enablecompletion",
        "completionnotify",
    ],
}

# API Response Status Codes
MOODLE_STATUS_CODES = {
    "SUCCESS": 200,
    "INVALID_TOKEN": 401,
    "FUNCTION_NOT_EXISTS": 404,
    "INVALID_PARAMETER": 400,
    "ACCESS_DENIED": 403,
    "SERVER_ERROR": 500,
}

# Sync Configuration
SYNC_SETTINGS = {
    "MAX_RETRY_ATTEMPTS": 3,
    "RETRY_DELAY_SECONDS": 300,  # 5 minutes
    "BATCH_SIZE": 50,
    "API_TIMEOUT_SECONDS": 30,
}

# Error Categories
ERROR_CATEGORIES = {
    "NETWORK": "network_error",
    "AUTHENTICATION": "auth_error",
    "VALIDATION": "validation_error",
    "CONFLICT": "conflict_error",
    "UNKNOWN": "unknown_error",
}

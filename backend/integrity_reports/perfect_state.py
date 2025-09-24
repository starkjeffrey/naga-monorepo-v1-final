# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class AcademicCanonicalrequirement(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    sequence_number = models.SmallIntegerField()
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField()
    notes = models.TextField()
    effective_term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)
    end_term = models.ForeignKey(
        "CurriculumTerm",
        models.DO_NOTHING,
        related_name="academiccanonicalrequirement_end_term_set",
        blank=True,
        null=True,
    )
    major = models.ForeignKey("CurriculumMajor", models.DO_NOTHING)
    required_course = models.ForeignKey("CurriculumCourse", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "academic_canonicalrequirement"
        unique_together = (
            ("major", "required_course", "effective_term"),
            ("major", "sequence_number", "effective_term"),
        )


class AcademicCourseequivalency(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()
    effective_term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)
    end_term = models.ForeignKey(
        "CurriculumTerm",
        models.DO_NOTHING,
        related_name="academiccourseequivalency_end_term_set",
        blank=True,
        null=True,
    )
    equivalent_course = models.ForeignKey("CurriculumCourse", models.DO_NOTHING)
    original_course = models.ForeignKey(
        "CurriculumCourse", models.DO_NOTHING, related_name="academiccourseequivalency_original_course_set"
    )
    approval_date = models.DateField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    reason = models.TextField()
    bidirectional = models.BooleanField()

    class Meta:
        managed = False
        db_table = "academic_courseequivalency"
        unique_together = (("original_course", "equivalent_course", "effective_term"),)


class AcademicRecordsDocumentQuota(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    total_units = models.IntegerField()
    used_units = models.IntegerField()
    is_active = models.BooleanField()
    expires_date = models.DateField()
    admin_fee_line_item = models.ForeignKey("FinanceInvoiceLineItem", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    cycle_status = models.ForeignKey("EnrollmentStudentCycleStatus", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentquota_updated_by_set",
        blank=True,
        null=True,
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = "academic_records_document_quota"
        unique_together = (("student", "term"),)


class AcademicRecordsDocumentQuotaUsage(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    units_consumed = models.IntegerField()
    usage_date = models.DateTimeField()
    document_request = models.ForeignKey("AcademicRecordsDocumentrequest", models.DO_NOTHING)
    quota = models.ForeignKey(AcademicRecordsDocumentQuota, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentquotausage_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "academic_records_document_quota_usage"


class AcademicRecordsDocumentrequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    request_id = models.UUIDField(unique=True)
    request_status = models.CharField(max_length=20)
    priority = models.CharField(max_length=10)
    delivery_method = models.CharField(max_length=20)
    recipient_name = models.CharField(max_length=200)
    recipient_address = models.TextField()
    recipient_email = models.CharField(max_length=254)
    request_notes = models.TextField()
    custom_data = models.JSONField()
    has_fee = models.BooleanField()
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_free_allowance = models.BooleanField()
    payment_required = models.BooleanField()
    payment_status = models.CharField(max_length=20)
    finance_invoice_id = models.IntegerField(blank=True, null=True)
    requested_date = models.DateTimeField()
    due_date = models.DateTimeField(blank=True, null=True)
    approved_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    assigned_to = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    processed_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentrequest_processed_by_set",
        blank=True,
        null=True,
    )
    requested_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="academicrecordsdocumentrequest_requested_by_set"
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    document_type = models.ForeignKey("AcademicRecordsDocumenttypeconfig", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentrequest_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentrequest_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "academic_records_documentrequest"


class AcademicRecordsDocumentrequestcomment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    comment_text = models.TextField()
    is_internal = models.BooleanField()
    author = models.ForeignKey("UsersUser", models.DO_NOTHING)
    document_request = models.ForeignKey(AcademicRecordsDocumentrequest, models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentrequestcomment_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentrequestcomment_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "academic_records_documentrequestcomment"


class AcademicRecordsDocumenttypeconfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    code = models.CharField(unique=True, max_length=50)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30)
    description = models.TextField()
    requires_approval = models.BooleanField()
    auto_generate = models.BooleanField()
    processing_time_hours = models.IntegerField()
    requires_grade_data = models.BooleanField()
    requires_attendance_data = models.BooleanField()
    requires_manual_input = models.BooleanField()
    allows_email_delivery = models.BooleanField()
    allows_pickup = models.BooleanField()
    allows_mail_delivery = models.BooleanField()
    allows_third_party_delivery = models.BooleanField()
    required_permission = models.CharField(max_length=100)
    has_fee = models.BooleanField()
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    fee_currency = models.CharField(max_length=3)
    free_allowance_per_term = models.IntegerField()
    free_allowance_per_year = models.IntegerField()
    free_allowance_lifetime = models.IntegerField()
    is_active = models.BooleanField()
    display_order = models.IntegerField()
    unit_cost = models.IntegerField()

    class Meta:
        managed = False
        db_table = "academic_records_documenttypeconfig"


class AcademicRecordsDocumentusagetracker(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    total_requested = models.IntegerField()
    total_completed = models.IntegerField()
    total_free_used = models.IntegerField()
    total_paid = models.IntegerField()
    current_term_count = models.IntegerField()
    current_year_count = models.IntegerField()
    last_request_date = models.DateTimeField(blank=True, null=True)
    last_completed_date = models.DateTimeField(blank=True, null=True)
    document_type = models.ForeignKey(AcademicRecordsDocumenttypeconfig, models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsdocumentusagetracker_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "academic_records_documentusagetracker"
        unique_together = (("student", "document_type"),)


class AcademicRecordsGenerateddocument(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    document_id = models.UUIDField(unique=True)
    file_path = models.CharField(max_length=500)
    file_size = models.IntegerField(blank=True, null=True)
    content_hash = models.CharField(max_length=64)
    verification_code = models.CharField(unique=True, max_length=32)
    qr_code_data = models.TextField()
    generated_date = models.DateTimeField()
    document_data = models.JSONField()
    access_count = models.IntegerField()
    last_accessed = models.DateTimeField(blank=True, null=True)
    document_request = models.ForeignKey(AcademicRecordsDocumentrequest, models.DO_NOTHING)
    generated_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsgenerateddocument_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="academicrecordsgenerateddocument_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "academic_records_generateddocument"


class AcademicStudentcourseoverride(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    detailed_reason = models.TextField()
    approval_status = models.CharField(max_length=10)
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField()
    supporting_documentation = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    effective_term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)
    expiration_term = models.ForeignKey(
        "CurriculumTerm",
        models.DO_NOTHING,
        related_name="academicstudentcourseoverride_expiration_term_set",
        blank=True,
        null=True,
    )
    original_course = models.ForeignKey("CurriculumCourse", models.DO_NOTHING)
    requested_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="academicstudentcourseoverride_requested_by_set"
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    substitute_course = models.ForeignKey(
        "CurriculumCourse", models.DO_NOTHING, related_name="academicstudentcourseoverride_substitute_course_set"
    )
    request_date = models.DateTimeField()
    academic_advisor_notes = models.TextField()
    reason = models.CharField(max_length=15)

    class Meta:
        managed = False
        db_table = "academic_studentcourseoverride"
        unique_together = (("student", "original_course", "substitute_course", "effective_term"),)


class AcademicStudentdegreeprogress(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    fulfillment_method = models.CharField(max_length=20)
    fulfillment_date = models.DateField()
    credits_earned = models.DecimalField(max_digits=4, decimal_places=2)
    grade = models.CharField(max_length=10)
    is_active = models.BooleanField()
    notes = models.TextField()
    canonical_requirement = models.ForeignKey(AcademicCanonicalrequirement, models.DO_NOTHING)
    fulfilling_enrollment = models.ForeignKey(
        "EnrollmentClassheaderenrollment", models.DO_NOTHING, blank=True, null=True
    )
    fulfilling_exception = models.ForeignKey(
        "AcademicStudentrequirementexception", models.DO_NOTHING, blank=True, null=True
    )
    fulfilling_transfer = models.ForeignKey("AcademicTransfercredit", models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()
    completion_status = models.CharField(max_length=20)
    last_updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "academic_studentdegreeprogress"
        unique_together = (("student", "canonical_requirement"),)


class AcademicStudentrequirementexception(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    exception_type = models.CharField(max_length=20)
    is_waived = models.BooleanField()
    reason = models.TextField()
    supporting_documentation = models.TextField()
    approval_status = models.CharField(max_length=20)
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField()
    notes = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    canonical_requirement = models.ForeignKey(AcademicCanonicalrequirement, models.DO_NOTHING)
    effective_term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)
    expiration_term = models.ForeignKey(
        "CurriculumTerm",
        models.DO_NOTHING,
        related_name="academicstudentrequirementexception_expiration_term_set",
        blank=True,
        null=True,
    )
    fulfilling_course = models.ForeignKey("CurriculumCourse", models.DO_NOTHING, blank=True, null=True)
    requested_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="academicstudentrequirementexception_requested_by_set"
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    fulfilling_transfer_credit = models.ForeignKey("AcademicTransfercredit", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "academic_studentrequirementexception"
        unique_together = (("student", "canonical_requirement", "effective_term"),)


class AcademicTransfercredit(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    external_institution = models.CharField(max_length=200)
    external_course_code = models.CharField(max_length=20)
    external_course_name = models.CharField(max_length=200)
    external_credits = models.DecimalField(max_digits=5, decimal_places=2)
    external_grade = models.CharField(max_length=10)
    credit_type = models.CharField(max_length=10)
    approval_status = models.CharField(max_length=10)
    equivalent_course = models.ForeignKey("CurriculumCourse", models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    awarded_credits = models.DecimalField(max_digits=5, decimal_places=2)
    documentation = models.TextField()
    review_date = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField()
    reviewed_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    term_taken = models.CharField(max_length=50)
    year_taken = models.SmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "academic_transfercredit"
        unique_together = (("student", "external_institution", "external_course_code"),)


class AccountEmailaddress(models.Model):
    email = models.CharField(unique=True, max_length=254)
    verified = models.BooleanField()
    primary = models.BooleanField()
    user = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "account_emailaddress"
        unique_together = (
            ("user", "email"),
            ("user", "primary"),
        )


class AccountEmailconfirmation(models.Model):
    created = models.DateTimeField()
    sent = models.DateTimeField(blank=True, null=True)
    key = models.CharField(unique=True, max_length=64)
    email_address = models.ForeignKey(AccountEmailaddress, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "account_emailconfirmation"


class AccountsDepartment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(unique=True, max_length=100)
    code = models.CharField(unique=True, max_length=20)
    description = models.TextField()
    is_active = models.BooleanField()
    display_order = models.SmallIntegerField()

    class Meta:
        managed = False
        db_table = "accounts_department"


class AccountsPermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    codename = models.CharField(unique=True, max_length=100)
    description = models.TextField()
    is_active = models.BooleanField()
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "accounts_permission"


class AccountsPosition(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=100)
    authority_level = models.SmallIntegerField()
    can_override_policies = models.JSONField()
    approval_limits = models.JSONField()
    is_active = models.BooleanField()
    description = models.TextField()
    department = models.ForeignKey(AccountsDepartment, models.DO_NOTHING, blank=True, null=True)
    reports_to = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "accounts_position"
        unique_together = (("title", "department"),)


class AccountsPositionassignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_acting = models.BooleanField()
    is_primary = models.BooleanField()
    delegation_start = models.DateField(blank=True, null=True)
    delegation_end = models.DateField(blank=True, null=True)
    notes = models.TextField()
    delegates_to = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    person = models.ForeignKey("PeoplePerson", models.DO_NOTHING)
    position = models.ForeignKey(AccountsPosition, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "accounts_positionassignment"


class AccountsRole(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    role_type = models.CharField(max_length=20)
    can_approve = models.BooleanField()
    can_edit = models.BooleanField()
    can_view = models.BooleanField()
    is_active = models.BooleanField()
    description = models.TextField()
    department = models.ForeignKey(AccountsDepartment, models.DO_NOTHING, blank=True, null=True)
    parent_role = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "accounts_role"
        unique_together = (("name", "department"),)


class AccountsRolepermission(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    object_id = models.IntegerField(blank=True, null=True)
    is_active = models.BooleanField()
    notes = models.TextField()
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING, blank=True, null=True)
    department = models.ForeignKey(AccountsDepartment, models.DO_NOTHING, blank=True, null=True)
    permission = models.ForeignKey(AccountsPermission, models.DO_NOTHING)
    role = models.ForeignKey(AccountsRole, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "accounts_rolepermission"
        unique_together = (("role", "permission", "department", "content_type", "object_id"),)


class AccountsTeachingassignment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    minimum_degree = models.CharField(max_length=20)
    authorized_levels = models.CharField(max_length=20)
    is_native_english_speaker = models.BooleanField()
    has_special_qualification = models.BooleanField()
    special_qualification_notes = models.TextField()
    can_approve_course_changes = models.BooleanField()
    is_department_coordinator = models.BooleanField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField()
    notes = models.TextField()
    department = models.ForeignKey(AccountsDepartment, models.DO_NOTHING)
    teacher = models.ForeignKey("PeopleTeacherprofile", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "accounts_teachingassignment"
        unique_together = (("teacher", "department"),)


class AccountsUserrole(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()
    assigned_date = models.DateTimeField()
    notes = models.TextField()
    department = models.ForeignKey(AccountsDepartment, models.DO_NOTHING, blank=True, null=True)
    role = models.ForeignKey(AccountsRole, models.DO_NOTHING)
    user = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "accounts_userrole"
        unique_together = (("user", "role", "department"),)


class AttendanceAttendancearchive(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    total_sessions = models.IntegerField()
    present_sessions = models.IntegerField()
    absent_sessions = models.IntegerField()
    late_sessions = models.IntegerField()
    excused_sessions = models.IntegerField()
    attendance_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    punctuality_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    archived_on = models.DateTimeField()
    session_details = models.JSONField()
    archived_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    class_part = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "attendance_attendancearchive"
        unique_together = (("class_part", "student", "term"),)


class AttendanceAttendancerecord(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15)
    submitted_code = models.CharField(max_length=5)
    code_correct = models.BooleanField(blank=True, null=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    submitted_latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    submitted_longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    within_geofence = models.BooleanField(blank=True, null=True)
    distance_from_class = models.IntegerField(blank=True, null=True)
    data_source = models.CharField(max_length=20)
    permission_reason = models.TextField()
    permission_approved = models.BooleanField(blank=True, null=True)
    permission_notes = models.TextField()
    notes = models.TextField()
    permission_approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    recorded_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="attendanceattendancerecord_recorded_by_set",
        blank=True,
        null=True,
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    attendance_session = models.ForeignKey("AttendanceAttendancesession", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "attendance_attendancerecord"
        unique_together = (("attendance_session", "student"),)


class AttendanceAttendancesession(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    session_date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    attendance_code = models.CharField(max_length=5)
    code_generated_at = models.DateTimeField()
    code_expires_at = models.DateTimeField()
    code_window_minutes = models.IntegerField()
    latitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    geofence_radius_meters = models.IntegerField()
    is_active = models.BooleanField()
    is_makeup_class = models.BooleanField()
    makeup_reason = models.TextField()
    is_substitute_session = models.BooleanField()
    substitute_reason = models.TextField()
    substitute_assigned_at = models.DateTimeField(blank=True, null=True)
    manual_fallback_enabled = models.BooleanField()
    django_fallback_enabled = models.BooleanField()
    total_students = models.IntegerField()
    present_count = models.IntegerField()
    absent_count = models.IntegerField()
    class_part = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)
    substitute_assigned_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    substitute_teacher = models.ForeignKey("PeopleTeacherprofile", models.DO_NOTHING, blank=True, null=True)
    teacher = models.ForeignKey(
        "PeopleTeacherprofile", models.DO_NOTHING, related_name="attendanceattendancesession_teacher_set"
    )

    class Meta:
        managed = False
        db_table = "attendance_attendancesession"


class AttendanceAttendancesettings(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    allows_permission_requests = models.BooleanField()
    auto_approve_permissions = models.BooleanField()
    parent_notification_required = models.BooleanField()
    attendance_required_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    late_threshold_minutes = models.IntegerField()
    default_code_window_minutes = models.IntegerField()
    default_geofence_radius = models.IntegerField()
    attendance_affects_grade = models.BooleanField()
    attendance_grade_weight = models.DecimalField(max_digits=4, decimal_places=3)
    program = models.ForeignKey("CurriculumDivision", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "attendance_attendancesettings"


class AttendancePermissionrequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    session_date = models.DateField()
    reason = models.TextField()
    request_status = models.CharField(max_length=15)
    program_type = models.CharField(max_length=15)
    requires_approval = models.BooleanField()
    approval_date = models.DateTimeField(blank=True, null=True)
    approval_notes = models.TextField()
    parent_notified = models.BooleanField()
    parent_notification_date = models.DateTimeField(blank=True, null=True)
    parent_response = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    class_part = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "attendance_permissionrequest"
        unique_together = (("student", "class_part", "session_date"),)


class AttendanceRostersync(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    sync_date = models.DateField()
    sync_timestamp = models.DateTimeField()
    sync_type = models.CharField(max_length=10)
    is_successful = models.BooleanField()
    error_message = models.TextField()
    student_count = models.IntegerField()
    enrollment_snapshot = models.JSONField()
    roster_changed = models.BooleanField()
    changes_summary = models.TextField()
    class_part = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "attendance_rostersync"
        unique_together = (("class_part", "sync_date", "sync_type"),)


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)
    permissions = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "auth_group"


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey("AuthPermission", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_group_permissions"
        unique_together = (("group", "permission"),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "auth_permission"
        unique_together = (("content_type", "codename"),)


class CommonActivitylog(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    activity_type = models.CharField(max_length=20)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField()
    session_key = models.CharField(max_length=40)
    object_id = models.IntegerField(blank=True, null=True)
    changes = models.JSONField()
    metadata = models.JSONField()
    success = models.BooleanField()
    error_message = models.TextField()
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="commonactivitylog_updated_by_set", blank=True, null=True
    )
    user = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="commonactivitylog_user_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "common_activitylog"


class CommonHoliday(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    eng_name = models.CharField(max_length=200)
    khmer_name = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField()
    notes = models.TextField()

    class Meta:
        managed = False
        db_table = "common_holiday"
        unique_together = (("eng_name", "start_date"),)


class CommonNotification(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20)
    priority = models.CharField(max_length=10)
    is_read = models.BooleanField()
    read_at = models.DateTimeField(blank=True, null=True)
    action_url = models.CharField(max_length=500)
    action_text = models.CharField(max_length=100)
    expires_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField()
    object_id = models.IntegerField(blank=True, null=True)
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="commonnotification_updated_by_set", blank=True, null=True
    )
    user = models.ForeignKey("UsersUser", models.DO_NOTHING, related_name="commonnotification_user_set")

    class Meta:
        managed = False
        db_table = "common_notification"


class CommonRoom(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    building = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    code = models.CharField(unique=True, max_length=20)
    capacity = models.IntegerField()
    room_type = models.CharField(max_length=20)
    has_projector = models.BooleanField()
    has_whiteboard = models.BooleanField()
    has_computers = models.BooleanField()
    is_active = models.BooleanField()
    notes = models.TextField()

    class Meta:
        managed = False
        db_table = "common_room"
        unique_together = (("building", "code"),)


class CommonStudentactivitylog(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    student_number = models.CharField(max_length=20)
    student_name = models.CharField(max_length=200)
    activity_type = models.CharField(max_length=40)
    description = models.TextField()
    term_name = models.CharField(max_length=100)
    class_code = models.CharField(max_length=20)
    class_section = models.CharField(max_length=10)
    program_name = models.CharField(max_length=100)
    activity_details = models.JSONField()
    is_system_generated = models.BooleanField()
    performed_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    visibility = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "common_studentactivitylog"


class CommonSystemauditlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    action_type = models.CharField(max_length=50)
    target_app = models.CharField(max_length=50, blank=True, null=True)
    target_model = models.CharField(max_length=50, blank=True, null=True)
    target_object_id = models.CharField(max_length=100, blank=True, null=True)
    override_reason = models.TextField()
    original_restriction = models.TextField()
    override_details = models.JSONField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField()
    performed_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING)
    object_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = "common_systemauditlog"


class ConstanceConstance(models.Model):
    key = models.CharField(unique=True, max_length=255)
    value = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "constance_constance"


class CurriculumCourse(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    code = models.CharField(max_length=15)
    title = models.CharField(max_length=100)
    short_title = models.CharField(max_length=30)
    description = models.TextField()
    credits = models.IntegerField()
    is_language = models.BooleanField()
    is_foundation_year = models.BooleanField()
    is_senior_project = models.BooleanField()
    recommended_term = models.IntegerField(blank=True, null=True)
    earliest_term = models.IntegerField(blank=True, null=True)
    latest_term = models.IntegerField(blank=True, null=True)
    failure_retry_priority = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField()
    cycle = models.ForeignKey("CurriculumCycle", models.DO_NOTHING)
    majors = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "curriculum_course"


class CurriculumCourseMajors(models.Model):
    id = models.BigAutoField(primary_key=True)
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    major = models.ForeignKey("CurriculumMajor", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "curriculum_course_majors"
        unique_together = (("course", "major"),)


class CurriculumCourseparttemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    part_type = models.CharField(max_length=15)
    part_code = models.CharField(max_length=10)
    name = models.CharField(max_length=100)
    session_number = models.SmallIntegerField()
    meeting_days = models.CharField(max_length=20)
    grade_weight = models.DecimalField(max_digits=4, decimal_places=3)
    display_order = models.IntegerField()
    is_active = models.BooleanField()
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    textbooks = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "curriculum_courseparttemplate"
        unique_together = (("course", "part_code"),)


class CurriculumCourseparttemplateTextbooks(models.Model):
    id = models.BigAutoField(primary_key=True)
    courseparttemplate = models.ForeignKey(CurriculumCourseparttemplate, models.DO_NOTHING)
    textbook = models.ForeignKey("CurriculumTextbook", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "curriculum_courseparttemplate_textbooks"
        unique_together = (("courseparttemplate", "textbook"),)


class CurriculumCourseprerequisite(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField()
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    prerequisite = models.ForeignKey(
        CurriculumCourse, models.DO_NOTHING, related_name="curriculumcourseprerequisite_prerequisite_set"
    )

    class Meta:
        managed = False
        db_table = "curriculum_courseprerequisite"
        unique_together = (("prerequisite", "course"),)


class CurriculumCycle(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50)
    typical_duration_terms = models.SmallIntegerField(blank=True, null=True)
    description = models.TextField()
    is_active = models.BooleanField()
    display_order = models.IntegerField()
    division = models.ForeignKey("CurriculumDivision", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "curriculum_cycle"
        unique_together = (("division", "short_name"),)


class CurriculumDivision(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50)
    description = models.TextField()
    is_active = models.BooleanField()
    display_order = models.IntegerField()

    class Meta:
        managed = False
        db_table = "curriculum_division"


class CurriculumMajor(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50)
    code = models.CharField(max_length=20)
    faculty_display_name = models.CharField(max_length=255)
    faculty_code = models.CharField(max_length=10)
    program_type = models.CharField(max_length=20)
    degree_awarded = models.CharField(max_length=20)
    description = models.TextField()
    total_credits_required = models.SmallIntegerField(blank=True, null=True)
    is_active = models.BooleanField()
    display_order = models.IntegerField()
    cycle = models.ForeignKey(CurriculumCycle, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "curriculum_major"
        unique_together = (("cycle", "code"),)


class CurriculumSeniorprojectgroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    project_title = models.CharField(max_length=255)
    final_title = models.CharField(max_length=255)
    project_description = models.TextField()
    status = models.CharField(max_length=20)
    proposal_date = models.DateField(blank=True, null=True)
    approval_date = models.DateField(blank=True, null=True)
    submission_date = models.DateField(blank=True, null=True)
    defense_date = models.DateField(blank=True, null=True)
    completion_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    advisor = models.ForeignKey("PeopleTeacherprofile", models.DO_NOTHING)
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    term = models.ForeignKey("CurriculumTerm", models.DO_NOTHING)
    students = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "curriculum_seniorprojectgroup"
        unique_together = (("course", "term", "project_title"),)


class CurriculumSeniorprojectgroupStudents(models.Model):
    id = models.BigAutoField(primary_key=True)
    seniorprojectgroup = models.ForeignKey(CurriculumSeniorprojectgroup, models.DO_NOTHING)
    studentprofile = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "curriculum_seniorprojectgroup_students"
        unique_together = (("seniorprojectgroup", "studentprofile"),)


class CurriculumTerm(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    code = models.CharField(max_length=100)
    description = models.TextField()
    term_type = models.CharField(max_length=20)
    ba_cohort_number = models.SmallIntegerField(blank=True, null=True)
    ma_cohort_number = models.SmallIntegerField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    discount_end_date = models.DateField(blank=True, null=True)
    add_date = models.DateField(blank=True, null=True)
    drop_date = models.DateField(blank=True, null=True)
    payment_deadline_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "curriculum_term"


class CurriculumTextbook(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20)
    publisher = models.CharField(max_length=100)
    edition = models.CharField(max_length=20)
    year = models.SmallIntegerField(blank=True, null=True)
    notes = models.TextField()

    class Meta:
        managed = False
        db_table = "curriculum_textbook"


class DebugToolbarHistoryentry(models.Model):
    request_id = models.UUIDField(primary_key=True)
    data = models.JSONField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "debug_toolbar_historyentry"


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "django_admin_log"


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "django_content_type"
        unique_together = (("app_label", "model"),)


class DjangoDramatiqTask(models.Model):
    id = models.UUIDField(primary_key=True)
    status = models.CharField(max_length=8)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    message_data = models.BinaryField()
    actor_name = models.CharField(max_length=300, blank=True, null=True)
    queue_name = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "django_dramatiq_task"


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "django_migrations"


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "django_session"


class DjangoSite(models.Model):
    domain = models.CharField(unique=True, max_length=100)
    name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "django_site"


class EnrollmentAcademicjourney(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    current_level = models.CharField(max_length=10)
    expected_completion_date = models.DateField(blank=True, null=True)
    data_source = models.CharField(max_length=20)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    data_issues = models.JSONField()
    requires_review = models.BooleanField()
    last_manual_review = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="enrollmentacademicjourney_updated_by_set", blank=True, null=True
    )
    program_type = models.CharField(max_length=20)
    program = models.ForeignKey(CurriculumMajor, models.DO_NOTHING, blank=True, null=True)
    start_date = models.DateField(blank=True, null=True)
    stop_date = models.DateField(blank=True, null=True)
    start_term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, blank=True, null=True)
    term_code = models.CharField(max_length=20)
    duration_in_terms = models.IntegerField()
    transition_status = models.CharField(max_length=20)
    language_level = models.CharField(max_length=20)
    accumulated_credits = models.DecimalField(max_digits=6, decimal_places=2)
    courses_completed = models.IntegerField()

    class Meta:
        managed = False
        db_table = "enrollment_academicjourney"
        unique_together = (("student", "program_type", "start_date"),)


class EnrollmentAcademicprogression(models.Model):
    student = models.OneToOneField("PeopleStudentprofile", models.DO_NOTHING, primary_key=True)
    student_name = models.CharField(max_length=200)
    student_id_number = models.CharField(max_length=20)
    entry_program = models.CharField(max_length=50)
    entry_date = models.DateField()
    entry_term = models.CharField(max_length=20)
    language_start_date = models.DateField(blank=True, null=True)
    language_end_date = models.DateField(blank=True, null=True)
    language_terms = models.IntegerField()
    language_final_level = models.CharField(max_length=20)
    language_completion_status = models.CharField(max_length=20)
    ba_start_date = models.DateField(blank=True, null=True)
    ba_major = models.CharField(max_length=100)
    ba_major_changes = models.IntegerField()
    ba_terms = models.IntegerField()
    ba_credits = models.DecimalField(max_digits=6, decimal_places=2)
    ba_gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    ba_completion_date = models.DateField(blank=True, null=True)
    ba_completion_status = models.CharField(max_length=20)
    ma_start_date = models.DateField(blank=True, null=True)
    ma_program = models.CharField(max_length=100)
    ma_terms = models.IntegerField()
    ma_credits = models.DecimalField(max_digits=6, decimal_places=2)
    ma_gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    ma_completion_date = models.DateField(blank=True, null=True)
    ma_completion_status = models.CharField(max_length=20)
    total_terms = models.IntegerField()
    total_gap_terms = models.IntegerField()
    time_to_ba_days = models.IntegerField(blank=True, null=True)
    time_to_ma_days = models.IntegerField(blank=True, null=True)
    current_status = models.CharField(max_length=50)
    last_enrollment_term = models.CharField(max_length=20)
    last_updated = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "enrollment_academicprogression"


class EnrollmentCertificateissuance(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    certificate_type = models.CharField(max_length=20)
    issue_date = models.DateField()
    completion_level = models.CharField(max_length=20)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    honors = models.CharField(max_length=50)
    certificate_number = models.CharField(unique=True, max_length=50)
    printed_date = models.DateField(blank=True, null=True)
    collected_date = models.DateField(blank=True, null=True)
    collected_by = models.CharField(max_length=100)
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    issued_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="enrollmentcertificateissuance_issued_by_set"
    )
    program = models.ForeignKey(CurriculumMajor, models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentcertificateissuance_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "enrollment_certificateissuance"


class EnrollmentClassheaderenrollment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20)
    final_grade = models.CharField(max_length=10)
    grade_points = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    enrollment_date = models.DateTimeField()
    completion_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    has_override = models.BooleanField()
    override_type = models.CharField(max_length=50)
    override_reason = models.TextField()
    is_audit = models.BooleanField()
    late_enrollment = models.BooleanField()
    class_header = models.ForeignKey("SchedulingClassheader", models.DO_NOTHING)
    enrolled_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentclassheaderenrollment_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentclassheaderenrollment_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "enrollment_classheaderenrollment"
        unique_together = (
            ("student", "class_header"),
            ("student", "class_header"),
        )


class EnrollmentClasspartenrollment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    enrollment_date = models.DateTimeField()
    is_active = models.BooleanField()
    notes = models.TextField()
    class_part = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentclasspartenrollment_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "enrollment_classpartenrollment"
        unique_together = (("student", "class_part", "is_active"),)


class EnrollmentClasssessionexemption(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    exemption_reason = models.CharField(max_length=100)
    exemption_date = models.DateTimeField()
    notes = models.TextField()
    class_header_enrollment = models.ForeignKey(EnrollmentClassheaderenrollment, models.DO_NOTHING)
    class_session = models.ForeignKey("SchedulingClasssession", models.DO_NOTHING)
    exempted_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentclasssessionexemption_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentclasssessionexemption_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "enrollment_classsessionexemption"
        unique_together = (("class_header_enrollment", "class_session"),)


class EnrollmentMajordeclaration(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    effective_date = models.DateField()
    declared_date = models.DateTimeField()
    is_active = models.BooleanField()
    is_self_declared = models.BooleanField()
    change_reason = models.TextField()
    supporting_documents = models.TextField()
    requires_approval = models.BooleanField()
    approved_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    declared_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentmajordeclaration_declared_by_set",
        blank=True,
        null=True,
    )
    major = models.ForeignKey(CurriculumMajor, models.DO_NOTHING)
    previous_declaration = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="enrollmentmajordeclaration_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="enrollmentmajordeclaration_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "enrollment_majordeclaration"
        unique_together = (("student", "effective_date", "is_active"),)


class EnrollmentProgramenrollment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    enrollment_type = models.CharField(max_length=10)
    status = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    entry_level = models.CharField(max_length=50)
    finishing_level = models.CharField(max_length=50)
    terms_active = models.IntegerField()
    is_joint = models.BooleanField()
    is_system_generated = models.BooleanField()
    last_status_update = models.DateTimeField()
    notes = models.TextField()
    end_term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, blank=True, null=True)
    enrolled_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    program = models.ForeignKey(CurriculumMajor, models.DO_NOTHING)
    start_term = models.ForeignKey(
        CurriculumTerm,
        models.DO_NOTHING,
        related_name="enrollmentprogramenrollment_start_term_set",
        blank=True,
        null=True,
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentprogramenrollment_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentprogramenrollment_updated_by_set",
        blank=True,
        null=True,
    )
    division = models.CharField(max_length=10)
    cycle = models.CharField(max_length=10)
    credits_earned = models.DecimalField(max_digits=6, decimal_places=2)
    credits_required = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    gpa_at_exit = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    exit_reason = models.CharField(max_length=15)
    is_deduced = models.BooleanField()
    deduction_confidence = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    completion_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    expected_completion_date = models.DateField(blank=True, null=True)
    time_to_completion = models.IntegerField(blank=True, null=True)
    enrollment_gaps = models.JSONField()
    legacy_section_code = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "enrollment_programenrollment"
        unique_together = (("student", "program", "start_date"),)


class EnrollmentProgrammilestone(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    milestone_type = models.CharField(max_length=20)
    milestone_date = models.DateField()
    level = models.CharField(max_length=10)
    is_inferred = models.BooleanField()
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    inference_method = models.CharField(max_length=50)
    notes = models.TextField()
    academic_term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    from_program = models.ForeignKey(CurriculumMajor, models.DO_NOTHING, blank=True, null=True)
    journey = models.ForeignKey(EnrollmentAcademicjourney, models.DO_NOTHING)
    program = models.ForeignKey(
        CurriculumMajor,
        models.DO_NOTHING,
        related_name="enrollmentprogrammilestone_program_set",
        blank=True,
        null=True,
    )
    recorded_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentprogrammilestone_recorded_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="enrollmentprogrammilestone_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "enrollment_programmilestone"


class EnrollmentProgramperiod(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    transition_type = models.CharField(max_length=20)
    transition_date = models.DateField()
    from_program_type = models.CharField(max_length=20, blank=True, null=True)
    to_program_type = models.CharField(max_length=20)
    program_name = models.CharField(max_length=200)
    duration_days = models.IntegerField()
    duration_months = models.DecimalField(max_digits=5, decimal_places=1)
    term_count = models.IntegerField()
    total_credits = models.DecimalField(max_digits=6, decimal_places=2)
    completed_credits = models.DecimalField(max_digits=6, decimal_places=2)
    gpa = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    completion_status = models.CharField(max_length=20)
    language_level = models.CharField(max_length=10)
    sequence_number = models.IntegerField()
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    notes = models.TextField()
    journey = models.ForeignKey(EnrollmentAcademicjourney, models.DO_NOTHING)
    to_program = models.ForeignKey(CurriculumMajor, models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="enrollmentprogramperiod_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "enrollment_programperiod"
        unique_together = (("journey", "sequence_number"),)


class EnrollmentProgramtransition(models.Model):
    id = models.BigAutoField(primary_key=True)
    transition_date = models.DateField()
    transition_type = models.CharField(max_length=10)
    transition_reason = models.TextField()
    credits_transferred = models.DecimalField(max_digits=6, decimal_places=2)
    gap_days = models.IntegerField()
    from_enrollment = models.ForeignKey(EnrollmentProgramenrollment, models.DO_NOTHING)
    to_enrollment = models.ForeignKey(
        EnrollmentProgramenrollment, models.DO_NOTHING, related_name="enrollmentprogramtransition_to_enrollment_set"
    )
    transition_term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "enrollment_programtransition"


class EnrollmentSeniorprojectgroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    project_title = models.CharField(max_length=255)
    final_title = models.CharField(max_length=255)
    project_description = models.TextField()
    status = models.CharField(max_length=20)
    proposal_date = models.DateField(blank=True, null=True)
    approval_date = models.DateField(blank=True, null=True)
    submission_date = models.DateField(blank=True, null=True)
    defense_date = models.DateField(blank=True, null=True)
    completion_date = models.DateField(blank=True, null=True)
    registration_date = models.DateField(blank=True, null=True)
    graduation_date = models.DateField(blank=True, null=True)
    is_graduated = models.BooleanField()
    notes = models.TextField()
    advisor = models.ForeignKey("PeopleTeacherprofile", models.DO_NOTHING)
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    registration_term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, blank=True, null=True)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, related_name="enrollmentseniorprojectgroup_term_set")
    students = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "enrollment_seniorprojectgroup"
        unique_together = (("course", "term", "project_title"),)


class EnrollmentSeniorprojectgroupStudents(models.Model):
    id = models.BigAutoField(primary_key=True)
    seniorprojectgroup = models.ForeignKey(EnrollmentSeniorprojectgroup, models.DO_NOTHING)
    studentprofile = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "enrollment_seniorprojectgroup_students"
        unique_together = (("seniorprojectgroup", "studentprofile"),)


class EnrollmentStudentCycleStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    cycle_type = models.CharField(max_length=3)
    detected_date = models.DateField()
    is_active = models.BooleanField()
    deactivated_date = models.DateField(blank=True, null=True)
    deactivation_reason = models.CharField(max_length=50)
    notes = models.TextField()
    source_program = models.ForeignKey(CurriculumMajor, models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    target_program = models.ForeignKey(
        CurriculumMajor, models.DO_NOTHING, related_name="enrollmentstudentcyclestatus_target_program_set"
    )
    is_deleted = models.BooleanField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "enrollment_student_cycle_status"
        unique_together = (("student", "cycle_type", "target_program"),)


class EnrollmentStudentcourseeligibility(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_eligible = models.BooleanField()
    is_retake = models.BooleanField()
    previous_attempts = models.SmallIntegerField()
    retry_priority_score = models.SmallIntegerField()
    last_calculated = models.DateTimeField()
    calculation_notes = models.TextField()
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="enrollmentstudentcourseeligibility_updated_by_set",
        blank=True,
        null=True,
    )
    missing_prerequisites = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "enrollment_studentcourseeligibility"
        unique_together = (("student", "course", "term"),)


class EnrollmentStudentcourseeligibilityMissingPrerequisites(models.Model):
    id = models.BigAutoField(primary_key=True)
    studentcourseeligibility = models.ForeignKey(EnrollmentStudentcourseeligibility, models.DO_NOTHING)
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "enrollment_studentcourseeligibility_missing_prerequisites"
        unique_together = (("studentcourseeligibility", "course"),)


class FinanceAdministrativeFeeConfig(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    cycle_type = models.CharField(unique=True, max_length=3)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    included_document_units = models.IntegerField()
    quota_validity_days = models.IntegerField()
    is_active = models.BooleanField()
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="financeadministrativefeeconfig_updated_by_set",
        blank=True,
        null=True,
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = "finance_administrative_fee_config"


class FinanceArReconstructionBatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    batch_id = models.CharField(unique=True, max_length=50)
    term_id = models.CharField(max_length=50, blank=True, null=True)
    processing_mode = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    total_receipts = models.IntegerField()
    processed_receipts = models.IntegerField()
    successful_reconstructions = models.IntegerField()
    failed_reconstructions = models.IntegerField()
    pending_review_count = models.IntegerField()
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    processing_parameters = models.JSONField()
    variance_summary = models.JSONField()
    processing_log = models.TextField()
    created_by = models.ForeignKey("PeopleStaffprofile", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "PeopleStaffprofile",
        models.DO_NOTHING,
        related_name="financearreconstructionbatch_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "finance_ar_reconstruction_batch"


class FinanceCashierSession(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    cashier = models.ForeignKey("UsersUser", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financecashiersession_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financecashiersession_updated_by_set", blank=True, null=True
    )
    session_number = models.CharField(unique=True, max_length=50, blank=True, null=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    closing_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    expected_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_cashier_session"


class FinanceCashierSessionBackup(models.Model):
    id = models.BigIntegerField(blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    opening_time = models.DateTimeField(blank=True, null=True)
    closing_time = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    variance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_cashier_session_backup"


class FinanceClerkIdentification(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    clerk_name = models.CharField(max_length=100)
    computer_identifier = models.CharField(max_length=100)
    receipt_id_pattern = models.CharField(max_length=200)
    extraction_confidence = models.CharField(max_length=10)
    first_seen_date = models.DateTimeField()
    last_seen_date = models.DateTimeField()
    receipt_count = models.IntegerField()
    verified_by_user = models.BooleanField()
    verification_notes = models.TextField()
    created_by = models.ForeignKey("PeopleStaffprofile", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "PeopleStaffprofile",
        models.DO_NOTHING,
        related_name="financeclerkidentification_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "finance_clerk_identification"
        unique_together = (("clerk_name", "computer_identifier"),)


class FinanceCourseFixedPricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    domestic_price = models.DecimalField(max_digits=10, decimal_places=2)
    foreign_price = models.DecimalField(max_digits=10, decimal_places=2)
    course = models.OneToOneField(CurriculumCourse, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financecoursefixedpricing_updated_by_set", blank=True, null=True
    )
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_course_fixed_pricing"
        unique_together = (("course", "effective_date"),)


class FinanceDefaultPricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    domestic_price = models.DecimalField(max_digits=10, decimal_places=2)
    foreign_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    cycle = models.OneToOneField(CurriculumCycle, models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financedefaultpricing_updated_by_set", blank=True, null=True
    )
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_default_pricing"
        unique_together = (("cycle", "effective_date"),)


class FinanceDiscountApplication(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_date = models.DateTimeField()
    payment_date = models.DateField()
    authority = models.CharField(max_length=50)
    approval_status = models.CharField(max_length=20)
    notes = models.TextField()
    legacy_receipt_ipk = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    discount_rule = models.ForeignKey("FinanceDiscountRule", models.DO_NOTHING)
    invoice = models.ForeignKey("FinanceInvoice", models.DO_NOTHING, blank=True, null=True)
    payment = models.ForeignKey("FinancePayment", models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financediscountapplication_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_discount_application"


class FinanceDiscountRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    rule_name = models.CharField(unique=True, max_length=100)
    rule_type = models.CharField(max_length=20)
    pattern_text = models.CharField(max_length=200)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    fixed_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    applies_to_terms = models.JSONField()
    applies_to_programs = models.JSONField()
    is_active = models.BooleanField()
    effective_date = models.DateField()
    times_applied = models.IntegerField()
    last_applied_date = models.DateTimeField(blank=True, null=True)
    created_by = models.ForeignKey("PeopleStaffprofile", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "PeopleStaffprofile",
        models.DO_NOTHING,
        related_name="financediscountrule_updated_by_set",
        blank=True,
        null=True,
    )
    applies_to_cycle = models.CharField(max_length=10)

    class Meta:
        managed = False
        db_table = "finance_discount_rule"


class FinanceDocumentExcessFee(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    units_charged = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    document_request = models.ForeignKey(AcademicRecordsDocumentrequest, models.DO_NOTHING)
    invoice_line_item = models.ForeignKey("FinanceInvoiceLineItem", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financedocumentexcessfee_updated_by_set", blank=True, null=True
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = "finance_document_excess_fee"


class FinanceFeeGlMapping(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    fee_type = models.CharField(max_length=20)
    fee_code = models.CharField(max_length=50)
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    receivable_account = models.ForeignKey("FinanceGlAccount", models.DO_NOTHING, blank=True, null=True)
    revenue_account = models.ForeignKey(
        "FinanceGlAccount", models.DO_NOTHING, related_name="financefeeglmapping_revenue_account_set"
    )
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financefeeglmapping_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_fee_gl_mapping"
        unique_together = (("fee_code", "effective_date"),)


class FinanceFeePricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    fee_type = models.CharField(max_length=20)
    currency = models.CharField(max_length=3)
    is_per_course = models.BooleanField()
    is_per_term = models.BooleanField()
    is_mandatory = models.BooleanField()
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    description = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financefeepricing_updated_by_set", blank=True, null=True
    )
    foreign_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    local_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_per_document = models.BooleanField()

    class Meta:
        managed = False
        db_table = "finance_fee_pricing"
        unique_together = (("name", "fee_type", "effective_date"),)


class FinanceFinancialtransaction(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    transaction_id = models.CharField(unique=True, max_length=100)
    transaction_type = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    description = models.CharField(max_length=300)
    transaction_date = models.DateTimeField()
    reference_data = models.JSONField()
    processed_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    invoice = models.ForeignKey("FinanceInvoice", models.DO_NOTHING, blank=True, null=True)
    payment = models.ForeignKey("FinancePayment", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="financefinancialtransaction_created_by_set",
        blank=True,
        null=True,
    )
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="financefinancialtransaction_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "finance_financialtransaction"


class FinanceGlAccount(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    account_code = models.CharField(unique=True, max_length=20)
    account_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20)
    account_category = models.CharField(max_length=30)
    is_active = models.BooleanField()
    requires_department = models.BooleanField()
    description = models.TextField()
    parent_account = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financeglaccount_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_gl_account"


class FinanceGlBatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    batch_number = models.CharField(unique=True, max_length=50)
    batch_date = models.DateField()
    accounting_period = models.CharField(max_length=7)
    status = models.CharField(max_length=20)
    total_entries = models.IntegerField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    export_file = models.CharField(max_length=255)
    exported_date = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField()
    notes = models.TextField()
    exported_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financeglbatch_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financeglbatch_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_gl_batch"


class FinanceInvoice(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    invoice_number = models.CharField(unique=True, max_length=50)
    issue_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=20)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    version = models.IntegerField()
    notes = models.TextField()
    sent_date = models.DateTimeField(blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financeinvoice_updated_by_set", blank=True, null=True
    )
    legacy_receipt_number = models.CharField(max_length=50)
    legacy_receipt_id = models.CharField(max_length=200, blank=True, null=True)
    legacy_notes = models.TextField()
    legacy_processing_clerk = models.CharField(max_length=100)
    is_historical = models.BooleanField()
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)
    reconstruction_status = models.CharField(max_length=20)
    needs_reprocessing = models.BooleanField()
    reprocessing_reason = models.TextField()
    reconstruction_batch = models.ForeignKey(FinanceArReconstructionBatch, models.DO_NOTHING, blank=True, null=True)
    legacy_ipk = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_invoice"


class FinanceInvoiceLineItem(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    line_item_type = models.CharField(max_length=20)
    description = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.DecimalField(max_digits=6, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    enrollment = models.ForeignKey(EnrollmentClassheaderenrollment, models.DO_NOTHING, blank=True, null=True)
    fee_pricing = models.ForeignKey(FinanceFeePricing, models.DO_NOTHING, blank=True, null=True)
    invoice = models.ForeignKey(FinanceInvoice, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financeinvoicelineitem_updated_by_set", blank=True, null=True
    )
    legacy_program_code = models.CharField(max_length=10)
    legacy_course_level = models.CharField(max_length=10)
    pricing_method_used = models.CharField(max_length=30)
    pricing_confidence = models.CharField(max_length=10)
    base_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_reason = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = "finance_invoice_line_item"


class FinanceJournalEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    entry_number = models.CharField(unique=True, max_length=50)
    entry_date = models.DateField()
    accounting_period = models.CharField(max_length=7)
    entry_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    description = models.CharField(max_length=200)
    reference_number = models.CharField(max_length=50)
    total_debits = models.DecimalField(max_digits=12, decimal_places=2)
    total_credits = models.DecimalField(max_digits=12, decimal_places=2)
    approved_date = models.DateTimeField(blank=True, null=True)
    posted_date = models.DateTimeField(blank=True, null=True)
    source_system = models.CharField(max_length=50)
    batch_id = models.CharField(max_length=50)
    notes = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    prepared_by = models.ForeignKey("UsersUser", models.DO_NOTHING, related_name="financejournalentry_prepared_by_set")
    reverses_entry = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financejournalentry_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financejournalentry_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_journal_entry"


class FinanceJournalEntryLine(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    line_number = models.SmallIntegerField()
    debit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    credit_amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=200)
    reference_type = models.CharField(max_length=50)
    reference_id = models.CharField(max_length=50)
    department_code = models.CharField(max_length=20)
    project_code = models.CharField(max_length=20)
    gl_account = models.ForeignKey(FinanceGlAccount, models.DO_NOTHING)
    journal_entry = models.ForeignKey(FinanceJournalEntry, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financejournalentryline_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "finance_journal_entry_line"
        unique_together = (("journal_entry", "line_number"),)


class FinanceLegacyReceiptMapping(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    legacy_receipt_number = models.CharField(max_length=20)
    legacy_receipt_id = models.CharField(max_length=200)
    legacy_student_id = models.CharField(max_length=10)
    legacy_term_id = models.CharField(max_length=50)
    legacy_amount = models.DecimalField(max_digits=10, decimal_places=2)
    legacy_net_amount = models.DecimalField(max_digits=10, decimal_places=2)
    legacy_discount = models.DecimalField(max_digits=10, decimal_places=2)
    reconstructed_total = models.DecimalField(max_digits=10, decimal_places=2)
    variance_amount = models.DecimalField(max_digits=10, decimal_places=2)
    processing_date = models.DateTimeField()
    validation_status = models.CharField(max_length=20)
    validation_notes = models.TextField()
    created_by = models.ForeignKey("PeopleStaffprofile", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "PeopleStaffprofile",
        models.DO_NOTHING,
        related_name="financelegacyreceiptmapping_updated_by_set",
        blank=True,
        null=True,
    )
    generated_invoice = models.ForeignKey(FinanceInvoice, models.DO_NOTHING)
    generated_payment = models.ForeignKey("FinancePayment", models.DO_NOTHING)
    reconstruction_batch = models.ForeignKey(FinanceArReconstructionBatch, models.DO_NOTHING)
    legacy_notes = models.TextField()
    parsed_note_type = models.CharField(max_length=50)
    parsed_amount_adjustment = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    parsed_percentage_adjustment = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    parsed_authority = models.CharField(max_length=100, blank=True, null=True)
    parsed_reason = models.CharField(max_length=200, blank=True, null=True)
    notes_processing_confidence = models.DecimalField(max_digits=3, decimal_places=2)
    ar_transaction_mapping = models.CharField(max_length=50)
    normalized_note = models.TextField()
    legacy_ipk = models.IntegerField(unique=True, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_legacy_receipt_mapping"
        unique_together = (("legacy_receipt_number", "reconstruction_batch"),)


class FinanceMaterialityThreshold(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    context = models.CharField(unique=True, max_length=20)
    absolute_threshold = models.DecimalField(max_digits=10, decimal_places=2)
    percentage_threshold = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    effective_date = models.DateField()
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financematerialitythreshold_updated_by_set"
    )

    class Meta:
        managed = False
        db_table = "finance_materiality_threshold"


class FinancePayment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    payment_reference = models.CharField(unique=True, max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    payment_method = models.CharField(max_length=20)
    payment_date = models.DateField()
    processed_date = models.DateTimeField()
    status = models.CharField(max_length=20)
    payer_name = models.CharField(max_length=200)
    external_reference = models.CharField(max_length=200)
    notes = models.TextField()
    invoice = models.ForeignKey(FinanceInvoice, models.DO_NOTHING)
    processed_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financepayment_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financepayment_updated_by_set", blank=True, null=True
    )
    legacy_receipt_reference = models.CharField(max_length=50)
    legacy_processing_clerk = models.CharField(max_length=100)
    legacy_business_notes = models.TextField()
    legacy_receipt_full_id = models.CharField(max_length=200)
    is_historical_payment = models.BooleanField()
    legacy_program_code = models.CharField(max_length=10)
    legacy_ipk = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_payment"
        unique_together = (("external_reference", "payment_method"),)


class FinanceReadingClassPricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    tier = models.CharField(max_length=10)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    cycle = models.ForeignKey(CurriculumCycle, models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financereadingclasspricing_updated_by_set", blank=True, null=True
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    domestic_price = models.DecimalField(max_digits=10, decimal_places=2)
    foreign_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = "finance_reading_class_pricing"
        unique_together = (
            ("cycle", "tier", "effective_date"),
            ("cycle", "tier"),
        )


class FinanceReconciliationAdjustment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    adjustment_type = models.CharField(max_length=20)
    description = models.CharField(max_length=200)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    adjusted_amount = models.DecimalField(max_digits=10, decimal_places=2)
    variance = models.DecimalField(max_digits=10, decimal_places=2)
    requires_approval = models.BooleanField()
    approved_date = models.DateTimeField(blank=True, null=True)
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financereconciliationadjustment_created_by_set"
    )
    gl_account = models.ForeignKey(FinanceGlAccount, models.DO_NOTHING, blank=True, null=True)
    journal_entry = models.ForeignKey(FinanceJournalEntry, models.DO_NOTHING, blank=True, null=True)
    payment = models.ForeignKey(FinancePayment, models.DO_NOTHING)
    reconciliation_batch = models.ForeignKey("FinanceReconciliationBatch", models.DO_NOTHING, blank=True, null=True)
    reconciliation_status = models.ForeignKey("FinanceReconciliationStatus", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING, blank=True, null=True)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financereconciliationadjustment_updated_by_set"
    )

    class Meta:
        managed = False
        db_table = "finance_reconciliation_adjustment"


class FinanceReconciliationBatch(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    batch_id = models.CharField(unique=True, max_length=50)
    batch_type = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20)
    total_payments = models.IntegerField()
    processed_payments = models.IntegerField()
    successful_matches = models.IntegerField()
    failed_matches = models.IntegerField()
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    parameters = models.JSONField()
    results_summary = models.JSONField()
    error_log = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financereconciliationbatch_updated_by_set"
    )

    class Meta:
        managed = False
        db_table = "finance_reconciliation_batch"


class FinanceReconciliationRule(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    rule_type = models.CharField(max_length=20)
    description = models.CharField(max_length=200)
    priority = models.IntegerField()
    is_active = models.BooleanField()
    parameters = models.JSONField()
    success_count = models.IntegerField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financereconciliationrule_updated_by_set"
    )
    rule_name = models.CharField(unique=True, max_length=100)
    confidence_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    times_applied = models.IntegerField()
    last_applied = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_reconciliation_rule"


class FinanceReconciliationStatus(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2)
    variance_amount = models.DecimalField(max_digits=10, decimal_places=2)
    variance_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    last_attempt_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    payment = models.OneToOneField(FinancePayment, models.DO_NOTHING)
    reconciled_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="financereconciliationstatus_reconciled_by_set",
        blank=True,
        null=True,
    )
    reconciliation_batch = models.ForeignKey(FinanceReconciliationBatch, models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financereconciliationstatus_updated_by_set"
    )
    confidence_level = models.CharField(max_length=10)
    pricing_method_applied = models.CharField(max_length=20, blank=True, null=True)
    refinement_attempts = models.IntegerField()
    confidence_history = models.JSONField()
    refinement_strategies_tried = models.JSONField()
    reconciled_date = models.DateTimeField(blank=True, null=True)
    error_category = models.CharField(max_length=50)
    error_details = models.JSONField()
    matched_enrollments = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_reconciliation_status"


class FinanceReconciliationStatusMatchedEnrollments(models.Model):
    id = models.BigAutoField(primary_key=True)
    reconciliationstatus = models.ForeignKey(FinanceReconciliationStatus, models.DO_NOTHING)
    classheaderenrollment = models.ForeignKey(EnrollmentClassheaderenrollment, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_reconciliation_status_matched_enrollments"
        unique_together = (("reconciliationstatus", "classheaderenrollment"),)


class FinanceReconstructionScholarshipEntry(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    scholarship_type = models.CharField(max_length=20)
    scholarship_amount = models.DecimalField(max_digits=10, decimal_places=2)
    scholarship_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    discovered_from_receipt = models.CharField(max_length=20)
    discovery_notes = models.TextField()
    requires_reprocessing = models.BooleanField()
    applied_to_reconstruction = models.BooleanField()
    created_by = models.ForeignKey("PeopleStaffprofile", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "PeopleStaffprofile",
        models.DO_NOTHING,
        related_name="financereconstructionscholarshipentry_updated_by_set",
        blank=True,
        null=True,
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "finance_reconstruction_scholarship_entry"
        unique_together = (("student", "term", "scholarship_type"),)


class FinanceSeniorProjectCourse(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    is_active = models.BooleanField()
    course = models.OneToOneField(CurriculumCourse, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="financeseniorprojectcourse_updated_by_set", blank=True, null=True
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    allows_groups = models.BooleanField()
    major_name = models.CharField(max_length=100, blank=True, null=True)
    project_code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_senior_project_course"


class FinanceSeniorProjectPricing(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    effective_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    tier = models.CharField(unique=True, max_length=10)
    advisor_payment = models.DecimalField(max_digits=10, decimal_places=2)
    committee_payment = models.DecimalField(max_digits=10, decimal_places=2)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="financeseniorprojectpricing_updated_by_set",
        blank=True,
        null=True,
    )
    deleted_at = models.DateTimeField(blank=True, null=True)
    foreign_individual_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    individual_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "finance_senior_project_pricing"
        unique_together = (("tier", "effective_date"),)


class GradingClasspartgrade(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    numeric_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    letter_grade = models.CharField(max_length=5)
    gpa_points = models.DecimalField(max_digits=4, decimal_places=2, blank=True, null=True)
    grade_source = models.CharField(max_length=20)
    grade_status = models.CharField(max_length=15)
    entered_at = models.DateTimeField()
    approved_at = models.DateTimeField(blank=True, null=True)
    student_notified = models.BooleanField()
    notification_date = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    class_part = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)
    enrollment = models.ForeignKey(EnrollmentClassheaderenrollment, models.DO_NOTHING)
    entered_by = models.ForeignKey("UsersUser", models.DO_NOTHING, related_name="gradingclasspartgrade_entered_by_set")
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradingclasspartgrade_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradingclasspartgrade_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "grading_classpartgrade"
        unique_together = (("enrollment", "class_part"),)


class GradingClasssessiongrade(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    calculated_score = models.DecimalField(max_digits=5, decimal_places=2)
    letter_grade = models.CharField(max_length=5)
    gpa_points = models.DecimalField(max_digits=4, decimal_places=2)
    calculated_at = models.DateTimeField()
    calculation_details = models.JSONField()
    class_session = models.ForeignKey("SchedulingClasssession", models.DO_NOTHING)
    enrollment = models.ForeignKey(EnrollmentClassheaderenrollment, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradingclasssessiongrade_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "grading_classsessiongrade"
        unique_together = (("enrollment", "class_session"),)


class GradingGparecord(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    gpa_type = models.CharField(max_length=15)
    gpa_value = models.DecimalField(max_digits=4, decimal_places=3)
    quality_points = models.DecimalField(max_digits=8, decimal_places=2)
    credit_hours_attempted = models.DecimalField(max_digits=6, decimal_places=2)
    credit_hours_earned = models.DecimalField(max_digits=6, decimal_places=2)
    calculated_at = models.DateTimeField()
    calculation_details = models.JSONField()
    major = models.ForeignKey(CurriculumMajor, models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradinggparecord_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "grading_gparecord"
        unique_together = (("student", "term", "major", "gpa_type"),)


class GradingGradechangehistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    change_type = models.CharField(max_length=20)
    changed_at = models.DateTimeField()
    previous_numeric_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    previous_letter_grade = models.CharField(max_length=5)
    previous_status = models.CharField(max_length=15)
    new_numeric_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    new_letter_grade = models.CharField(max_length=5)
    new_status = models.CharField(max_length=15)
    reason = models.TextField()
    additional_details = models.JSONField()
    changed_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    class_part_grade = models.ForeignKey(GradingClasspartgrade, models.DO_NOTHING)
    created_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradinggradechangehistory_created_by_set", blank=True, null=True
    )
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradinggradechangehistory_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "grading_gradechangehistory"


class GradingGradeconversion(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    letter_grade = models.CharField(max_length=5)
    min_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    max_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    gpa_points = models.DecimalField(max_digits=4, decimal_places=2)
    display_order = models.SmallIntegerField()
    grading_scale = models.ForeignKey("GradingGradingscale", models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradinggradeconversion_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "grading_gradeconversion"
        unique_together = (
            ("grading_scale", "letter_grade"),
            ("grading_scale", "max_percentage"),
            ("grading_scale", "min_percentage"),
        )


class GradingGradingscale(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    scale_type = models.CharField(unique=True, max_length=20)
    description = models.TextField()
    is_active = models.BooleanField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="gradinggradingscale_updated_by_set", blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "grading_gradingscale"


class LanguageLanguagelevelskiprequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    current_level = models.CharField(max_length=50)
    target_level = models.CharField(max_length=50)
    program = models.CharField(max_length=20)
    levels_skipped = models.SmallIntegerField()
    reason_category = models.CharField(max_length=30)
    detailed_reason = models.TextField()
    supporting_evidence = models.TextField()
    status = models.CharField(max_length=20)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField()
    implemented_at = models.DateTimeField(blank=True, null=True)
    implemented_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    new_enrollment = models.ForeignKey(EnrollmentClassheaderenrollment, models.DO_NOTHING, blank=True, null=True)
    requested_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="languagelanguagelevelskiprequest_requested_by_set"
    )
    reviewed_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="languagelanguagelevelskiprequest_reviewed_by_set",
        blank=True,
        null=True,
    )
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "language_languagelevelskiprequest"


class LanguageLanguageprogrampromotion(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    program = models.CharField(max_length=20)
    status = models.CharField(max_length=20)
    students_promoted_count = models.IntegerField()
    classes_cloned_count = models.IntegerField()
    initiated_at = models.DateTimeField()
    completed_at = models.DateTimeField(blank=True, null=True)
    notes = models.TextField()
    initiated_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    source_term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    target_term = models.ForeignKey(
        CurriculumTerm, models.DO_NOTHING, related_name="languagelanguageprogrampromotion_target_term_set"
    )

    class Meta:
        managed = False
        db_table = "language_languageprogrampromotion"
        unique_together = (("source_term", "target_term", "program"),)


class LanguageLanguagestudentpromotion(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    from_level = models.CharField(max_length=50)
    to_level = models.CharField(max_length=50)
    result = models.CharField(max_length=20)
    final_grade = models.CharField(max_length=10)
    notes = models.TextField()
    has_level_skip_override = models.BooleanField()
    skip_reason = models.TextField()
    promotion_batch = models.ForeignKey(LanguageLanguageprogrampromotion, models.DO_NOTHING)
    skip_approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    source_class = models.ForeignKey("SchedulingClassheader", models.DO_NOTHING)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)
    target_class = models.ForeignKey(
        "SchedulingClassheader",
        models.DO_NOTHING,
        related_name="languagelanguagestudentpromotion_target_class_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "language_languagestudentpromotion"
        unique_together = (("promotion_batch", "student"),)


class LegacyAcademicClasses(models.Model):
    termid = models.TextField(db_column="TermID", blank=True, null=True)  # Field name made lowercase.
    program = models.TextField(db_column="Program", blank=True, null=True)  # Field name made lowercase.
    major = models.TextField(db_column="Major", blank=True, null=True)  # Field name made lowercase.
    groupid = models.TextField(db_column="GroupID", blank=True, null=True)  # Field name made lowercase.
    desgroupid = models.TextField(db_column="desGroupID", blank=True, null=True)  # Field name made lowercase.
    coursecode = models.TextField(db_column="CourseCode", blank=True, null=True)  # Field name made lowercase.
    classid = models.TextField(db_column="ClassID", blank=True, null=True)  # Field name made lowercase.
    coursetitle = models.TextField(db_column="CourseTitle", blank=True, null=True)  # Field name made lowercase.
    stnumber = models.TextField(db_column="StNumber", blank=True, null=True)  # Field name made lowercase.
    coursetype = models.TextField(db_column="CourseType", blank=True, null=True)  # Field name made lowercase.
    schooltime = models.TextField(db_column="SchoolTime", blank=True, null=True)  # Field name made lowercase.
    color = models.TextField(db_column="Color", blank=True, null=True)  # Field name made lowercase.
    pos = models.TextField(db_column="Pos", blank=True, null=True)  # Field name made lowercase.
    subject = models.TextField(db_column="Subject", blank=True, null=True)  # Field name made lowercase.
    exsubject = models.TextField(db_column="ExSubject", blank=True, null=True)  # Field name made lowercase.
    isshadow = models.TextField(db_column="IsShadow", blank=True, null=True)  # Field name made lowercase.
    gidpos = models.TextField(db_column="gidPOS", blank=True, null=True)  # Field name made lowercase.
    cidpos = models.TextField(db_column="cidPOS", blank=True, null=True)  # Field name made lowercase.
    propos = models.TextField(db_column="proPOS", blank=True, null=True)  # Field name made lowercase.
    ipk = models.TextField(db_column="IPK", blank=True, null=True)  # Field name made lowercase.
    createddate = models.TextField(db_column="CreatedDate", blank=True, null=True)  # Field name made lowercase.
    modifieddate = models.TextField(db_column="ModifiedDate", blank=True, null=True)  # Field name made lowercase.
    normalizedcourse = models.TextField(
        db_column="NormalizedCourse", blank=True, null=True
    )  # Field name made lowercase.
    normalizedpart = models.TextField(db_column="NormalizedPart", blank=True, null=True)  # Field name made lowercase.
    normalizedsection = models.TextField(
        db_column="NormalizedSection", blank=True, null=True
    )  # Field name made lowercase.
    normalizedtod = models.TextField(db_column="NormalizedTOD", blank=True, null=True)  # Field name made lowercase.
    oldcoursecode = models.TextField(db_column="OldCourseCode", blank=True, null=True)  # Field name made lowercase.
    csv_row_number = models.IntegerField(blank=True, null=True)
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "legacy_academic_classes"


class LegacyCourseTakers(models.Model):
    id = models.TextField(db_column="ID", blank=True, null=True)  # Field name made lowercase.
    classid = models.TextField(db_column="ClassID", blank=True, null=True)  # Field name made lowercase.
    repeatnum = models.TextField(db_column="RepeatNum", blank=True, null=True)  # Field name made lowercase.
    lscore = models.TextField(db_column="LScore", blank=True, null=True)  # Field name made lowercase.
    uscore = models.TextField(db_column="UScore", blank=True, null=True)  # Field name made lowercase.
    credit = models.TextField(db_column="Credit", blank=True, null=True)  # Field name made lowercase.
    gradepoint = models.TextField(db_column="GradePoint", blank=True, null=True)  # Field name made lowercase.
    totalpoint = models.TextField(db_column="TotalPoint", blank=True, null=True)  # Field name made lowercase.
    grade = models.TextField(db_column="Grade", blank=True, null=True)  # Field name made lowercase.
    previousgrade = models.TextField(db_column="PreviousGrade", blank=True, null=True)  # Field name made lowercase.
    comment = models.TextField(db_column="Comment", blank=True, null=True)  # Field name made lowercase.
    passed = models.TextField(db_column="Passed", blank=True, null=True)  # Field name made lowercase.
    remarks = models.TextField(db_column="Remarks", blank=True, null=True)  # Field name made lowercase.
    color = models.TextField(db_column="Color", blank=True, null=True)  # Field name made lowercase.
    registermode = models.TextField(db_column="RegisterMode", blank=True, null=True)  # Field name made lowercase.
    attendance = models.TextField(db_column="Attendance", blank=True, null=True)  # Field name made lowercase.
    forecolor = models.TextField(db_column="ForeColor", blank=True, null=True)  # Field name made lowercase.
    backcolor = models.TextField(db_column="BackColor", blank=True, null=True)  # Field name made lowercase.
    quicknote = models.TextField(db_column="QuickNote", blank=True, null=True)  # Field name made lowercase.
    pos = models.TextField(db_column="Pos", blank=True, null=True)  # Field name made lowercase.
    gpos = models.TextField(db_column="GPos", blank=True, null=True)  # Field name made lowercase.
    adder = models.TextField(db_column="Adder", blank=True, null=True)  # Field name made lowercase.
    addtime = models.TextField(db_column="AddTime", blank=True, null=True)  # Field name made lowercase.
    lastupdate = models.TextField(db_column="LastUpdate", blank=True, null=True)  # Field name made lowercase.
    ipk = models.TextField(db_column="IPK", blank=True, null=True)  # Field name made lowercase.
    createddate = models.TextField(db_column="CreatedDate", blank=True, null=True)  # Field name made lowercase.
    modifieddate = models.TextField(db_column="ModifiedDate", blank=True, null=True)  # Field name made lowercase.
    section = models.TextField(blank=True, null=True)
    time_slot = models.TextField(blank=True, null=True)
    parsed_termid = models.TextField(blank=True, null=True)
    parsed_coursecode = models.TextField(blank=True, null=True)
    parsed_langcourse = models.TextField(blank=True, null=True)
    normalizedcourse = models.TextField(
        db_column="NormalizedCourse", blank=True, null=True
    )  # Field name made lowercase.
    normalizedpart = models.TextField(db_column="NormalizedPart", blank=True, null=True)  # Field name made lowercase.
    normalizedsection = models.TextField(
        db_column="NormalizedSection", blank=True, null=True
    )  # Field name made lowercase.
    normalizedtod = models.TextField(db_column="NormalizedTOD", blank=True, null=True)  # Field name made lowercase.
    csv_row_number = models.IntegerField(blank=True, null=True)
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "legacy_course_takers"


class LegacyEtResults(models.Model):
    termid = models.TextField(db_column="TermID", blank=True, null=True)  # Field name made lowercase.
    serialid = models.TextField(db_column="SerialID", blank=True, null=True)  # Field name made lowercase.
    id = models.TextField(db_column="ID", blank=True, null=True)  # Field name made lowercase.
    name = models.TextField(db_column="Name", blank=True, null=True)  # Field name made lowercase.
    birthdate = models.TextField(db_column="BirthDate", blank=True, null=True)  # Field name made lowercase.
    birthplace = models.TextField(db_column="BirthPlace", blank=True, null=True)  # Field name made lowercase.
    gender = models.TextField(db_column="Gender", blank=True, null=True)  # Field name made lowercase.
    mobilephone = models.TextField(db_column="MobilePhone", blank=True, null=True)  # Field name made lowercase.
    admissiondate = models.TextField(db_column="AdmissionDate", blank=True, null=True)  # Field name made lowercase.
    testtype = models.TextField(db_column="TestType", blank=True, null=True)  # Field name made lowercase.
    result = models.TextField(db_column="Result", blank=True, null=True)  # Field name made lowercase.
    result1 = models.TextField(db_column="Result1", blank=True, null=True)  # Field name made lowercase.
    admittedtopuc = models.TextField(db_column="AdmittedToPUC", blank=True, null=True)  # Field name made lowercase.
    notes = models.TextField(db_column="Notes", blank=True, null=True)  # Field name made lowercase.
    backcolor = models.TextField(db_column="BackColor", blank=True, null=True)  # Field name made lowercase.
    forecolor = models.TextField(db_column="ForeColor", blank=True, null=True)  # Field name made lowercase.
    classtime = models.TextField(db_column="ClassTime", blank=True, null=True)  # Field name made lowercase.
    program = models.TextField(db_column="Program", blank=True, null=True)  # Field name made lowercase.
    overalltime = models.TextField(db_column="OverallTime", blank=True, null=True)  # Field name made lowercase.
    admitted = models.TextField(db_column="Admitted", blank=True, null=True)  # Field name made lowercase.
    firstpaydate = models.TextField(db_column="FirstPayDate", blank=True, null=True)  # Field name made lowercase.
    recid = models.TextField(db_column="RecID", blank=True, null=True)  # Field name made lowercase.
    receiptid = models.TextField(db_column="ReceiptID", blank=True, null=True)  # Field name made lowercase.
    owner = models.TextField(db_column="Owner", blank=True, null=True)  # Field name made lowercase.
    addtime = models.TextField(db_column="AddTime", blank=True, null=True)  # Field name made lowercase.
    lastaccessuser = models.TextField(db_column="LastAccessUser", blank=True, null=True)  # Field name made lowercase.
    lastmodifyuser = models.TextField(db_column="LastModifyUser", blank=True, null=True)  # Field name made lowercase.
    lastmodifytime = models.TextField(db_column="LastModifyTime", blank=True, null=True)  # Field name made lowercase.
    lastaccesstime = models.TextField(db_column="LastAccessTime", blank=True, null=True)  # Field name made lowercase.
    refunded = models.TextField(db_column="Refunded", blank=True, null=True)  # Field name made lowercase.
    ipk = models.TextField(db_column="IPK", blank=True, null=True)  # Field name made lowercase.
    csv_row_number = models.IntegerField(blank=True, null=True)
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "legacy_et_results"


class LegacyReceiptHeaders(models.Model):
    id = models.TextField(db_column="ID", blank=True, null=True)  # Field name made lowercase.
    termid = models.TextField(db_column="TermID", blank=True, null=True)  # Field name made lowercase.
    program = models.TextField(db_column="Program", blank=True, null=True)  # Field name made lowercase.
    intreceiptno = models.TextField(db_column="IntReceiptNo", blank=True, null=True)  # Field name made lowercase.
    receiptno = models.TextField(db_column="ReceiptNo", blank=True, null=True)  # Field name made lowercase.
    receiptid = models.TextField(db_column="ReceiptID", blank=True, null=True)  # Field name made lowercase.
    pmtdate = models.TextField(db_column="PmtDate", blank=True, null=True)  # Field name made lowercase.
    amount = models.TextField(db_column="Amount", blank=True, null=True)  # Field name made lowercase.
    netamount = models.TextField(db_column="NetAmount", blank=True, null=True)  # Field name made lowercase.
    netdiscount = models.TextField(db_column="NetDiscount", blank=True, null=True)  # Field name made lowercase.
    scholargrant = models.TextField(db_column="ScholarGrant", blank=True, null=True)  # Field name made lowercase.
    balance = models.TextField(db_column="Balance", blank=True, null=True)  # Field name made lowercase.
    termname = models.TextField(db_column="TermName", blank=True, null=True)  # Field name made lowercase.
    receipttype = models.TextField(db_column="ReceiptType", blank=True, null=True)  # Field name made lowercase.
    notes = models.TextField(db_column="Notes", blank=True, null=True)  # Field name made lowercase.
    receiver = models.TextField(db_column="Receiver", blank=True, null=True)  # Field name made lowercase.
    deleted = models.TextField(db_column="Deleted", blank=True, null=True)  # Field name made lowercase.
    name = models.TextField(blank=True, null=True)
    recid = models.TextField(db_column="recID", blank=True, null=True)  # Field name made lowercase.
    otherdeduct = models.TextField(db_column="OtherDeduct", blank=True, null=True)  # Field name made lowercase.
    latefee = models.TextField(db_column="LateFee", blank=True, null=True)  # Field name made lowercase.
    prepaidfee = models.TextField(db_column="PrepaidFee", blank=True, null=True)  # Field name made lowercase.
    pmttype = models.TextField(db_column="PmtType", blank=True, null=True)  # Field name made lowercase.
    checkno = models.TextField(db_column="CheckNo", blank=True, null=True)  # Field name made lowercase.
    gender = models.TextField(db_column="Gender", blank=True, null=True)  # Field name made lowercase.
    curlevel = models.TextField(db_column="CurLevel", blank=True, null=True)  # Field name made lowercase.
    cash_received = models.TextField(db_column="Cash_received", blank=True, null=True)  # Field name made lowercase.
    transtype = models.TextField(db_column="TransType", blank=True, null=True)  # Field name made lowercase.
    ipk = models.TextField(db_column="IPK", blank=True, null=True)  # Field name made lowercase.
    csv_row_number = models.IntegerField(blank=True, null=True)
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "legacy_receipt_headers"


class LegacyStudents(models.Model):
    ui = models.TextField(db_column="UI", blank=True, null=True)  # Field name made lowercase.
    pw = models.TextField(db_column="PW", blank=True, null=True)  # Field name made lowercase.
    id = models.TextField(db_column="ID", blank=True, null=True)  # Field name made lowercase.
    name = models.TextField(db_column="Name", blank=True, null=True)  # Field name made lowercase.
    kname = models.TextField(db_column="KName", blank=True, null=True)  # Field name made lowercase.
    birthdate = models.TextField(db_column="BirthDate", blank=True, null=True)  # Field name made lowercase.
    birthplace = models.TextField(db_column="BirthPlace", blank=True, null=True)  # Field name made lowercase.
    gender = models.TextField(db_column="Gender", blank=True, null=True)  # Field name made lowercase.
    maritalstatus = models.TextField(db_column="MaritalStatus", blank=True, null=True)  # Field name made lowercase.
    nationality = models.TextField(db_column="Nationality", blank=True, null=True)  # Field name made lowercase.
    homeaddress = models.TextField(db_column="HomeAddress", blank=True, null=True)  # Field name made lowercase.
    homephone = models.TextField(db_column="HomePhone", blank=True, null=True)  # Field name made lowercase.
    email = models.TextField(db_column="Email", blank=True, null=True)  # Field name made lowercase.
    mobilephone = models.TextField(db_column="MobilePhone", blank=True, null=True)  # Field name made lowercase.
    employmentplace = models.TextField(
        db_column="EmploymentPlace", blank=True, null=True
    )  # Field name made lowercase.
    position = models.TextField(db_column="Position", blank=True, null=True)  # Field name made lowercase.
    fathername = models.TextField(db_column="FatherName", blank=True, null=True)  # Field name made lowercase.
    spousename = models.TextField(db_column="SpouseName", blank=True, null=True)  # Field name made lowercase.
    emg_contactperson = models.TextField(
        db_column="Emg_ContactPerson", blank=True, null=True
    )  # Field name made lowercase.
    relationship = models.TextField(db_column="Relationship", blank=True, null=True)  # Field name made lowercase.
    contactpersonaddress = models.TextField(
        db_column="ContactPersonAddress", blank=True, null=True
    )  # Field name made lowercase.
    contactpersonphone = models.TextField(
        db_column="ContactPersonPhone", blank=True, null=True
    )  # Field name made lowercase.
    highschoolprogram_school = models.TextField(
        db_column="HighSchoolProgram_School", blank=True, null=True
    )  # Field name made lowercase.
    highschoolprogram_province = models.TextField(
        db_column="HighSchoolProgram_Province", blank=True, null=True
    )  # Field name made lowercase.
    highschoolprogram_year = models.TextField(
        db_column="HighSchoolProgram_Year", blank=True, null=True
    )  # Field name made lowercase.
    highschoolprogram_diploma = models.TextField(
        db_column="HighSchoolProgram_Diploma", blank=True, null=True
    )  # Field name made lowercase.
    englishprogram_school = models.TextField(
        db_column="EnglishProgram_School", blank=True, null=True
    )  # Field name made lowercase.
    englishprogram_level = models.TextField(
        db_column="EnglishProgram_Level", blank=True, null=True
    )  # Field name made lowercase.
    englishprogram_year = models.TextField(
        db_column="EnglishProgram_Year", blank=True, null=True
    )  # Field name made lowercase.
    lessthanfouryearprogram_school = models.TextField(
        db_column="LessThanFourYearProgram_School", blank=True, null=True
    )  # Field name made lowercase.
    lessthanfouryearprogram_year = models.TextField(
        db_column="LessThanFourYearProgram_Year", blank=True, null=True
    )  # Field name made lowercase.
    fouryearprogram_school = models.TextField(
        db_column="FourYearProgram_School", blank=True, null=True
    )  # Field name made lowercase.
    fouryearprogram_degree = models.TextField(
        db_column="FourYearProgram_Degree", blank=True, null=True
    )  # Field name made lowercase.
    fouryearprogram_major = models.TextField(
        db_column="FourYearProgram_Major", blank=True, null=True
    )  # Field name made lowercase.
    fouryearprogram_year = models.TextField(
        db_column="FourYearProgram_Year", blank=True, null=True
    )  # Field name made lowercase.
    graduateprogram_school = models.TextField(
        db_column="GraduateProgram_School", blank=True, null=True
    )  # Field name made lowercase.
    graduateprogram_degree = models.TextField(
        db_column="GraduateProgram_Degree", blank=True, null=True
    )  # Field name made lowercase.
    graduateprogram_major = models.TextField(
        db_column="GraduateProgram_Major", blank=True, null=True
    )  # Field name made lowercase.
    graduateprogram_year = models.TextField(
        db_column="GraduateProgram_Year", blank=True, null=True
    )  # Field name made lowercase.
    postgraduateprogram_school = models.TextField(
        db_column="PostGraduateProgram_School", blank=True, null=True
    )  # Field name made lowercase.
    postgraduateprogram_degree = models.TextField(
        db_column="PostGraduateProgram_Degree", blank=True, null=True
    )  # Field name made lowercase.
    postgraduateprogram_major = models.TextField(
        db_column="PostGraduateProgram_Major", blank=True, null=True
    )  # Field name made lowercase.
    postgraduateprogram_year = models.TextField(
        db_column="PostGraduateProgram_Year", blank=True, null=True
    )  # Field name made lowercase.
    currentprogram = models.TextField(db_column="CurrentProgram", blank=True, null=True)  # Field name made lowercase.
    selprogram = models.TextField(db_column="SelProgram", blank=True, null=True)  # Field name made lowercase.
    selectedprogram = models.TextField(
        db_column="SelectedProgram", blank=True, null=True
    )  # Field name made lowercase.
    selmajor = models.TextField(db_column="SelMajor", blank=True, null=True)  # Field name made lowercase.
    selectedmajor = models.TextField(db_column="SelectedMajor", blank=True, null=True)  # Field name made lowercase.
    selfaculty = models.TextField(db_column="SelFaculty", blank=True, null=True)  # Field name made lowercase.
    selectedfaculty = models.TextField(
        db_column="SelectedFaculty", blank=True, null=True
    )  # Field name made lowercase.
    selecteddegreetype = models.TextField(
        db_column="SelectedDegreeType", blank=True, null=True
    )  # Field name made lowercase.
    admissiondate = models.TextField(db_column="AdmissionDate", blank=True, null=True)  # Field name made lowercase.
    admissiondateforunder = models.TextField(
        db_column="AdmissionDateForUnder", blank=True, null=True
    )  # Field name made lowercase.
    admissiondateformaster = models.TextField(
        db_column="AdmissionDateForMaster", blank=True, null=True
    )  # Field name made lowercase.
    admissiondatefordoctor = models.TextField(
        db_column="AdmissionDateForDoctor", blank=True, null=True
    )  # Field name made lowercase.
    previousdegree = models.TextField(db_column="PreviousDegree", blank=True, null=True)  # Field name made lowercase.
    previousinstitution = models.TextField(
        db_column="PreviousInstitution", blank=True, null=True
    )  # Field name made lowercase.
    yearawarded = models.TextField(db_column="YearAwarded", blank=True, null=True)  # Field name made lowercase.
    othercredittransferinstitution = models.TextField(
        db_column="OtherCreditTransferInstitution", blank=True, null=True
    )  # Field name made lowercase.
    degreeawarded = models.TextField(db_column="DegreeAwarded", blank=True, null=True)  # Field name made lowercase.
    graduationdate = models.TextField(db_column="GraduationDate", blank=True, null=True)  # Field name made lowercase.
    firstterm = models.TextField(db_column="FirstTerm", blank=True, null=True)  # Field name made lowercase.
    paidterm = models.TextField(db_column="PaidTerm", blank=True, null=True)  # Field name made lowercase.
    batchid = models.TextField(db_column="BatchID", blank=True, null=True)  # Field name made lowercase.
    batchidforunder = models.TextField(
        db_column="BatchIDForUnder", blank=True, null=True
    )  # Field name made lowercase.
    batchidformaster = models.TextField(
        db_column="BatchIDForMaster", blank=True, null=True
    )  # Field name made lowercase.
    batchidfordoctor = models.TextField(
        db_column="BatchIDForDoctor", blank=True, null=True
    )  # Field name made lowercase.
    groupid = models.TextField(db_column="GroupID", blank=True, null=True)  # Field name made lowercase.
    intgroupid = models.TextField(db_column="intGroupID", blank=True, null=True)  # Field name made lowercase.
    color = models.TextField(db_column="Color", blank=True, null=True)  # Field name made lowercase.
    admitted = models.TextField(db_column="Admitted", blank=True, null=True)  # Field name made lowercase.
    deleted = models.TextField(db_column="Deleted", blank=True, null=True)  # Field name made lowercase.
    status = models.TextField(db_column="Status", blank=True, null=True)  # Field name made lowercase.
    schoolemail = models.TextField(db_column="SchoolEmail", blank=True, null=True)  # Field name made lowercase.
    bagraddate = models.TextField(db_column="BAGradDate", blank=True, null=True)  # Field name made lowercase.
    magraddate = models.TextField(db_column="MAGradDate", blank=True, null=True)  # Field name made lowercase.
    notes = models.TextField(db_column="Notes", blank=True, null=True)  # Field name made lowercase.
    lastenroll = models.TextField(db_column="Lastenroll", blank=True, null=True)  # Field name made lowercase.
    firstenroll = models.TextField(db_column="Firstenroll", blank=True, null=True)  # Field name made lowercase.
    firstenroll_lang = models.TextField(
        db_column="Firstenroll_Lang", blank=True, null=True
    )  # Field name made lowercase.
    firstenroll_ba = models.TextField(db_column="Firstenroll_BA", blank=True, null=True)  # Field name made lowercase.
    firstenroll_ma = models.TextField(db_column="Firstenroll_MA", blank=True, null=True)  # Field name made lowercase.
    transfer = models.TextField(db_column="Transfer", blank=True, null=True)  # Field name made lowercase.
    kname2 = models.TextField(db_column="KName2", blank=True, null=True)  # Field name made lowercase.
    createddate = models.TextField(db_column="CreatedDate", blank=True, null=True)  # Field name made lowercase.
    modifieddate = models.TextField(db_column="ModifiedDate", blank=True, null=True)  # Field name made lowercase.
    ipk = models.TextField(db_column="IPK", blank=True, null=True)  # Field name made lowercase.
    csv_row_number = models.IntegerField(blank=True, null=True)
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "legacy_students"


class LegacyStudentsValidated(models.Model):
    id = models.CharField(primary_key=True, max_length=10)
    name = models.CharField(max_length=100)
    ui = models.CharField(max_length=100, blank=True, null=True)
    pw = models.CharField(max_length=10, blank=True, null=True)
    kname = models.CharField(max_length=100, blank=True, null=True)
    birth_date = models.DateTimeField()
    birth_place = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=30, blank=True, null=True)
    marital_status = models.CharField(max_length=30, blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, null=True)
    home_address = models.CharField(max_length=250, blank=True, null=True)
    home_phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(max_length=50, blank=True, null=True)
    mobile_phone = models.CharField(max_length=50, blank=True, null=True)
    employment_place = models.CharField(max_length=200, blank=True, null=True)
    position = models.CharField(max_length=150, blank=True, null=True)
    father_name = models.CharField(max_length=50, blank=True, null=True)
    spouse_name = models.CharField(max_length=50, blank=True, null=True)
    emg_contact_person = models.CharField(max_length=50, blank=True, null=True)
    relationship = models.CharField(max_length=50, blank=True, null=True)
    contact_person_address = models.CharField(max_length=250, blank=True, null=True)
    contact_person_phone = models.CharField(max_length=30, blank=True, null=True)
    high_school_program_school = models.CharField(max_length=150, blank=True, null=True)
    high_school_program_province = models.CharField(max_length=100, blank=True, null=True)
    high_school_program_year = models.IntegerField(blank=True, null=True)
    high_school_program_diploma = models.CharField(max_length=10, blank=True, null=True)
    english_program_school = models.CharField(max_length=150, blank=True, null=True)
    english_program_level = models.CharField(max_length=50, blank=True, null=True)
    english_program_year = models.IntegerField(blank=True, null=True)
    current_program = models.CharField(max_length=50, blank=True, null=True)
    selected_program = models.CharField(max_length=100, blank=True, null=True)
    selected_major = models.CharField(max_length=100, blank=True, null=True)
    selected_faculty = models.CharField(max_length=150, blank=True, null=True)
    admission_date = models.DateTimeField(blank=True, null=True)
    graduation_date = models.DateTimeField(blank=True, null=True)
    ba_grad_date = models.DateTimeField(blank=True, null=True)
    ma_grad_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15, blank=True, null=True)
    batch_id = models.CharField(max_length=20, blank=True, null=True)
    first_term = models.CharField(max_length=50, blank=True, null=True)
    ipk = models.IntegerField(blank=True, null=True)
    csv_row_number = models.IntegerField(blank=True, null=True)
    imported_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "legacy_students_validated"


class LevelTestingDuplicatecandidate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    existing_person_id = models.IntegerField()
    match_type = models.CharField(max_length=20)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2)
    matched_name = models.CharField(max_length=100)
    matched_birth_date = models.DateField(blank=True, null=True)
    matched_phone = models.CharField(max_length=20)
    has_outstanding_debt = models.BooleanField()
    debt_amount = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    reviewed = models.BooleanField()
    is_confirmed_duplicate = models.BooleanField()
    review_notes = models.TextField()
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    potential_student = models.ForeignKey("LevelTestingPotentialstudent", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "level_testing_duplicatecandidate"
        unique_together = (("potential_student", "existing_person_id"),)


class LevelTestingPlacementtest(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    program = models.CharField(max_length=20)
    test_type = models.CharField(max_length=20)
    max_score = models.SmallIntegerField()
    passing_score = models.SmallIntegerField()
    duration_minutes = models.SmallIntegerField()
    instructions = models.TextField()
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "level_testing_placementtest"


class LevelTestingPotentialstudent(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    application_id = models.UUIDField(unique=True)
    test_number = models.CharField(unique=True, max_length=10)
    family_name_eng = models.CharField(max_length=50)
    personal_name_eng = models.CharField(max_length=50)
    family_name_khm = models.CharField(max_length=50)
    personal_name_khm = models.CharField(max_length=50)
    preferred_gender = models.CharField(max_length=1)
    date_of_birth = models.DateField()
    birth_province = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20)
    telegram_number = models.CharField(max_length=20)
    personal_email = models.CharField(max_length=254)
    current_school = models.CharField(max_length=20)
    other_school_name = models.CharField(max_length=100)
    current_grade = models.SmallIntegerField(blank=True, null=True)
    is_graduate = models.BooleanField()
    last_english_school = models.CharField(max_length=100)
    last_english_date = models.DateField(blank=True, null=True)
    preferred_program = models.CharField(max_length=20)
    preferred_time_slot = models.CharField(max_length=20)
    preferred_start_term = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    status_history = models.JSONField()
    first_time_at_puc = models.BooleanField()
    how_did_you_hear = models.CharField(max_length=20)
    comments = models.TextField()
    converted_person_id = models.IntegerField(blank=True, null=True)
    converted_student_number = models.CharField(max_length=10)
    duplicate_check_performed = models.BooleanField()
    duplicate_check_status = models.CharField(max_length=20)
    duplicate_check_notes = models.TextField()
    duplicate_check_cleared_at = models.DateTimeField(blank=True, null=True)
    duplicate_check_cleared_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    last_english_study_period = models.CharField(max_length=20, blank=True, null=True)
    current_high_school = models.CharField(max_length=20)
    current_study_status = models.CharField(max_length=20)
    current_university = models.CharField(max_length=20)
    work_field = models.CharField(max_length=20)
    last_english_level = models.CharField(max_length=50)
    last_english_textbook = models.CharField(max_length=100)
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_phone = models.CharField(max_length=20)
    emergency_contact_relationship = models.CharField(max_length=15)
    access_token_link = models.OneToOneField("LevelTestingTestaccesstoken", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "level_testing_potentialstudent"


class LevelTestingTestaccesstoken(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    access_code = models.CharField(unique=True, max_length=7)
    payment_amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    payment_received_at = models.DateTimeField()
    qr_code_url = models.CharField(max_length=200)
    qr_code_data = models.JSONField()
    student_name = models.CharField(max_length=100)
    student_phone = models.CharField(max_length=20)
    is_used = models.BooleanField()
    used_at = models.DateTimeField(blank=True, null=True)
    telegram_id = models.CharField(max_length=50)
    telegram_username = models.CharField(max_length=50)
    telegram_verified = models.BooleanField()
    telegram_verification_code = models.CharField(max_length=6)
    telegram_verified_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField()
    application = models.OneToOneField(LevelTestingPotentialstudent, models.DO_NOTHING, blank=True, null=True)
    cashier = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "level_testing_testaccesstoken"


class LevelTestingTestattempt(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    raw_score = models.SmallIntegerField(blank=True, null=True)
    percentage_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    recommended_level = models.CharField(max_length=20)
    proctor_notes = models.TextField()
    technical_issues = models.TextField()
    is_completed = models.BooleanField()
    is_graded = models.BooleanField()
    placement_test = models.ForeignKey(LevelTestingPlacementtest, models.DO_NOTHING)
    potential_student = models.ForeignKey(LevelTestingPotentialstudent, models.DO_NOTHING)
    test_session = models.ForeignKey("LevelTestingTestsession", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "level_testing_testattempt"
        unique_together = (("potential_student", "test_session"),)


class LevelTestingTestcompletion(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    internal_code = models.CharField(unique=True, max_length=7)
    qr_code_data = models.JSONField()
    slip_printed_at = models.DateTimeField(blank=True, null=True)
    is_payment_linked = models.BooleanField()
    is_telegram_linked = models.BooleanField()
    payment_transaction_id = models.IntegerField(blank=True, null=True)
    telegram_data = models.JSONField()
    completion_notes = models.TextField()
    test_attempt = models.OneToOneField(LevelTestingTestattempt, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "level_testing_testcompletion"


class LevelTestingTestpayment(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    payment_method = models.CharField(max_length=20)
    payment_reference = models.CharField(max_length=50)
    paid_at = models.DateTimeField(blank=True, null=True)
    is_paid = models.BooleanField()
    finance_transaction_id = models.IntegerField(blank=True, null=True)
    potential_student = models.OneToOneField(LevelTestingPotentialstudent, models.DO_NOTHING)
    received_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "level_testing_testpayment"


class LevelTestingTestsession(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    session_date = models.DateTimeField()
    location = models.CharField(max_length=100)
    max_capacity = models.SmallIntegerField()
    is_active = models.BooleanField()
    session_notes = models.TextField()
    administrator = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "level_testing_testsession"


class MfaAuthenticator(models.Model):
    id = models.BigAutoField(primary_key=True)
    type = models.CharField(max_length=20)
    data = models.JSONField()
    user = models.ForeignKey("UsersUser", models.DO_NOTHING)
    created_at = models.DateTimeField()
    last_used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "mfa_authenticator"
        unique_together = (("user", "type"),)


class MobileAuthAttempts(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    email = models.CharField(max_length=254)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=30)
    student_id = models.IntegerField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "mobile_auth_attempts"


class MobileAuthTokens(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    device_id = models.CharField(max_length=255)
    token_id = models.CharField(unique=True, max_length=255)
    expires_at = models.DateTimeField()
    last_used = models.DateTimeField(blank=True, null=True)
    revoked = models.BooleanField()
    user = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "mobile_auth_tokens"


class PeopleEmergencycontact(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=40)
    primary_phone = models.CharField(max_length=100)
    secondary_phone = models.CharField(max_length=100)
    email = models.CharField(max_length=254)
    address = models.TextField()
    is_primary = models.BooleanField()
    person = models.ForeignKey("PeoplePerson", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_emergencycontact"
        unique_together = (("person", "is_primary"),)


class PeoplePerson(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    unique_id = models.UUIDField(unique=True)
    family_name = models.CharField(max_length=255)
    personal_name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    khmer_name = models.CharField(max_length=255)
    preferred_gender = models.CharField(max_length=1)
    use_legal_name_for_documents = models.BooleanField()
    alternate_family_name = models.CharField(max_length=255)
    alternate_personal_name = models.CharField(max_length=255)
    alternate_khmer_name = models.CharField(max_length=255)
    alternate_gender = models.CharField(max_length=1)
    photo = models.CharField(max_length=100, blank=True, null=True)
    school_email = models.CharField(unique=True, max_length=254, blank=True, null=True)
    personal_email = models.CharField(max_length=254, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    birth_province = models.CharField(max_length=50, blank=True, null=True)
    citizenship = models.CharField(max_length=2)

    class Meta:
        managed = False
        db_table = "people_person"


class PeoplePersoneventlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(max_length=20)
    timestamp = models.DateTimeField()
    details = models.JSONField()
    notes = models.TextField()
    changed_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    person = models.ForeignKey(PeoplePerson, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_personeventlog"


class PeoplePhonenumber(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    number = models.CharField(max_length=100)
    comment = models.CharField(max_length=100)
    is_preferred = models.BooleanField()
    is_telegram = models.BooleanField()
    is_verified = models.BooleanField()
    last_verification = models.DateTimeField(blank=True, null=True)
    person = models.ForeignKey(PeoplePerson, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_phonenumber"
        unique_together = (("person", "is_preferred"),)


class PeopleStaffprofile(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    position = models.CharField(max_length=100)
    status = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    person = models.OneToOneField(PeoplePerson, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_staffprofile"


class PeopleStudentauditlog(models.Model):
    id = models.BigAutoField(primary_key=True)
    action = models.CharField(max_length=15)
    timestamp = models.DateTimeField()
    changes = models.JSONField()
    object_id = models.IntegerField(blank=True, null=True)
    notes = models.TextField()
    changed_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    content_type = models.ForeignKey(DjangoContentType, models.DO_NOTHING, blank=True, null=True)
    student = models.ForeignKey("PeopleStudentprofile", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_studentauditlog"


class PeopleStudentphoto(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    photo_file = models.CharField(max_length=100)
    thumbnail = models.CharField(max_length=100, blank=True, null=True)
    upload_timestamp = models.DateTimeField()
    upload_source = models.CharField(max_length=20)
    is_current = models.BooleanField()
    verified_at = models.DateTimeField(blank=True, null=True)
    file_hash = models.CharField(unique=True, max_length=64)
    file_size = models.IntegerField()
    width = models.IntegerField(blank=True, null=True)
    height = models.IntegerField(blank=True, null=True)
    reminder_sent_at = models.DateTimeField(blank=True, null=True)
    reminder_count = models.IntegerField()
    skip_reminder = models.BooleanField()
    original_filename = models.CharField(max_length=255)
    notes = models.TextField()
    person = models.ForeignKey(PeoplePerson, models.DO_NOTHING)
    verified_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "people_studentphoto"
        unique_together = (("person", "is_current"),)


class PeopleStudentprofile(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    student_id = models.IntegerField(unique=True)
    is_monk = models.BooleanField()
    is_transfer_student = models.BooleanField()
    current_status = models.CharField(max_length=11)
    study_time_preference = models.CharField(max_length=20)
    last_enrollment_date = models.DateField(blank=True, null=True)
    person = models.OneToOneField(PeoplePerson, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_studentprofile"


class PeopleTeacherleaverequest(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    leave_date = models.DateField()
    leave_type = models.CharField(max_length=15)
    reason = models.TextField()
    is_emergency = models.BooleanField()
    substitute_confirmed = models.BooleanField()
    substitute_assigned_at = models.DateTimeField(blank=True, null=True)
    approval_status = models.CharField(max_length=15)
    approved_at = models.DateTimeField(blank=True, null=True)
    denial_reason = models.TextField()
    notification_sent = models.BooleanField()
    substitute_found = models.BooleanField()
    notes = models.TextField()
    approved_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    substitute_assigned_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="peopleteacherleaverequest_substitute_assigned_by_set",
        blank=True,
        null=True,
    )
    substitute_teacher = models.ForeignKey("PeopleTeacherprofile", models.DO_NOTHING, blank=True, null=True)
    teacher = models.ForeignKey(
        "PeopleTeacherprofile", models.DO_NOTHING, related_name="peopleteacherleaverequest_teacher_set"
    )
    affected_class_parts = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "people_teacherleaverequest"


class PeopleTeacherleaverequestAffectedClassParts(models.Model):
    id = models.BigAutoField(primary_key=True)
    teacherleaverequest = models.ForeignKey(PeopleTeacherleaverequest, models.DO_NOTHING)
    classpart = models.ForeignKey("SchedulingClasspart", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_teacherleaverequest_affected_class_parts"
        unique_together = (("teacherleaverequest", "classpart"),)


class PeopleTeacherprofile(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    terminal_degree = models.CharField(max_length=50)
    status = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    person = models.OneToOneField(PeoplePerson, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "people_teacherprofile"


class SchedulingClassheader(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    section_id = models.CharField(max_length=5)
    time_of_day = models.CharField(max_length=10)
    class_type = models.CharField(max_length=15)
    status = models.CharField(max_length=15)
    is_paired = models.BooleanField()
    max_enrollment = models.SmallIntegerField()
    notes = models.TextField()
    legacy_class_id = models.CharField(max_length=50)
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)
    paired_with = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    combined_class_instance = models.ForeignKey(
        "SchedulingCombinedclassinstance", models.DO_NOTHING, blank=True, null=True
    )
    combined_class_group = models.ForeignKey("SchedulingCombinedclassgroup", models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "scheduling_classheader"
        unique_together = (("course", "term", "section_id", "time_of_day"),)


class SchedulingClasspart(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    internal_part_id = models.UUIDField(unique=True)
    class_part_type = models.CharField(max_length=15)
    class_part_code = models.SmallIntegerField()
    name = models.CharField(max_length=100)
    meeting_days = models.CharField(max_length=20)
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    grade_weight = models.DecimalField(max_digits=4, decimal_places=3)
    notes = models.TextField()
    legacy_class_id = models.CharField(max_length=50)
    room = models.ForeignKey(CommonRoom, models.DO_NOTHING, blank=True, null=True)
    teacher = models.ForeignKey(PeopleTeacherprofile, models.DO_NOTHING, blank=True, null=True)
    class_session = models.ForeignKey("SchedulingClasssession", models.DO_NOTHING)
    template_derived = models.BooleanField()
    textbooks = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "scheduling_classpart"
        unique_together = (("class_session", "class_part_code"),)


class SchedulingClasspartTextbooks(models.Model):
    id = models.BigAutoField(primary_key=True)
    classpart = models.ForeignKey(SchedulingClasspart, models.DO_NOTHING)
    textbook = models.ForeignKey(CurriculumTextbook, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_classpart_textbooks"
        unique_together = (("classpart", "textbook"),)


class SchedulingClassparttemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    class_part_type = models.CharField(max_length=20)
    class_part_code = models.SmallIntegerField()
    name = models.CharField(max_length=100)
    meeting_days_pattern = models.CharField(max_length=50)
    sequence_order = models.IntegerField()
    grade_weight = models.DecimalField(max_digits=4, decimal_places=3)
    is_active = models.BooleanField()
    notes = models.TextField()
    template_set = models.ForeignKey("SchedulingClassparttemplateset", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_classparttemplate"
        unique_together = (("template_set", "class_part_code"),)


class SchedulingClassparttemplateDefaultTextbooks(models.Model):
    id = models.BigAutoField(primary_key=True)
    classparttemplate = models.ForeignKey(SchedulingClassparttemplate, models.DO_NOTHING)
    textbook = models.ForeignKey(CurriculumTextbook, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_classparttemplate_default_textbooks"
        unique_together = (("classparttemplate", "textbook"),)


class SchedulingClassparttemplateset(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    program_code = models.CharField(max_length=20)
    level_number = models.IntegerField()
    effective_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    version = models.IntegerField()
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField()
    auto_apply_on_promotion = models.BooleanField()
    preserve_section_cohort = models.BooleanField()

    class Meta:
        managed = False
        db_table = "scheduling_classparttemplateset"
        unique_together = (("program_code", "level_number", "version"),)


class SchedulingClasspromotionrule(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    source_program = models.CharField(max_length=20)
    source_level = models.IntegerField()
    destination_program = models.CharField(max_length=20)
    destination_level = models.IntegerField()
    preserve_cohort = models.BooleanField()
    auto_create_classes = models.BooleanField()
    apply_template = models.BooleanField()
    is_active = models.BooleanField()
    notes = models.TextField()

    class Meta:
        managed = False
        db_table = "scheduling_classpromotionrule"
        unique_together = (("source_program", "source_level", "destination_program", "destination_level"),)


class SchedulingClasssession(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    internal_session_id = models.UUIDField(unique=True)
    session_number = models.SmallIntegerField()
    session_name = models.CharField(max_length=50)
    grade_weight = models.DecimalField(max_digits=4, decimal_places=3)
    notes = models.TextField()
    class_header = models.ForeignKey(SchedulingClassheader, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_classsession"
        unique_together = (("class_header", "session_number"),)


class SchedulingCombinedclassgroup(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_combinedclassgroup"
        unique_together = (("term", "name"),)


class SchedulingCombinedclassinstance(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=15)
    section_id = models.CharField(max_length=5)
    max_enrollment = models.SmallIntegerField()
    notes = models.TextField()
    auto_created = models.BooleanField()
    primary_room = models.ForeignKey(CommonRoom, models.DO_NOTHING, blank=True, null=True)
    primary_teacher = models.ForeignKey(PeopleTeacherprofile, models.DO_NOTHING, blank=True, null=True)
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    template = models.ForeignKey("SchedulingCombinedcoursetemplate", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_combinedclassinstance"
        unique_together = (("template", "term", "section_id"),)


class SchedulingCombinedcoursetemplate(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(unique=True, max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=15)
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING)
    courses = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "scheduling_combinedcoursetemplate"


class SchedulingCombinedcoursetemplateCourses(models.Model):
    id = models.BigAutoField(primary_key=True)
    combinedcoursetemplate = models.ForeignKey(SchedulingCombinedcoursetemplate, models.DO_NOTHING)
    course = models.ForeignKey(CurriculumCourse, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_combinedcoursetemplate_courses"
        unique_together = (("combinedcoursetemplate", "course"),)


class SchedulingReadingclass(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    tier = models.CharField(max_length=10)
    target_enrollment = models.SmallIntegerField()
    enrollment_status = models.CharField(max_length=15)
    description = models.TextField()
    class_header = models.OneToOneField(SchedulingClassheader, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_readingclass"


class SchedulingTestperiodreset(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    test_type = models.CharField(max_length=10)
    reset_date = models.DateField()
    applies_to_all_language_classes = models.BooleanField()
    notes = models.TextField()
    term = models.ForeignKey(CurriculumTerm, models.DO_NOTHING)
    specific_classes = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "scheduling_testperiodreset"
        unique_together = (("term", "test_type", "applies_to_all_language_classes"),)


class SchedulingTestperiodresetSpecificClasses(models.Model):
    id = models.BigAutoField(primary_key=True)
    testperiodreset = models.ForeignKey(SchedulingTestperiodreset, models.DO_NOTHING)
    classheader = models.ForeignKey(SchedulingClassheader, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "scheduling_testperiodreset_specific_classes"
        unique_together = (("testperiodreset", "classheader"),)


class ScholarshipsScholarship(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    name = models.CharField(max_length=200)
    scholarship_type = models.CharField(max_length=20)
    award_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    award_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20)
    description = models.TextField()
    conditions = models.TextField()
    notes = models.TextField()
    student = models.ForeignKey(PeopleStudentprofile, models.DO_NOTHING)
    sponsored_student = models.OneToOneField("ScholarshipsSponsoredstudent", models.DO_NOTHING, blank=True, null=True)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="scholarshipsscholarship_updated_by_set", blank=True, null=True
    )
    cycle = models.ForeignKey(CurriculumCycle, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "scholarships_scholarship"
        unique_together = (("student", "cycle", "scholarship_type", "start_date"),)


class ScholarshipsSponsor(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    code = models.CharField(unique=True, max_length=10)
    name = models.CharField(max_length=100)
    contact_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=254)
    contact_phone = models.CharField(max_length=20)
    billing_email = models.CharField(max_length=254)
    mou_start_date = models.DateField()
    mou_end_date = models.DateField(blank=True, null=True)
    default_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    requests_tax_addition = models.BooleanField()
    requests_consolidated_invoicing = models.BooleanField()
    admin_fee_exempt_until = models.DateField(blank=True, null=True)
    requests_attendance_reporting = models.BooleanField()
    requests_grade_reporting = models.BooleanField()
    requests_scheduling_reporting = models.BooleanField()
    is_active = models.BooleanField()
    notes = models.TextField()
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser", models.DO_NOTHING, related_name="scholarshipssponsor_updated_by_set", blank=True, null=True
    )
    payment_mode = models.CharField(max_length=20)
    billing_cycle = models.CharField(max_length=20)
    invoice_generation_day = models.IntegerField(blank=True, null=True)
    payment_terms_days = models.IntegerField()

    class Meta:
        managed = False
        db_table = "scholarships_sponsor"


class ScholarshipsSponsoredstudent(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()
    deleted_at = models.DateTimeField(blank=True, null=True)
    sponsorship_type = models.CharField(max_length=20)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    notes = models.TextField()
    sponsor = models.ForeignKey(ScholarshipsSponsor, models.DO_NOTHING)
    student = models.ForeignKey(PeopleStudentprofile, models.DO_NOTHING)
    created_by = models.ForeignKey("UsersUser", models.DO_NOTHING, blank=True, null=True)
    updated_by = models.ForeignKey(
        "UsersUser",
        models.DO_NOTHING,
        related_name="scholarshipssponsoredstudent_updated_by_set",
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = "scholarships_sponsoredstudent"
        unique_together = (("sponsor", "student", "start_date"),)


class SocialaccountSocialaccount(models.Model):
    provider = models.CharField(max_length=200)
    uid = models.CharField(max_length=191)
    last_login = models.DateTimeField()
    date_joined = models.DateTimeField()
    extra_data = models.JSONField()
    user = models.ForeignKey("UsersUser", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "socialaccount_socialaccount"
        unique_together = (("provider", "uid"),)


class SocialaccountSocialapp(models.Model):
    provider = models.CharField(max_length=30)
    name = models.CharField(max_length=40)
    client_id = models.CharField(max_length=191)
    secret = models.CharField(max_length=191)
    key = models.CharField(max_length=191)
    provider_id = models.CharField(max_length=200)
    settings = models.JSONField()
    sites = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "socialaccount_socialapp"


class SocialaccountSocialappSites(models.Model):
    id = models.BigAutoField(primary_key=True)
    socialapp = models.ForeignKey(SocialaccountSocialapp, models.DO_NOTHING)
    site = models.ForeignKey(DjangoSite, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "socialaccount_socialapp_sites"
        unique_together = (("socialapp", "site"),)


class SocialaccountSocialtoken(models.Model):
    token = models.TextField()
    token_secret = models.TextField()
    expires_at = models.DateTimeField(blank=True, null=True)
    account = models.ForeignKey(SocialaccountSocialaccount, models.DO_NOTHING)
    app = models.ForeignKey(SocialaccountSocialapp, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "socialaccount_socialtoken"
        unique_together = (("app", "account"),)


class UsersUser(models.Model):
    id = models.BigAutoField(primary_key=True)
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    email = models.CharField(unique=True, max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()
    name = models.CharField(max_length=255)
    groups = models.TextField(blank=True, null=True)
    user_permissions = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "users_user"


class UsersUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UsersUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "users_user_groups"
        unique_together = (("user", "group"),)


class UsersUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(UsersUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "users_user_user_permissions"
        unique_together = (("user", "permission"),)

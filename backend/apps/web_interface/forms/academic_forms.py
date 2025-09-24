"""
Academic forms for secure data entry and validation.

This module contains forms for grade entry, enrollment, and other academic operations
with proper security measures against overposting and injection attacks.
"""

from django import forms


class GradeEntryForm(forms.Form):
    """Secure form for grade entry that explicitly declares expected fields."""

    def __init__(self, *args, enrollments=None, **kwargs):
        super().__init__(*args, **kwargs)
        if enrollments:
            for enrollment in enrollments:
                field_name = f"grade_{enrollment.id}"
                self.fields[field_name] = forms.DecimalField(
                    required=False,
                    min_value=0,
                    max_value=100,
                    decimal_places=2,
                    label=f"{enrollment.student.person.get_full_name()}",
                )

                comment_field = f"comment_{enrollment.id}"
                self.fields[comment_field] = forms.CharField(
                    required=False,
                    max_length=500,
                    widget=forms.Textarea(attrs={"rows": 2}),
                    label=f"Comments for {enrollment.student.person.get_full_name()}",
                )

    def clean(self):
        """Additional validation for grade data."""
        cleaned_data = super().clean()
        # Django's field-level validation (min_value=0, max_value=100) handles range validation
        # No additional range validation needed here
        return cleaned_data

    def get_enrollment_grades(self):
        """Extract grade data for enrollments from cleaned form data."""
        if not self.is_valid():
            return {}

        enrollment_grades = {}
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith("grade_") and value is not None:
                enrollment_id = field_name.replace("grade_", "")
                try:
                    enrollment_id = int(enrollment_id)
                    comment_field = f"comment_{enrollment_id}"
                    comment = self.cleaned_data.get(comment_field, "")

                    enrollment_grades[enrollment_id] = {"grade": value, "comment": comment}
                except ValueError:
                    # Invalid enrollment ID - skip
                    continue

        return enrollment_grades

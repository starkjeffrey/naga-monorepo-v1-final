from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model

User = get_user_model()

emails = ["staff@pucsr.edu.kh", "finadmin@pucsr.edu.kh", "testadmin@pucsr.edu.kh"]

for email in emails:
    try:
        u = User.objects.get(email=email)
        email_obj, created = EmailAddress.objects.get_or_create(
            user=u, email=email, defaults={"verified": True, "primary": True}
        )
        if not created:
            email_obj.verified = True
            email_obj.primary = True
            email_obj.save()
        print(f"Email verified for {email}")
    except User.DoesNotExist:
        print(f"User not found: {email}")

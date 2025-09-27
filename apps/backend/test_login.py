from django.contrib.auth import authenticate, get_user_model

User = get_user_model()

# Test each user
test_users = [
    ("staff@pucsr.edu.kh", "staff123"),
    ("finadmin@pucsr.edu.kh", "finadmin123"),
    ("testadmin@pucsr.edu.kh", "testadmin123"),
]

for email, password in test_users:
    # Check if user exists
    try:
        user = User.objects.get(email=email)
        print(f"\n{email}:")
        print("  Exists: Yes")
        print(f"  Is staff: {user.is_staff}")
        print(f"  Is active: {user.is_active}")
        print(f"  Is superuser: {user.is_superuser}")

        # Try to authenticate
        auth_user = authenticate(username=email, password=password)
        if auth_user:
            print("  Authentication: SUCCESS")
        else:
            print("  Authentication: FAILED")
            # Reset password
            user.set_password(password)
            user.save()
            print(f"  Password reset to: {password}")

    except User.DoesNotExist:
        print(f"\n{email}: User does not exist")

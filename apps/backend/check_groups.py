from django.contrib.auth import get_user_model

User = get_user_model()

for email in ["staff@pucsr.edu.kh", "finadmin@pucsr.edu.kh"]:
    u = User.objects.get(email=email)
    groups = list(u.groups.values_list("name", flat=True))
    print(f"{email}: Groups = {groups}")

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create/update the demo user"

    def handle(self, *args, **kwargs):
        User = get_user_model()
        u, _ = User.objects.get_or_create(username="demo")
        u.is_active = True
        u.set_password("demo12345")
        u.save()
        self.stdout.write(self.style.SUCCESS("Demo user ready (demo / demo12345)"))

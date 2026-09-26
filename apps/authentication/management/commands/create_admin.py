import os

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from apps.authentication.models import Admin


class Command(BaseCommand):
    """Crea (o actualiza la contraseña de) un administrador de la API."""

    help = "Crea o actualiza un administrador usando django.contrib.auth.hashers.make_password."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True, help="Correo del administrador (único en la tabla admins).")
        parser.add_argument("--name", default=None, help="Nombre visible del administrador.")
        parser.add_argument(
            "--password",
            default=None,
            help="Contraseña en texto plano. Si se omite se usa la variable de entorno ADMIN_PASSWORD.",
        )

    def handle(self, *args, **options):
        password = options["password"] or os.getenv("ADMIN_PASSWORD")
        if not password:
            raise CommandError("Indique --password o defina la variable de entorno ADMIN_PASSWORD.")

        admin, created = Admin.objects.update_or_create(
            email=options["email"],
            defaults={"name": options["name"], "password": make_password(password)},
        )
        action = "creado" if created else "actualizado"
        self.stdout.write(self.style.SUCCESS(f"Administrador {action}: {admin.email}"))
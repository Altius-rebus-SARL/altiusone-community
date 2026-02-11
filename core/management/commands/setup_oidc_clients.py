"""
Register OAuth2/OIDC client applications for Nextcloud and MinIO.
Reads credentials from environment variables; skips if already registered.
"""
import os

from django.core.management.base import BaseCommand
from oauth2_provider.models import Application


class Command(BaseCommand):
    help = "Create or update OAuth2 OIDC client applications for Nextcloud and MinIO"

    def handle(self, *args, **options):
        clients = []

        # --- Nextcloud ---
        nc_client_id = os.environ.get("NEXTCLOUD_OIDC_CLIENT_ID")
        nc_client_secret = os.environ.get("NEXTCLOUD_OIDC_CLIENT_SECRET")
        nc_domain = os.environ.get("NEXTCLOUD_DOMAIN", "")

        if nc_client_id and nc_client_secret:
            redirect_uris = ""
            if nc_domain:
                redirect_uris = (
                    f"https://{nc_domain}/apps/user_oidc/code\n"
                    f"http://{nc_domain}/apps/user_oidc/code"
                )
            clients.append({
                "client_id": nc_client_id,
                "client_secret": nc_client_secret,
                "name": "Nextcloud",
                "redirect_uris": redirect_uris,
                "client_type": Application.CLIENT_CONFIDENTIAL,
                "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
                "skip_authorization": True,
            })

        # --- MinIO ---
        minio_client_id = os.environ.get("MINIO_OIDC_CLIENT_ID")
        minio_client_secret = os.environ.get("MINIO_OIDC_CLIENT_SECRET")
        minio_domain = os.environ.get("MINIO_CONSOLE_DOMAIN", "")
        minio_port = os.environ.get("MINIO_CONSOLE_PORT", "9001")

        if minio_client_id and minio_client_secret:
            redirect_uris = ""
            if minio_domain:
                redirect_uris = (
                    f"https://{minio_domain}/oauth_callback\n"
                    f"http://{minio_domain}/oauth_callback"
                )
            else:
                redirect_uris = f"http://localhost:{minio_port}/oauth_callback"
            clients.append({
                "client_id": minio_client_id,
                "client_secret": minio_client_secret,
                "name": "MinIO",
                "redirect_uris": redirect_uris,
                "client_type": Application.CLIENT_CONFIDENTIAL,
                "authorization_grant_type": Application.GRANT_AUTHORIZATION_CODE,
                "skip_authorization": True,
            })

        if not clients:
            self.stdout.write(self.style.WARNING(
                "No OIDC client credentials found in environment. "
                "Set NEXTCLOUD_OIDC_CLIENT_ID/SECRET and/or MINIO_OIDC_CLIENT_ID/SECRET."
            ))
            return

        for conf in clients:
            client_id = conf.pop("client_id")
            client_secret = conf.pop("client_secret")
            name = conf["name"]

            app, created = Application.objects.update_or_create(
                client_id=client_id,
                defaults={
                    "client_secret": client_secret,
                    **conf,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(
                    f"  Created OIDC client: {name} (client_id={client_id})"
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"  Updated OIDC client: {name} (client_id={client_id})"
                ))

        self.stdout.write(self.style.SUCCESS("OIDC clients setup complete."))

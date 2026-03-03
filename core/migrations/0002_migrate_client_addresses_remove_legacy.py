# Generated migration: migrate legacy address fields to adresse_siege, then remove them.

from django.db import migrations


def migrate_client_addresses(apps, schema_editor):
    """Copy legacy fields (siege, canton_rc, npa, localite) into adresse_siege FK."""
    Client = apps.get_model('core', 'Client')
    Adresse = apps.get_model('core', 'Adresse')

    for client in Client.objects.select_related('adresse_siege').all():
        if not client.adresse_siege_id:
            # No adresse_siege at all -> create one from legacy fields
            adresse = Adresse.objects.create(
                code_postal=client.npa or '',
                localite=client.localite or client.siege or '',
                canton=client.canton_rc or '',
                rue='',
                pays='CH',
            )
            client.adresse_siege = adresse
            client.save(update_fields=['adresse_siege_id'])
        else:
            # Enrich adresse_siege from legacy fields if adresse_siege is incomplete
            adresse = client.adresse_siege
            changed = False
            if client.npa and not adresse.code_postal:
                adresse.code_postal = client.npa
                changed = True
            if client.localite and not adresse.localite:
                adresse.localite = client.localite
                changed = True
            if client.canton_rc and not adresse.canton:
                adresse.canton = client.canton_rc
                changed = True
            if changed:
                adresse.save()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        # Step 1: data migration
        migrations.RunPython(migrate_client_addresses, noop),
        # Step 2: remove legacy fields
        migrations.RemoveField(model_name='client', name='siege'),
        migrations.RemoveField(model_name='client', name='canton_rc'),
        migrations.RemoveField(model_name='client', name='npa'),
        migrations.RemoveField(model_name='client', name='localite'),
    ]

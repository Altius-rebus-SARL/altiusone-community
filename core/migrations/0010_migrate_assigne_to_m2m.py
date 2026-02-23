"""Data migration: copy assigne_a FK → assignes M2M for each Tache."""

from django.db import migrations


def migrate_assigne_to_m2m(apps, schema_editor):
    Tache = apps.get_model('core', 'Tache')
    for tache in Tache.objects.filter(assigne_a__isnull=False):
        tache.assignes.add(tache.assigne_a)


def reverse_m2m_to_assigne(apps, schema_editor):
    Tache = apps.get_model('core', 'Tache')
    for tache in Tache.objects.all():
        first_assignee = tache.assignes.first()
        if first_assignee:
            tache.assigne_a = first_assignee
            tache.save(update_fields=['assigne_a'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_tache_add_assignes_m2m_prestation'),
    ]

    operations = [
        migrations.RunPython(
            migrate_assigne_to_m2m,
            reverse_m2m_to_assigne,
        ),
    ]

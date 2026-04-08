# Generated manually — Conversation.mandat FK → mandats M2M

from django.db import migrations, models


def migrate_fk_to_m2m(apps, schema_editor):
    """Copie les FK mandat existantes vers la nouvelle relation M2M."""
    Conversation = apps.get_model('documents', 'Conversation')
    for conv in Conversation.objects.filter(mandat__isnull=False).iterator():
        conv.mandats.add(conv.mandat_id)


def migrate_m2m_to_fk(apps, schema_editor):
    """Reverse: copie le premier mandat M2M vers la FK."""
    Conversation = apps.get_model('documents', 'Conversation')
    for conv in Conversation.objects.prefetch_related('mandats').iterator():
        first_mandat = conv.mandats.first()
        if first_mandat:
            conv.mandat_id = first_mandat.pk
            conv.save(update_fields=['mandat_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0007_langue_saisie'),
        ('core', '0019_alter_client_responsable_optional'),
    ]

    operations = [
        # 1. Ajouter le champ M2M
        migrations.AddField(
            model_name='conversation',
            name='mandats',
            field=models.ManyToManyField(
                blank=True,
                help_text='Mandats pour le contexte documentaire',
                related_name='conversations_m2m',
                to='core.mandat',
                verbose_name='Mandats',
            ),
        ),
        # 2. Copier les données FK → M2M
        migrations.RunPython(migrate_fk_to_m2m, migrate_m2m_to_fk),
        # 3. Supprimer l'index sur mandat + statut
        migrations.RemoveIndex(
            model_name='conversation',
            name='conversatio_mandat__d70888_idx',
        ),
        # 4. Supprimer la FK mandat
        migrations.RemoveField(
            model_name='conversation',
            name='mandat',
        ),
        # 5. Renommer le related_name temporaire
        migrations.AlterField(
            model_name='conversation',
            name='mandats',
            field=models.ManyToManyField(
                blank=True,
                help_text='Mandats pour le contexte documentaire',
                related_name='conversations',
                to='core.mandat',
                verbose_name='Mandats',
            ),
        ),
    ]

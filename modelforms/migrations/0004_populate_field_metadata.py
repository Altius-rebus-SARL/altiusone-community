# apps/modelforms/migrations/0004_populate_field_metadata.py
"""
Data migration: populate label and help_text on existing ModelFieldMapping
records from the Django model's verbose_name and help_text.
"""
from django.db import migrations


def populate_field_metadata(apps, schema_editor):
    """Fill empty label/help_text from model field introspection."""
    from django.apps import apps as django_apps

    ModelFieldMapping = apps.get_model('modelforms', 'ModelFieldMapping')

    for mapping in ModelFieldMapping.objects.all():
        if mapping.label and mapping.help_text:
            continue  # Already populated

        try:
            app_label, model_name = mapping.source_model.split('.')
            model_class = django_apps.get_model(app_label, model_name)
        except (ValueError, LookupError):
            continue

        try:
            field = model_class._meta.get_field(mapping.field_name)
        except Exception:
            continue

        updated = False
        if not mapping.label:
            verbose = str(getattr(field, 'verbose_name', ''))
            if verbose:
                mapping.label = verbose
                updated = True

        if not mapping.help_text:
            ht = str(getattr(field, 'help_text', '') or '')
            if ht:
                mapping.help_text = ht
                updated = True

        if updated:
            mapping.save(update_fields=['label', 'help_text'])


class Migration(migrations.Migration):

    dependencies = [
        ('modelforms', '0003_public_access_and_mandats'),
    ]

    operations = [
        migrations.RunPython(populate_field_metadata, migrations.RunPython.noop),
    ]

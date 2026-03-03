# comptabilite/migrations/0005_populate_code_tva_ref.py
from django.db import migrations


def populate_code_tva_ref(apps, schema_editor):
    """Best-effort: link existing EcritureComptable.code_tva to CodeTVA FK."""
    EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    ConfigurationTVA = apps.get_model('tva', 'ConfigurationTVA')
    CodeTVA = apps.get_model('tva', 'CodeTVA')

    for ecriture in EcritureComptable.objects.filter(
        code_tva_ref__isnull=True
    ).exclude(code_tva='').select_related('mandat'):
        # Find the regime via mandat → config_tva → regime
        regime_id = None
        try:
            config = ConfigurationTVA.objects.get(mandat=ecriture.mandat)
            regime_id = config.regime_id
        except ConfigurationTVA.DoesNotExist:
            pass

        if regime_id:
            code_tva_obj = CodeTVA.objects.filter(
                regime_id=regime_id,
                code=ecriture.code_tva,
            ).first()
            if code_tva_obj:
                ecriture.code_tva_ref = code_tva_obj
                ecriture.save(update_fields=['code_tva_ref'])


def reverse_populate(apps, schema_editor):
    EcritureComptable = apps.get_model('comptabilite', 'EcritureComptable')
    EcritureComptable.objects.all().update(code_tva_ref=None)


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0004_ecriturecomptable_piececomptable_tiers'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_code_tva_ref, reverse_populate),
    ]

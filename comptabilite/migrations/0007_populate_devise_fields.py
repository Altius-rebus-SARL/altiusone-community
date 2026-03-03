# comptabilite/migrations/0007_populate_devise_fields.py
"""
Populate devise on PlanComptable from mandat.devise.
Populate code_tva_defaut_ref on Compte from code_tva_defaut text.
"""
from django.db import migrations


def populate_plan_comptable_devise(apps, schema_editor):
    """Populate PlanComptable.devise from mandat.devise"""
    PlanComptable = apps.get_model('comptabilite', 'PlanComptable')
    Mandat = apps.get_model('core', 'Mandat')

    for plan in PlanComptable.objects.filter(mandat__isnull=False):
        try:
            mandat = Mandat.objects.get(pk=plan.mandat_id)
            if mandat.devise_id:
                plan.devise_id = mandat.devise_id
                plan.save(update_fields=['devise'])
        except Exception:
            pass


def populate_compte_code_tva_ref(apps, schema_editor):
    """Populate Compte.code_tva_defaut_ref from code_tva_defaut CharField"""
    Compte = apps.get_model('comptabilite', 'Compte')
    CodeTVA = apps.get_model('tva', 'CodeTVA')

    for compte in Compte.objects.exclude(code_tva_defaut=''):
        # Try to find matching CodeTVA by code
        code_tva = CodeTVA.objects.filter(code=compte.code_tva_defaut).first()
        if code_tva:
            compte.code_tva_defaut_ref_id = code_tva.pk
            compte.save(update_fields=['code_tva_defaut_ref'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0006_plancomptable_devise_journal_devise_piece_devise_compte_codetva'),
        ('core', '0007_mandat_regime_devise_not_null'),
        ('tva', '0005_alter_correctiontva_base_calcul_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_plan_comptable_devise, noop),
        migrations.RunPython(populate_compte_code_tva_ref, noop),
    ]

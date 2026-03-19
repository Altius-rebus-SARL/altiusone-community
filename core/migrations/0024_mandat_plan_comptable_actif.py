# Generated migration for plan_comptable_actif on Mandat
import django.db.models.deletion
from django.db import migrations, models


def set_plan_comptable_actif(apps, schema_editor):
    """Pour chaque mandat existant, définir plan_comptable_actif
    à partir du premier plan comptable existant."""
    Mandat = apps.get_model('core', 'Mandat')
    PlanComptable = apps.get_model('comptabilite', 'PlanComptable')

    for mandat in Mandat.objects.filter(plan_comptable_actif__isnull=True):
        plan = PlanComptable.objects.filter(
            mandat=mandat, is_template=False
        ).first()
        if plan:
            mandat.plan_comptable_actif = plan
            mandat.save(update_fields=['plan_comptable_actif'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_modelembedding'),
        ('comptabilite', '0008_alter_ecriturecomptable_devise'),
    ]

    operations = [
        migrations.AddField(
            model_name='mandat',
            name='plan_comptable_actif',
            field=models.ForeignKey(
                blank=True,
                help_text='Plan comptable utilisé par ce mandat',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='mandats_actifs',
                to='comptabilite.plancomptable',
                verbose_name='Plan comptable actif',
            ),
        ),
        migrations.RunPython(set_plan_comptable_actif, migrations.RunPython.noop),
    ]

# Safe idempotent migration for plan_comptable_actif on Mandat

from django.db import migrations, models
import django.db.models.deletion


def add_plan_comptable_actif_if_missing(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'mandats' AND column_name = 'plan_comptable_actif_id'"
    )
    if not cursor.fetchone():
        cursor.execute(
            'ALTER TABLE "mandats" ADD COLUMN "plan_comptable_actif_id" uuid NULL '
            'REFERENCES "plans_comptables"("id") ON DELETE SET NULL'
        )


def set_plan_comptable_actif(apps, schema_editor):
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
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='mandat',
                    name='plan_comptable_actif',
                    field=models.ForeignKey(blank=True, help_text='Plan comptable utilisé par ce mandat', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='mandats_actifs', to='comptabilite.plancomptable', verbose_name='Plan comptable actif'),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_plan_comptable_actif_if_missing, migrations.RunPython.noop),
                migrations.RunPython(set_plan_comptable_actif, migrations.RunPython.noop),
            ],
        ),
    ]

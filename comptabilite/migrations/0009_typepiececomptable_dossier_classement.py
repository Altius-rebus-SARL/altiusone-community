# Safe idempotent migration for dossier_classement on TypePieceComptable

from django.db import migrations, models


def add_dossier_classement_if_missing(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    cursor.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'types_pieces_comptables' AND column_name = 'dossier_classement'"
    )
    if not cursor.fetchone():
        cursor.execute(
            'ALTER TABLE "types_pieces_comptables" ADD COLUMN "dossier_classement" '
            "varchar(100) NOT NULL DEFAULT ''"
        )


def set_default_dossier_classement(apps, schema_editor):
    TypePieceComptable = apps.get_model('comptabilite', 'TypePieceComptable')
    mapping = {
        'FAC_ACH': 'Comptabilité',
        'FAC_VTE': 'Comptabilité',
        'AVOIR_ACH': 'Comptabilité',
        'AVOIR_VTE': 'Comptabilité',
        'NDF': 'Comptabilité',
        'REL_BNQ': 'Comptabilité',
        'CAISSE': 'Comptabilité',
        'SALAIRE': 'Salaires',
        'OD': 'Comptabilité',
    }
    for code, dossier in mapping.items():
        TypePieceComptable.objects.filter(code=code).update(
            dossier_classement=dossier
        )


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0008_alter_ecriturecomptable_devise'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='typepiececomptable',
                    name='dossier_classement',
                    field=models.CharField(blank=True, help_text='Nom du sous-dossier cible pour le classement automatique (ex: Comptabilité, Salaires)', max_length=100, verbose_name='Dossier de classement'),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_dossier_classement_if_missing, migrations.RunPython.noop),
                migrations.RunPython(set_default_dossier_classement, migrations.RunPython.noop),
            ],
        ),
    ]

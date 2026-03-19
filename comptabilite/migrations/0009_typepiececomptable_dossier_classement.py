# Generated migration for dossier_classement on TypePieceComptable
from django.db import migrations, models


def set_default_dossier_classement(apps, schema_editor):
    """Définir les dossiers de classement par défaut pour les types existants."""
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
        migrations.AddField(
            model_name='typepiececomptable',
            name='dossier_classement',
            field=models.CharField(
                blank=True,
                help_text='Nom du sous-dossier cible pour le classement automatique (ex: Comptabilité, Salaires)',
                max_length=100,
                verbose_name='Dossier de classement',
            ),
        ),
        migrations.RunPython(set_default_dossier_classement, migrations.RunPython.noop),
    ]

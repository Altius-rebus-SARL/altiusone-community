# Data migration to create default Entreprise

from django.db import migrations


def create_default_entreprise(apps, schema_editor):
    """Crée l'entreprise par défaut avec son adresse."""
    Adresse = apps.get_model('core', 'Adresse')
    Entreprise = apps.get_model('core', 'Entreprise')
    
    # Vérifier si une entreprise existe déjà
    if Entreprise.objects.exists():
        return
    
    # Créer l'adresse du siège
    adresse = Adresse.objects.create(
        rue='Chemin du Clos de la Pépinière',
        numero='20',
        code_postal='1040',
        localite='Echallens',
        canton='VD',
        pays='CH'
    )
    
    # Créer l'entreprise
    Entreprise.objects.create(
        raison_sociale='Altius Academy SNC',
        forme_juridique='SNC',
        ide_number='CHE-138.647.564',
        ch_id='CH-550-1237137-3',
        ofrc_id='1613327',
        siege='Echallens',
        canton_rc='VD',
        adresse=adresse,
        but="offrir des services de haute qualité aux particuliers et aux entreprises dans des domaines variés tels que l'ingénierie, l'éducation et d'autres prestations de services, en visant l'excellence et la satisfaction du client.",
        date_creation='2023-11-01',
        date_inscription_rc='2023-11-16',
        statut='ACTIVE',
        associes=[
            {
                'nom': 'Guindo',
                'prenom': 'Paul dit Akouni',
                'origine': 'du Mali',
                'domicile': 'Echallens',
                'signature': 'individuelle'
            },
            {
                'nom': 'Guindo',
                'prenom': 'Sandy',
                'origine': 'de Lausanne',
                'domicile': 'Echallens',
                'signature': 'individuelle'
            }
        ],
        derniere_publication_fosc='No. 1005890308 de 21.11.2023 - Nouvelle inscription'
    )


def reverse_migration(apps, schema_editor):
    """Supprime l'entreprise par défaut."""
    Entreprise = apps.get_model('core', 'Entreprise')
    Entreprise.objects.filter(ide_number='CHE-138.647.564').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_entreprise_model'),
    ]

    operations = [
        migrations.RunPython(create_default_entreprise, reverse_migration),
    ]

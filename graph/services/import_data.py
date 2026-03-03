# graph/services/import_data.py
"""Service d'import de données dans le graphe."""
import csv
import io
import logging

logger = logging.getLogger(__name__)


def importer_csv(file, type_id, mapping, created_by=None):
    """
    Importe des entités depuis un fichier CSV.

    Args:
        file: Fichier CSV (InMemoryUploadedFile ou similaire)
        type_id: UUID du OntologieType (entity) cible
        mapping: dict {colonne_csv: champ_entite} ex: {"Company": "nom", "Address": "attributs.adresse"}
        created_by: User ayant lancé l'import

    Returns:
        dict: {created: int, errors: list[str]}
    """
    from graph.models import OntologieType, Entite

    try:
        ont_type = OntologieType.objects.get(pk=type_id, categorie='entity')
    except OntologieType.DoesNotExist:
        return {'created': 0, 'errors': [f"Type d'ontologie introuvable: {type_id}"]}

    # Lire le CSV
    content = file.read()
    if isinstance(content, bytes):
        content = content.decode('utf-8-sig')

    reader = csv.DictReader(io.StringIO(content))
    created = 0
    errors = []

    for row_num, row in enumerate(reader, start=2):
        try:
            nom = None
            description = ''
            attributs = {}

            for col_csv, champ in mapping.items():
                valeur = row.get(col_csv, '').strip()
                if not valeur:
                    continue

                if champ == 'nom':
                    nom = valeur
                elif champ == 'description':
                    description = valeur
                elif champ.startswith('attributs.'):
                    attr_key = champ.split('.', 1)[1]
                    attributs[attr_key] = valeur
                elif champ == 'tags':
                    # Tags séparés par des virgules
                    pass  # Handled below

            if not nom:
                errors.append(f"Ligne {row_num}: nom manquant")
                continue

            tags = []
            if 'tags' in mapping:
                tag_col = [k for k, v in mapping.items() if v == 'tags']
                if tag_col:
                    tags_raw = row.get(tag_col[0], '')
                    tags = [t.strip() for t in tags_raw.split(',') if t.strip()]

            Entite.objects.create(
                type=ont_type,
                nom=nom,
                description=description,
                attributs=attributs,
                tags=tags,
                source='import',
                created_by=created_by,
            )
            created += 1

        except Exception as e:
            errors.append(f"Ligne {row_num}: {e}")

    logger.info(f"Import CSV: {created} entités créées, {len(errors)} erreurs")
    return {'created': created, 'errors': errors}


def importer_document_ocr(document_id, created_by=None):
    """
    Crée une entité graphe à partir d'un document traité par OCR.

    Crée une entité de type 'Document' avec un GenericForeignKey
    vers le document source.

    Args:
        document_id: UUID du document
        created_by: User

    Returns:
        dict: {entite_id: str} ou {error: str}
    """
    from graph.models import OntologieType, Entite
    from documents.models import Document
    from django.contrib.contenttypes.models import ContentType

    try:
        document = Document.objects.get(pk=document_id)
    except Document.DoesNotExist:
        return {'error': f'Document introuvable: {document_id}'}

    # Trouver ou créer le type 'Document' dans l'ontologie
    doc_type, _ = OntologieType.objects.get_or_create(
        nom='Document',
        categorie='entity',
        defaults={
            'icone': 'ph-file-text',
            'couleur': '#f59e0b',
            'description': 'Document importé',
        },
    )

    ct = ContentType.objects.get_for_model(Document)

    # Vérifier si une entité existe déjà pour ce document
    existing = Entite.objects.filter(
        content_type=ct,
        object_id=document.pk,
        is_active=True,
    ).first()

    if existing:
        return {'entite_id': str(existing.pk), 'existed': True}

    entite = Entite.objects.create(
        type=doc_type,
        nom=document.nom_fichier,
        description=getattr(document, 'texte_ocr', '') or '',
        attributs={
            'extension': getattr(document, 'extension', ''),
            'taille': getattr(document, 'taille', 0),
        },
        source='ocr',
        content_type=ct,
        object_id=document.pk,
        created_by=created_by,
    )

    logger.info(f"Entité créée depuis document OCR: {entite.nom} ({entite.pk})")
    return {'entite_id': str(entite.pk), 'existed': False}

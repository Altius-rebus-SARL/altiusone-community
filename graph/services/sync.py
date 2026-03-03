# graph/services/sync.py
"""
Service de synchronisation des modèles Django vers le graphe relationnel.

Chaque instance de modèle mappé dans sync_config → une Entite (via GenericFK).
Chaque FK entre instances mappées → une Relation.
"""
import logging

from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger(__name__)

# Cache local pour les OntologieType (évite N+1)
_type_cache = {}


def _get_type_cache():
    """Charge et retourne le cache des OntologieType par nom."""
    if not _type_cache:
        from graph.models import OntologieType
        for t in OntologieType.objects.filter(is_active=True):
            _type_cache[(t.categorie, t.nom)] = t
    return _type_cache


def invalidate_type_cache():
    """Invalide le cache (à appeler après init_ontologie)."""
    _type_cache.clear()


def _resolve_field(instance, field_path):
    """
    Résout la valeur d'un champ, y compris les traversées FK (role__nom)
    et les callables (get_full_name, __str__).
    """
    if field_path == '__str__':
        return str(instance)

    parts = field_path.split('__')
    obj = instance
    for part in parts:
        if obj is None:
            return None
        attr = getattr(obj, part, None)
        if attr is None:
            return None
        if callable(attr) and not isinstance(attr, type):
            obj = attr()
        else:
            obj = attr
    return obj


def _build_attributs(instance, fields):
    """Construit le dict attributs à partir de la liste de champs."""
    attributs = {}
    for field_path in fields:
        val = _resolve_field(instance, field_path)
        if val is not None:
            # Clé = dernier segment du path (role__nom → nom)
            key = field_path.split('__')[-1]
            # Convertir les types non-sérialisables
            attributs[key] = str(val) if not isinstance(val, (str, int, float, bool)) else val
    return attributs


def _get_nom(instance, nom_field):
    """Résout le nom de l'entité."""
    val = _resolve_field(instance, nom_field)
    return str(val) if val else str(instance)


def _get_model_key(instance):
    """Retourne la clé 'app_label.ModelName' pour un modèle."""
    meta = instance._meta
    return f'{meta.app_label}.{meta.object_name}'


def get_or_create_entite(instance):
    """
    Trouve ou crée l'Entite correspondant à une instance Django.
    Lookup par content_type + object_id (GenericFK).
    Retourne (entite, created).
    """
    from graph.models import Entite

    ct = ContentType.objects.get_for_model(instance)
    try:
        entite = Entite.objects.get(content_type=ct, object_id=instance.pk)
        return entite, False
    except Entite.DoesNotExist:
        return None, True


def sync_instance(instance):
    """
    Crée ou met à jour l'Entite correspondant à une instance Django.
    Retourne l'Entite ou None si le modèle n'est pas mappé.
    """
    from graph.models import Entite
    from graph.sync_config import MODEL_GRAPH_CONFIG

    model_key = _get_model_key(instance)
    config = MODEL_GRAPH_CONFIG.get(model_key)
    if not config:
        return None

    cache = _get_type_cache()
    type_obj = cache.get(('entity', config['type_nom']))
    if not type_obj:
        logger.warning(f"Type d'ontologie introuvable: {config['type_nom']}")
        return None

    ct = ContentType.objects.get_for_model(instance)
    nom = _get_nom(instance, config['nom_field'])
    description = ''
    if config.get('description_field'):
        description = _resolve_field(instance, config['description_field']) or ''
    attributs = _build_attributs(instance, config.get('attributs_fields', []))

    entite, created = Entite.objects.update_or_create(
        content_type=ct,
        object_id=instance.pk,
        defaults={
            'type': type_obj,
            'nom': nom[:255],
            'description': str(description),
            'attributs': attributs,
            'source': config.get('source', 'systeme'),
            'confiance': 1.0,
        },
    )

    action = 'Créée' if created else 'MAJ'
    logger.debug(f"Entite {action}: {entite.nom} ({model_key} #{instance.pk})")
    return entite


def sync_relations(instance):
    """
    Pour chaque FK dans RELATION_MAPPINGS, crée/met à jour la Relation
    entre l'Entite source (instance) et l'Entite cible (FK target).
    """
    from graph.models import Entite, Relation
    from graph.sync_config import RELATION_MAPPINGS

    model_key = _get_model_key(instance)
    fk_mappings = RELATION_MAPPINGS.get(model_key)
    if not fk_mappings:
        return

    ct_source = ContentType.objects.get_for_model(instance)
    try:
        source_entite = Entite.objects.get(content_type=ct_source, object_id=instance.pk)
    except Entite.DoesNotExist:
        logger.debug(f"Pas d'Entite source pour {model_key} #{instance.pk}")
        return

    cache = _get_type_cache()

    for fk_field, relation_type_nom in fk_mappings.items():
        # Récupérer l'objet FK cible
        fk_id = getattr(instance, f'{fk_field}_id', None)
        if fk_id is None:
            # Supprimer la relation existante si la FK a été vidée
            _cleanup_relation(source_entite, fk_field, relation_type_nom, cache)
            continue

        fk_obj = getattr(instance, fk_field, None)
        if fk_obj is None:
            continue

        # Trouver l'Entite cible
        ct_cible = ContentType.objects.get_for_model(fk_obj)
        try:
            cible_entite = Entite.objects.get(content_type=ct_cible, object_id=fk_obj.pk)
        except Entite.DoesNotExist:
            logger.debug(
                f"Pas d'Entite cible pour {fk_field} "
                f"({fk_obj._meta.label} #{fk_obj.pk})"
            )
            continue

        # Trouver le type de relation
        rel_type = cache.get(('relation', relation_type_nom))
        if not rel_type:
            logger.warning(f"Type de relation introuvable: {relation_type_nom}")
            continue

        # Upsert la relation
        Relation.objects.update_or_create(
            source=source_entite,
            cible=cible_entite,
            type=rel_type,
            defaults={
                'confiance': 1.0,
                'en_cours': True,
            },
        )
        logger.debug(
            f"Relation: {source_entite.nom} → {relation_type_nom} → {cible_entite.nom}"
        )


def _cleanup_relation(source_entite, fk_field, relation_type_nom, cache):
    """Supprime une relation si la FK source a été vidée."""
    from graph.models import Relation

    rel_type = cache.get(('relation', relation_type_nom))
    if rel_type:
        Relation.objects.filter(
            source=source_entite,
            type=rel_type,
        ).delete()


def delete_instance(instance):
    """
    Désactive l'Entite et ses relations quand l'instance Django est supprimée.
    """
    from graph.models import Entite

    ct = ContentType.objects.get_for_model(instance)
    try:
        entite = Entite.objects.get(content_type=ct, object_id=instance.pk)
    except Entite.DoesNotExist:
        return

    # Désactiver les relations sortantes et entrantes
    entite.relations_sortantes.update(is_active=False)
    entite.relations_entrantes.update(is_active=False)
    # Désactiver l'entité
    entite.is_active = False
    entite.save(update_fields=['is_active', 'updated_at'])

    logger.debug(f"Entite désactivée: {entite.nom} ({_get_model_key(instance)} #{instance.pk})")

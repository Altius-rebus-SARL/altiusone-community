# graph/tests/factories.py
"""Factories pour les tests du graphe relationnel."""
import uuid
from graph.models import OntologieType, Entite, Relation, Anomalie, RequeteSauvegardee


def make_ontologie_type(categorie='entity', nom=None, **kwargs):
    """Crée un OntologieType pour les tests."""
    if nom is None:
        nom = f'TestType_{uuid.uuid4().hex[:6]}'
    defaults = {
        'nom': nom,
        'categorie': categorie,
        'icone': 'ph-circle',
        'couleur': '#6366f1',
        'schema_attributs': {},
    }
    defaults.update(kwargs)
    return OntologieType.objects.create(**defaults)


def make_entite(type_obj=None, nom=None, **kwargs):
    """Crée une Entite pour les tests."""
    if type_obj is None:
        type_obj = make_ontologie_type(categorie='entity')
    if nom is None:
        nom = f'TestEntite_{uuid.uuid4().hex[:6]}'
    defaults = {
        'type': type_obj,
        'nom': nom,
        'source': 'manuelle',
        'confiance': 1.0,
    }
    defaults.update(kwargs)
    return Entite.objects.create(**defaults)


def make_relation(type_obj=None, source=None, cible=None, **kwargs):
    """Crée une Relation pour les tests."""
    if type_obj is None:
        type_obj = make_ontologie_type(categorie='relation', verbe='relie', verbe_inverse='est relié à')
    if source is None:
        source = make_entite()
    if cible is None:
        cible = make_entite(type_obj=source.type)
    defaults = {
        'type': type_obj,
        'source': source,
        'cible': cible,
        'poids': 1.0,
        'confiance': 1.0,
    }
    defaults.update(kwargs)
    return Relation.objects.create(**defaults)


def make_anomalie(entite=None, **kwargs):
    """Crée une Anomalie pour les tests."""
    if entite is None:
        entite = make_entite()
    defaults = {
        'type': 'doublon',
        'entite': entite,
        'titre': f'Test anomalie {uuid.uuid4().hex[:6]}',
        'score': 0.85,
        'statut': 'nouveau',
    }
    defaults.update(kwargs)
    return Anomalie.objects.create(**defaults)


def make_requete_sauvegardee(**kwargs):
    """Crée une RequeteSauvegardee pour les tests."""
    defaults = {
        'nom': f'Test requête {uuid.uuid4().hex[:6]}',
        'profondeur': 2,
    }
    defaults.update(kwargs)
    return RequeteSauvegardee.objects.create(**defaults)

# graph/tests/factories.py
"""Factories pour les tests du graphe relationnel."""
import uuid
from datetime import date
from decimal import Decimal

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


# --- Factories pour les modèles Django (tests sync) ---

def make_user(**kwargs):
    """Crée un User minimal pour les tests."""
    from core.models import User
    uid = uuid.uuid4().hex[:6]
    defaults = {
        'username': f'testuser_{uid}',
        'email': f'test_{uid}@example.com',
        'first_name': 'Test',
        'last_name': f'User_{uid}',
    }
    defaults.update(kwargs)
    return User.objects.create_user(password='testpass123', **defaults)


def make_adresse(**kwargs):
    """Crée une Adresse minimale pour les tests."""
    from core.models import Adresse
    defaults = {
        'rue': 'Rue de Test 1',
        'code_postal': '1201',
        'localite': 'Genève',
        'canton': 'GE',
        'pays': 'CH',
    }
    defaults.update(kwargs)
    return Adresse.objects.create(**defaults)


def make_client(responsable=None, adresse_siege=None, **kwargs):
    """Crée un Client minimal pour les tests."""
    from core.models import Client
    uid = uuid.uuid4().hex[:6]
    if responsable is None:
        responsable = make_user()
    if adresse_siege is None:
        adresse_siege = make_adresse()
    ide_base = f"{100 + hash(uid) % 900}.{100 + hash(uid[:3]) % 900}.{100 + hash(uid[3:]) % 900}"
    defaults = {
        'raison_sociale': f'Test SA {uid}',
        'forme_juridique': 'SA',
        'ide_number': f'CHE-{ide_base}',
        'adresse_siege': adresse_siege,
        'email': f'info_{uid}@test.ch',
        'telephone': '+41 22 000 00 00',
        'date_creation': date(2020, 1, 1),
        'date_debut_exercice': date(2025, 1, 1),
        'date_fin_exercice': date(2025, 12, 31),
        'responsable': responsable,
        'statut': 'ACTIF',
    }
    defaults.update(kwargs)
    return Client.objects.create(**defaults)


def make_mandat(client=None, responsable=None, **kwargs):
    """Crée un Mandat minimal pour les tests."""
    from core.models import Mandat
    uid = uuid.uuid4().hex[:6]
    if responsable is None:
        responsable = make_user()
    if client is None:
        client = make_client(responsable=responsable)
    defaults = {
        'client': client,
        'numero': f'MAN-TEST-{uid}',
        'type_mandat': 'COMPTA',
        'date_debut': date(2025, 1, 1),
        'responsable': responsable,
        'statut': 'ACTIF',
    }
    defaults.update(kwargs)
    return Mandat.objects.create(**defaults)

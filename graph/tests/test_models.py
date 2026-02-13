# graph/tests/test_models.py
"""Tests des modèles du graphe relationnel."""
from django.test import TestCase
from django.db import IntegrityError
from graph.models import OntologieType, Entite, Relation, Anomalie, RequeteSauvegardee
from .factories import (
    make_ontologie_type, make_entite, make_relation, make_anomalie,
    make_requete_sauvegardee,
)


class OntologieTypeTestCase(TestCase):
    def test_create_entity_type(self):
        t = make_ontologie_type(categorie='entity', nom='Personne')
        self.assertEqual(t.nom, 'Personne')
        self.assertEqual(t.categorie, 'entity')
        self.assertTrue(t.is_active)
        self.assertIsNotNone(t.pk)

    def test_create_relation_type(self):
        t = make_ontologie_type(
            categorie='relation', nom='Emploi',
            verbe='emploie', verbe_inverse='est employé par',
        )
        self.assertEqual(t.verbe, 'emploie')
        self.assertEqual(t.verbe_inverse, 'est employé par')

    def test_str(self):
        t = make_ontologie_type(categorie='entity', nom='Entreprise')
        self.assertIn('Entreprise', str(t))
        self.assertIn('Entité', str(t))

    def test_schema_attributs_default(self):
        t = make_ontologie_type()
        self.assertEqual(t.schema_attributs, {})

    def test_m2m_source_cible_types(self):
        personne = make_ontologie_type(categorie='entity', nom='Personne')
        entreprise = make_ontologie_type(categorie='entity', nom='Entreprise')
        emploi = make_ontologie_type(categorie='relation', nom='Emploi')

        emploi.source_types_autorises.add(entreprise)
        emploi.cible_types_autorises.add(personne)

        self.assertEqual(emploi.source_types_autorises.count(), 1)
        self.assertEqual(emploi.cible_types_autorises.count(), 1)


class EntiteTestCase(TestCase):
    def test_create_entite(self):
        e = make_entite(nom='Test SA')
        self.assertEqual(e.nom, 'Test SA')
        self.assertEqual(e.confiance, 1.0)
        self.assertEqual(e.source, 'manuelle')

    def test_str(self):
        e = make_entite(nom='Acme Corp')
        self.assertEqual(str(e), 'Acme Corp')

    def test_texte_pour_embedding(self):
        t = make_ontologie_type(nom='Entreprise')
        e = make_entite(
            type_obj=t, nom='Acme Corp',
            description='Leader mondial',
            attributs={'secteur': 'Tech'},
        )
        texte = e.texte_pour_embedding()
        self.assertIn('Entreprise', texte)
        self.assertIn('Acme Corp', texte)
        self.assertIn('Leader mondial', texte)
        self.assertIn('secteur: Tech', texte)

    def test_tags_default(self):
        e = make_entite()
        self.assertEqual(e.tags, [])

    def test_geom_null_by_default(self):
        e = make_entite()
        self.assertIsNone(e.geom)

    def test_embedding_null_by_default(self):
        e = make_entite()
        self.assertIsNone(e.embedding)


class RelationTestCase(TestCase):
    def test_create_relation(self):
        r = make_relation()
        self.assertIsNotNone(r.pk)
        self.assertIsNotNone(r.source)
        self.assertIsNotNone(r.cible)
        self.assertEqual(r.poids, 1.0)

    def test_str(self):
        rel_type = make_ontologie_type(categorie='relation', nom='Emploi', verbe='emploie')
        source = make_entite(nom='Acme')
        cible = make_entite(nom='Jean', type_obj=source.type)
        r = make_relation(type_obj=rel_type, source=source, cible=cible)
        self.assertIn('Acme', str(r))
        self.assertIn('emploie', str(r))
        self.assertIn('Jean', str(r))

    def test_unique_constraint(self):
        rel_type = make_ontologie_type(categorie='relation')
        source = make_entite()
        cible = make_entite(type_obj=source.type)
        make_relation(type_obj=rel_type, source=source, cible=cible)
        with self.assertRaises(IntegrityError):
            make_relation(type_obj=rel_type, source=source, cible=cible)

    def test_en_cours_default_true(self):
        r = make_relation()
        self.assertTrue(r.en_cours)


class AnomalieTestCase(TestCase):
    def test_create_anomalie(self):
        a = make_anomalie()
        self.assertIsNotNone(a.pk)
        self.assertEqual(a.type, 'doublon')
        self.assertEqual(a.statut, 'nouveau')

    def test_str(self):
        a = make_anomalie(titre='Doublon détecté')
        self.assertIn('Doublon', str(a))

    def test_ordering_by_score(self):
        e = make_entite()
        a1 = make_anomalie(entite=e, score=0.5, titre='Low')
        a2 = make_anomalie(entite=e, score=0.9, titre='High')
        anomalies = list(Anomalie.objects.filter(entite=e))
        self.assertEqual(anomalies[0].score, 0.9)


class RequeteSauvegardeeTestCase(TestCase):
    def test_create_requete(self):
        r = make_requete_sauvegardee(nom='Ma recherche')
        self.assertEqual(r.nom, 'Ma recherche')
        self.assertEqual(r.profondeur, 2)
        self.assertFalse(r.partage)

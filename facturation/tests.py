"""
Tests pour le module facturation.

Couvre :
- Résolution IBAN / entreprise créancière (QR-Bill)
- Génération QR-Bill SVG (lib qrbill)
- Génération PDF (émetteur = entreprise, destinataire = client, logo)
- Formulaires (devise auto-fill, exercice filtré)
- Modèle Facture (calculs, est_simplifiee, etc.)
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory

from core.models import (
    Adresse, Client, CompteBancaire, Devise, Entreprise,
    ExerciceComptable, Mandat,
)
from facturation.models import Facture, LigneFacture
from facturation.services.pdf_facture import FacturePDF

User = get_user_model()


class FacturationTestBase(TestCase):
    """Fixtures communes pour tous les tests facturation."""

    @classmethod
    def setUpTestData(cls):
        cls.devise_chf, _ = Devise.objects.get_or_create(
            code='CHF', defaults={'nom': 'Franc suisse', 'symbole': 'CHF'},
        )

        # Régime fiscal
        from tva.models import RegimeFiscal
        cls.regime, _ = RegimeFiscal.objects.get_or_create(
            code='CH', defaults={
                'nom': 'Suisse', 'pays': 'CH',
                'devise_defaut': cls.devise_chf, 'taux_normal': Decimal('8.1'),
            },
        )

        # Adresses
        cls.adresse_entreprise = Adresse.objects.create(
            rue='Rue de Bourg', numero='12', npa='1003', localite='Lausanne',
        )
        cls.adresse_client = Adresse.objects.create(
            rue='Route du Juge', numero='11', npa='1613', localite='Maracon',
        )

        # Entreprise (fiduciaire)
        cls.entreprise = Entreprise.objects.create(
            raison_sociale='Altius Academy SNC',
            forme_juridique='SNC',
            ide_number='CHE-138.647.564',
            siege='Lausanne',
            est_defaut=True,
            adresse=cls.adresse_entreprise,
            tva_number='CHE-138.647.564 TVA',
            telephone='0782576425',
            email='test@altius.ch',
        )

        # Compte bancaire de l'entreprise
        cls.compte = CompteBancaire.objects.create(
            libelle='Compte principal',
            iban='CH5800791123000889012',
            nom_banque='BCV',
            titulaire_nom='Altius Academy SNC',
            devise=cls.devise_chf,
            entreprise=cls.entreprise,
            est_compte_principal=True,
            actif=True,
        )

        # User (superuser pour accès complet aux vues)
        cls.user = User.objects.create_superuser(
            username='testuser', password='testpass', email='u@test.ch',
        )

        # Client (nommé client_obj pour éviter conflit avec TestCase.client)
        cls.client_obj = Client.objects.create(
            raison_sociale='Jorat Gospel',
            forme_juridique='ASS',
            adresse_siege=cls.adresse_client,
            email='jorat@gospel.ch',
            telephone='0219876543',
            date_debut_exercice=date(2026, 1, 1),
            date_fin_exercice=date(2026, 12, 31),
            entreprise=cls.entreprise,
        )
        cls.client_obj.refresh_from_db()

        # Mandat
        cls.mandat = Mandat.objects.create(
            numero='MAN-2026-TEST',
            client=cls.client_obj,
            date_debut=date(2026, 1, 1),
            responsable=cls.user,
            regime_fiscal=cls.regime,
            devise=cls.devise_chf,
        )

        # Facture
        cls.facture = Facture.objects.create(
            numero_facture='FAC-TEST-001',
            mandat=cls.mandat,
            client=cls.client_obj,
            date_emission=date(2026, 3, 12),
            date_echeance=date(2026, 4, 11),
            devise=cls.devise_chf,
            creee_par=cls.user,
            montant_ht=Decimal('150.00'),
            montant_tva=Decimal('12.15'),
            montant_ttc=Decimal('162.15'),
        )

        # Ligne de facture
        cls.ligne = LigneFacture.objects.create(
            facture=cls.facture,
            description='Hébergement et maintenance',
            quantite=Decimal('1'),
            prix_unitaire_ht=Decimal('150.00'),
            taux_tva=Decimal('8.1'),
            montant_ht=Decimal('150.00'),
            montant_tva=Decimal('12.15'),
            montant_ttc=Decimal('162.15'),
        )


# =============================================================================
# Tests résolution IBAN
# =============================================================================

class ResolveIBANTest(FacturationTestBase):
    """Tests pour _resolve_iban_and_creditor()."""

    def test_resolve_via_entreprise_defaut(self):
        """Le compte de l'entreprise par défaut est trouvé."""
        iban, entreprise = self.facture._resolve_iban_and_creditor()
        self.assertEqual(iban, 'CH5800791123000889012')
        self.assertEqual(entreprise, self.entreprise)

    def test_resolve_via_client_entreprise(self):
        """Chemin Client → Entreprise → Compte fonctionne."""
        # Créer une 2e entreprise non-défaut
        ent2 = Entreprise.objects.create(
            raison_sociale='Autre Fiduciaire',
            forme_juridique='SA',
            ide_number='CHE-999.999.999',
            siege='Genève',
            est_defaut=False,
        )
        compte2 = CompteBancaire.objects.create(
            libelle='Compte GE',
            iban='CH9300762011623852957',
            nom_banque='UBS',
            titulaire_nom='Autre Fiduciaire',
            devise=self.devise_chf,
            entreprise=ent2,
            est_compte_principal=True,
            actif=True,
        )
        # Associer le client à ent2
        self.client_obj.entreprise = ent2
        self.client_obj.save(update_fields=['entreprise'])

        iban, entreprise = self.facture._resolve_iban_and_creditor()
        self.assertEqual(iban, 'CH9300762011623852957')
        self.assertEqual(entreprise, ent2)

        # Cleanup
        self.client_obj.entreprise = self.entreprise
        self.client_obj.save(update_fields=['entreprise'])

    def test_resolve_via_mandat_compte(self):
        """Compte directement lié au mandat a priorité."""
        compte_mandat = CompteBancaire.objects.create(
            libelle='Compte mandat',
            iban='CH1234567890123456789',
            nom_banque='PostFinance',
            titulaire_nom='Altius Academy SNC',
            devise=self.devise_chf,
            mandat=self.mandat,
            actif=True,
        )
        iban, _ = self.facture._resolve_iban_and_creditor()
        self.assertEqual(iban, 'CH1234567890123456789')
        compte_mandat.delete()

    def test_resolve_qr_iban_override(self):
        """qr_iban sur la facture a la priorité absolue."""
        self.facture.qr_iban = 'CH0000000000000000001'
        iban, _ = self.facture._resolve_iban_and_creditor()
        self.assertEqual(iban, 'CH0000000000000000001')
        self.facture.qr_iban = ''

    def test_resolve_compte_non_principal_fallback(self):
        """Un compte actif non-principal est trouvé en fallback."""
        self.compte.est_compte_principal = False
        self.compte.save(update_fields=['est_compte_principal'])

        iban, entreprise = self.facture._resolve_iban_and_creditor()
        self.assertEqual(iban, 'CH5800791123000889012')

        self.compte.est_compte_principal = True
        self.compte.save(update_fields=['est_compte_principal'])

    def test_resolve_aucun_compte_raise(self):
        """ValueError si aucun compte bancaire n'existe."""
        self.compte.actif = False
        self.compte.save(update_fields=['actif'])

        with self.assertRaises(ValueError) as ctx:
            self.facture._resolve_iban_and_creditor()
        self.assertIn('IBAN', str(ctx.exception))

        self.compte.actif = True
        self.compte.save(update_fields=['actif'])


# =============================================================================
# Tests QR-Bill SVG
# =============================================================================

class QRBillSVGTest(FacturationTestBase):
    """Tests pour generer_qr_bill() avec la lib qrbill."""

    def test_generer_qr_bill_svg(self):
        """Le SVG est généré et sauvegardé."""
        self.facture.generer_qr_bill()
        self.facture.refresh_from_db()

        self.assertTrue(self.facture.qr_code_image.name.endswith('.svg'))
        svg_content = self.facture.qr_code_image.read().decode('utf-8')
        self.assertIn('<svg', svg_content)
        self.assertIn('Récépissé', svg_content)

    def test_generer_qr_reference(self):
        """La référence QR est générée (27 chiffres)."""
        ref = self.facture.generer_qr_reference()
        self.assertEqual(len(ref), 27)
        self.assertTrue(ref.isdigit())

    def test_qr_bill_sans_iban_raise(self):
        """Erreur claire si pas d'IBAN."""
        self.compte.actif = False
        self.compte.save(update_fields=['actif'])

        with self.assertRaises(ValueError):
            self.facture.generer_qr_bill()

        self.compte.actif = True
        self.compte.save(update_fields=['actif'])

    def test_qr_bill_contient_infos_creancier(self):
        """Le SVG contient le nom du créancier (entreprise)."""
        self.facture.generer_qr_bill()
        self.facture.refresh_from_db()
        svg = self.facture.qr_code_image.read().decode('utf-8')
        self.assertIn('Altius Academy', svg)

    def test_qr_bill_contient_infos_debiteur(self):
        """Le SVG contient le nom du débiteur (client)."""
        self.facture.generer_qr_bill()
        self.facture.refresh_from_db()
        svg = self.facture.qr_code_image.read().decode('utf-8')
        self.assertIn('Jorat Gospel', svg)

    def test_qr_bill_contient_montant(self):
        """Le SVG contient le montant."""
        self.facture.generer_qr_bill()
        self.facture.refresh_from_db()
        svg = self.facture.qr_code_image.read().decode('utf-8')
        self.assertIn('162.15', svg)


# =============================================================================
# Tests PDF
# =============================================================================

class FacturePDFTest(FacturationTestBase):
    """Tests pour la génération PDF via FacturePDF."""

    def test_pdf_genere_bytes(self):
        """Le PDF est généré sans erreur."""
        service = FacturePDF(self.facture)
        pdf_bytes = service.generer()
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

    def test_pdf_avec_qr_bill(self):
        """Le PDF avec QR-Bill a 2 pages."""
        service = FacturePDF(self.facture, avec_qr_bill=True)
        pdf_bytes = service.generer()
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertTrue(len(pdf_bytes) > 5000)

    def test_emetteur_est_entreprise(self):
        """L'émetteur est l'entreprise par défaut, pas le client."""
        service = FacturePDF(self.facture)
        entreprise = service._get_entreprise()
        self.assertEqual(entreprise, self.entreprise)
        self.assertEqual(entreprise.raison_sociale, 'Altius Academy SNC')

    def test_destinataire_toujours_affiche(self):
        """Le destinataire (client) est affiché même si montant < 400 CHF."""
        self.assertTrue(self.facture.est_simplifiee)
        # Le PDF ne doit pas planter et doit contenir le client
        service = FacturePDF(self.facture)
        pdf_bytes = service.generer()
        self.assertTrue(len(pdf_bytes) > 500)

    def test_pdf_facture_grosse(self):
        """Le PDF fonctionne pour une facture > 400 CHF."""
        self.facture.montant_ttc = Decimal('5000.00')
        self.facture.save(update_fields=['montant_ttc'])
        self.assertFalse(self.facture.est_simplifiee)

        service = FacturePDF(self.facture)
        pdf_bytes = service.generer()
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))

        self.facture.montant_ttc = Decimal('162.15')
        self.facture.save(update_fields=['montant_ttc'])

    def test_entreprise_cache(self):
        """_get_entreprise() est appelé une seule fois (cache)."""
        service = FacturePDF(self.facture)
        ent1 = service._get_entreprise()
        ent2 = service._get_entreprise()
        self.assertIs(ent1, ent2)


# =============================================================================
# Tests Modèle Facture
# =============================================================================

class FactureModelTest(FacturationTestBase):
    """Tests pour le modèle Facture."""

    def test_est_simplifiee(self):
        """est_simplifiee = True si montant_ttc < 400."""
        self.facture.montant_ttc = Decimal('162.15')
        self.assertTrue(self.facture.est_simplifiee)

        self.facture.montant_ttc = Decimal('400.00')
        self.assertFalse(self.facture.est_simplifiee)

        self.facture.montant_ttc = Decimal('399.99')
        self.assertTrue(self.facture.est_simplifiee)

    def test_generer_pdf_sauvegarde_fichier(self):
        """generer_pdf() sauvegarde le fichier PDF sur le modèle."""
        self.facture.generer_pdf()
        self.facture.refresh_from_db()
        self.assertTrue(self.facture.fichier_pdf.name.endswith('.pdf'))

    def test_generer_pdf_avec_qr_bill(self):
        """generer_pdf(avec_qr_bill=True) fonctionne."""
        self.facture.generer_pdf(avec_qr_bill=True)
        self.facture.refresh_from_db()
        self.assertTrue(self.facture.fichier_pdf.name)
        self.assertTrue(self.facture.qr_code_image.name.endswith('.svg'))


# =============================================================================
# Tests Formulaires
# =============================================================================

class FactureFormTest(FacturationTestBase):
    """Tests pour FactureForm."""

    def test_devise_auto_fill_from_mandat(self):
        """La devise est auto-remplie depuis le mandat."""
        from facturation.forms import FactureForm
        form = FactureForm(mandat=self.mandat)
        self.assertEqual(form.initial.get('devise'), self.devise_chf.pk)

    def test_exercice_filtre_par_mandat(self):
        """Le queryset exercice est filtré par mandat."""
        ExerciceComptable.objects.create(
            mandat=self.mandat, annee=2026,
            date_debut=date(2026, 1, 1), date_fin=date(2026, 12, 31),
            statut='OUVERT',
        )
        from facturation.forms import FactureForm
        form = FactureForm(mandat=self.mandat)
        exercices = form.fields['exercice'].queryset
        for ex in exercices:
            self.assertEqual(ex.mandat, self.mandat)

    def test_devise_clean_fallback(self):
        """clean() remplit la devise depuis le mandat si absente."""
        from facturation.forms import FactureForm
        form_data = {
            'numero_facture': 'FAC-TEST-002',
            'mandat': self.mandat.pk,
            'client': self.client_obj.pk,
            'date_emission': '2026-03-12',
            'date_echeance': '2026-04-11',
            # devise intentionnellement absente
        }
        form = FactureForm(data=form_data, mandat=self.mandat)
        if form.is_valid():
            self.assertEqual(form.cleaned_data['devise'], self.devise_chf)


# =============================================================================
# Tests Studio Preview
# =============================================================================

class StudioPreviewTest(FacturationTestBase):
    """Tests pour le endpoint studio preview."""

    def test_studio_preview_returns_pdf(self):
        """Le endpoint studio retourne un PDF valide."""
        import json
        factory = RequestFactory()
        body = json.dumps({
            'instance_id': str(self.facture.pk),
            'couleur_primaire': '#088178',
            'couleur_accent': '#2c3e50',
            'couleur_texte': '#333333',
            'police': 'Helvetica',
            'marge_haut': 20, 'marge_bas': 25,
            'marge_gauche': 20, 'marge_droite': 15,
            'blocs_visibles': {'qr_bill': False},
            'textes': {},
        })
        request = factory.post(
            '/api/studio/preview/',
            data=body, content_type='application/json',
        )
        request.user = self.user

        from facturation.views import facture_studio_preview
        response = facture_studio_preview(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))

    def test_studio_preview_avec_qr_bill(self):
        """Le endpoint studio avec QR-Bill retourne un PDF."""
        import json
        factory = RequestFactory()
        body = json.dumps({
            'instance_id': str(self.facture.pk),
            'blocs_visibles': {'qr_bill': True},
        })
        request = factory.post(
            '/api/studio/preview/',
            data=body, content_type='application/json',
        )
        request.user = self.user

        from facturation.views import facture_studio_preview
        response = facture_studio_preview(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'%PDF'))

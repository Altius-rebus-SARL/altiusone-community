# apps/facturation/models.py
from django.db import models
from core.models import BaseModel, Mandat, Client, User
from decimal import Decimal
from datetime import datetime, date, timedelta


class Prestation(BaseModel):
    """Prestation/Service fourni"""

    TYPE_CHOICES = [
        ('COMPTABILITE', 'Comptabilité'),
        ('TVA', 'TVA'),
        ('SALAIRES', 'Salaires'),
        ('CONSEIL', 'Conseil'),
        ('AUDIT', 'Audit'),
        ('FISCALITE', 'Fiscalité'),
        ('JURIDIQUE', 'Juridique'),
        ('CREATION', 'Création entreprise'),
        ('AUTRE', 'Autre'),
    ]

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    libelle = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    type_prestation = models.CharField(max_length=20, choices=TYPE_CHOICES)

    # Tarification par défaut
    prix_unitaire_ht = models.DecimalField(max_digits=10, decimal_places=2,
                                           null=True, blank=True)
    unite = models.CharField(max_length=50, default='heure',
                             help_text='heure, jour, forfait, unité')

    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2,
                                       null=True, blank=True)

    # TVA
    soumis_tva = models.BooleanField(default=True)
    taux_tva_defaut = models.DecimalField(max_digits=5, decimal_places=2, default=8.1)

    # Compte comptable
    compte_produit = models.ForeignKey('comptabilite.Compte',
                                       on_delete=models.SET_NULL,
                                       null=True, blank=True,
                                       related_name='+')

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'prestations'
        verbose_name = 'Prestation'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class TimeTracking(BaseModel):
    """Suivi du temps de travail sur les prestations"""

    # Rattachement
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='temps_travail')
    utilisateur = models.ForeignKey(User, on_delete=models.PROTECT,
                                    related_name='temps_travail')
    prestation = models.ForeignKey(Prestation, on_delete=models.PROTECT,
                                   related_name='temps_travail')

    # Temps
    date_travail = models.DateField(db_index=True)
    heure_debut = models.TimeField(null=True, blank=True)
    heure_fin = models.TimeField(null=True, blank=True)
    duree_minutes = models.IntegerField(help_text='Durée en minutes')

    # Description
    description = models.TextField()
    notes_internes = models.TextField(blank=True)

    # Facturation
    facturable = models.BooleanField(default=True)
    taux_horaire = models.DecimalField(max_digits=10, decimal_places=2)
    montant_ht = models.DecimalField(max_digits=10, decimal_places=2)

    facture = models.ForeignKey('Facture', on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='temps_factures')
    date_facturation = models.DateField(null=True, blank=True)

    # Validation
    valide = models.BooleanField(default=False)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True,
                                   related_name='+')

    class Meta:
        db_table = 'time_tracking'
        verbose_name = 'Suivi du temps'
        ordering = ['-date_travail', 'utilisateur']
        indexes = [
            models.Index(fields=['mandat', 'date_travail']),
            models.Index(fields=['utilisateur', 'date_travail']),
            models.Index(fields=['facturable', 'facture']),
        ]

    def __str__(self):
        return f"{self.date_travail} - {self.utilisateur.username} - {self.duree_minutes}min"

    @property
    def duree_heures(self):
        """Retourne la durée en heures décimales"""
        return Decimal(self.duree_minutes) / Decimal('60')

    def calculer_montant(self):
        """Calcule le montant HT basé sur durée et taux"""
        heures = Decimal(self.duree_minutes) / Decimal("60")
        self.montant_ht = (heures * self.taux_horaire).quantize(Decimal("0.01"))
        self.save(update_fields=["montant_ht"])
        return self.montant_ht

    def ajouter_a_facture(self, facture):
        """Ajoute ce temps à une facture existante"""
        # Trouver ou créer la ligne correspondante
        ligne = facture.lignes.filter(prestation=self.prestation).first()

        if ligne:
            # Ajouter au temps existant
            ligne.quantite += self.duree_heures
            ligne.save()
        else:
            # Créer nouvelle ligne
            ordre = facture.lignes.aggregate(models.Max("ordre"))["ordre__max"] or 0
            ligne = LigneFacture.objects.create(
                facture=facture,
                ordre=ordre + 1,
                prestation=self.prestation,
                description=self.description,
                quantite=self.duree_heures,
                unite="heure",
                prix_unitaire_ht=self.taux_horaire,
                taux_tva=self.prestation.taux_tva_defaut
                if self.prestation
                else Decimal("8.1"),
            )

        # Lier le temps à la ligne
        ligne.temps_factures.add(self)

        # Marquer comme facturé
        self.facture = facture
        self.date_facturation = date.today()
        self.save()

        # Recalculer la facture
        facture.calculer_totaux()

        return ligne

class Facture(BaseModel):
    """Facture client"""

    STATUT_CHOICES = [
        ('BROUILLON', 'Brouillon'),
        ('PROFORMA', 'Pro forma'),
        ('EMISE', 'Émise'),
        ('ENVOYEE', 'Envoyée'),
        ('RELANCEE', 'Relancée'),
        ('PARTIELLEMENT_PAYEE', 'Partiellement payée'),
        ('PAYEE', 'Payée'),
        ('EN_RETARD', 'En retard'),
        ('ANNULEE', 'Annulée'),
        ('AVOIR', 'Avoir'),
    ]

    TYPE_CHOICES = [
        ('FACTURE', 'Facture'),
        ('AVOIR', 'Avoir'),
        ('ACOMPTE', 'Facture d\'acompte'),
    ]

    # Identification
    numero_facture = models.CharField(max_length=50, unique=True, db_index=True)
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='factures')
    client = models.ForeignKey(Client, on_delete=models.PROTECT,
                               related_name='factures')

    type_facture = models.CharField(max_length=20, choices=TYPE_CHOICES,
                                    default='FACTURE')

    # Dates
    date_emission = models.DateField(db_index=True)
    date_echeance = models.DateField(db_index=True)
    date_service_debut = models.DateField(null=True, blank=True,
                                          help_text='Début période facturée')
    date_service_fin = models.DateField(null=True, blank=True,
                                        help_text='Fin période facturée')

    # Montants
    montant_ht = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    montant_tva = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    montant_ttc = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Remises
    remise_pourcent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remise_montant = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Paiement
    delai_paiement_jours = models.IntegerField(default=30)
    conditions_paiement = models.TextField(blank=True)

    # QR-Bill Suisse
    qr_reference = models.CharField(max_length=27, 
                                    blank=True,
                                    null=True, 
                                    unique=True,
                                    help_text='Référence QR structurée')
    qr_iban = models.CharField(max_length=34, blank=True)
    qr_code_image = models.ImageField(upload_to='factures/qr/',
                                      null=True, blank=True)

    # Statut
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES,
                              default='BROUILLON', db_index=True)

    # Paiements
    montant_paye = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    montant_restant = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    date_paiement_complet = models.DateField(null=True, blank=True)

    # Relances
    nombre_relances = models.IntegerField(default=0)
    date_derniere_relance = models.DateField(null=True, blank=True)

    # Avoir / Annulation
    facture_origine = models.ForeignKey('self', on_delete=models.SET_NULL,
                                        null=True, blank=True,
                                        related_name='avoirs')
    motif_annulation = models.TextField(blank=True)

    # Fichiers
    fichier_pdf = models.FileField(upload_to='factures/pdf/',
                                   null=True, blank=True)

    # Comptabilité
    ecriture_comptable = models.ForeignKey('comptabilite.PieceComptable',
                                           on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='factures')

    # Textes
    introduction = models.TextField(blank=True,
                                    help_text='Texte introduction facture')
    conclusion = models.TextField(blank=True,
                                  help_text='Texte conclusion/remerciements')
    notes = models.TextField(blank=True, help_text='Notes internes')

    # Création/validation
    creee_par = models.ForeignKey(User, on_delete=models.PROTECT,
                                  related_name='factures_creees')
    date_validation = models.DateTimeField(null=True, blank=True)
    validee_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='factures_validees')

    class Meta:
        db_table = 'factures'
        verbose_name = 'Facture'
        ordering = ['-date_emission', 'numero_facture']
        indexes = [
            models.Index(fields=['client', 'statut']),
            models.Index(fields=['date_emission']),
            models.Index(fields=['date_echeance', 'statut']),
            models.Index(fields=['numero_facture']),
        ]

    def __str__(self):
        return f"{self.numero_facture} - {self.client.raison_sociale} - {self.montant_ttc} CHF"

    def save(self, *args, **kwargs):
        # Génération numéro facture
        if not self.numero_facture:
            year = self.date_emission.year
            last = Facture.objects.filter(
                numero_facture__startswith=f'FAC-{year}'
            ).order_by('numero_facture').last()

            if last:
                last_num = int(last.numero_facture.split('-')[-1])
                self.numero_facture = f'FAC-{year}-{last_num + 1:04d}'
            else:
                self.numero_facture = f'FAC-{year}-0001'

        # Calcul montant restant
        self.montant_restant = self.montant_ttc - self.montant_paye

        # Mise à jour statut basé sur paiement
        if self.montant_paye >= self.montant_ttc and self.statut != 'PAYEE':
            self.statut = 'PAYEE'
            if not self.date_paiement_complet:
                self.date_paiement_complet = models.functions.Now()
        elif self.montant_paye > 0 and self.statut == 'EMISE':
            self.statut = 'PARTIELLEMENT_PAYEE'

        super().save(*args, **kwargs)

    def generer_qr_reference(self):
        """Génère la référence QR structurée selon norme suisse"""
        # Référence QR : 27 chiffres avec checksum
        # Format: [ID Créancier 6 digits][ID Facture 14 digits][Checksum 1 digit]

        # ID créancier (à adapter selon votre système)
        id_creancier = str(self.mandat.id)[:6].zfill(6)

        # ID facture unique
        id_facture = str(self.id).zfill(14)

        # Référence de base (26 digits)
        ref_base = id_creancier + id_facture

        # Calcul checksum modulo 10 récursif
        checksum = self._calcul_checksum_modulo10(ref_base)

        # Référence complète (27 digits)
        self.qr_reference = ref_base + str(checksum)
        self.save(update_fields=["qr_reference"])

        return self.qr_reference

    def _calcul_checksum_modulo10(self, reference):
        """Calcul checksum modulo 10 récursif (norme suisse)"""
        table = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
        carry = 0
        for char in reference:
            carry = table[(carry + int(char)) % 10]
        return (10 - carry) % 10

    def generer_qr_bill(self):
        """Génère le QR-Bill SVG avec la librairie qrbill"""
        from qrbill import QRBill
        from django.core.files.base import ContentFile
        import tempfile

        # Configuration du QR-Bill
        creditor_info = {
            "name": self.mandat.client.raison_sociale or self.mandat.client.nom_complet,
            "street": self.mandat.client.adresse_ligne1 or "",
            "pcode": self.mandat.client.code_postal or "",
            "city": self.mandat.client.ville or "",
            "country": self.mandat.client.pays or "CH",
        }

        debtor_info = None
        if hasattr(self, "client") and self.client:
            debtor_info = {
                "name": self.client.raison_sociale or self.client.nom_complet,
                "street": self.client.adresse_ligne1 or "",
                "pcode": self.client.code_postal or "",
                "city": self.client.ville or "",
                "country": self.client.pays or "CH",
            }

        # IBAN du compte (à configurer dans le mandat ou settings)
        iban = self.qr_iban or getattr(self.mandat, "iban_qr", "CH5800791123000889012")

        # Créer le QR-Bill
        qr_bill = QRBill(
            account=iban,
            creditor=creditor_info,
            debtor=debtor_info,
            amount=str(self.montant_ttc),
            reference_number=self.qr_reference,
            additional_information=f"Facture {self.numero_facture}",
            language="fr",  # ou 'de', 'it' selon la langue
        )

        # Générer le SVG dans un fichier temporaire
        with tempfile.NamedTemporaryFile(
            suffix=".svg", delete=False, mode="w"
        ) as temp_svg:
            qr_bill.as_svg(temp_svg.name)

            # Lire le contenu
            with open(temp_svg.name, "rb") as f:
                svg_content = f.read()

            # Sauvegarder comme fichier Django
            self.qr_code_image.save(
                f"qr_bill_{self.numero_facture}.svg",
                ContentFile(svg_content),
                save=True,
            )

        return self.qr_code_image

    def generer_pdf(self):
        """Génère le PDF complet de la facture avec QR-Bill"""
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas as pdf_canvas
        from django.core.files.base import ContentFile

        buffer = io.BytesIO()
        p = pdf_canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # EN-TÊTE
        p.setFont("Helvetica-Bold", 16)
        p.drawString(2 * cm, height - 2 * cm, "FACTURE")

        # Informations créancier (émetteur = mandat.client)
        p.setFont("Helvetica-Bold", 10)
        p.drawString(2 * cm, height - 4 * cm, self.mandat.client.raison_sociale)
        
        p.setFont("Helvetica", 9)
        y = height - 4.5 * cm
        adresse = self.mandat.client.adresse_siege
        p.drawString(2 * cm, y, f"{adresse.rue} {adresse.numero}")
        y -= 0.4 * cm
        if adresse.complement:
            p.drawString(2 * cm, y, adresse.complement)
            y -= 0.4 * cm
        p.drawString(2 * cm, y, f"{adresse.npa} {adresse.localite}")
        y -= 0.4 * cm
        if self.mandat.client.tva_number:
            p.drawString(2 * cm, y, f"N° TVA: {self.mandat.client.tva_number}")

        # Informations débiteur (client facturé)
        y = height - 6.5 * cm
        p.setFont("Helvetica-Bold", 9)
        p.drawString(12 * cm, y, "Facture adressée à:")
        y -= 0.5 * cm
        
        p.setFont("Helvetica", 9)
        p.drawString(12 * cm, y, self.client.raison_sociale)
        y -= 0.4 * cm
        
        adresse_client = self.client.adresse_correspondance or self.client.adresse_siege
        p.drawString(12 * cm, y, f"{adresse_client.rue} {adresse_client.numero}")
        y -= 0.4 * cm
        if adresse_client.complement:
            p.drawString(12 * cm, y, adresse_client.complement)
            y -= 0.4 * cm
        p.drawString(12 * cm, y, f"{adresse_client.npa} {adresse_client.localite}")
        y -= 0.4 * cm
        if self.client.tva_number:
            p.drawString(12 * cm, y, f"N° TVA: {self.client.tva_number}")
        y -= 0.4 * cm
        p.drawString(12 * cm, y, f"N° IDE: {self.client.ide_number}")

        # Informations facture
        y = height - 10 * cm
        p.setFont("Helvetica-Bold", 12)
        p.drawString(2 * cm, y, f"Facture N° {self.numero_facture}")
        y -= 0.7 * cm
        
        p.setFont("Helvetica", 9)
        p.drawString(2 * cm, y, f"Date d'émission: {self.date_emission.strftime('%d.%m.%Y')}")
        y -= 0.5 * cm
        p.drawString(2 * cm, y, f"Date d'échéance: {self.date_echeance.strftime('%d.%m.%Y')}")
        
        if self.date_service_debut and self.date_service_fin:
            y -= 0.5 * cm
            p.drawString(2 * cm, y, f"Période: {self.date_service_debut.strftime('%d.%m.%Y')} - {self.date_service_fin.strftime('%d.%m.%Y')}")

        # Introduction
        if self.introduction:
            y -= 1 * cm
            p.setFont("Helvetica", 9)
            # Wrapper le texte si trop long
            lines = self.introduction.split('\n')
            for line in lines[:3]:  # Max 3 lignes
                p.drawString(2 * cm, y, line[:100])
                y -= 0.5 * cm

        # TABLEAU DES LIGNES
        y -= 1 * cm

        # En-tête tableau
        p.setFont("Helvetica-Bold", 9)
        p.drawString(2 * cm, y, "Description")
        p.drawRightString(12 * cm, y, "Qté")
        p.drawRightString(14 * cm, y, "Prix unit.")
        p.drawRightString(16 * cm, y, "TVA")
        p.drawRightString(19 * cm, y, "Total HT")

        y -= 0.2 * cm
        p.line(2 * cm, y, 19 * cm, y)
        y -= 0.6 * cm

        # Lignes
        p.setFont("Helvetica", 9)
        for ligne in self.lignes.all().order_by("ordre"):
            desc = ligne.description[:70]
            p.drawString(2 * cm, y, desc)
            p.drawRightString(12 * cm, y, f"{ligne.quantite:.2f} {ligne.unite}")
            p.drawRightString(14 * cm, y, f"{ligne.prix_unitaire_ht:.2f}")
            p.drawRightString(16 * cm, y, f"{ligne.taux_tva:.1f}%")
            p.drawRightString(19 * cm, y, f"{ligne.montant_ht:.2f}")
            y -= 0.5 * cm

            # Nouvelle page si nécessaire
            if y < 8 * cm:
                p.showPage()
                y = height - 2 * cm
                p.setFont("Helvetica", 9)

        # TOTAUX
        y -= 0.5 * cm
        p.line(14 * cm, y, 19 * cm, y)
        y -= 0.6 * cm

        p.setFont("Helvetica-Bold", 10)
        p.drawString(14 * cm, y, "Sous-total HT:")
        p.drawRightString(19 * cm, y, f"{self.montant_ht:.2f} CHF")
        y -= 0.5 * cm

        if self.remise_pourcent > 0:
            p.setFont("Helvetica", 9)
            p.drawString(14 * cm, y, f"Remise ({self.remise_pourcent}%):")
            p.drawRightString(19 * cm, y, f"-{self.remise_montant:.2f} CHF")
            y -= 0.5 * cm

        p.setFont("Helvetica-Bold", 10)
        p.drawString(14 * cm, y, "TVA:")
        p.drawRightString(19 * cm, y, f"{self.montant_tva:.2f} CHF")
        y -= 0.5 * cm

        p.line(14 * cm, y, 19 * cm, y)
        y -= 0.6 * cm

        p.setFont("Helvetica-Bold", 14)
        p.drawString(14 * cm, y, "TOTAL TTC:")
        p.drawRightString(19 * cm, y, f"{self.montant_ttc:.2f} CHF")

        # Conclusion
        if self.conclusion:
            y -= 1.5 * cm
            p.setFont("Helvetica", 9)
            lines = self.conclusion.split('\n')
            for line in lines[:3]:
                if y < 3 * cm:
                    p.showPage()
                    y = height - 2 * cm
                p.drawString(2 * cm, y, line[:100])
                y -= 0.5 * cm

        # Conditions de paiement
        if self.conditions_paiement:
            y -= 0.5 * cm
            p.setFont("Helvetica-Bold", 9)
            p.drawString(2 * cm, y, "Conditions de paiement:")
            y -= 0.5 * cm
            p.setFont("Helvetica", 8)
            lines = self.conditions_paiement.split('\n')
            for line in lines[:3]:
                if y < 3 * cm:
                    break
                p.drawString(2 * cm, y, line[:100])
                y -= 0.4 * cm

        p.save()

        pdf_content = buffer.getvalue()
        buffer.close()

        self.fichier_pdf.save(
            f"facture_{self.numero_facture}.pdf", ContentFile(pdf_content), save=True
        )

        return self.fichier_pdf
    
    def calculer_totaux(self):
        """Recalcule tous les totaux à partir des lignes"""
        from django.db.models import Sum

        lignes = self.lignes.all()

        # Total HT
        self.montant_ht = lignes.aggregate(Sum("montant_ht"))[
            "montant_ht__sum"
        ] or Decimal("0")

        # Application remise globale
        if self.remise_pourcent:
            self.remise_montant = (
                self.montant_ht * self.remise_pourcent / 100
            ).quantize(Decimal("0.01"))

        montant_ht_net = self.montant_ht - self.remise_montant

        # TVA
        self.montant_tva = lignes.aggregate(Sum("montant_tva"))[
            "montant_tva__sum"
        ] or Decimal("0")

        # TTC
        self.montant_ttc = montant_ht_net + self.montant_tva

        # Montant restant
        self.montant_restant = self.montant_ttc - self.montant_paye

        self.save(
            update_fields=[
                "montant_ht",
                "montant_tva",
                "montant_ttc",
                "remise_montant",
                "montant_restant",
            ]
        )

        return self

    def valider(self, user):
        """Valide la facture"""
        if not self.lignes.exists():
            raise ValueError("La facture doit avoir au moins une ligne")

        # Recalculer les totaux
        self.calculer_totaux()

        # Générer QR-Bill
        if not self.qr_reference:
            self.generer_qr_reference()

        # Changer le statut
        self.statut = "EMISE"
        self.validee_par = user
        self.date_validation = datetime.now()
        self.save()

        return self

    def enregistrer_paiement(
        self, montant, date_paiement, mode_paiement, reference="", user=None
    ):
        """Enregistre un paiement pour cette facture"""
        paiement = Paiement.objects.create(
            facture=self,
            montant=montant,
            date_paiement=date_paiement,
            mode_paiement=mode_paiement,
            reference=reference,
            valide=True,
            valide_par=user,
            date_validation=datetime.now() if user else None,
        )

        return paiement

    def creer_avoir(self, montant=None, motif="", user=None):
        """Crée un avoir pour cette facture"""
        montant_avoir = montant or self.montant_ttc

        avoir = Facture.objects.create(
            mandat=self.mandat,
            client=self.client,
            type_facture="AVOIR",
            facture_origine=self,
            date_emission=date.today(),
            date_echeance=date.today() + timedelta(days=30),
            montant_ht=-abs(montant_avoir),
            montant_ttc=-abs(montant_avoir),
            statut="EMISE",
            motif_annulation=motif,
            creee_par=user or self.creee_par,
        )

        # Copier les lignes (en négatif)
        for ligne in self.lignes.all():
            LigneFacture.objects.create(
                facture=avoir,
                ordre=ligne.ordre,
                prestation=ligne.prestation,
                description=ligne.description,
                quantite=-ligne.quantite,
                unite=ligne.unite,
                prix_unitaire_ht=ligne.prix_unitaire_ht,
                taux_tva=ligne.taux_tva,
            )

        return avoir

    def creer_relance(self, niveau=None, user=None):
        """Crée une relance pour cette facture"""
        niveau_relance = niveau or (self.nombre_relances + 1)

        # Frais selon le niveau
        frais = Decimal("0")
        if niveau_relance == 2:
            frais = Decimal("20.00")
        elif niveau_relance >= 3:
            frais = Decimal("40.00")

        relance = Relance.objects.create(
            facture=self,
            niveau=niveau_relance,
            date_echeance=date.today() + timedelta(days=15),
            montant_frais=frais,
        )

        # Mettre à jour la facture
        self.nombre_relances += 1
        self.date_derniere_relance = date.today()
        if self.statut not in ["EN_RETARD", "ANNULEE"]:
            self.statut = "RELANCEE"
        self.save()

        return relance

    def est_en_retard(self):
        """Vérifie si la facture est en retard"""
        return (
            self.date_echeance < date.today()
            and self.montant_restant > 0
            and self.statut not in ["PAYEE", "ANNULEE", "AVOIR"]
        )

    def jours_retard(self):
        """Retourne le nombre de jours de retard"""
        if self.est_en_retard():
            return (date.today() - self.date_echeance).days
        return 0


class LigneFacture(BaseModel):
    """Ligne de facture"""

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE,
                                related_name='lignes')

    # Ordre d'affichage
    ordre = models.IntegerField(default=0)

    # Prestation/Produit
    prestation = models.ForeignKey(Prestation, on_delete=models.SET_NULL,
                                   null=True, blank=True)

    # Description
    description = models.TextField()
    description_detaillee = models.TextField(blank=True)

    # Quantité et prix
    quantite = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unite = models.CharField(max_length=50, default='heure')
    prix_unitaire_ht = models.DecimalField(max_digits=10, decimal_places=2)

    # Montants
    montant_ht = models.DecimalField(max_digits=15, decimal_places=2)

    # TVA
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=8.1)
    montant_tva = models.DecimalField(max_digits=15, decimal_places=2)
    montant_ttc = models.DecimalField(max_digits=15, decimal_places=2)

    # Remise spécifique ligne
    remise_pourcent = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Lien time tracking
    temps_factures = models.ManyToManyField(TimeTracking, blank=True,
                                            related_name='lignes_facture')

    class Meta:
        db_table = 'lignes_facture'
        verbose_name = 'Ligne de facture'
        ordering = ['facture', 'ordre']

    def __str__(self):
        return f"{self.facture.numero_facture} - {self.description[:50]}"

    def save(self, *args, **kwargs):
        # Calcul automatique des montants
        montant_brut = self.quantite * self.prix_unitaire_ht

        # Application remise ligne
        if self.remise_pourcent:
            montant_brut = montant_brut * (1 - self.remise_pourcent / 100)

        self.montant_ht = montant_brut.quantize(Decimal('0.01'))
        self.montant_tva = (self.montant_ht * self.taux_tva / 100).quantize(Decimal('0.01'))
        self.montant_ttc = self.montant_ht + self.montant_tva

        super().save(*args, **kwargs)


class Paiement(BaseModel):
    """Paiement d'une facture"""

    MODE_PAIEMENT_CHOICES = [
        ('VIREMENT', 'Virement bancaire'),
        ('QR_BILL', 'QR-Bill'),
        ('CARTE', 'Carte bancaire'),
        ('ESPECES', 'Espèces'),
        ('CHEQUE', 'Chèque'),
        ('COMPENSATION', 'Compensation'),
        ('AUTRE', 'Autre'),
    ]

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE,
                                related_name='paiements')

    # Montant
    montant = models.DecimalField(max_digits=15, decimal_places=2)
    devise = models.CharField(max_length=3, default='CHF')

    # Date et mode
    date_paiement = models.DateField(db_index=True)
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES)

    # Référence
    reference = models.CharField(max_length=100, blank=True,
                                 help_text='Référence bancaire, numéro transaction')

    # Validation
    valide = models.BooleanField(default=False)
    date_validation = models.DateTimeField(null=True, blank=True)
    valide_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                   null=True, blank=True)

    # Comptabilisation
    ecriture_comptable = models.ForeignKey('comptabilite.EcritureComptable',
                                           on_delete=models.SET_NULL,
                                           null=True, blank=True,
                                           related_name='paiements')

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'paiements'
        verbose_name = 'Paiement'
        ordering = ['-date_paiement']
        indexes = [
            models.Index(fields=['facture', 'date_paiement']),
            models.Index(fields=['date_paiement']),
        ]

    def __str__(self):
        return f"Paiement {self.montant} CHF - {self.facture.numero_facture}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        # Mise à jour du montant payé sur la facture
        self.facture.montant_paye = self.facture.paiements.filter(
            valide=True
        ).aggregate(
            total=models.Sum('montant')
        )['total'] or Decimal('0')

        self.facture.save(update_fields=['montant_paye', 'montant_restant', 'statut'])


class Relance(BaseModel):
    """Relance de paiement"""

    NIVEAU_CHOICES = [
        (1, '1ère relance'),
        (2, '2ème relance'),
        (3, '3ème relance'),
        (4, 'Mise en demeure'),
    ]

    facture = models.ForeignKey(Facture, on_delete=models.CASCADE,
                                related_name='relances')

    niveau = models.IntegerField(choices=NIVEAU_CHOICES)
    date_relance = models.DateField(auto_now_add=True)
    date_echeance = models.DateField(help_text='Nouvelle échéance')

    montant_frais = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                        help_text='Frais de relance')
    montant_interets = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text='Intérêts de retard')

    envoyee = models.BooleanField(default=False)
    date_envoi = models.DateField(null=True, blank=True)

    fichier_pdf = models.FileField(upload_to='factures/relances/',
                                   null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'relances'
        verbose_name = 'Relance'
        ordering = ['-date_relance']

    def __str__(self):
        return f"Relance niv.{self.niveau} - {self.facture.numero_facture}"
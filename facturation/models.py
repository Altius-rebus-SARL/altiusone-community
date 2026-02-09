# apps/facturation/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import BaseModel, Mandat, Client, User
from decimal import Decimal
from datetime import datetime, date, timedelta


class Prestation(BaseModel):
    """Prestation/Service fourni"""

    TYPE_CHOICES = [
        ('COMPTABILITE', _('Comptabilité')),
        ('TVA', _('TVA')),
        ('SALAIRES', _('Salaires')),
        ('CONSEIL', _('Conseil')),
        ('AUDIT', _('Audit')),
        ('FISCALITE', _('Fiscalité')),
        ('JURIDIQUE', _('Juridique')),
        ('CREATION', _('Création entreprise')),
        ('AUTRE', _('Autre')),
    ]

    # Identification
    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Code"),
        help_text=_("Code unique de la prestation")
    )
    libelle = models.CharField(
        max_length=255,
        verbose_name=_("Libellé"),
        help_text=_("Libellé de la prestation")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description"),
        help_text=_("Description détaillée de la prestation")
    )

    type_prestation = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_("Type de prestation"),
        help_text=_("Catégorie de la prestation")
    )

    # Tarification par défaut
    prix_unitaire_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Prix unitaire HT"),
        help_text=_("Prix unitaire hors taxes par défaut")
    )
    unite = models.CharField(
        max_length=50,
        default='heure',
        verbose_name=_("Unité"),
        help_text=_("Unité de facturation (heure, jour, forfait, unité)")
    )

    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Taux horaire"),
        help_text=_("Taux horaire de facturation")
    )

    # TVA
    soumis_tva = models.BooleanField(
        default=True,
        verbose_name=_("Soumis à TVA"),
        help_text=_("Indique si la prestation est soumise à TVA")
    )
    taux_tva_defaut = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8.1,
        verbose_name=_("Taux TVA par défaut"),
        help_text=_("Taux de TVA appliqué par défaut")
    )

    # Compte comptable
    compte_produit = models.ForeignKey(
        'comptabilite.Compte',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Compte de produit"),
        help_text=_("Compte comptable de produit associé")
    )

    actif = models.BooleanField(
        default=True,
        verbose_name=_("Actif"),
        help_text=_("Indique si la prestation est active")
    )

    class Meta:
        db_table = 'prestations'
        verbose_name = _('Prestation')
        verbose_name_plural = _('Prestations')
        ordering = ['code']

    def __str__(self):
        return f"{self.code} - {self.libelle}"


class TimeTracking(BaseModel):
    """Suivi du temps de travail sur les prestations"""

    # Rattachement
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='temps_travail',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné par ce temps de travail")
    )
    utilisateur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='temps_travail',
        verbose_name=_("Utilisateur"),
        help_text=_("Collaborateur ayant effectué le travail")
    )
    prestation = models.ForeignKey(
        Prestation,
        on_delete=models.PROTECT,
        related_name='temps_travail',
        verbose_name=_("Prestation"),
        help_text=_("Type de prestation effectuée")
    )

    # Temps
    date_travail = models.DateField(
        db_index=True,
        verbose_name=_("Date du travail"),
        help_text=_("Date à laquelle le travail a été effectué")
    )
    heure_debut = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Heure de début"),
        help_text=_("Heure de début du travail")
    )
    heure_fin = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_("Heure de fin"),
        help_text=_("Heure de fin du travail")
    )
    duree_minutes = models.IntegerField(
        verbose_name=_("Durée (minutes)"),
        help_text=_("Durée du travail en minutes")
    )

    # Description
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Description du travail effectué")
    )
    notes_internes = models.TextField(
        blank=True,
        verbose_name=_("Notes internes"),
        help_text=_("Notes internes non visibles sur la facture")
    )

    # Facturation
    facturable = models.BooleanField(
        default=True,
        verbose_name=_("Facturable"),
        help_text=_("Indique si ce temps est facturable au client")
    )
    taux_horaire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Taux horaire"),
        help_text=_("Taux horaire appliqué pour ce travail")
    )
    montant_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Montant HT"),
        help_text=_("Montant hors taxes calculé")
    )

    facture = models.ForeignKey(
        'Facture',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='temps_factures',
        verbose_name=_("Facture"),
        help_text=_("Facture associée si ce temps a été facturé")
    )
    date_facturation = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de facturation"),
        help_text=_("Date à laquelle ce temps a été facturé")
    )

    # Validation
    valide = models.BooleanField(
        default=False,
        verbose_name=_("Validé"),
        help_text=_("Indique si ce temps a été validé")
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_("Validé par"),
        help_text=_("Utilisateur ayant validé ce temps")
    )

    class Meta:
        db_table = 'time_tracking'
        verbose_name = _('Suivi du temps')
        verbose_name_plural = _('Suivis du temps')
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
        ('BROUILLON', _('Brouillon')),
        ('PROFORMA', _('Pro forma')),
        ('EMISE', _('Émise')),
        ('ENVOYEE', _('Envoyée')),
        ('RELANCEE', _('Relancée')),
        ('PARTIELLEMENT_PAYEE', _('Partiellement payée')),
        ('PAYEE', _('Payée')),
        ('EN_RETARD', _('En retard')),
        ('ANNULEE', _('Annulée')),
        ('AVOIR', _('Avoir')),
    ]

    TYPE_CHOICES = [
        ('FACTURE', _('Facture')),
        ('AVOIR', _('Avoir')),
        ('ACOMPTE', _("Facture d'acompte")),
    ]

    # Identification
    numero_facture = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_("Numéro de facture"),
        help_text=_("Numéro unique de la facture")
    )
    mandat = models.ForeignKey(
        Mandat,
        on_delete=models.CASCADE,
        related_name='factures',
        verbose_name=_("Mandat"),
        help_text=_("Mandat concerné par cette facture")
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.PROTECT,
        related_name='factures',
        verbose_name=_("Client"),
        help_text=_("Client facturé")
    )

    type_facture = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='FACTURE',
        verbose_name=_("Type de facture"),
        help_text=_("Type de document (Facture, Avoir, Acompte)")
    )

    # Dates
    date_emission = models.DateField(
        db_index=True,
        verbose_name=_("Date d'émission"),
        help_text=_("Date d'émission de la facture")
    )
    date_echeance = models.DateField(
        db_index=True,
        verbose_name=_("Date d'échéance"),
        help_text=_("Date limite de paiement")
    )
    date_service_debut = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Début de période"),
        help_text=_("Date de début de la période facturée")
    )
    date_service_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Fin de période"),
        help_text=_("Date de fin de la période facturée")
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant HT"),
        help_text=_("Montant total hors taxes")
    )
    montant_tva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant TVA"),
        help_text=_("Montant total de la TVA")
    )
    montant_ttc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant TTC"),
        help_text=_("Montant total toutes taxes comprises")
    )

    # Remises
    remise_pourcent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Remise (%)"),
        help_text=_("Pourcentage de remise globale")
    )
    remise_montant = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant remise"),
        help_text=_("Montant de la remise calculée")
    )

    # Paiement
    delai_paiement_jours = models.IntegerField(
        default=30,
        verbose_name=_("Délai de paiement (jours)"),
        help_text=_("Nombre de jours accordés pour le paiement")
    )
    conditions_paiement = models.TextField(
        blank=True,
        verbose_name=_("Conditions de paiement"),
        help_text=_("Conditions de paiement spécifiques")
    )

    # QR-Bill Suisse
    qr_reference = models.CharField(
        max_length=27,
        blank=True,
        null=True,
        unique=True,
        verbose_name=_("Référence QR"),
        help_text=_("Référence QR structurée pour le paiement suisse")
    )
    qr_iban = models.CharField(
        max_length=34,
        blank=True,
        verbose_name=_("IBAN QR"),
        help_text=_("IBAN pour le QR-Bill")
    )
    qr_code_image = models.ImageField(
        upload_to='factures/qr/',
        null=True,
        blank=True,
        verbose_name=_("Image QR code"),
        help_text=_("Image du QR code généré")
    )

    # Statut
    statut = models.CharField(
        max_length=30,
        choices=STATUT_CHOICES,
        default='BROUILLON',
        db_index=True,
        verbose_name=_("Statut"),
        help_text=_("Statut actuel de la facture")
    )

    # Paiements
    montant_paye = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant payé"),
        help_text=_("Montant total déjà payé")
    )
    montant_restant = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name=_("Montant restant"),
        help_text=_("Montant restant à payer")
    )

    date_paiement_complet = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date de paiement complet"),
        help_text=_("Date à laquelle la facture a été entièrement payée")
    )

    # Relances
    nombre_relances = models.IntegerField(
        default=0,
        verbose_name=_("Nombre de relances"),
        help_text=_("Nombre de relances envoyées")
    )
    date_derniere_relance = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date dernière relance"),
        help_text=_("Date de la dernière relance envoyée")
    )

    # Avoir / Annulation
    facture_origine = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='avoirs',
        verbose_name=_("Facture d'origine"),
        help_text=_("Facture d'origine pour un avoir")
    )
    motif_annulation = models.TextField(
        blank=True,
        verbose_name=_("Motif d'annulation"),
        help_text=_("Raison de l'annulation ou de l'avoir")
    )

    # Fichiers
    fichier_pdf = models.FileField(
        upload_to='factures/pdf/',
        null=True,
        blank=True,
        verbose_name=_("Fichier PDF"),
        help_text=_("Fichier PDF de la facture")
    )

    # Comptabilité
    ecriture_comptable = models.ForeignKey(
        'comptabilite.PieceComptable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures',
        verbose_name=_("Pièce comptable"),
        help_text=_("Pièce comptable associée")
    )

    # Textes
    introduction = models.TextField(
        blank=True,
        verbose_name=_("Introduction"),
        help_text=_("Texte d'introduction de la facture")
    )
    conclusion = models.TextField(
        blank=True,
        verbose_name=_("Conclusion"),
        help_text=_("Texte de conclusion/remerciements")
    )
    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes internes"),
        help_text=_("Notes internes non visibles sur la facture")
    )

    # Création/validation
    creee_par = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='factures_creees',
        verbose_name=_("Créée par"),
        help_text=_("Utilisateur ayant créé la facture")
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Date et heure de validation")
    )
    validee_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures_validees',
        verbose_name=_("Validée par"),
        help_text=_("Utilisateur ayant validé la facture")
    )

    class Meta:
        db_table = 'factures'
        verbose_name = _('Facture')
        verbose_name_plural = _('Factures')
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
        # Format: [ID Créancier 6 digits][ID Facture 20 digits][Checksum 1 digit]

        # Convertir UUID en nombre (utiliser les chiffres du hash)
        # Pour l'ID créancier: convertir UUID hex en int et prendre 6 chiffres
        mandat_hash = int(str(self.mandat.id).replace('-', '')[:12], 16)
        id_creancier = str(mandat_hash)[-6:].zfill(6)

        # Pour l'ID facture: convertir UUID hex en int et prendre 20 chiffres
        facture_hash = int(str(self.id).replace('-', ''), 16)
        id_facture = str(facture_hash)[-20:].zfill(20)

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
        """
        Génère le QR code Swiss QR-Bill au format PNG.

        Le QR code contient toutes les données de paiement selon la norme
        Swiss Payment Standards (ISO 20022).
        """
        try:
            import qrcode
            from qrcode.image.pil import PilImage
        except ImportError:
            raise ImportError("Le package 'qrcode' et 'pillow' sont requis.")

        from django.core.files.base import ContentFile
        import io

        # Générer la référence QR si pas encore fait
        if not self.qr_reference:
            self.generer_qr_reference()

        # Récupérer les adresses
        adresse_creancier = self.mandat.client.adresse_siege
        adresse_debiteur = self.client.adresse_correspondance or self.client.adresse_siege

        # IBAN du compte - Ordre de priorité:
        # 1. qr_iban de la facture (si défini manuellement)
        # 2. Compte bancaire associé au mandat
        # 3. Compte bancaire principal de la fiduciaire
        iban = None
        compte_bancaire = None

        if self.qr_iban:
            iban = self.qr_iban
        else:
            from core.models import CompteBancaire
            # Chercher un compte associé au mandat
            compte_bancaire = CompteBancaire.objects.filter(
                mandat=self.mandat, actif=True
            ).first()

            if not compte_bancaire:
                # Chercher le compte principal de la fiduciaire
                compte_bancaire = CompteBancaire.objects.filter(
                    est_compte_principal=True, actif=True
                ).first()

            if compte_bancaire:
                iban = compte_bancaire.iban

        if not iban:
            raise ValueError("Aucun IBAN configuré. Créez un compte bancaire principal ou associez-en un au mandat.")
        iban = iban.replace(" ", "").upper()

        # Construire le payload QR selon Swiss QR Bill standard
        # Format: https://www.paymentstandards.ch/dam/downloads/ig-qr-bill-fr.pdf

        # Déterminer si c'est un QR-IBAN (IID 30000-31999)
        is_qr_iban = False
        if iban.startswith('CH') and len(iban) >= 9:
            try:
                iid = int(iban[4:9])
                is_qr_iban = 30000 <= iid <= 31999
            except ValueError:
                pass

        qr_data_lines = [
            "SPC",  # QR Type
            "0200",  # Version
            "1",  # Coding Type (UTF-8)
            iban,  # IBAN
            # Creditor (Address Type S = Structured)
            "S",  # Address Type
            self.mandat.client.raison_sociale[:70],  # Name
            f"{adresse_creancier.rue} {adresse_creancier.numero}"[:70] if adresse_creancier else "",  # Street
            "",  # Building number (included in street)
            adresse_creancier.npa if adresse_creancier else "",  # Postal code
            adresse_creancier.localite[:35] if adresse_creancier else "",  # City
            "CH",  # Country
            # Ultimate Creditor (empty)
            "", "", "", "", "", "", "",
            # Payment Amount
            f"{float(self.montant_ttc):.2f}",  # Amount
            "CHF",  # Currency
            # Ultimate Debtor (Address Type S)
            "S",
            self.client.raison_sociale[:70],
            f"{adresse_debiteur.rue} {adresse_debiteur.numero}"[:70] if adresse_debiteur else "",
            "",
            adresse_debiteur.npa if adresse_debiteur else "",
            adresse_debiteur.localite[:35] if adresse_debiteur else "",
            "CH",
            # Reference Type and Reference
            "QRR" if is_qr_iban else "NON",  # QRR only with QR-IBAN
            self.qr_reference if is_qr_iban else "",  # Reference (only with QRR)
            # Unstructured message
            f"Facture {self.numero_facture}",
            "EPD",  # Trailer
            # Additional info (billing info) - optional
            "",
        ]

        qr_payload = "\r\n".join(qr_data_lines)

        # Créer le QR code
        qr = qrcode.QRCode(
            version=None,  # Auto-size
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=0,  # Pas de bordure, on la gère manuellement
        )
        qr.add_data(qr_payload)
        qr.make(fit=True)

        # Générer l'image PNG
        img = qr.make_image(fill_color="black", back_color="white")

        # Sauvegarder en PNG
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)

        # Sauvegarder comme fichier Django
        self.qr_code_image.save(
            f"qr_code_{self.numero_facture}.png",
            ContentFile(buffer.read()),
            save=True,
        )

        return self.qr_code_image

    def generer_pdf(self, avec_qr_bill=False):
        """
        Génère le PDF complet de la facture.

        Args:
            avec_qr_bill: Si True, ajoute le QR-Bill suisse en bas de page.
                          Génère automatiquement le QR code si nécessaire.
        """
        import io
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm, mm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.pdfgen import canvas as pdf_canvas
        from django.core.files.base import ContentFile

        # Si QR-Bill demandé, générer le QR code d'abord
        if avec_qr_bill:
            # Générer la référence QR si pas encore fait
            if not self.qr_reference:
                self.generer_qr_reference()

            # Toujours régénérer le QR code PNG pour s'assurer qu'il est à jour
            try:
                self.generer_qr_bill()
                # Recharger l'instance pour avoir le chemin à jour
                self.refresh_from_db(fields=['qr_code_image'])
            except Exception as e:
                # Log l'erreur mais continue sans QR code
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Impossible de générer le QR-Bill: {e}")

        buffer = io.BytesIO()
        width, height = A4

        # Marges - marge normale pour toutes les pages
        # Le QR-Bill sera ajouté à la fin (nouvelle page si nécessaire)
        margin_left = 2 * cm
        margin_right = 1.5 * cm
        margin_top = 2 * cm
        margin_bottom = 2.5 * cm  # Marge normale pour toutes les pages

        # Créer le canvas
        p = pdf_canvas.Canvas(buffer, pagesize=A4)

        # ==================== EN-TÊTE ====================
        y = height - margin_top

        # Titre FACTURE
        p.setFont("Helvetica-Bold", 18)
        p.drawString(margin_left, y, "FACTURE")

        # Numéro facture à droite
        p.setFont("Helvetica-Bold", 12)
        p.drawRightString(width - margin_right, y, f"N° {self.numero_facture}")

        # ==================== ÉMETTEUR (gauche) ====================
        y = height - 4 * cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin_left, y, self.mandat.client.raison_sociale)

        p.setFont("Helvetica", 9)
        y -= 0.45 * cm
        adresse = self.mandat.client.adresse_siege
        if adresse:
            p.drawString(margin_left, y, f"{adresse.rue} {adresse.numero}")
            y -= 0.4 * cm
            if adresse.complement:
                p.drawString(margin_left, y, adresse.complement)
                y -= 0.4 * cm
            p.drawString(margin_left, y, f"{adresse.npa} {adresse.localite}")
            y -= 0.4 * cm
        if self.mandat.client.tva_number:
            p.drawString(margin_left, y, f"N° TVA: {self.mandat.client.tva_number}")

        # ==================== DESTINATAIRE (droite) ====================
        y_right = height - 4 * cm
        x_right = 11.5 * cm

        p.setFont("Helvetica-Bold", 9)
        p.drawString(x_right, y_right, "Adressée à:")
        y_right -= 0.5 * cm

        p.setFont("Helvetica", 9)
        p.drawString(x_right, y_right, self.client.raison_sociale)
        y_right -= 0.4 * cm

        adresse_client = self.client.adresse_correspondance or self.client.adresse_siege
        if adresse_client:
            p.drawString(x_right, y_right, f"{adresse_client.rue} {adresse_client.numero}")
            y_right -= 0.4 * cm
            if adresse_client.complement:
                p.drawString(x_right, y_right, adresse_client.complement)
                y_right -= 0.4 * cm
            p.drawString(x_right, y_right, f"{adresse_client.npa} {adresse_client.localite}")
            y_right -= 0.4 * cm
        if self.client.tva_number:
            p.drawString(x_right, y_right, f"N° TVA: {self.client.tva_number}")

        # ==================== INFORMATIONS FACTURE ====================
        y = height - 8.5 * cm

        # Bloc info avec fond gris clair
        p.setFillColor(colors.Color(0.95, 0.95, 0.95))
        p.rect(margin_left, y - 1.2 * cm, width - margin_left - margin_right, 1.5 * cm, fill=1, stroke=0)
        p.setFillColor(colors.black)

        y -= 0.1 * cm
        p.setFont("Helvetica", 9)
        p.drawString(margin_left + 0.3 * cm, y, f"Date d'émission: {self.date_emission.strftime('%d.%m.%Y')}")
        p.drawString(7 * cm, y, f"Échéance: {self.date_echeance.strftime('%d.%m.%Y')}")

        if self.date_service_debut and self.date_service_fin:
            p.drawString(12 * cm, y, f"Période: {self.date_service_debut.strftime('%d.%m.%Y')} - {self.date_service_fin.strftime('%d.%m.%Y')}")

        # Introduction
        if self.introduction:
            y -= 1.2 * cm
            p.setFont("Helvetica", 9)
            # Wrapper le texte
            intro_lines = self._wrap_text(self.introduction, 100)
            for line in intro_lines[:3]:
                p.drawString(margin_left, y, line)
                y -= 0.4 * cm

        # ==================== TABLEAU DES LIGNES ====================
        y -= 0.8 * cm

        # Définition des colonnes avec largeurs fixes
        # Description: 8cm, Qté: 2cm, Prix: 2.5cm, TVA: 1.5cm, Total: 2.5cm
        col_widths = [8 * cm, 2 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm]

        # Fonction pour dessiner l'en-tête du tableau
        def dessiner_entete_tableau(canvas, y_pos):
            """Dessine l'en-tête du tableau des lignes"""
            canvas.setFillColor(colors.Color(0.2, 0.2, 0.2))
            canvas.rect(margin_left, y_pos - 0.5 * cm, sum(col_widths), 0.7 * cm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)

            canvas.setFont("Helvetica-Bold", 9)
            x = margin_left + 0.2 * cm
            canvas.drawString(x, y_pos - 0.3 * cm, "Description")
            x += col_widths[0]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "Qté")
            x += col_widths[1]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "Prix unit.")
            x += col_widths[2]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "TVA")
            x += col_widths[3]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "Total HT")

            canvas.setFillColor(colors.black)
            return y_pos - 0.9 * cm

        # Fonction pour créer une nouvelle page (sans en-tête facture, juste suite)
        def nouvelle_page_suite(canvas, current_y):
            """Crée une nouvelle page pour la suite du tableau"""
            canvas.showPage()

            # Petit en-tête de continuation
            canvas.setFont("Helvetica", 8)
            canvas.drawString(margin_left, height - 1.5 * cm, f"Facture {self.numero_facture} - Suite")
            canvas.drawRightString(width - margin_right, height - 1.5 * cm, f"Page {canvas.getPageNumber()}")

            # Ligne de séparation
            canvas.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
            canvas.line(margin_left, height - 1.8 * cm, width - margin_right, height - 1.8 * cm)

            new_y = height - 2.5 * cm
            # Redessiner l'en-tête du tableau
            new_y = dessiner_entete_tableau(canvas, new_y)
            return new_y

        # Dessiner le premier en-tête
        y = dessiner_entete_tableau(p, y)

        # Lignes de facture
        p.setFont("Helvetica", 8)
        row_height_single = 0.4 * cm  # Hauteur pour une ligne
        row_height_double = 0.7 * cm  # Hauteur pour deux lignes de description
        max_desc_chars = 50  # Max caractères par ligne de description
        alternate = False

        lignes_list = list(self.lignes.all().order_by("ordre"))

        for ligne in lignes_list:
            # Calculer si la description nécessite 2 lignes
            desc_lines = []
            desc_text = ligne.description
            if len(desc_text) <= max_desc_chars:
                desc_lines = [desc_text]
                current_row_height = row_height_single
            else:
                # Couper en deux lignes
                # Trouver un bon point de coupure (espace)
                cut_point = desc_text[:max_desc_chars].rfind(' ')
                if cut_point == -1 or cut_point < max_desc_chars // 2:
                    cut_point = max_desc_chars
                line1 = desc_text[:cut_point].strip()
                line2 = desc_text[cut_point:].strip()
                if len(line2) > max_desc_chars:
                    line2 = line2[:max_desc_chars-3] + "..."
                desc_lines = [line1, line2]
                current_row_height = row_height_double

            # Vérifier si on a besoin d'une nouvelle page AVANT de dessiner
            min_y = margin_bottom + 3.5 * cm
            if y - current_row_height < min_y:
                y = nouvelle_page_suite(p, y)
                alternate = False

            # Fond alterné pour lisibilité
            if alternate:
                p.setFillColor(colors.Color(0.96, 0.96, 0.96))
                p.rect(margin_left, y - current_row_height + 0.15 * cm, sum(col_widths), current_row_height, fill=1, stroke=0)
                p.setFillColor(colors.black)
            alternate = not alternate

            # Description (avec retour à la ligne si nécessaire)
            p.setFont("Helvetica", 8)
            x_desc = margin_left + 0.2 * cm
            y_desc = y
            for i, desc_line in enumerate(desc_lines):
                p.drawString(x_desc, y_desc, desc_line)
                if i == 0 and len(desc_lines) > 1:
                    y_desc -= 0.3 * cm

            # Les autres colonnes sont alignées sur la première ligne
            x = margin_left + col_widths[0]

            # Quantité + unité
            qty_text = f"{ligne.quantite:.2f}".rstrip('0').rstrip('.')
            if ligne.unite:
                qty_text += f" {ligne.unite[:3]}"
            p.drawRightString(x - 0.2 * cm, y, qty_text)

            # Prix unitaire
            x += col_widths[1]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.prix_unitaire_ht:.2f}")

            # TVA
            x += col_widths[2]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.taux_tva:.1f}%")

            # Total HT
            x += col_widths[3]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.montant_ht:.2f}")

            y -= current_row_height

        # ==================== TOTAUX ====================
        y -= 0.2 * cm

        # Ligne de séparation
        totaux_x = margin_left + col_widths[0] + col_widths[1]  # Aligner avec Prix unit.
        totaux_width = col_widths[2] + col_widths[3] + col_widths[4]

        p.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        p.line(totaux_x, y, totaux_x + totaux_width, y)
        y -= 0.35 * cm

        p.setFont("Helvetica", 8)
        label_x = totaux_x + 0.2 * cm
        value_x = margin_left + sum(col_widths) - 0.2 * cm

        # Sous-total HT
        p.drawString(label_x, y, "Sous-total HT:")
        p.drawRightString(value_x, y, f"{self.montant_ht:.2f} CHF")
        y -= 0.35 * cm

        # Remise si applicable
        if self.remise_pourcent and self.remise_pourcent > 0:
            p.drawString(label_x, y, f"Remise ({self.remise_pourcent}%):")
            p.drawRightString(value_x, y, f"-{self.remise_montant:.2f} CHF")
            y -= 0.35 * cm

        # TVA
        p.drawString(label_x, y, "TVA:")
        p.drawRightString(value_x, y, f"{self.montant_tva:.2f} CHF")
        y -= 0.35 * cm

        # Ligne avant total
        p.line(totaux_x, y + 0.1 * cm, totaux_x + totaux_width, y + 0.1 * cm)
        y -= 0.25 * cm

        # TOTAL TTC
        p.setFont("Helvetica-Bold", 10)
        p.drawString(label_x, y, "TOTAL TTC:")
        p.drawRightString(value_x, y, f"{self.montant_ttc:.2f} CHF")

        # Montant payé si applicable
        if self.montant_paye and self.montant_paye > 0:
            y -= 0.4 * cm
            p.setFont("Helvetica", 8)
            p.drawString(label_x, y, "Déjà payé:")
            p.drawRightString(value_x, y, f"-{self.montant_paye:.2f} CHF")
            y -= 0.35 * cm
            p.setFont("Helvetica-Bold", 9)
            p.drawString(label_x, y, "Reste à payer:")
            p.drawRightString(value_x, y, f"{self.montant_restant:.2f} CHF")

        # ==================== CONDITIONS & NOTES ====================
        y -= 0.5 * cm

        if self.conditions_paiement:
            p.setFont("Helvetica-Bold", 8)
            p.drawString(margin_left, y, "Conditions de paiement:")
            y -= 0.3 * cm
            p.setFont("Helvetica", 7)
            cond_lines = self._wrap_text(self.conditions_paiement, 100)
            for line in cond_lines[:2]:
                p.drawString(margin_left, y, line)
                y -= 0.28 * cm

        if self.conclusion:
            y -= 0.2 * cm
            p.setFont("Helvetica-Oblique", 7)
            concl_lines = self._wrap_text(self.conclusion, 100)
            for line in concl_lines[:2]:
                p.drawString(margin_left, y, line)
                y -= 0.28 * cm

        # ==================== QR-BILL (si demandé) ====================
        if avec_qr_bill:
            # Le QR-Bill est toujours sur une page dédiée à la fin
            # Cela évite de couper la facture et garantit un bulletin propre
            p.showPage()

            # En-tête minimal sur la page du bulletin de versement
            p.setFont("Helvetica", 9)
            p.drawString(margin_left, height - 1.5 * cm, f"Facture {self.numero_facture}")
            p.setFont("Helvetica-Bold", 11)
            p.drawString(margin_left, height - 2.2 * cm, "Bulletin de versement")

            # Informations de paiement au-dessus du QR-Bill
            p.setFont("Helvetica", 9)
            p.drawString(margin_left, height - 3.2 * cm, f"Montant à payer: CHF {self.montant_restant:.2f}")
            p.drawString(margin_left, height - 3.7 * cm, f"Échéance: {self.date_echeance.strftime('%d.%m.%Y')}")

            self._ajouter_qr_bill(p, width, height)

        p.save()

        pdf_content = buffer.getvalue()
        buffer.close()

        # Nom du fichier
        suffix = "_qr" if avec_qr_bill else ""
        filename = f"facture_{self.numero_facture}{suffix}.pdf"

        from core.pdf import save_pdf_overwrite
        return save_pdf_overwrite(self, 'fichier_pdf', pdf_content, filename)

    def _wrap_text(self, text, max_chars):
        """Découpe un texte en lignes de max_chars caractères"""
        if not text:
            return []
        words = text.replace('\n', ' ').split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def _ajouter_qr_bill(self, canvas, page_width, page_height):
        """Ajoute le QR-Bill suisse en bas de la facture"""
        from reportlab.lib.units import mm
        from reportlab.lib import colors

        # Récupérer l'IBAN depuis CompteBancaire
        iban = None
        if self.qr_iban:
            iban = self.qr_iban
        else:
            from core.models import CompteBancaire
            compte = CompteBancaire.objects.filter(
                mandat=self.mandat, actif=True
            ).first()
            if not compte:
                compte = CompteBancaire.objects.filter(
                    est_compte_principal=True, actif=True
                ).first()
            if compte:
                iban = compte.iban_formate  # IBAN formaté avec espaces

        if not iban:
            iban = "IBAN NON CONFIGURÉ"

        # Dimensions du QR-Bill suisse: 210mm x 105mm (bas de page A4)
        qr_height = 105 * mm
        qr_y = 0  # En bas de page

        # Ligne de découpe perforée
        canvas.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        canvas.setDash(3, 3)
        canvas.line(0, qr_height, page_width, qr_height)
        canvas.setDash()

        # Symbole ciseaux
        canvas.setFont("Helvetica", 10)
        canvas.drawString(5 * mm, qr_height + 2 * mm, "✂")

        # Section Récépissé (gauche: 62mm)
        receipt_width = 62 * mm

        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(5 * mm, qr_height - 10 * mm, "Récépissé")

        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(5 * mm, qr_height - 18 * mm, "Compte / Payable à")

        canvas.setFont("Helvetica", 8)
        y_receipt = qr_height - 23 * mm

        # IBAN
        canvas.drawString(5 * mm, y_receipt, iban)
        y_receipt -= 4 * mm

        # Créancier
        canvas.drawString(5 * mm, y_receipt, self.mandat.client.raison_sociale[:30])
        y_receipt -= 4 * mm
        adresse = self.mandat.client.adresse_siege
        if adresse:
            canvas.drawString(5 * mm, y_receipt, f"{adresse.rue} {adresse.numero}"[:30])
            y_receipt -= 4 * mm
            canvas.drawString(5 * mm, y_receipt, f"{adresse.npa} {adresse.localite}"[:30])

        # Référence
        y_receipt -= 8 * mm
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(5 * mm, y_receipt, "Référence")
        y_receipt -= 4 * mm
        canvas.setFont("Helvetica", 8)
        ref = self.qr_reference or self.numero_facture
        canvas.drawString(5 * mm, y_receipt, ref)

        # Payable par
        y_receipt -= 8 * mm
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(5 * mm, y_receipt, "Payable par")
        y_receipt -= 4 * mm
        canvas.setFont("Helvetica", 8)
        canvas.drawString(5 * mm, y_receipt, self.client.raison_sociale[:30])
        y_receipt -= 4 * mm
        adresse_client = self.client.adresse_correspondance or self.client.adresse_siege
        if adresse_client:
            canvas.drawString(5 * mm, y_receipt, f"{adresse_client.rue} {adresse_client.numero}"[:30])
            y_receipt -= 4 * mm
            canvas.drawString(5 * mm, y_receipt, f"{adresse_client.npa} {adresse_client.localite}"[:30])

        # Montant
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(5 * mm, 15 * mm, "Monnaie")
        canvas.drawString(20 * mm, 15 * mm, "Montant")
        canvas.setFont("Helvetica", 8)
        canvas.drawString(5 * mm, 10 * mm, "CHF")
        canvas.drawString(20 * mm, 10 * mm, f"{self.montant_ttc:.2f}")

        # Point d'acceptation
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawString(35 * mm, 20 * mm, "Point de dépôt")

        # Ligne séparatrice verticale
        canvas.setStrokeColor(colors.black)
        canvas.line(receipt_width, 0, receipt_width, qr_height)

        # Section Bulletin de paiement (droite: 148mm)
        payment_x = receipt_width + 5 * mm

        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(payment_x, qr_height - 10 * mm, "Section paiement")

        # Zone QR Code (46mm x 46mm) - norme Swiss QR Bill
        qr_code_x = payment_x
        qr_code_y = qr_height - 60 * mm
        qr_code_size = 46 * mm

        # Dessiner le QR code PNG si disponible
        qr_drawn = False
        if self.qr_code_image and self.qr_code_image.name:
            try:
                import os
                qr_path = self.qr_code_image.path
                if os.path.exists(qr_path):
                    # Dessiner l'image PNG directement
                    canvas.drawImage(
                        qr_path,
                        qr_code_x,
                        qr_code_y,
                        width=qr_code_size,
                        height=qr_code_size,
                        preserveAspectRatio=True,
                        mask='auto'
                    )
                    qr_drawn = True
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Erreur dessin QR: {e}")

        if not qr_drawn:
            # Fallback: cadre vide avec texte
            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(0.5)
            canvas.rect(qr_code_x, qr_code_y, qr_code_size, qr_code_size, stroke=1, fill=0)
            canvas.setFont("Helvetica", 8)
            canvas.drawCentredString(qr_code_x + qr_code_size/2, qr_code_y + qr_code_size/2, "QR Code")

        # Informations à droite du QR code
        info_x = qr_code_x + qr_code_size + 5 * mm

        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(info_x, qr_height - 18 * mm, "Compte / Payable à")

        canvas.setFont("Helvetica", 10)
        y_info = qr_height - 25 * mm
        canvas.drawString(info_x, y_info, iban)
        y_info -= 5 * mm
        canvas.drawString(info_x, y_info, self.mandat.client.raison_sociale[:40])
        y_info -= 5 * mm
        if adresse:
            canvas.drawString(info_x, y_info, f"{adresse.rue} {adresse.numero}"[:40])
            y_info -= 5 * mm
            canvas.drawString(info_x, y_info, f"{adresse.npa} {adresse.localite}"[:40])

        # Référence
        y_info -= 10 * mm
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(info_x, y_info, "Référence")
        y_info -= 5 * mm
        canvas.setFont("Helvetica", 10)
        canvas.drawString(info_x, y_info, ref)

        # Informations supplémentaires
        y_info -= 10 * mm
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(info_x, y_info, "Informations supplémentaires")
        y_info -= 5 * mm
        canvas.setFont("Helvetica", 9)
        canvas.drawString(info_x, y_info, f"Facture {self.numero_facture}")

        # Payable par
        y_info -= 10 * mm
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(info_x, y_info, "Payable par")
        y_info -= 5 * mm
        canvas.setFont("Helvetica", 10)
        canvas.drawString(info_x, y_info, self.client.raison_sociale[:40])
        y_info -= 5 * mm
        if adresse_client:
            canvas.drawString(info_x, y_info, f"{adresse_client.rue} {adresse_client.numero}"[:40])
            y_info -= 5 * mm
            canvas.drawString(info_x, y_info, f"{adresse_client.npa} {adresse_client.localite}"[:40])

        # Montant en bas
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(payment_x, 20 * mm, "Monnaie")
        canvas.drawString(payment_x + 25 * mm, 20 * mm, "Montant")
        canvas.setFont("Helvetica", 12)
        canvas.drawString(payment_x, 12 * mm, "CHF")
        canvas.drawString(payment_x + 25 * mm, 12 * mm, f"{self.montant_ttc:.2f}")

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
            raise ValueError(_("La facture doit avoir au moins une ligne"))

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

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_("Facture"),
        help_text=_("Facture à laquelle appartient cette ligne")
    )

    # Ordre d'affichage
    ordre = models.IntegerField(
        default=0,
        verbose_name=_("Ordre"),
        help_text=_("Ordre d'affichage de la ligne")
    )

    # Prestation/Produit
    prestation = models.ForeignKey(
        Prestation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Prestation"),
        help_text=_("Prestation associée à cette ligne")
    )

    # Description
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("Description de la ligne")
    )
    description_detaillee = models.TextField(
        blank=True,
        verbose_name=_("Description détaillée"),
        help_text=_("Description détaillée additionnelle")
    )

    # Quantité et prix
    quantite = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
        verbose_name=_("Quantité"),
        help_text=_("Quantité facturée")
    )
    unite = models.CharField(
        max_length=50,
        default='heure',
        verbose_name=_("Unité"),
        help_text=_("Unité de mesure")
    )
    prix_unitaire_ht = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Prix unitaire HT"),
        help_text=_("Prix unitaire hors taxes")
    )

    # Montants
    montant_ht = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant HT"),
        help_text=_("Montant hors taxes de la ligne")
    )

    # TVA
    taux_tva = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8.1,
        verbose_name=_("Taux TVA"),
        help_text=_("Taux de TVA appliqué")
    )
    montant_tva = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant TVA"),
        help_text=_("Montant de TVA calculé")
    )
    montant_ttc = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant TTC"),
        help_text=_("Montant toutes taxes comprises")
    )

    # Remise spécifique ligne
    remise_pourcent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name=_("Remise (%)"),
        help_text=_("Pourcentage de remise sur cette ligne")
    )

    # Lien time tracking
    temps_factures = models.ManyToManyField(
        TimeTracking,
        blank=True,
        related_name='lignes_facture',
        verbose_name=_("Temps facturés"),
        help_text=_("Temps de travail associés à cette ligne")
    )

    class Meta:
        db_table = 'lignes_facture'
        verbose_name = _('Ligne de facture')
        verbose_name_plural = _('Lignes de facture')
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
        ('VIREMENT', _('Virement bancaire')),
        ('QR_BILL', _('QR-Bill')),
        ('CARTE', _('Carte bancaire')),
        ('ESPECES', _('Espèces')),
        ('CHEQUE', _('Chèque')),
        ('COMPENSATION', _('Compensation')),
        ('AUTRE', _('Autre')),
    ]

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name=_("Facture"),
        help_text=_("Facture concernée par ce paiement")
    )

    # Montant
    montant = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name=_("Montant"),
        help_text=_("Montant du paiement")
    )
    devise = models.CharField(
        max_length=3,
        default='CHF',
        verbose_name=_("Devise"),
        help_text=_("Devise du paiement")
    )

    # Date et mode
    date_paiement = models.DateField(
        db_index=True,
        verbose_name=_("Date de paiement"),
        help_text=_("Date du paiement")
    )
    mode_paiement = models.CharField(
        max_length=20,
        choices=MODE_PAIEMENT_CHOICES,
        verbose_name=_("Mode de paiement"),
        help_text=_("Mode de paiement utilisé")
    )

    # Référence
    reference = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_("Référence"),
        help_text=_("Référence bancaire ou numéro de transaction")
    )

    # Validation
    valide = models.BooleanField(
        default=False,
        verbose_name=_("Validé"),
        help_text=_("Indique si le paiement est validé")
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Date de validation"),
        help_text=_("Date et heure de validation")
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Validé par"),
        help_text=_("Utilisateur ayant validé le paiement")
    )

    # Comptabilisation
    ecriture_comptable = models.ForeignKey(
        'comptabilite.EcritureComptable',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='paiements',
        verbose_name=_("Écriture comptable"),
        help_text=_("Écriture comptable associée")
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Notes concernant ce paiement")
    )

    class Meta:
        db_table = 'paiements'
        verbose_name = _('Paiement')
        verbose_name_plural = _('Paiements')
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
        (1, _('1ère relance')),
        (2, _('2ème relance')),
        (3, _('3ème relance')),
        (4, _('Mise en demeure')),
    ]

    facture = models.ForeignKey(
        Facture,
        on_delete=models.CASCADE,
        related_name='relances',
        verbose_name=_("Facture"),
        help_text=_("Facture concernée par cette relance")
    )

    niveau = models.IntegerField(
        choices=NIVEAU_CHOICES,
        verbose_name=_("Niveau"),
        help_text=_("Niveau de la relance (1ère, 2ème, etc.)")
    )
    date_relance = models.DateField(
        auto_now_add=True,
        verbose_name=_("Date de relance"),
        help_text=_("Date de création de la relance")
    )
    date_echeance = models.DateField(
        verbose_name=_("Date d'échéance"),
        help_text=_("Nouvelle date limite de paiement")
    )

    montant_frais = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Frais de relance"),
        help_text=_("Montant des frais de relance")
    )
    montant_interets = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name=_("Intérêts de retard"),
        help_text=_("Montant des intérêts de retard")
    )

    envoyee = models.BooleanField(
        default=False,
        verbose_name=_("Envoyée"),
        help_text=_("Indique si la relance a été envoyée")
    )
    date_envoi = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date d'envoi"),
        help_text=_("Date d'envoi de la relance")
    )

    fichier_pdf = models.FileField(
        upload_to='factures/relances/',
        null=True,
        blank=True,
        verbose_name=_("Fichier PDF"),
        help_text=_("Fichier PDF de la relance")
    )

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes"),
        help_text=_("Notes concernant cette relance")
    )

    class Meta:
        db_table = 'relances'
        verbose_name = _('Relance')
        verbose_name_plural = _('Relances')
        ordering = ['-date_relance']

    def __str__(self):
        return f"Relance niv.{self.niveau} - {self.facture.numero_facture}"

# apps/analytics/models.py
from django.db import models
from core.models import BaseModel, Mandat, User, Client, Periodicite
from decimal import Decimal


class TableauBord(BaseModel):
    """Configuration de tableau de bord"""

    VISIBILITE_CHOICES = [
        ('PRIVE', 'Privé'),
        ('EQUIPE', 'Équipe'),
        ('TOUS', 'Tous'),
    ]

    nom = models.CharField(
        max_length=100,
        verbose_name='Nom',
        help_text='Nom du tableau de bord'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description détaillée du tableau de bord'
    )

    # Propriétaire
    proprietaire = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='tableaux_bord',
        verbose_name='Propriétaire',
        help_text='Utilisateur ayant créé ce tableau de bord'
    )

    # Visibilité
    visibilite = models.CharField(
        max_length=20, choices=VISIBILITE_CHOICES,
        default='PRIVE',
        verbose_name='Visibilité',
        help_text='Niveau de partage du tableau de bord'
    )
    utilisateurs_partage = models.ManyToManyField(
        User, blank=True,
        related_name='tableaux_partages',
        verbose_name='Utilisateurs partagés',
        help_text='Utilisateurs ayant accès à ce tableau de bord'
    )

    # Configuration
    configuration = models.JSONField(
        default=dict,
        verbose_name='Configuration',
        help_text='Configuration des widgets et layout au format JSON'
    )

    # Filtres par défaut
    filtres_defaut = models.JSONField(
        default=dict, blank=True,
        verbose_name='Filtres par défaut',
        help_text='Filtres appliqués par défaut à l\'ouverture'
    )

    # Paramètres
    auto_refresh = models.BooleanField(
        default=False,
        verbose_name='Actualisation automatique',
        help_text='Actualise automatiquement les données'
    )
    refresh_interval = models.IntegerField(
        default=300,
        verbose_name='Intervalle d\'actualisation',
        help_text='Intervalle en secondes entre deux actualisations'
    )

    favori = models.BooleanField(
        default=False,
        verbose_name='Favori',
        help_text='Marquer comme tableau de bord favori'
    )
    ordre = models.IntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position d\'affichage dans la liste'
    )

    class Meta:
        db_table = 'tableaux_bord'
        verbose_name = 'Tableau de bord'
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class Indicateur(BaseModel):
    """Indicateur de performance (KPI)"""

    CATEGORIE_CHOICES = [
        ('FINANCIER', 'Financier'),
        ('OPERATIONNEL', 'Opérationnel'),
        ('CLIENT', 'Client'),
        ('QUALITE', 'Qualité'),
        ('RH', 'Ressources Humaines'),
    ]

    TYPE_CALCUL_CHOICES = [
        ('SOMME', 'Somme'),
        ('MOYENNE', 'Moyenne'),
        ('RATIO', 'Ratio'),
        ('POURCENTAGE', 'Pourcentage'),
        ('COMPTE', 'Comptage'),
        ('CUSTOM', 'Formule personnalisée'),
    ]

    # Conservé pour compatibilité/migration
    PERIODICITE_CHOICES = [
        ('TEMPS_REEL', 'Temps réel'),
        ('JOUR', 'Journalier'),
        ('SEMAINE', 'Hebdomadaire'),
        ('MOIS', 'Mensuel'),
        ('TRIMESTRE', 'Trimestriel'),
        ('ANNEE', 'Annuel'),
    ]

    # Identification
    code = models.CharField(
        max_length=50, unique=True, db_index=True,
        verbose_name='Code',
        help_text='Identifiant unique de l\'indicateur (ex: CA_MENSUEL)'
    )
    nom = models.CharField(
        max_length=100,
        verbose_name='Nom',
        help_text='Libellé de l\'indicateur'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Explication détaillée de l\'indicateur'
    )

    categorie = models.CharField(
        max_length=20, choices=CATEGORIE_CHOICES,
        verbose_name='Catégorie',
        help_text='Domaine de l\'indicateur'
    )

    # Calcul
    type_calcul = models.CharField(
        max_length=20, choices=TYPE_CALCUL_CHOICES,
        verbose_name='Type de calcul',
        help_text='Méthode de calcul de l\'indicateur'
    )
    formule = models.TextField(
        blank=True,
        verbose_name='Formule',
        help_text='Formule personnalisée si type_calcul = CUSTOM'
    )

    # Source de données
    source_table = models.CharField(
        max_length=100, blank=True,
        verbose_name='Table source',
        help_text='Nom de la table Django contenant les données'
    )
    source_champ = models.CharField(
        max_length=100, blank=True,
        verbose_name='Champ source',
        help_text='Nom du champ à agréger'
    )
    filtres_source = models.JSONField(
        default=dict, blank=True,
        verbose_name='Filtres source',
        help_text='Filtres à appliquer sur les données sources'
    )

    # Nouveau: Référence vers Periodicite
    periodicite_ref = models.ForeignKey(
        Periodicite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='indicateurs',
        verbose_name='Périodicité',
        help_text='Fréquence de calcul de l\'indicateur'
    )
    # Ancien champ conservé pour compatibilité/migration
    periodicite = models.CharField(
        max_length=20,
        choices=PERIODICITE_CHOICES,
        default='MOIS',
        verbose_name='Périodicité (ancien)',
        blank=True
    )

    # Objectifs
    objectif_min = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name='Objectif minimum',
        help_text='Seuil minimal acceptable'
    )
    objectif_cible = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name='Objectif cible',
        help_text='Valeur cible à atteindre'
    )
    objectif_max = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name='Objectif maximum',
        help_text='Seuil maximal souhaité'
    )

    # Format affichage
    unite = models.CharField(
        max_length=20, blank=True,
        verbose_name='Unité',
        help_text='Unité d\'affichage (CHF, %, h, etc.)'
    )
    decimales = models.IntegerField(
        default=2,
        verbose_name='Décimales',
        help_text='Nombre de décimales à afficher'
    )

    # Seuils d'alerte
    seuil_alerte_bas = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name='Seuil d\'alerte bas',
        help_text='Valeur en dessous de laquelle une alerte est déclenchée'
    )
    seuil_alerte_haut = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name='Seuil d\'alerte haut',
        help_text='Valeur au-dessus de laquelle une alerte est déclenchée'
    )

    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si l\'indicateur est utilisé'
    )

    class Meta:
        db_table = 'indicateurs'
        verbose_name = 'Indicateur'
        ordering = ['categorie', 'nom']

    def __str__(self):
        return f"{self.code} - {self.nom}"


class ValeurIndicateur(BaseModel):
    """Valeur d'un indicateur à un moment donné"""

    indicateur = models.ForeignKey(
        Indicateur, on_delete=models.CASCADE,
        related_name='valeurs',
        verbose_name='Indicateur',
        help_text='Indicateur mesuré'
    )
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='valeurs_indicateurs',
        verbose_name='Mandat',
        help_text='Mandat concerné (optionnel pour indicateurs globaux)'
    )

    # Période
    date_mesure = models.DateField(
        db_index=True,
        verbose_name='Date de mesure',
        help_text='Date à laquelle la valeur a été mesurée'
    )
    periode_debut = models.DateField(
        null=True, blank=True,
        verbose_name='Début de période',
        help_text='Date de début de la période de calcul'
    )
    periode_fin = models.DateField(
        null=True, blank=True,
        verbose_name='Fin de période',
        help_text='Date de fin de la période de calcul'
    )

    # Valeur
    valeur = models.DecimalField(
        max_digits=15, decimal_places=4,
        verbose_name='Valeur',
        help_text='Valeur mesurée de l\'indicateur'
    )
    valeur_precedente = models.DecimalField(
        max_digits=15, decimal_places=4,
        null=True, blank=True,
        verbose_name='Valeur précédente',
        help_text='Valeur de la période précédente pour comparaison'
    )

    # Variation
    variation_absolue = models.DecimalField(
        max_digits=15, decimal_places=4,
        null=True, blank=True,
        verbose_name='Variation absolue',
        help_text='Différence avec la valeur précédente'
    )
    variation_pourcent = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True,
        verbose_name='Variation en %',
        help_text='Variation en pourcentage par rapport à la période précédente'
    )

    # Statut par rapport aux objectifs
    atteint_objectif = models.BooleanField(
        null=True, blank=True,
        verbose_name='Objectif atteint',
        help_text='Indique si l\'objectif cible est atteint'
    )
    ecart_objectif = models.DecimalField(
        max_digits=15, decimal_places=2,
        null=True, blank=True,
        verbose_name='Écart à l\'objectif',
        help_text='Différence entre la valeur et l\'objectif cible'
    )

    # Métadonnées calcul
    date_calcul = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de calcul',
        help_text='Date et heure du calcul de cette valeur'
    )
    details_calcul = models.JSONField(
        default=dict, blank=True,
        verbose_name='Détails du calcul',
        help_text='Informations techniques sur le calcul effectué'
    )

    class Meta:
        db_table = 'valeurs_indicateur'
        verbose_name = 'Valeur d\'indicateur'
        unique_together = [['indicateur', 'mandat', 'date_mesure']]
        ordering = ['-date_mesure']
        indexes = [
            models.Index(fields=['indicateur', 'date_mesure']),
            models.Index(fields=['mandat', 'date_mesure']),
        ]

    def __str__(self):
        return f"{self.indicateur.code} - {self.date_mesure} - {self.valeur}"

    def calculer_variation(self):
        """Calcule la variation par rapport à la valeur précédente"""
        if self.valeur_precedente:
            self.variation_absolue = self.valeur - self.valeur_precedente
            if self.valeur_precedente != 0:
                self.variation_pourcent = (
                        (self.valeur - self.valeur_precedente) / abs(self.valeur_precedente) * 100
                ).quantize(Decimal('0.01'))

        # Vérification objectif
        if self.indicateur.objectif_cible:
            self.ecart_objectif = self.valeur - self.indicateur.objectif_cible
            self.atteint_objectif = self.valeur >= self.indicateur.objectif_cible

        self.save()


class Rapport(BaseModel):
    """Rapport généré"""

    TYPE_RAPPORT_CHOICES = [
        ('BILAN', 'Bilan'),
        ('COMPTE_RESULTATS', 'Compte de résultats'),
        ('BALANCE', 'Balance'),
        ('TRESORERIE', 'Tableau de trésorerie'),
        ('TVA', 'Rapport TVA'),
        ('SALAIRES', 'Rapport salaires'),
        ('EVOLUTION_CA', 'Évolution CA'),
        ('RENTABILITE', 'Analyse rentabilité'),
        ('CUSTOM', 'Rapport personnalisé'),
    ]

    FORMAT_CHOICES = [
        ('PDF', 'PDF'),
        ('EXCEL', 'Excel'),
        ('CSV', 'CSV'),
        ('HTML', 'HTML'),
    ]

    STATUT_CHOICES = [
        ('EN_COURS', 'En cours de génération'),
        ('TERMINE', 'Terminé'),
        ('ERREUR', 'Erreur'),
    ]

    # Identification
    nom = models.CharField(
        max_length=255,
        verbose_name='Nom',
        help_text='Titre du rapport'
    )
    type_rapport = models.CharField(
        max_length=30, choices=TYPE_RAPPORT_CHOICES,
        verbose_name='Type de rapport',
        help_text='Catégorie du rapport'
    )

    # Rattachement
    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='rapports',
        verbose_name='Mandat',
        help_text='Mandat concerné par ce rapport'
    )

    # Période
    date_debut = models.DateField(
        verbose_name='Date de début',
        help_text='Début de la période couverte par le rapport'
    )
    date_fin = models.DateField(
        verbose_name='Date de fin',
        help_text='Fin de la période couverte par le rapport'
    )

    # Paramètres
    parametres = models.JSONField(
        default=dict,
        verbose_name='Paramètres',
        help_text='Paramètres spécifiques au rapport au format JSON'
    )

    # Génération
    genere_par = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Généré par',
        help_text='Utilisateur ayant demandé la génération'
    )
    date_generation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de génération',
        help_text='Date et heure de création du rapport'
    )

    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='EN_COURS',
        verbose_name='Statut',
        help_text='État de génération du rapport'
    )

    # Fichier
    format_fichier = models.CharField(
        max_length=10, choices=FORMAT_CHOICES,
        verbose_name='Format',
        help_text='Format du fichier généré'
    )
    fichier = models.FileField(
        upload_to='rapports/', null=True, blank=True,
        verbose_name='Fichier',
        help_text='Fichier du rapport généré'
    )
    taille_fichier = models.IntegerField(
        null=True, blank=True,
        verbose_name='Taille du fichier',
        help_text='Taille en octets'
    )

    # Métriques
    duree_generation_secondes = models.IntegerField(
        null=True, blank=True,
        verbose_name='Durée de génération',
        help_text='Temps de génération en secondes'
    )
    nombre_pages = models.IntegerField(
        null=True, blank=True,
        verbose_name='Nombre de pages',
        help_text='Nombre de pages du document'
    )

    # Partage
    envoi_email = models.BooleanField(
        default=False,
        verbose_name='Envoi par email',
        help_text='Envoyer automatiquement par email'
    )
    destinataires = models.JSONField(
        default=list, blank=True,
        verbose_name='Destinataires',
        help_text='Liste des adresses email destinataires'
    )

    # Planification
    est_recurrent = models.BooleanField(
        default=False,
        verbose_name='Récurrent',
        help_text='Indique si ce rapport est généré automatiquement'
    )
    planification = models.ForeignKey(
        'PlanificationRapport',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='rapports_generes',
        verbose_name='Planification',
        help_text='Planification ayant déclenché cette génération'
    )

    class Meta:
        db_table = 'rapports'
        verbose_name = 'Rapport'
        ordering = ['-date_generation']
        indexes = [
            models.Index(fields=['mandat', 'type_rapport']),
            models.Index(fields=['date_generation']),
        ]

    def __str__(self):
        return f"{self.nom} - {self.date_generation.strftime('%Y-%m-%d %H:%M')}"


class PlanificationRapport(BaseModel):
    """Planification de génération automatique de rapports"""

    # Conservé pour compatibilité/migration
    FREQUENCE_CHOICES = [
        ('JOUR', 'Quotidien'),
        ('SEMAINE', 'Hebdomadaire'),
        ('MOIS', 'Mensuel'),
        ('TRIMESTRE', 'Trimestriel'),
        ('ANNEE', 'Annuel'),
    ]

    nom = models.CharField(
        max_length=255,
        verbose_name='Nom',
        help_text='Nom de la planification'
    )
    type_rapport = models.CharField(
        max_length=30,
        verbose_name='Type de rapport',
        help_text='Type de rapport à générer'
    )

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='planifications_rapports',
        verbose_name='Mandat',
        help_text='Mandat concerné par cette planification'
    )

    # Nouveau: Référence vers Periodicite
    frequence_ref = models.ForeignKey(
        Periodicite,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='planifications_rapports',
        verbose_name='Fréquence',
        help_text='Fréquence de génération du rapport'
    )
    # Ancien champ conservé pour compatibilité/migration
    frequence = models.CharField(
        max_length=20,
        choices=FREQUENCE_CHOICES,
        verbose_name='Fréquence (ancien)',
        blank=True
    )
    jour_semaine = models.IntegerField(
        null=True, blank=True,
        verbose_name='Jour de la semaine',
        help_text='1 (lundi) à 7 (dimanche) pour les planifications hebdomadaires'
    )
    jour_mois = models.IntegerField(
        null=True, blank=True,
        verbose_name='Jour du mois',
        help_text='1 à 31 pour les planifications mensuelles'
    )
    heure_generation = models.TimeField(
        default='08:00',
        verbose_name='Heure de génération',
        help_text='Heure à laquelle le rapport est généré'
    )

    # Paramètres
    parametres = models.JSONField(
        default=dict,
        verbose_name='Paramètres',
        help_text='Paramètres de génération du rapport'
    )
    format_fichier = models.CharField(
        max_length=10, default='PDF',
        verbose_name='Format',
        help_text='Format du fichier généré'
    )

    # Destinataires
    destinataires = models.JSONField(
        default=list,
        verbose_name='Destinataires',
        help_text='Liste des adresses email destinataires'
    )

    # Statut
    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si la planification est active'
    )
    date_prochaine_execution = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Prochaine exécution',
        help_text='Date et heure de la prochaine génération'
    )
    date_derniere_execution = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Dernière exécution',
        help_text='Date et heure de la dernière génération'
    )

    class Meta:
        db_table = 'planifications_rapport'
        verbose_name = 'Planification de rapport'
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} - {self.get_frequence_display()}"


class ComparaisonPeriode(BaseModel):
    """Comparaison entre deux périodes"""

    TYPE_COMPARAISON_CHOICES = [
        ('N_VS_N-1', 'Année N vs N-1'),
        ('TRIMESTRE', 'Comparaison trimestrielle'),
        ('MOIS', 'Comparaison mensuelle'),
        ('BUDGET_REEL', 'Budget vs Réalisé'),
        ('CUSTOM', 'Personnalisée'),
    ]

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='comparaisons',
        verbose_name='Mandat',
        help_text='Mandat concerné par cette comparaison'
    )

    type_comparaison = models.CharField(
        max_length=20, choices=TYPE_COMPARAISON_CHOICES,
        verbose_name='Type de comparaison',
        help_text='Mode de comparaison entre les périodes'
    )
    nom = models.CharField(
        max_length=255,
        verbose_name='Nom',
        help_text='Intitulé de la comparaison'
    )

    # Période 1
    periode1_debut = models.DateField(
        verbose_name='Début période 1',
        help_text='Date de début de la première période'
    )
    periode1_fin = models.DateField(
        verbose_name='Fin période 1',
        help_text='Date de fin de la première période'
    )
    libelle_periode1 = models.CharField(
        max_length=100,
        verbose_name='Libellé période 1',
        help_text='Nom affiché pour la première période'
    )

    # Période 2
    periode2_debut = models.DateField(
        verbose_name='Début période 2',
        help_text='Date de début de la deuxième période'
    )
    periode2_fin = models.DateField(
        verbose_name='Fin période 2',
        help_text='Date de fin de la deuxième période'
    )
    libelle_periode2 = models.CharField(
        max_length=100,
        verbose_name='Libellé période 2',
        help_text='Nom affiché pour la deuxième période'
    )

    # Résultats
    resultats = models.JSONField(
        default=dict,
        verbose_name='Résultats',
        help_text='Résultats détaillés de la comparaison au format JSON'
    )

    date_calcul = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de calcul',
        help_text='Date et heure du calcul de la comparaison'
    )

    class Meta:
        db_table = 'comparaisons_periode'
        verbose_name = 'Comparaison de période'
        ordering = ['-date_calcul']

    def __str__(self):
        return f"{self.nom} - {self.libelle_periode1} vs {self.libelle_periode2}"


class AlerteMetrique(BaseModel):
    """Alerte sur dépassement de seuil"""

    NIVEAU_CHOICES = [
        ('INFO', 'Information'),
        ('ATTENTION', 'Attention'),
        ('CRITIQUE', 'Critique'),
    ]

    STATUT_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ACQUITTEE', 'Acquittée'),
        ('RESOLUE', 'Résolue'),
        ('IGNOREE', 'Ignorée'),
    ]

    indicateur = models.ForeignKey(
        Indicateur, on_delete=models.CASCADE,
        related_name='alertes',
        verbose_name='Indicateur',
        help_text='Indicateur ayant déclenché l\'alerte'
    )
    valeur_indicateur = models.ForeignKey(
        ValeurIndicateur, on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Valeur indicateur',
        help_text='Valeur spécifique ayant déclenché l\'alerte'
    )

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Mandat',
        help_text='Mandat concerné par l\'alerte'
    )

    # Alerte
    niveau = models.CharField(
        max_length=20, choices=NIVEAU_CHOICES,
        verbose_name='Niveau',
        help_text='Niveau de criticité de l\'alerte'
    )
    message = models.TextField(
        verbose_name='Message',
        help_text='Description détaillée de l\'alerte'
    )

    valeur_detectee = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Valeur détectée',
        help_text='Valeur ayant déclenché l\'alerte'
    )
    seuil_depasse = models.DecimalField(
        max_digits=15, decimal_places=2,
        verbose_name='Seuil dépassé',
        help_text='Seuil qui a été franchi'
    )

    date_detection = models.DateTimeField(
        auto_now_add=True, db_index=True,
        verbose_name='Date de détection',
        help_text='Date et heure de détection de l\'alerte'
    )

    # Gestion
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES,
        default='ACTIVE', db_index=True,
        verbose_name='Statut',
        help_text='État de traitement de l\'alerte'
    )

    acquittee_par = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alertes_acquittees',
        verbose_name='Acquittée par',
        help_text='Utilisateur ayant pris en charge l\'alerte'
    )
    date_acquittement = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date d\'acquittement',
        help_text='Date et heure de prise en charge'
    )

    commentaire = models.TextField(
        blank=True,
        verbose_name='Commentaire',
        help_text='Notes sur le traitement de l\'alerte'
    )

    # Notification
    notification_envoyee = models.BooleanField(
        default=False,
        verbose_name='Notification envoyée',
        help_text='Indique si une notification a été envoyée'
    )
    destinataires_notifies = models.JSONField(
        default=list, blank=True,
        verbose_name='Destinataires notifiés',
        help_text='Liste des utilisateurs ayant reçu la notification'
    )

    class Meta:
        db_table = 'alertes_metrique'
        verbose_name = 'Alerte métrique'
        ordering = ['-date_detection']
        indexes = [
            models.Index(fields=['statut', 'niveau']),
            models.Index(fields=['mandat', 'statut']),
        ]

    def __str__(self):
        return f"{self.get_niveau_display()} - {self.indicateur.nom} - {self.date_detection.strftime('%Y-%m-%d')}"


class ExportDonnees(BaseModel):
    """Export de données pour analyses externes"""

    TYPE_EXPORT_CHOICES = [
        ('COMPTABILITE', 'Données comptables'),
        ('TVA', 'Données TVA'),
        ('SALAIRES', 'Données salaires'),
        ('FACTURATION', 'Données facturation'),
        ('TOUS', 'Toutes les données'),
    ]

    FORMAT_CHOICES = [
        ('CSV', 'CSV'),
        ('EXCEL', 'Excel'),
        ('JSON', 'JSON'),
        ('XML', 'XML'),
    ]

    nom = models.CharField(
        max_length=255,
        verbose_name='Nom',
        help_text='Nom de l\'export'
    )
    type_export = models.CharField(
        max_length=30, choices=TYPE_EXPORT_CHOICES,
        verbose_name='Type d\'export',
        help_text='Catégorie de données à exporter'
    )

    mandat = models.ForeignKey(
        Mandat, on_delete=models.CASCADE,
        related_name='exports',
        verbose_name='Mandat',
        help_text='Mandat dont les données sont exportées'
    )

    # Période
    date_debut = models.DateField(
        verbose_name='Date de début',
        help_text='Début de la période exportée'
    )
    date_fin = models.DateField(
        verbose_name='Date de fin',
        help_text='Fin de la période exportée'
    )

    # Filtres
    filtres = models.JSONField(
        default=dict, blank=True,
        verbose_name='Filtres',
        help_text='Filtres appliqués aux données exportées'
    )

    # Format
    format_export = models.CharField(
        max_length=10, choices=FORMAT_CHOICES,
        verbose_name='Format d\'export',
        help_text='Format du fichier d\'export'
    )

    # Fichier
    fichier = models.FileField(
        upload_to='exports/', null=True, blank=True,
        verbose_name='Fichier',
        help_text='Fichier d\'export généré'
    )
    taille_fichier = models.IntegerField(
        null=True, blank=True,
        verbose_name='Taille du fichier',
        help_text='Taille en octets'
    )
    nombre_lignes = models.IntegerField(
        null=True, blank=True,
        verbose_name='Nombre de lignes',
        help_text='Nombre de lignes de données exportées'
    )

    # Génération
    demande_par = models.ForeignKey(
        User, on_delete=models.PROTECT,
        verbose_name='Demandé par',
        help_text='Utilisateur ayant demandé l\'export'
    )
    date_demande = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de demande',
        help_text='Date et heure de la demande d\'export'
    )
    date_generation = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date de génération',
        help_text='Date et heure de fin de génération'
    )

    # Sécurité
    hash_fichier = models.CharField(
        max_length=64, blank=True,
        verbose_name='Hash du fichier',
        help_text='Empreinte SHA-256 du fichier pour vérification d\'intégrité'
    )
    date_expiration = models.DateTimeField(
        null=True, blank=True,
        verbose_name='Date d\'expiration',
        help_text='Date d\'expiration du lien de téléchargement'
    )

    class Meta:
        db_table = 'exports_donnees'
        verbose_name = 'Export de données'
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.nom} - {self.date_demande.strftime('%Y-%m-%d %H:%M')}"


class TypeGraphiqueRapport(BaseModel):
    """
    Graphiques prédéfinis et validés statistiquement pour les rapports.

    Chaque graphique est associé à un ou plusieurs types de rapports et
    utilise des données cohérentes (jamais de mélange montants/comptages).
    """

    TYPE_GRAPHIQUE_CHOICES = [
        ('donut', 'Donut / Camembert'),
        ('bar', 'Barres verticales'),
        ('horizontal_bar', 'Barres horizontales'),
        ('line', 'Ligne'),
        ('area', 'Aire'),
        ('stacked_bar', 'Barres empilées'),
    ]

    UNITE_DONNEES_CHOICES = [
        ('CHF', 'Montants (CHF)'),
        ('POURCENTAGE', 'Pourcentages (%)'),
        ('NOMBRE', 'Nombres/Comptages'),
    ]

    # Identification
    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='Code',
        help_text='Code unique ex: BILAN_REPARTITION_ACTIF_PASSIF'
    )
    nom = models.CharField(
        max_length=200,
        verbose_name='Nom',
        help_text='Nom affiché du graphique'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description de ce que montre le graphique'
    )

    # Types de rapports compatibles (stocké en JSON array)
    types_rapport_compatibles = models.JSONField(
        default=list,
        verbose_name='Types de rapports compatibles',
        help_text='Liste des types de rapports compatibles avec ce graphique'
    )

    # Configuration du graphique
    type_graphique = models.CharField(
        max_length=20,
        choices=TYPE_GRAPHIQUE_CHOICES,
        verbose_name='Type de graphique',
        help_text='Mode de représentation visuelle'
    )
    unite_donnees = models.CharField(
        max_length=20,
        choices=UNITE_DONNEES_CHOICES,
        default='CHF',
        verbose_name='Unité des données',
        help_text='Unité des données pour éviter les mélanges'
    )

    # Configuration de la source de données
    config_source = models.JSONField(
        default=dict,
        verbose_name='Configuration source',
        help_text='Configuration pour récupérer les données au format JSON'
    )

    # Options d'affichage
    options_affichage = models.JSONField(
        default=dict,
        verbose_name='Options d\'affichage',
        help_text='Options de style et d\'affichage au format JSON'
    )

    # Ordre d'affichage et activation
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position d\'affichage dans la liste'
    )
    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si ce type de graphique est disponible'
    )

    class Meta:
        db_table = 'types_graphique_rapport'
        verbose_name = 'Type de graphique rapport'
        verbose_name_plural = 'Types de graphiques rapport'
        ordering = ['ordre', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_graphique_display()})"

    def est_compatible(self, type_rapport: str) -> bool:
        """Vérifie si ce graphique est compatible avec un type de rapport."""
        return type_rapport in self.types_rapport_compatibles


class SectionRapport(BaseModel):
    """
    Section d'un rapport personnalisable.

    Permet à l'utilisateur de composer son rapport avec différentes
    sections (texte, graphiques, tableaux) dans l'ordre souhaité.
    """

    TYPE_SECTION_CHOICES = [
        ('titre', 'Titre'),
        ('texte', 'Texte/Paragraphe'),
        ('graphique', 'Graphique'),
        ('tableau', 'Tableau de données'),
        ('kpi', 'Indicateurs clés (KPI)'),
        ('saut_page', 'Saut de page'),
        ('separateur', 'Séparateur horizontal'),
    ]

    # Rattachement au rapport
    rapport = models.ForeignKey(
        Rapport,
        on_delete=models.CASCADE,
        related_name='sections',
        verbose_name='Rapport',
        help_text='Rapport contenant cette section'
    )

    # Position et type
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position de la section dans le rapport'
    )
    type_section = models.CharField(
        max_length=20,
        choices=TYPE_SECTION_CHOICES,
        verbose_name='Type de section',
        help_text='Nature du contenu de la section'
    )

    # Contenu selon le type
    # Pour type='titre' ou 'texte': contenu HTML
    contenu_texte = models.TextField(
        blank=True,
        verbose_name='Contenu texte',
        help_text='Contenu HTML pour les sections titre/texte'
    )

    # Pour type='graphique': référence vers un graphique prédéfini
    type_graphique = models.ForeignKey(
        TypeGraphiqueRapport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections_utilisant',
        verbose_name='Type de graphique',
        help_text='Graphique prédéfini à utiliser'
    )

    # Configuration spécifique (surcharge des options par défaut)
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Configuration',
        help_text='Configuration spécifique à cette section au format JSON'
    )

    # Visibilité
    visible = models.BooleanField(
        default=True,
        verbose_name='Visible',
        help_text='Si désactivé, la section n\'apparaît pas dans le PDF'
    )

    class Meta:
        db_table = 'sections_rapport'
        verbose_name = 'Section de rapport'
        verbose_name_plural = 'Sections de rapport'
        ordering = ['rapport', 'ordre']
        indexes = [
            models.Index(fields=['rapport', 'ordre']),
        ]

    def __str__(self):
        return f"{self.rapport.nom} - Section {self.ordre} ({self.get_type_section_display()})"


class ModeleRapport(BaseModel):
    """
    Modèle de rapport réutilisable avec sections prédéfinies.

    Permet de sauvegarder une configuration de rapport pour la réutiliser.
    """

    nom = models.CharField(
        max_length=200,
        verbose_name='Nom',
        help_text='Nom du modèle de rapport'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Description du modèle et de son utilisation'
    )

    # Type de rapport associé
    type_rapport = models.CharField(
        max_length=30,
        choices=Rapport.TYPE_RAPPORT_CHOICES,
        verbose_name='Type de rapport',
        help_text='Type de rapport généré par ce modèle'
    )

    # Propriétaire (null = modèle système)
    proprietaire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='modeles_rapport',
        verbose_name='Propriétaire',
        help_text='Utilisateur propriétaire (vide pour les modèles système)'
    )

    # Configuration des sections par défaut
    sections_defaut = models.JSONField(
        default=list,
        verbose_name='Sections par défaut',
        help_text='Configuration des sections incluses dans ce modèle'
    )

    # Paramètres par défaut du rapport
    parametres_defaut = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Paramètres par défaut',
        help_text='Paramètres appliqués par défaut aux rapports générés'
    )

    # Activation et ordre
    actif = models.BooleanField(
        default=True,
        verbose_name='Actif',
        help_text='Indique si ce modèle est disponible'
    )
    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordre',
        help_text='Position d\'affichage dans la liste des modèles'
    )

    # Statistiques d'utilisation
    nombre_utilisations = models.PositiveIntegerField(
        default=0,
        verbose_name='Nombre d\'utilisations',
        help_text='Compteur de rapports générés avec ce modèle'
    )

    class Meta:
        db_table = 'modeles_rapport'
        verbose_name = 'Modèle de rapport'
        verbose_name_plural = 'Modèles de rapport'
        ordering = ['type_rapport', 'ordre', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.get_type_rapport_display()})"

    def creer_sections_pour_rapport(self, rapport: Rapport) -> list:
        """
        Crée les sections pour un rapport basé sur ce modèle.

        Returns:
            Liste des SectionRapport créées
        """
        sections_creees = []

        for idx, section_config in enumerate(self.sections_defaut):
            section_data = {
                'rapport': rapport,
                'ordre': idx * 10,  # Espacement pour permettre l'insertion
                'type_section': section_config.get('type', 'texte'),
                'visible': True,
            }

            # Contenu texte
            if section_config.get('contenu'):
                section_data['contenu_texte'] = section_config['contenu']

            # Graphique prédéfini
            if section_config.get('code_graphique'):
                try:
                    type_graph = TypeGraphiqueRapport.objects.get(
                        code=section_config['code_graphique'],
                        actif=True
                    )
                    section_data['type_graphique'] = type_graph
                except TypeGraphiqueRapport.DoesNotExist:
                    pass

            # Configuration additionnelle
            if section_config.get('config'):
                section_data['config'] = section_config['config']

            section = SectionRapport.objects.create(**section_data)
            sections_creees.append(section)

        # Incrémenter le compteur d'utilisation
        self.nombre_utilisations += 1
        self.save(update_fields=['nombre_utilisations'])

        return sections_creees
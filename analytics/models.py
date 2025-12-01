# apps/analytics/models.py
from django.db import models
from core.models import BaseModel, Mandat, User, Client
from decimal import Decimal


class TableauBord(BaseModel):
    """Configuration de tableau de bord"""

    VISIBILITE_CHOICES = [
        ('PRIVE', 'Privé'),
        ('EQUIPE', 'Équipe'),
        ('TOUS', 'Tous'),
    ]

    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Propriétaire
    proprietaire = models.ForeignKey(User, on_delete=models.CASCADE,
                                     related_name='tableaux_bord')

    # Visibilité
    visibilite = models.CharField(max_length=20, choices=VISIBILITE_CHOICES,
                                  default='PRIVE')
    utilisateurs_partage = models.ManyToManyField(User, blank=True,
                                                  related_name='tableaux_partages')

    # Configuration
    configuration = models.JSONField(default=dict, help_text="""
    Configuration des widgets et layout:
    {
        "layout": "grid",
        "widgets": [
            {
                "type": "kpi_card",
                "metric": "ca_mensuel",
                "position": {"x": 0, "y": 0, "w": 3, "h": 2}
            },
            {
                "type": "chart",
                "chart_type": "line",
                "metric": "evolution_ca",
                "position": {"x": 3, "y": 0, "w": 6, "h": 4}
            }
        ]
    }
    """)

    # Filtres par défaut
    filtres_defaut = models.JSONField(default=dict, blank=True)

    # Paramètres
    auto_refresh = models.BooleanField(default=False)
    refresh_interval = models.IntegerField(default=300,
                                           help_text='Intervalle en secondes')

    favori = models.BooleanField(default=False)
    ordre = models.IntegerField(default=0)

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

    PERIODICITE_CHOICES = [
        ('TEMPS_REEL', 'Temps réel'),
        ('JOUR', 'Journalier'),
        ('SEMAINE', 'Hebdomadaire'),
        ('MOIS', 'Mensuel'),
        ('TRIMESTRE', 'Trimestriel'),
        ('ANNEE', 'Annuel'),
    ]

    # Identification
    code = models.CharField(max_length=50, unique=True, db_index=True)
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    categorie = models.CharField(max_length=20, choices=CATEGORIE_CHOICES)

    # Calcul
    type_calcul = models.CharField(max_length=20, choices=TYPE_CALCUL_CHOICES)
    formule = models.TextField(blank=True, help_text="""
    Formule de calcul si type_calcul = CUSTOM
    Ex: (chiffre_affaires - charges) / chiffre_affaires * 100
    """)

    # Source de données
    source_table = models.CharField(max_length=100, blank=True)
    source_champ = models.CharField(max_length=100, blank=True)
    filtres_source = models.JSONField(default=dict, blank=True)

    # Périodicité
    periodicite = models.CharField(max_length=20, choices=PERIODICITE_CHOICES,
                                   default='MOIS')

    # Objectifs
    objectif_min = models.DecimalField(max_digits=15, decimal_places=2,
                                       null=True, blank=True)
    objectif_cible = models.DecimalField(max_digits=15, decimal_places=2,
                                         null=True, blank=True)
    objectif_max = models.DecimalField(max_digits=15, decimal_places=2,
                                       null=True, blank=True)

    # Format affichage
    unite = models.CharField(max_length=20, blank=True,
                             help_text='CHF, %, h, etc.')
    decimales = models.IntegerField(default=2)

    # Seuils d'alerte
    seuil_alerte_bas = models.DecimalField(max_digits=15, decimal_places=2,
                                           null=True, blank=True)
    seuil_alerte_haut = models.DecimalField(max_digits=15, decimal_places=2,
                                            null=True, blank=True)

    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'indicateurs'
        verbose_name = 'Indicateur'
        ordering = ['categorie', 'nom']

    def __str__(self):
        return f"{self.code} - {self.nom}"


class ValeurIndicateur(BaseModel):
    """Valeur d'un indicateur à un moment donné"""

    indicateur = models.ForeignKey(Indicateur, on_delete=models.CASCADE,
                                   related_name='valeurs')
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='valeurs_indicateurs')

    # Période
    date_mesure = models.DateField(db_index=True)
    periode_debut = models.DateField(null=True, blank=True)
    periode_fin = models.DateField(null=True, blank=True)

    # Valeur
    valeur = models.DecimalField(max_digits=15, decimal_places=4)
    valeur_precedente = models.DecimalField(max_digits=15, decimal_places=4,
                                            null=True, blank=True)

    # Variation
    variation_absolue = models.DecimalField(max_digits=15, decimal_places=4,
                                            null=True, blank=True)
    variation_pourcent = models.DecimalField(max_digits=10, decimal_places=2,
                                             null=True, blank=True)

    # Statut par rapport aux objectifs
    atteint_objectif = models.BooleanField(null=True, blank=True)
    ecart_objectif = models.DecimalField(max_digits=15, decimal_places=2,
                                         null=True, blank=True)

    # Métadonnées calcul
    date_calcul = models.DateTimeField(auto_now_add=True)
    details_calcul = models.JSONField(default=dict, blank=True)

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
    nom = models.CharField(max_length=255)
    type_rapport = models.CharField(max_length=30, choices=TYPE_RAPPORT_CHOICES)

    # Rattachement
    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='rapports')

    # Période
    date_debut = models.DateField()
    date_fin = models.DateField()

    # Paramètres
    parametres = models.JSONField(default=dict, help_text="""
    Paramètres spécifiques au rapport:
    {
        "niveau_detail": "compte",
        "inclure_budget": true,
        "comparatif_n-1": true
    }
    """)

    # Génération
    genere_par = models.ForeignKey(User, on_delete=models.PROTECT)
    date_generation = models.DateTimeField(auto_now_add=True)

    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='EN_COURS')

    # Fichier
    format_fichier = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    fichier = models.FileField(upload_to='rapports/', null=True, blank=True)
    taille_fichier = models.IntegerField(null=True, blank=True)

    # Métriques
    duree_generation_secondes = models.IntegerField(null=True, blank=True)
    nombre_pages = models.IntegerField(null=True, blank=True)

    # Partage
    envoi_email = models.BooleanField(default=False)
    destinataires = models.JSONField(default=list, blank=True)

    # Planification
    est_recurrent = models.BooleanField(default=False)
    planification = models.ForeignKey('PlanificationRapport',
                                      on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='rapports_generes')

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

    FREQUENCE_CHOICES = [
        ('JOUR', 'Quotidien'),
        ('SEMAINE', 'Hebdomadaire'),
        ('MOIS', 'Mensuel'),
        ('TRIMESTRE', 'Trimestriel'),
        ('ANNEE', 'Annuel'),
    ]

    nom = models.CharField(max_length=255)
    type_rapport = models.CharField(max_length=30)

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True,
                               related_name='planifications_rapports')

    # Planification
    frequence = models.CharField(max_length=20, choices=FREQUENCE_CHOICES)
    jour_semaine = models.IntegerField(null=True, blank=True,
                                       help_text='1-7 pour lundi-dimanche')
    jour_mois = models.IntegerField(null=True, blank=True,
                                    help_text='1-31')
    heure_generation = models.TimeField(default='08:00')

    # Paramètres
    parametres = models.JSONField(default=dict)
    format_fichier = models.CharField(max_length=10, default='PDF')

    # Destinataires
    destinataires = models.JSONField(default=list, help_text="""
    Liste des destinataires:
    ["email1@example.com", "email2@example.com"]
    """)

    # Statut
    actif = models.BooleanField(default=True)
    date_prochaine_execution = models.DateTimeField(null=True, blank=True)
    date_derniere_execution = models.DateTimeField(null=True, blank=True)

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

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='comparaisons')

    type_comparaison = models.CharField(max_length=20, choices=TYPE_COMPARAISON_CHOICES)
    nom = models.CharField(max_length=255)

    # Période 1
    periode1_debut = models.DateField()
    periode1_fin = models.DateField()
    libelle_periode1 = models.CharField(max_length=100)

    # Période 2
    periode2_debut = models.DateField()
    periode2_fin = models.DateField()
    libelle_periode2 = models.CharField(max_length=100)

    # Résultats
    resultats = models.JSONField(default=dict, help_text="""
    Résultats de la comparaison:
    {
        "chiffre_affaires": {
            "periode1": 1000000,
            "periode2": 1200000,
            "variation": 200000,
            "variation_pct": 20.0
        },
        "charges": {...},
        "resultat": {...}
    }
    """)

    date_calcul = models.DateTimeField(auto_now_add=True)

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

    indicateur = models.ForeignKey(Indicateur, on_delete=models.CASCADE,
                                   related_name='alertes')
    valeur_indicateur = models.ForeignKey(ValeurIndicateur, on_delete=models.CASCADE,
                                          null=True, blank=True)

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               null=True, blank=True)

    # Alerte
    niveau = models.CharField(max_length=20, choices=NIVEAU_CHOICES)
    message = models.TextField()

    valeur_detectee = models.DecimalField(max_digits=15, decimal_places=2)
    seuil_depasse = models.DecimalField(max_digits=15, decimal_places=2)

    date_detection = models.DateTimeField(auto_now_add=True, db_index=True)

    # Gestion
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES,
                              default='ACTIVE', db_index=True)

    acquittee_par = models.ForeignKey(User, on_delete=models.SET_NULL,
                                      null=True, blank=True,
                                      related_name='alertes_acquittees')
    date_acquittement = models.DateTimeField(null=True, blank=True)

    commentaire = models.TextField(blank=True)

    # Notification
    notification_envoyee = models.BooleanField(default=False)
    destinataires_notifies = models.JSONField(default=list, blank=True)

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

    nom = models.CharField(max_length=255)
    type_export = models.CharField(max_length=30, choices=TYPE_EXPORT_CHOICES)

    mandat = models.ForeignKey(Mandat, on_delete=models.CASCADE,
                               related_name='exports')

    # Période
    date_debut = models.DateField()
    date_fin = models.DateField()

    # Filtres
    filtres = models.JSONField(default=dict, blank=True)

    # Format
    format_export = models.CharField(max_length=10, choices=FORMAT_CHOICES)

    # Fichier
    fichier = models.FileField(upload_to='exports/', null=True, blank=True)
    taille_fichier = models.IntegerField(null=True, blank=True)
    nombre_lignes = models.IntegerField(null=True, blank=True)

    # Génération
    demande_par = models.ForeignKey(User, on_delete=models.PROTECT)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_generation = models.DateTimeField(null=True, blank=True)

    # Sécurité
    hash_fichier = models.CharField(max_length=64, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True,
                                           help_text='Date d\'expiration du lien de téléchargement')

    class Meta:
        db_table = 'exports_donnees'
        verbose_name = 'Export de données'
        ordering = ['-date_demande']

    def __str__(self):
        return f"{self.nom} - {self.date_demande.strftime('%Y-%m-%d %H:%M')}"
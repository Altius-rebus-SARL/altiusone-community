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

    # Conservé pour compatibilité/migration
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
        help_text="Code unique ex: BILAN_REPARTITION_ACTIF_PASSIF"
    )
    nom = models.CharField(max_length=200)
    description = models.TextField(
        blank=True,
        help_text="Description de ce que montre le graphique"
    )

    # Types de rapports compatibles (stocké en JSON array)
    types_rapport_compatibles = models.JSONField(
        default=list,
        help_text='Liste des types de rapports: ["BILAN", "COMPTE_RESULTATS"]'
    )

    # Configuration du graphique
    type_graphique = models.CharField(
        max_length=20,
        choices=TYPE_GRAPHIQUE_CHOICES
    )
    unite_donnees = models.CharField(
        max_length=20,
        choices=UNITE_DONNEES_CHOICES,
        default='CHF',
        help_text="Unité des données pour éviter les mélanges"
    )

    # Configuration de la source de données
    config_source = models.JSONField(
        default=dict,
        help_text="""
        Configuration pour récupérer les données:
        {
            "source": "ecritures_comptables",
            "agregation": "sum",
            "champ_valeur": "montant",
            "grouper_par": "classe",
            "filtres": {"classe__in": [1, 2]}
        }
        """
    )

    # Options d'affichage
    options_affichage = models.JSONField(
        default=dict,
        help_text="""
        Options de style et d'affichage:
        {
            "couleurs": ["#4680FF", "#2CA87F"],
            "afficher_legende": true,
            "afficher_valeurs": true,
            "format_valeur": "currency"
        }
        """
    )

    # Ordre d'affichage et activation
    ordre = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)

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
        related_name='sections'
    )

    # Position et type
    ordre = models.PositiveIntegerField(
        default=0,
        help_text="Position de la section dans le rapport"
    )
    type_section = models.CharField(
        max_length=20,
        choices=TYPE_SECTION_CHOICES
    )

    # Contenu selon le type
    # Pour type='titre' ou 'texte': contenu HTML
    contenu_texte = models.TextField(
        blank=True,
        help_text="Contenu HTML pour les sections titre/texte"
    )

    # Pour type='graphique': référence vers un graphique prédéfini
    type_graphique = models.ForeignKey(
        TypeGraphiqueRapport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sections_utilisant',
        help_text="Graphique prédéfini à utiliser"
    )

    # Configuration spécifique (surcharge des options par défaut)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="""
        Configuration spécifique à cette section:
        - Pour graphique: {"titre_personnalise": "Mon titre"}
        - Pour tableau: {"colonnes": ["compte", "libelle", "solde"], "max_lignes": 20}
        - Pour kpi: {"indicateurs": ["ca_total", "marge_brute"]}
        """
    )

    # Visibilité
    visible = models.BooleanField(
        default=True,
        help_text="Si False, la section n'apparaît pas dans le PDF"
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

    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Type de rapport associé
    type_rapport = models.CharField(
        max_length=30,
        choices=Rapport.TYPE_RAPPORT_CHOICES
    )

    # Propriétaire (null = modèle système)
    proprietaire = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='modeles_rapport',
        help_text="Null pour les modèles système"
    )

    # Configuration des sections par défaut
    sections_defaut = models.JSONField(
        default=list,
        help_text="""
        Liste des sections par défaut:
        [
            {"type": "titre", "contenu": "Rapport {type_rapport}"},
            {"type": "texte", "contenu": "<p>Introduction...</p>"},
            {"type": "graphique", "code_graphique": "BILAN_REPARTITION"},
            {"type": "tableau", "config": {"source": "comptes_bilan"}}
        ]
        """
    )

    # Paramètres par défaut du rapport
    parametres_defaut = models.JSONField(
        default=dict,
        blank=True
    )

    # Activation et ordre
    actif = models.BooleanField(default=True)
    ordre = models.PositiveIntegerField(default=0)

    # Statistiques d'utilisation
    nombre_utilisations = models.PositiveIntegerField(default=0)

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
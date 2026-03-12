# Generated migration for CategorieTemps model and TimeTracking type_entree/categorie fields

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("facturation", "0015_devis_and_echeance"),
    ]

    operations = [
        # 1. Create CategorieTemps model
        migrations.CreateModel(
            name="CategorieTemps",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        max_length=30,
                        unique=True,
                        verbose_name="Code",
                        help_text="Code technique unique (ex: FORMATION, VACANCES)",
                    ),
                ),
                (
                    "libelle",
                    models.CharField(
                        max_length=100,
                        verbose_name="Libellé",
                        help_text="Nom affiché (ex: Formation, Vacances)",
                    ),
                ),
                (
                    "description",
                    models.TextField(blank=True, verbose_name="Description"),
                ),
                (
                    "type_categorie",
                    models.CharField(
                        max_length=10,
                        choices=[
                            ("INTERNE", "Temps interne"),
                            ("ABSENCE", "Absence"),
                        ],
                        verbose_name="Type",
                        help_text="Interne = temps de travail non facturable, Absence = jour non travaillé",
                    ),
                ),
                (
                    "icone",
                    models.CharField(
                        blank=True,
                        default="ph-clock",
                        max_length=50,
                        verbose_name="Icône",
                    ),
                ),
                (
                    "couleur",
                    models.CharField(
                        blank=True,
                        default="secondary",
                        max_length=20,
                        verbose_name="Couleur",
                    ),
                ),
                (
                    "decompte_vacances",
                    models.BooleanField(
                        default=False,
                        verbose_name="Décompte vacances",
                        help_text="Si coché, cette catégorie décompte du solde de jours de vacances",
                    ),
                ),
                (
                    "decompte_maladie",
                    models.BooleanField(
                        default=False,
                        verbose_name="Décompte maladie",
                        help_text="Si coché, cette catégorie incrémente le compteur jours maladie",
                    ),
                ),
                (
                    "ordre",
                    models.IntegerField(default=0, verbose_name="Ordre"),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Actif"),
                ),
            ],
            options={
                "db_table": "categories_temps",
                "verbose_name": "Catégorie de temps",
                "verbose_name_plural": "Catégories de temps",
                "ordering": ["type_categorie", "ordre", "libelle"],
            },
        ),
        # 2. Add type_entree field to TimeTracking
        migrations.AddField(
            model_name="timetracking",
            name="type_entree",
            field=models.CharField(
                choices=[
                    ("CLIENT", "Temps client (mandat)"),
                    ("INTERNE", "Temps interne"),
                    ("ABSENCE", "Absence"),
                ],
                db_index=True,
                default="CLIENT",
                help_text="CLIENT=mandat, INTERNE=formation/admin, ABSENCE=vacances/maladie",
                max_length=10,
                verbose_name="Type d'entrée",
            ),
        ),
        # 3. Add categorie FK to TimeTracking
        migrations.AddField(
            model_name="timetracking",
            name="categorie",
            field=models.ForeignKey(
                blank=True,
                help_text="Catégorie de temps interne ou type d'absence",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="temps",
                to="facturation.categorietemps",
                verbose_name="Catégorie",
            ),
        ),
        # 4. Make mandat nullable (for INTERNE/ABSENCE entries)
        migrations.AlterField(
            model_name="timetracking",
            name="mandat",
            field=models.ForeignKey(
                blank=True,
                help_text="Mandat concerné (obligatoire pour type CLIENT)",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="temps_travail",
                to="core.mandat",
                verbose_name="Mandat",
            ),
        ),
        # 5. Make prestation nullable (for INTERNE/ABSENCE entries)
        migrations.AlterField(
            model_name="timetracking",
            name="prestation",
            field=models.ForeignKey(
                blank=True,
                help_text="Type de prestation (obligatoire pour type CLIENT)",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="temps_travail",
                to="facturation.prestation",
                verbose_name="Prestation",
            ),
        ),
        # 6. Add default=0 to taux_horaire and montant_ht
        migrations.AlterField(
            model_name="timetracking",
            name="taux_horaire",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name="Taux horaire",
                help_text="Taux horaire appliqué pour ce travail",
            ),
        ),
        migrations.AlterField(
            model_name="timetracking",
            name="montant_ht",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=10,
                verbose_name="Montant HT",
                help_text="Montant hors taxes calculé",
            ),
        ),
        # 7. Add composite index for type_entree queries
        migrations.AddIndex(
            model_name="timetracking",
            index=models.Index(
                fields=["type_entree", "utilisateur", "date_travail"],
                name="facturation_tt_type_user_date",
            ),
        ),
        # 7. Seed default categories
        migrations.RunPython(
            code=lambda apps, schema_editor: _seed_categories(apps, schema_editor),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def _seed_categories(apps, schema_editor):
    """Insère les catégories par défaut."""
    CategorieTemps = apps.get_model("facturation", "CategorieTemps")

    categories = [
        # Temps interne
        {"code": "REUNION", "libelle": "Réunion interne", "type_categorie": "INTERNE", "icone": "ph-users", "couleur": "info", "ordre": 1},
        {"code": "FORMATION", "libelle": "Formation", "type_categorie": "INTERNE", "icone": "ph-graduation-cap", "couleur": "info", "ordre": 2},
        {"code": "ADMIN", "libelle": "Administration", "type_categorie": "INTERNE", "icone": "ph-gear", "couleur": "secondary", "ordre": 3},
        {"code": "PROSPECTION", "libelle": "Prospection", "type_categorie": "INTERNE", "icone": "ph-magnifying-glass", "couleur": "success", "ordre": 4},
        {"code": "SUPPORT_IT", "libelle": "Support informatique", "type_categorie": "INTERNE", "icone": "ph-desktop", "couleur": "warning", "ordre": 5},
        # Absences
        {"code": "VACANCES", "libelle": "Vacances", "type_categorie": "ABSENCE", "icone": "ph-sun", "couleur": "success", "decompte_vacances": True, "ordre": 1},
        {"code": "MALADIE", "libelle": "Maladie", "type_categorie": "ABSENCE", "icone": "ph-thermometer", "couleur": "danger", "decompte_maladie": True, "ordre": 2},
        {"code": "ACCIDENT", "libelle": "Accident", "type_categorie": "ABSENCE", "icone": "ph-first-aid", "couleur": "danger", "ordre": 3},
        {"code": "CONGE_PERSONNEL", "libelle": "Congé personnel", "type_categorie": "ABSENCE", "icone": "ph-house", "couleur": "warning", "ordre": 4},
        {"code": "SERVICE_MILITAIRE", "libelle": "Service militaire / civil", "type_categorie": "ABSENCE", "icone": "ph-shield", "couleur": "secondary", "ordre": 5},
        {"code": "MATERNITE", "libelle": "Congé maternité / paternité", "type_categorie": "ABSENCE", "icone": "ph-baby", "couleur": "info", "ordre": 6},
        {"code": "JOUR_FERIE", "libelle": "Jour férié", "type_categorie": "ABSENCE", "icone": "ph-calendar-star", "couleur": "primary", "ordre": 7},
    ]

    for cat_data in categories:
        CategorieTemps.objects.create(**cat_data)

# apps/modelforms/management/commands/create_default_templates.py
"""
Commande Django pour créer les templates de formulaires prédéfinis.

Usage:
    python manage.py create_default_templates
"""
from django.core.management.base import BaseCommand
from modelforms.models import FormTemplate


class Command(BaseCommand):
    help = 'Crée les templates de formulaires prédéfinis'

    def handle(self, *args, **options):
        templates = [
            {
                'code': 'CLIENT_RAPIDE',
                'name': 'Création rapide client/prospect',
                'description': 'Formulaire simplifié pour créer un nouveau client ou prospect avec les informations essentielles.',
                'category': FormTemplate.Category.CLIENT,
                'icon': 'ph-user-plus',
                'is_system': True,
                'template_config': {
                    'code': 'CLIENT_RAPIDE',
                    'name': 'Création rapide client',
                    'target_model': 'core.Client',
                    'category': 'CLIENT',
                    'related_models': [
                        {
                            'model': 'core.Adresse',
                            'field': 'adresse_siege',
                            'required': True,
                        }
                    ],
                    'form_schema': {
                        'sections': [
                            {
                                'id': 'identity',
                                'title': 'Identification',
                                'fields': ['raison_sociale', 'nom_commercial', 'forme_juridique', 'ide_number']
                            },
                            {
                                'id': 'address',
                                'title': 'Adresse du siège',
                                'fields': ['adresse_siege.rue', 'adresse_siege.numero', 'adresse_siege.code_postal', 'adresse_siege.localite', 'adresse_siege.canton']
                            },
                            {
                                'id': 'contact',
                                'title': 'Contact',
                                'fields': ['email', 'telephone']
                            },
                        ]
                    },
                    'default_values': {
                        'statut': 'PROSPECT',
                        'responsable': '{{current_user.id}}',
                        'date_creation': '{{today}}',
                        'date_debut_exercice': '{{today}}',
                        'adresse_siege.pays': 'CH',
                    },
                    'validation_rules': [
                        {
                            'type': 'regex',
                            'field': 'ide_number',
                            'pattern': '^CHE-\\d{3}\\.\\d{3}\\.\\d{3}$',
                            'message': 'Format IDE invalide (CHE-XXX.XXX.XXX)',
                        }
                    ],
                    'field_mappings': [
                        {'field_name': 'raison_sociale', 'order': 1, 'section': 'identity', 'required': True},
                        {'field_name': 'nom_commercial', 'order': 2, 'section': 'identity'},
                        {'field_name': 'forme_juridique', 'order': 3, 'section': 'identity', 'widget_type': 'select'},
                        {'field_name': 'ide_number', 'order': 4, 'section': 'identity', 'widget_type': 'ide', 'placeholder': 'CHE-XXX.XXX.XXX'},
                        {'field_name': 'email', 'order': 10, 'section': 'contact', 'widget_type': 'email'},
                        {'field_name': 'telephone', 'order': 11, 'section': 'contact', 'widget_type': 'phone'},
                    ],
                },
            },
            {
                'code': 'NOUVEL_EMPLOYE',
                'name': 'Nouvel employé',
                'description': 'Formulaire complet pour l\'onboarding d\'un nouvel employé avec toutes les informations nécessaires.',
                'category': FormTemplate.Category.EMPLOYE,
                'icon': 'ph-user-circle-plus',
                'is_system': True,
                'template_config': {
                    'code': 'NOUVEL_EMPLOYE',
                    'name': 'Nouvel employé',
                    'target_model': 'salaires.Employe',
                    'category': 'EMPLOYE',
                    'related_models': [
                        {
                            'model': 'core.Adresse',
                            'field': 'adresse',
                            'required': True,
                        }
                    ],
                    'form_schema': {
                        'sections': [
                            {
                                'id': 'identity',
                                'title': 'Identité',
                                'fields': ['nom', 'prenom', 'civilite', 'date_naissance', 'nationalite', 'avs_number']
                            },
                            {
                                'id': 'address',
                                'title': 'Adresse',
                                'fields': ['adresse.rue', 'adresse.numero', 'adresse.code_postal', 'adresse.localite', 'adresse.canton']
                            },
                            {
                                'id': 'contact',
                                'title': 'Contact',
                                'fields': ['email', 'telephone', 'telephone_urgence']
                            },
                            {
                                'id': 'employment',
                                'title': 'Emploi',
                                'fields': ['mandat', 'fonction', 'type_contrat', 'taux_activite', 'date_entree']
                            },
                            {
                                'id': 'salary',
                                'title': 'Salaire',
                                'fields': ['salaire_brut_mensuel', 'mode_paiement']
                            },
                            {
                                'id': 'bank',
                                'title': 'Coordonnées bancaires',
                                'fields': ['iban', 'nom_banque']
                            },
                        ]
                    },
                    'default_values': {
                        'statut': 'ACTIF',
                        'date_entree': '{{today}}',
                        'adresse.pays': 'CH',
                        'nationalite': 'CH',
                    },
                    'require_validation': True,
                    'field_mappings': [
                        {'field_name': 'nom', 'order': 1, 'section': 'identity', 'required': True},
                        {'field_name': 'prenom', 'order': 2, 'section': 'identity', 'required': True},
                        {'field_name': 'avs_number', 'order': 6, 'section': 'identity', 'widget_type': 'avs', 'placeholder': '756.XXXX.XXXX.XX'},
                        {'field_name': 'mandat', 'order': 20, 'section': 'employment', 'widget_type': 'autocomplete'},
                        {'field_name': 'salaire_brut_mensuel', 'order': 30, 'section': 'salary', 'widget_type': 'currency'},
                        {'field_name': 'iban', 'order': 40, 'section': 'bank', 'widget_type': 'iban'},
                    ],
                },
            },
            {
                'code': 'SAISIE_TEMPS',
                'name': 'Saisie de temps',
                'description': 'Formulaire pour enregistrer le temps travaillé sur un mandat.',
                'category': FormTemplate.Category.FACTURATION,
                'icon': 'ph-clock',
                'is_system': True,
                'template_config': {
                    'code': 'SAISIE_TEMPS',
                    'name': 'Saisie de temps',
                    'target_model': 'facturation.TimeTracking',
                    'category': 'FACTURATION',
                    'form_schema': {
                        'sections': [
                            {
                                'id': 'main',
                                'title': 'Saisie',
                                'fields': ['mandat', 'date', 'duree_heures', 'description', 'prestation_type']
                            },
                        ]
                    },
                    'default_values': {
                        'utilisateur': '{{current_user.id}}',
                        'date': '{{today}}',
                    },
                    'field_mappings': [
                        {'field_name': 'mandat', 'order': 1, 'widget_type': 'autocomplete', 'required': True},
                        {'field_name': 'date', 'order': 2, 'widget_type': 'date', 'required': True},
                        {'field_name': 'duree_heures', 'order': 3, 'widget_type': 'decimal', 'required': True, 'label': 'Durée (heures)'},
                        {'field_name': 'description', 'order': 4, 'widget_type': 'textarea'},
                    ],
                },
            },
            {
                'code': 'DEMANDE_VALIDATION',
                'name': 'Demande avec validation',
                'description': 'Template générique pour créer un formulaire de demande nécessitant une validation.',
                'category': FormTemplate.Category.WORKFLOW,
                'icon': 'ph-check-circle',
                'is_system': True,
                'template_config': {
                    'code': 'DEMANDE_VALIDATION',
                    'name': 'Demande avec validation',
                    'target_model': 'core.Tache',
                    'category': 'WORKFLOW',
                    'form_schema': {
                        'sections': [
                            {
                                'id': 'main',
                                'title': 'Demande',
                                'fields': ['titre', 'description', 'priorite', 'date_echeance']
                            },
                        ]
                    },
                    'default_values': {
                        'cree_par': '{{current_user.id}}',
                        'assigne_a': '{{current_user.id}}',
                        'statut': 'A_FAIRE',
                    },
                    'require_validation': True,
                    'post_actions': [
                        {
                            'type': 'notification',
                            'message': 'Nouvelle demande soumise',
                        }
                    ],
                    'field_mappings': [
                        {'field_name': 'titre', 'order': 1, 'required': True},
                        {'field_name': 'description', 'order': 2, 'widget_type': 'textarea'},
                        {'field_name': 'priorite', 'order': 3, 'widget_type': 'select'},
                        {'field_name': 'date_echeance', 'order': 4, 'widget_type': 'date'},
                    ],
                },
            },
        ]

        created_count = 0
        updated_count = 0

        for template_data in templates:
            template, created = FormTemplate.objects.update_or_create(
                code=template_data['code'],
                defaults=template_data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Créé: {template.code}"))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f"  Mis à jour: {template.code}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé: {created_count} créé(s), {updated_count} mis à jour"
        ))

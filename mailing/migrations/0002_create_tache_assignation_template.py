"""Data migration: create TACHE_ASSIGNATION email template."""

import uuid
from django.db import migrations


TEMPLATE_HTML = """
<div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background-color: #4F46E5; padding: 20px; border-radius: 8px 8px 0 0; text-align: center;">
        <h1 style="color: #ffffff; margin: 0; font-size: 22px;">Nouvelle tâche assignée</h1>
    </div>
    <div style="background-color: #f9fafb; padding: 30px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
        <p style="font-size: 16px; color: #374151;">
            Bonjour <strong>{{ destinataire_prenom }}</strong>,
        </p>
        <p style="font-size: 14px; color: #6b7280;">
            <strong>{{ assigne_par }}</strong> vous a assigné une nouvelle tâche :
        </p>

        <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px;">
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; color: #6b7280; width: 140px;">Titre</td>
                <td style="padding: 10px; color: #111827; font-weight: 600;">{{ titre_tache }}</td>
            </tr>
            {% if description_tache %}
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; color: #6b7280;">Description</td>
                <td style="padding: 10px; color: #374151;">{{ description_tache }}</td>
            </tr>
            {% endif %}
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; color: #6b7280;">Priorité</td>
                <td style="padding: 10px; color: #374151;">{{ priorite }}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; color: #6b7280;">Échéance</td>
                <td style="padding: 10px; color: #374151;">{{ date_echeance }}</td>
            </tr>
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; color: #6b7280;">Mandat</td>
                <td style="padding: 10px; color: #374151;">{{ mandat }}</td>
            </tr>
            {% if prestation and prestation != '-' %}
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 10px; color: #6b7280;">Prestation</td>
                <td style="padding: 10px; color: #374151;">{{ prestation }}</td>
            </tr>
            {% endif %}
        </table>

        <div style="text-align: center; margin-top: 30px;">
            <a href="{{ lien_tache }}" style="background-color: #4F46E5; color: #ffffff; padding: 12px 30px; text-decoration: none; border-radius: 6px; font-size: 14px; font-weight: 600;">
                Voir la tâche
            </a>
        </div>

        <p style="font-size: 12px; color: #9ca3af; margin-top: 30px; text-align: center;">
            Cet email a été envoyé automatiquement par AltiusOne.
        </p>
    </div>
</div>
"""

TEMPLATE_TEXT = """Bonjour {{ destinataire_prenom }},

{{ assigne_par }} vous a assigné une nouvelle tâche :

Titre : {{ titre_tache }}
Description : {{ description_tache }}
Priorité : {{ priorite }}
Échéance : {{ date_echeance }}
Mandat : {{ mandat }}
Prestation : {{ prestation }}

Voir la tâche : {{ lien_tache }}

---
Cet email a été envoyé automatiquement par AltiusOne.
"""


def create_template(apps, schema_editor):
    TemplateEmail = apps.get_model('mailing', 'TemplateEmail')
    TemplateEmail.objects.get_or_create(
        code='TACHE_ASSIGNATION',
        defaults={
            'id': uuid.uuid4(),
            'nom': 'Notification assignation tâche',
            'type_template': 'NOTIFICATION',
            'sujet': '[AltiusOne] Nouvelle tâche assignée : {{ titre_tache }}',
            'corps_html': TEMPLATE_HTML.strip(),
            'corps_texte': TEMPLATE_TEXT.strip(),
            'variables_disponibles': [
                'destinataire_prenom',
                'titre_tache',
                'description_tache',
                'priorite',
                'date_echeance',
                'mandat',
                'prestation',
                'assigne_par',
                'lien_tache',
            ],
            'actif': True,
        }
    )


def delete_template(apps, schema_editor):
    TemplateEmail = apps.get_model('mailing', 'TemplateEmail')
    TemplateEmail.objects.filter(code='TACHE_ASSIGNATION').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('mailing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_template, delete_template),
    ]

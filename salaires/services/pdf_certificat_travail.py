"""
Generateur PDF pour CertificatTravail.

Format lettre professionnel style suisse avec:
- En-tete premiere page: logo + adresse employeur (papier a en-tete)
- Titre adapte au type (ATTESTATION / CERTIFICAT INTERMEDIAIRE / CERTIFICAT)
- Corps en paragraphes Platypus justifies
- Sections conditionnelles (taches, formations, evaluation, motif depart)
- Signature avec ligne fine
- Footer brande
"""
from datetime import date
from io import BytesIO

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from .pdf_styles import (
    ALTIUSONE_BORDER,
    ALTIUSONE_DARK,
    ALTIUSONE_GREEN,
    ALTIUSONE_GREY,
    ALTIUSONE_GREY_LIGHT,
    GreenLine,
    build_doc,
    create_salaire_doc,
    get_logo_image,
    get_salaires_styles,
    make_spacer,
)

PAGE_WIDTH, PAGE_HEIGHT = A4


class CertificatTravailPDF:
    """Generateur PDF pour un CertificatTravail."""

    def __init__(self, certificat, style_config=None):
        self.cert = certificat
        self.employe = certificat.employe
        self.client = certificat.employe.mandat.client
        self.adresse_client = self.client.adresse_siege
        self.style_config = style_config
        if style_config:
            from salaires.services.pdf_styles import get_salaires_styles_custom
            self.styles = get_salaires_styles_custom(style_config)
        else:
            self.styles = get_salaires_styles()

    def _get_titre(self):
        """Retourne le titre selon le type de certificat."""
        if self.cert.type_certificat == 'SIMPLE':
            return "ATTESTATION DE TRAVAIL"
        elif self.cert.type_certificat == 'INTERMEDIAIRE':
            return "CERTIFICAT DE TRAVAIL INTERMEDIAIRE"
        return "CERTIFICAT DE TRAVAIL"

    def _build_entete_employeur(self):
        """Construit l'en-tete avec logo et adresse employeur."""
        elements = []

        # Logo + infos employeur cote a cote
        logo = get_logo_image(width=2.5 * cm)

        employer_lines = [f"<b>{self.client.raison_sociale}</b>"]
        if self.adresse_client:
            employer_lines.append(
                f"{self.adresse_client.rue} {self.adresse_client.numero or ''}"
            )
            employer_lines.append(
                f"{self.adresse_client.code_postal} {self.adresse_client.localite}"
            )
        if self.client.ide_number:
            employer_lines.append(f"IDE: {self.client.ide_number}")

        employer_text = "<br/>".join(employer_lines)
        employer_para = Paragraph(employer_text, self.styles['employer_detail'])

        if logo:
            header_data = [[logo, employer_para]]
            header_table = Table(header_data, colWidths=[3 * cm, 12 * cm])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(header_table)
        else:
            elements.append(Paragraph(
                f"<b>{self.client.raison_sociale}</b>",
                self.styles['employer_name']
            ))
            if self.adresse_client:
                elements.append(Paragraph(
                    f"{self.adresse_client.rue} {self.adresse_client.numero or ''}<br/>"
                    f"{self.adresse_client.code_postal} {self.adresse_client.localite}",
                    self.styles['employer_detail']
                ))
            if self.client.ide_number:
                elements.append(Paragraph(
                    f"IDE: {self.client.ide_number}",
                    self.styles['employer_detail']
                ))

        elements.append(make_spacer(5))
        elements.append(GreenLine())
        elements.append(make_spacer(15))

        return elements

    def _build_titre_section(self):
        """Construit le titre du document."""
        title_style = ParagraphStyle(
            'cert_title',
            parent=self.styles['doc_title'],
            fontSize=16,
            textColor=ALTIUSONE_DARK,
            spaceAfter=10 * mm,
        )
        return Paragraph(self._get_titre(), title_style)

    def _build_introduction(self):
        """Construit le paragraphe d'introduction."""
        emp = self.employe
        civilite = "Monsieur" if emp.sexe == 'M' else "Madame"
        nom_complet = f"{civilite} {emp.prenom} {emp.nom}"
        accord_e = "e" if emp.sexe == 'F' else ""

        date_naissance = emp.date_naissance.strftime('%d.%m.%Y') if emp.date_naissance else ''
        nationalite = str(emp.nationalite.name) if emp.nationalite else 'Suisse'

        intro = f"{nom_complet}, n\u00e9{accord_e} le {date_naissance}, de nationalit\u00e9 {nationalite.lower()}, "

        date_debut = self.cert.date_debut_emploi.strftime('%d.%m.%Y')
        if self.cert.date_fin_emploi:
            date_fin = self.cert.date_fin_emploi.strftime('%d.%m.%Y')
            intro += f"a \u00e9t\u00e9 employ\u00e9{accord_e} dans notre entreprise du {date_debut} au {date_fin}"
        else:
            intro += f"est employ\u00e9{accord_e} dans notre entreprise depuis le {date_debut}"

        fonction_text = f" en qualit\u00e9 de {self.cert.fonction_principale}"
        if self.cert.taux_occupation < 100:
            fonction_text += f" \u00e0 {self.cert.taux_occupation}%"
        fonction_text += "."

        return Paragraph(intro + fonction_text, self.styles['body_justify'])

    def _build_taches(self):
        """Construit la section description des taches."""
        if self.cert.type_certificat == 'SIMPLE' or not self.cert.description_taches:
            return []

        elements = []
        bold_style = ParagraphStyle(
            'bold_body',
            parent=self.styles['body_justify'],
            fontName='Helvetica-Bold',
            spaceBefore=4 * mm,
        )
        elements.append(Paragraph("Principales responsabilit\u00e9s:", bold_style))
        elements.append(Paragraph(self.cert.description_taches, self.styles['body_justify']))
        return elements

    def _build_formations(self):
        """Construit la section formations."""
        if self.cert.type_certificat == 'SIMPLE' or not self.cert.formations_suivies:
            return []

        emp = self.employe
        civilite = "Monsieur" if emp.sexe == 'M' else "Madame"

        elements = []
        elements.append(Paragraph(
            f"Durant son emploi, {civilite.lower()} {emp.nom} a suivi les formations suivantes:",
            self.styles['body_justify']
        ))
        elements.append(Paragraph(self.cert.formations_suivies, self.styles['body_justify']))
        return elements

    def _build_evaluation(self):
        """Construit la section evaluation."""
        if self.cert.type_certificat == 'SIMPLE':
            return []

        texte_eval = self.cert.texte_evaluation or self.cert.generer_texte_evaluation()
        if not texte_eval:
            return []

        return [Paragraph(texte_eval, self.styles['body_justify'])]

    def _build_motif_depart(self):
        """Construit la section motif de depart."""
        if not self.cert.date_fin_emploi or not self.cert.motif_depart:
            return []

        emp = self.employe
        civilite = "Monsieur" if emp.sexe == 'M' else "Madame"

        motifs_textes = {
            'DEMISSION': f"{civilite} {emp.nom} nous quitte de sa propre initiative.",
            'FIN_CONTRAT': "Le contrat \u00e0 dur\u00e9e d\u00e9termin\u00e9e est arriv\u00e9 \u00e0 son terme.",
            'LICENCIEMENT_ECO': "La fin des rapports de travail est due \u00e0 des raisons \u00e9conomiques.",
            'RETRAITE': f"{civilite} {emp.nom} prend une retraite bien m\u00e9rit\u00e9e.",
            'ACCORD_MUTUEL': "Les rapports de travail ont pris fin d'un commun accord.",
        }
        motif_text = motifs_textes.get(self.cert.motif_depart, "")
        if not motif_text:
            return []

        return [Paragraph(motif_text, self.styles['body_justify'])]

    def _build_formule_fin(self):
        """Construit la formule de fin."""
        formule = self.cert.formule_fin or self.cert.generer_formule_fin_standard()
        if not formule:
            return []
        return [Paragraph(formule, self.styles['body_justify'])]

    def _build_signature(self):
        """Construit la section date, lieu et signature."""
        elements = []
        elements.append(make_spacer(10))

        # Lieu et date
        lieu = self.adresse_client.localite if self.adresse_client else ""
        date_emission = self.cert.date_emission
        if date_emission:
            date_str = date_emission.strftime('%d %B %Y')
        else:
            date_str = date.today().strftime('%d %B %Y')

        elements.append(Paragraph(
            f"{lieu}, le {date_str}",
            self.styles['body_left']
        ))
        elements.append(make_spacer(15))

        # Ligne de signature fine
        sig_line_style = ParagraphStyle(
            'sig_line',
            parent=self.styles['body_left'],
            fontName='Helvetica',
            fontSize=11,
            textColor=ALTIUSONE_DARK,
        )
        elements.append(Paragraph(
            "_" * 40,
            sig_line_style
        ))
        elements.append(Paragraph(self.client.raison_sociale, self.styles['body_left']))

        if self.cert.emis_par:
            elements.append(Paragraph(
                self.cert.emis_par.get_full_name(),
                self.styles['body_left']
            ))

        return elements

    def generer(self):
        """
        Genere le PDF et retourne les bytes.

        Returns:
            bytes: Contenu du PDF
        """
        buffer = BytesIO()
        doc = create_salaire_doc(
            buffer,
            title="Certificat de travail",
            confidential=True,
            margins={'top': 20 * mm, 'bottom': 20 * mm, 'left': 25 * mm, 'right': 25 * mm},
        )

        elements = []

        # En-tete employeur (premiere page seulement via flowables)
        elements.extend(self._build_entete_employeur())

        # Titre
        elements.append(self._build_titre_section())

        # Introduction
        elements.append(self._build_introduction())

        # Taches
        elements.extend(self._build_taches())

        # Formations
        elements.extend(self._build_formations())

        # Evaluation
        elements.extend(self._build_evaluation())

        # Motif de depart
        elements.extend(self._build_motif_depart())

        # Formule de fin
        elements.extend(self._build_formule_fin())

        # Signature
        elements.extend(self._build_signature())

        build_doc(doc, elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

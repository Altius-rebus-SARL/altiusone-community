"""
Generateur PDF pour FicheSalaire.

Refonte complete du bulletin de salaire mensuel avec:
- Info employeur + employe en table 2 colonnes
- Grille de presence
- Salaire brut avec header vert et rangees alternees
- Cotisations en rouge
- Autres deductions conditionnelles
- Allocations conditionnelles en vert
- Bloc SALAIRE NET pleine largeur fond vert
- Info bancaire et charges patronales
"""
from io import BytesIO

from reportlab.lib.colors import white
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from .pdf_styles import (
    ALTIUSONE_BORDER,
    ALTIUSONE_DARK,
    ALTIUSONE_GREEN,
    ALTIUSONE_GREEN_AMOUNT,
    ALTIUSONE_GREEN_LIGHT,
    ALTIUSONE_GREY,
    ALTIUSONE_GREY_LIGHT,
    ALTIUSONE_RED,
    ALTIUSONE_WHITE,
    GreenLine,
    build_doc,
    create_salaire_doc,
    format_montant_suisse,
    get_alternating_row_colors,
    get_logo_for_client,
    get_logo_image,
    get_salaires_styles,
    make_spacer,
)

PAGE_WIDTH, PAGE_HEIGHT = A4
MOIS_NOMS = [
    '', 'Janvier', 'Fevrier', 'Mars', 'Avril', 'Mai', 'Juin',
    'Juillet', 'Aout', 'Septembre', 'Octobre', 'Novembre', 'Decembre'
]


class FicheSalairePDF:
    """Generateur PDF pour une FicheSalaire mensuelle."""

    def __init__(self, fiche, style_config=None):
        self.fiche = fiche
        self.employe = fiche.employe
        self.client = fiche.employe.mandat.client
        self.adresse = self.client.adresse_siege
        self.style_config = style_config
        if style_config:
            from salaires.services.pdf_styles import get_salaires_styles_custom
            self.styles = get_salaires_styles_custom(style_config)
        else:
            self.styles = get_salaires_styles()

    def _fmt(self, montant):
        return format_montant_suisse(montant) or '-'

    def _build_header(self):
        """Construit l'en-tete: employeur + titre + periode."""
        elements = []

        # Logo + Employeur + Titre + Periode dans une table 3 colonnes
        logo = get_logo_for_client(self.client, width=2 * cm)

        # Colonne gauche: employeur
        employer_lines = [f"<b>{self.client.raison_sociale}</b>"]
        if self.adresse:
            rue = self.adresse.rue.strip()
            if self.adresse.numero and self.adresse.numero not in rue:
                rue = f"{rue} {self.adresse.numero}"
            employer_lines.append(rue)
            employer_lines.append(f"{self.adresse.code_postal} {self.adresse.localite}")
        employer_text = Paragraph("<br/>".join(employer_lines), self.styles['employer_detail'])

        # Colonne centre: titre
        title_style = ParagraphStyle(
            'fiche_title',
            parent=self.styles['doc_title'],
            fontSize=14,
            spaceAfter=0,
            spaceBefore=0,
        )
        title = Paragraph("FICHE DE SALAIRE", title_style)

        # Colonne droite: periode + numero
        periode_str = f"{MOIS_NOMS[self.fiche.mois]} {self.fiche.annee}"
        right_style = ParagraphStyle(
            'right_info',
            parent=self.styles['value'],
            alignment=TA_RIGHT,
            fontSize=10,
        )
        right_style_small = ParagraphStyle(
            'right_info_small',
            parent=self.styles['label'],
            alignment=TA_RIGHT,
        )
        right_content = Paragraph(
            f"<b>{periode_str}</b><br/>N\u00b0 {self.fiche.numero_fiche}",
            right_style,
        )

        # Assemblage
        col_left = employer_text
        if logo:
            logo_table = Table([[logo, employer_text]], colWidths=[2.5 * cm, 6 * cm])
            logo_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            col_left = logo_table

        header_data = [[col_left, title, right_content]]
        header_table = Table(header_data, colWidths=[8.5 * cm, 5 * cm, 4.5 * cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(header_table)
        elements.append(make_spacer(2))
        elements.append(GreenLine())
        elements.append(make_spacer(4))
        return elements

    def _build_info_employe(self):
        """Construit la table d'informations employe."""
        emp = self.employe
        data = [
            ['Nom:', f"{emp.prenom} {emp.nom}", 'Matricule:', emp.matricule],
            ['N\u00b0 AVS:', emp.avs_number or '-', 'Fonction:', (emp.fonction[:25] if emp.fonction else '-')],
            ['Date entree:', emp.date_entree.strftime('%d.%m.%Y'), 'Taux:', f"{emp.taux_occupation}%"],
        ]

        col_widths = [3 * cm, 5.5 * cm, 3 * cm, 5.5 * cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ALTIUSONE_GREY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), ALTIUSONE_GREY),
            ('TEXTCOLOR', (2, 0), (2, -1), ALTIUSONE_GREY),
            ('TEXTCOLOR', (1, 0), (1, -1), ALTIUSONE_DARK),
            ('TEXTCOLOR', (3, 0), (3, -1), ALTIUSONE_DARK),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ]))
        return table

    def _build_presence(self):
        """Construit la grille de presence."""
        f = self.fiche
        data = [
            ['Jours travailles:', f"{f.jours_travailles:.1f}",
             'Heures supp.:', f"{f.heures_supplementaires:.2f}"],
            ['Jours absence:', f"{f.jours_absence:.1f}",
             'Jours vacances:', f"{f.jours_vacances:.1f}"],
            ['Jours maladie:', f"{f.jours_maladie:.1f}", '', ''],
        ]

        col_widths = [3.5 * cm, 3 * cm, 3.5 * cm, 3 * cm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TEXTCOLOR', (0, 0), (0, -1), ALTIUSONE_GREY),
            ('TEXTCOLOR', (2, 0), (2, -1), ALTIUSONE_GREY),
            ('TEXTCOLOR', (1, 0), (1, -1), ALTIUSONE_DARK),
            ('TEXTCOLOR', (3, 0), (3, -1), ALTIUSONE_DARK),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        return table

    def _build_salaire_brut(self):
        """Construit la table salaire brut."""
        f = self.fiche
        lignes = [
            ("Salaire de base", f.salaire_base),
            ("Heures supplementaires", f.heures_supp_montant),
            ("Primes", f.primes),
            ("Indemnites", f.indemnites),
            ("13eme salaire", f.treizieme_mois),
        ]

        header = ['SALAIRE BRUT', 'CHF']
        data = [header]
        for libelle, montant in lignes:
            if montant and montant > 0:
                data.append([libelle, format_montant_suisse(montant)])

        # Total
        data.append(['TOTAL BRUT', format_montant_suisse(f.salaire_brut_total)])

        num_rows = len(data)
        table = Table(data, colWidths=[12 * cm, 5 * cm])

        style_cmds = [
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), ALTIUSONE_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), ALTIUSONE_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            # Data rows
            ('FONTNAME', (0, 1), (0, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), ALTIUSONE_GREEN_LIGHT),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            # Amount alignment
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            # Grid
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        # Alternating rows
        style_cmds += get_alternating_row_colors(num_rows, start_row=1)
        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_cotisations(self):
        """Construit la table des cotisations salariales."""
        f = self.fiche
        cotisations = [
            ("AVS/AI/APG", f.avs_employe),
            ("AC (Assurance chomage)", f.ac_employe),
            ("AC supplementaire", f.ac_supp_employe),
            ("LPP (2eme pilier)", f.lpp_employe),
            ("LAA (Accident)", f.laa_employe),
            ("LAAC (Complementaire)", f.laac_employe),
            ("IJM (Indemnites journalieres)", f.ijm_employe),
        ]

        header = ['COTISATIONS (part employe)', 'CHF']
        data = [header]
        for libelle, montant in cotisations:
            if montant and montant > 0:
                data.append([libelle, f"-{format_montant_suisse(montant)}"])

        # Total
        data.append(['Total cotisations', f"-{format_montant_suisse(f.total_cotisations_employe)}"])

        num_rows = len(data)
        table = Table(data, colWidths=[12 * cm, 5 * cm])

        style_cmds = [
            # Header - rouge pour deductions
            ('BACKGROUND', (0, 0), (-1, 0), ALTIUSONE_RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), ALTIUSONE_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            # Data
            ('FONTNAME', (0, 1), (0, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            ('TEXTCOLOR', (1, 1), (1, -1), ALTIUSONE_RED),
            # Total
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 8),
            # Alignment
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            # Grid
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        style_cmds += get_alternating_row_colors(num_rows, start_row=1)
        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_autres_deductions(self):
        """Construit la table des autres deductions (conditionnelle)."""
        f = self.fiche
        deductions = [
            ("Impot a la source", f.impot_source),
            ("Avance sur salaire", f.avance_salaire),
            ("Saisie sur salaire", f.saisie_salaire),
            ("Autres deductions", f.autres_deductions),
        ]

        has_deductions = any(d[1] and d[1] > 0 for d in deductions)
        if not has_deductions:
            return None

        header = ['AUTRES DEDUCTIONS', 'CHF']
        data = [header]
        for libelle, montant in deductions:
            if montant and montant > 0:
                data.append([libelle, f"-{format_montant_suisse(montant)}"])

        num_rows = len(data)
        table = Table(data, colWidths=[12 * cm, 5 * cm])

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), ALTIUSONE_RED),
            ('TEXTCOLOR', (0, 0), (-1, 0), ALTIUSONE_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (1, 1), (1, -1), ALTIUSONE_RED),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        style_cmds += get_alternating_row_colors(num_rows, start_row=1)
        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_allocations(self):
        """Construit la table des allocations (conditionnelle)."""
        f = self.fiche
        has_alloc = (
            (f.allocations_familiales and f.allocations_familiales > 0)
            or (f.autres_allocations and f.autres_allocations > 0)
        )
        if not has_alloc:
            return None

        header = ['ALLOCATIONS', 'CHF']
        data = [header]
        if f.allocations_familiales and f.allocations_familiales > 0:
            data.append(['Allocations familiales', f"+{format_montant_suisse(f.allocations_familiales)}"])
        if f.autres_allocations and f.autres_allocations > 0:
            data.append(['Autres allocations', f"+{format_montant_suisse(f.autres_allocations)}"])

        num_rows = len(data)
        table = Table(data, colWidths=[12 * cm, 5 * cm])

        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), ALTIUSONE_GREEN_AMOUNT),
            ('TEXTCOLOR', (0, 0), (-1, 0), ALTIUSONE_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TEXTCOLOR', (1, 1), (1, -1), ALTIUSONE_GREEN_AMOUNT),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]
        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_salaire_net(self):
        """Construit le bloc SALAIRE NET pleine largeur."""
        net = format_montant_suisse(self.fiche.salaire_net)
        data = [['SALAIRE NET A PAYER', f'CHF {net}']]
        table = Table(data, colWidths=[12 * cm, 5 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ALTIUSONE_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, -1), ALTIUSONE_WHITE),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (0, 0), 11),
            ('FONTSIZE', (1, 0), (1, 0), 13),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BOX', (0, 0), (-1, -1), 1, ALTIUSONE_GREEN),
        ]))
        return table

    def _build_info_bancaire(self):
        """Construit la section informations bancaires."""
        emp = self.employe
        lines = [f"Versement sur: {emp.iban or 'IBAN non renseigne'}"]
        if emp.banque:
            lines.append(f"Banque: {emp.banque}")
        return Paragraph("<br/>".join(lines), self.styles['label'])

    def _build_charges_patronales(self):
        """Construit la section charges patronales (informative)."""
        f = self.fiche
        charges_style = ParagraphStyle(
            'charges_info',
            parent=self.styles['label'],
            fontSize=7,
            textColor=ALTIUSONE_GREY,
            leading=10,
        )

        charges_title = ParagraphStyle(
            'charges_title',
            parent=self.styles['label'],
            fontName='Helvetica-Bold',
            fontSize=7,
            textColor=ALTIUSONE_GREY,
        )

        elements = []
        elements.append(Paragraph("Charges patronales (pour information)", charges_title))

        line1 = (
            f"AVS: {format_montant_suisse(f.avs_employeur) or '0.00'} | "
            f"AC: {format_montant_suisse(f.ac_employeur) or '0.00'} | "
            f"LPP: {format_montant_suisse(f.lpp_employeur) or '0.00'} | "
            f"LAA: {format_montant_suisse(f.laa_employeur) or '0.00'} | "
            f"AF: {format_montant_suisse(f.af_employeur) or '0.00'}"
        )
        elements.append(Paragraph(line1, charges_style))

        line2 = (
            f"Total charges patronales: CHF {format_montant_suisse(f.total_charges_patronales) or '0.00'} | "
            f"Cout total employeur: CHF {format_montant_suisse(f.cout_total_employeur) or '0.00'}"
        )
        elements.append(Paragraph(line2, charges_style))
        return elements

    def generer(self):
        """
        Genere le PDF et retourne les bytes.

        Returns:
            bytes: Contenu du PDF
        """
        buffer = BytesIO()
        logo_source = self.client.get_logo() if hasattr(self.client, 'get_logo') else None
        doc = create_salaire_doc(
            buffer,
            title="Fiche de salaire",
            confidential=True,
            margins={'top': 18 * mm, 'bottom': 18 * mm, 'left': 15 * mm, 'right': 15 * mm},
            logo_source=logo_source,
        )

        elements = []

        # Header
        elements.extend(self._build_header())

        # Section EMPLOYE
        elements.append(Paragraph("EMPLOYE", self.styles['section_title']))
        elements.append(self._build_info_employe())
        elements.append(make_spacer(4))

        # Section PRESENCE
        elements.append(Paragraph("PRESENCE", self.styles['section_title']))
        elements.append(self._build_presence())
        elements.append(make_spacer(4))

        # Section SALAIRE BRUT
        elements.append(self._build_salaire_brut())
        elements.append(make_spacer(3))

        # Section COTISATIONS
        elements.append(self._build_cotisations())
        elements.append(make_spacer(3))

        # Section AUTRES DEDUCTIONS (conditionnelle)
        autres_ded = self._build_autres_deductions()
        if autres_ded:
            elements.append(autres_ded)
            elements.append(make_spacer(3))

        # Section ALLOCATIONS (conditionnelle)
        allocations = self._build_allocations()
        if allocations:
            elements.append(allocations)
            elements.append(make_spacer(3))

        # SALAIRE NET
        elements.append(self._build_salaire_net())
        elements.append(make_spacer(6))

        # Info bancaire
        elements.append(self._build_info_bancaire())
        elements.append(make_spacer(6))

        # Charges patronales
        elements.extend(self._build_charges_patronales())

        # Footer: date de generation
        elements.append(make_spacer(5))
        date_gen = self.fiche.created_at.strftime('%d.%m.%Y') if self.fiche.created_at else '-'
        elements.append(Paragraph(
            f"Document genere le {date_gen} - {self.client.raison_sociale}",
            self.styles['footer']
        ))

        build_doc(doc, elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

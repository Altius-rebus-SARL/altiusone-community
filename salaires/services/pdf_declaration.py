"""
Generateur PDF pour DeclarationCotisations.

Re-style la declaration existante (deja Platypus) avec le branding Altiusone:
- Header/footer avec logo
- Palette de couleurs brandee
- Headers de table en vert + texte blanc
- Rangees alternees
- Format montant suisse
"""
from io import BytesIO

from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from .pdf_styles import (
    ALTIUSONE_BORDER,
    ALTIUSONE_DARK,
    ALTIUSONE_GREEN,
    ALTIUSONE_GREEN_LIGHT,
    ALTIUSONE_GREY,
    ALTIUSONE_GREY_LIGHT,
    ALTIUSONE_WHITE,
    build_doc,
    create_salaire_doc,
    format_montant_suisse,
    get_alternating_row_colors,
    get_data_table_style,
    get_salaires_styles,
    get_section_table_style,
    get_total_row_style,
    make_spacer,
)


class DeclarationCotisationsPDF:
    """Generateur PDF pour une DeclarationCotisations."""

    def __init__(self, declaration):
        self.declaration = declaration
        self.styles = get_salaires_styles()

    def _fmt(self, montant):
        """Formate un montant avec CHF."""
        formatted = format_montant_suisse(montant)
        return f"{formatted} CHF" if formatted else "-"

    def _build_titre(self):
        """Construit le titre de la declaration."""
        return Paragraph(
            f"DECLARATION DE COTISATIONS - {self.declaration.get_organisme_display()}",
            self.styles['doc_title'],
        )

    def _build_info_employeur(self):
        """Construit la table d'informations employeur."""
        client = self.declaration.mandat.client
        data = [
            ['Employeur:', client.raison_sociale],
            ['N\u00b0 IDE:', client.numero_ide or '-'],
            ['N\u00b0 affilie:', self.declaration.numero_affilie or '-'],
            [
                'Periode:',
                f"{self.declaration.periode_debut.strftime('%d.%m.%Y')} au "
                f"{self.declaration.periode_fin.strftime('%d.%m.%Y')}",
            ],
        ]
        if self.declaration.nom_caisse:
            data.insert(1, ['Caisse:', self.declaration.nom_caisse])

        table = Table(data, colWidths=[40 * mm, 120 * mm])
        table.setStyle(get_section_table_style())
        return table

    def _build_recap(self):
        """Construit la table recapitulative."""
        decl = self.declaration

        header = [['RECAPITULATIF', '']]
        rows = [
            ["Nombre d'employes:", str(decl.nombre_employes)],
            ['Masse salariale brute:', self._fmt(decl.masse_salariale_brute)],
            ['Masse salariale soumise:', self._fmt(decl.masse_salariale_soumise)],
        ]

        # Details selon organisme
        detail_rows = []
        if decl.organisme == 'AVS':
            detail_rows = [
                ['', ''],
                ['Cotisation AVS:', self._fmt(decl.cotisation_avs)],
                ['Cotisation AI:', self._fmt(decl.cotisation_ai)],
                ['Cotisation APG:', self._fmt(decl.cotisation_apg)],
                ['Cotisation AC:', self._fmt(decl.cotisation_ac)],
            ]
            if decl.cotisation_ac_supp > 0:
                detail_rows.append(['Cotisation AC suppl.:', self._fmt(decl.cotisation_ac_supp)])
            if decl.frais_administration > 0:
                detail_rows.append(['Frais administration:', self._fmt(decl.frais_administration)])
        elif decl.organisme == 'LPP':
            detail_rows = [
                ['', ''],
                ['Cotisation employe:', self._fmt(decl.cotisation_lpp_employe)],
                ['Cotisation employeur:', self._fmt(decl.cotisation_lpp_employeur)],
            ]
        elif decl.organisme == 'LAA':
            detail_rows = [
                ['', ''],
                ['LAA professionnelle:', self._fmt(decl.cotisation_laa_pro)],
                ['LAA non professionnelle:', self._fmt(decl.cotisation_laa_non_pro)],
            ]
            if decl.cotisation_laac > 0:
                detail_rows.append(['LAAC complementaire:', self._fmt(decl.cotisation_laac)])
        elif decl.organisme == 'AF':
            detail_rows = [['', ''], ['Cotisation AF:', self._fmt(decl.cotisation_af)]]
        elif decl.organisme == 'IJM':
            detail_rows = [['', ''], ['Cotisation IJM:', self._fmt(decl.cotisation_ijm)]]

        total_rows = [
            ['', ''],
            ['Part employe:', self._fmt(decl.total_cotisations_employe)],
            ['Part employeur:', self._fmt(decl.total_cotisations_employeur)],
            ['TOTAL A PAYER:', self._fmt(decl.montant_cotisations)],
        ]

        all_data = header + rows + detail_rows + total_rows
        num_rows = len(all_data)

        table = Table(all_data, colWidths=[65 * mm, 65 * mm])

        style_cmds = [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), ALTIUSONE_GREEN),
            ('TEXTCOLOR', (0, 0), (-1, 0), ALTIUSONE_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            # Total row (last)
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), ALTIUSONE_GREEN_LIGHT),
            ('FONTSIZE', (0, -1), (-1, -1), 10),
            # General
            ('FONTNAME', (0, 1), (0, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 9),
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ]
        # Alternating rows (skip header and empty rows)
        style_cmds += get_alternating_row_colors(num_rows, start_row=1)

        table.setStyle(TableStyle(style_cmds))
        return table

    def _build_detail_employes(self):
        """Construit la table detail par employe."""
        elements = []
        elements.append(Paragraph('DETAIL PAR EMPLOYE', self.styles['section_title']))
        elements.append(make_spacer(3))

        lignes = self.declaration.lignes.select_related('employe').order_by('employe__nom')
        if not lignes.exists():
            elements.append(Paragraph('Aucun employe dans cette declaration.', self.styles['label']))
            return elements

        header = ['N\u00b0 AVS', 'Nom Prenom', 'Salaire', 'Part emp.', 'Part empr.', 'Total']
        data = [header]
        for ligne in lignes:
            data.append([
                ligne.employe.avs_number or '-',
                f"{ligne.employe.nom} {ligne.employe.prenom}",
                format_montant_suisse(ligne.salaire_brut) or '-',
                format_montant_suisse(ligne.cotisation_employe) or '-',
                format_montant_suisse(ligne.cotisation_employeur) or '-',
                format_montant_suisse(ligne.cotisation_totale) or '-',
            ])

        col_widths = [35 * mm, 50 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm]
        table = Table(data, colWidths=col_widths)
        table.setStyle(get_data_table_style(len(data)))

        # Align amounts to right
        extra = [('ALIGN', (2, 1), (-1, -1), 'RIGHT')]
        table.setStyle(TableStyle(extra))

        elements.append(table)
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
            title=f"Declaration {self.declaration.get_organisme_display()}",
            confidential=True,
        )

        elements = []
        elements.append(self._build_titre())
        elements.append(make_spacer(5))
        elements.append(self._build_info_employeur())
        elements.append(make_spacer(8))
        elements.append(self._build_recap())
        elements.append(make_spacer(8))
        elements.extend(self._build_detail_employes())

        build_doc(doc, elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

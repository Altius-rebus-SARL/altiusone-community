"""
Generateur PDF pour CertificatSalaire - Formulaire 11 officiel suisse.

Conformite AFC preservee: tous les numeros de chiffres, lettres de section,
options de checkboxes et formules restent identiques. Seule la presentation
visuelle change.

Structure:
- Sections A-B: Informations employeur
- Sections C-E: Informations employe, periode
- Sections F-G: Occupation et transport (checkboxes)
- Chiffres 1-7: Revenus
- Chiffre 8: Total brut (surligne)
- Chiffres 9-10: Deductions
- Chiffre 11: Salaire net (surligne + double ligne)
- Chiffres 12-15: Frais professionnels
- Section I: Remarques
- Signature
"""
from datetime import date as date_class
from decimal import Decimal
from io import BytesIO

from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .pdf_styles import (
    ALTIUSONE_BORDER,
    ALTIUSONE_DARK,
    ALTIUSONE_GREEN,
    ALTIUSONE_GREEN_LIGHT,
    ALTIUSONE_GREY,
    ALTIUSONE_GREY_LIGHT,
    ALTIUSONE_WHITE,
    GreenLine,
    build_doc,
    create_salaire_doc,
    format_montant_suisse,
    get_salaires_styles,
    make_spacer,
)

PAGE_WIDTH, PAGE_HEIGHT = A4


# ==============================================================================
# Checkbox flowable
# ==============================================================================

class Checkbox(Flowable):
    """Case a cocher propre: rectangle avec X vert si cochee."""

    def __init__(self, checked=False, size=3.5 * mm, label=""):
        super().__init__()
        self.checked = checked
        self.size = size
        self.label = label

    def wrap(self, avail_width, avail_height):
        self.width = self.size + 2 * mm
        if self.label:
            self.width += len(self.label) * 2 * mm + 5 * mm
        self.height = self.size + 1 * mm
        return self.width, self.height

    def draw(self):
        c = self.canv
        s = self.size
        # Rectangle
        c.setStrokeColor(ALTIUSONE_DARK)
        c.setLineWidth(0.5)
        c.rect(0, 0, s, s, fill=0)
        # X en vert si coche
        if self.checked:
            c.setStrokeColor(ALTIUSONE_GREEN)
            c.setLineWidth(1.2)
            c.line(0.5 * mm, 0.5 * mm, s - 0.5 * mm, s - 0.5 * mm)
            c.line(0.5 * mm, s - 0.5 * mm, s - 0.5 * mm, 0.5 * mm)
        # Label
        if self.label:
            c.setFont("Helvetica", 7)
            c.setFillColor(ALTIUSONE_DARK)
            c.drawString(s + 1.5 * mm, 0.5 * mm, self.label)


# ==============================================================================
# Service
# ==============================================================================

class CertificatSalairePDF:
    """Generateur PDF pour le Formulaire 11 (certificat de salaire)."""

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

    def _fmt(self, val):
        """Formate un montant suisse, vide si 0 ou None."""
        return format_montant_suisse(val)

    def _build_titre(self):
        """Titre: CERTIFICAT DE SALAIRE + sous-titre + annee."""
        elements = []

        # Table: titre centre + annee a droite
        title_style = ParagraphStyle(
            'f11_title',
            parent=self.styles['doc_title'],
            fontSize=14,
            spaceAfter=0,
            spaceBefore=0,
        )
        subtitle_style = ParagraphStyle(
            'f11_subtitle',
            parent=self.styles['doc_subtitle'],
            fontSize=8,
            spaceAfter=0,
        )
        year_style = ParagraphStyle(
            'f11_year',
            parent=self.styles['value'],
            fontSize=14,
            alignment=TA_RIGHT,
        )

        title = Paragraph("CERTIFICAT DE SALAIRE", title_style)
        subtitle = Paragraph(
            "Attestation de rentes, pensions et prestations en capital",
            subtitle_style,
        )
        year = Paragraph(str(self.cert.annee), year_style)

        # Combine titre + sous-titre
        title_block = Table(
            [[title], [subtitle]],
            colWidths=[12 * cm],
        )
        title_block.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))

        header_table = Table(
            [[title_block, year]],
            colWidths=[14 * cm, 3.5 * cm],
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))

        elements.append(header_table)
        elements.append(make_spacer(4))
        return elements

    def _build_section_ab(self):
        """Sections A-B: Informations employeur."""
        client = self.client
        adr = self.adresse_client

        sect_label = ParagraphStyle(
            'sect_label', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=8, textColor=ALTIUSONE_GREEN,
        )
        sect_value = ParagraphStyle(
            'sect_value', parent=self.styles['label'],
            fontSize=8,
        )

        data = []
        # A. Employeur
        a_text = client.raison_sociale
        if adr:
            rue = adr.rue.strip()
            if adr.numero and adr.numero not in rue:
                rue = f"{rue} {adr.numero}"
            a_text += f"<br/>{rue}<br/>{adr.code_postal} {adr.localite}"
        data.append([
            Paragraph("A.", sect_label),
            Paragraph("Employeur / Caisse AVS:", sect_label),
            Paragraph(a_text, sect_value),
        ])

        # B. IDE + AVS employeur
        ide = client.ide_number or ''
        avs_empl = getattr(client, 'numero_ahv_employeur', '') or ''
        b_text = f"N\u00b0 IDE: {ide}<br/>N\u00b0 AVS employeur: {avs_empl}"
        data.append([
            Paragraph("B.", sect_label),
            Paragraph("Identification:", sect_label),
            Paragraph(b_text, sect_value),
        ])

        table = Table(data, colWidths=[8 * mm, 35 * mm, 120 * mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ALTIUSONE_GREY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        return table

    def _build_section_cde(self):
        """Sections C-E: Employe, periode, adresse."""
        emp = self.employe
        cert = self.cert

        sect_label = ParagraphStyle(
            'sect_label_cde', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=8, textColor=ALTIUSONE_GREEN,
        )
        sect_value = ParagraphStyle(
            'sect_value_cde', parent=self.styles['label'],
            fontSize=8,
        )

        # C. AVS + Periode
        date_debut = cert.date_debut.strftime('%d.%m.%Y') if cert.date_debut else ''
        date_fin = cert.date_fin.strftime('%d.%m.%Y') if cert.date_fin else ''
        c_text = f"N\u00b0 AVS: {emp.avs_number or '-'}    du {date_debut}  au {date_fin}"

        # D. Nom prenom
        d_text = f"{emp.nom} {emp.prenom}"

        # E. Adresse
        adresse_emp = emp.adresse
        e_text = ""
        if adresse_emp:
            rue_emp = adresse_emp.rue.strip()
            if adresse_emp.numero and adresse_emp.numero not in rue_emp:
                rue_emp = f"{rue_emp} {adresse_emp.numero}"
            e_text = f"{rue_emp}, {adresse_emp.code_postal} {adresse_emp.localite}"

        data = [
            [Paragraph("C.", sect_label), Paragraph("AVS / Periode:", sect_label), Paragraph(c_text, sect_value)],
            [Paragraph("D.", sect_label), Paragraph("Nom, prenom:", sect_label), Paragraph(d_text, sect_value)],
            [Paragraph("E.", sect_label), Paragraph("Adresse:", sect_label), Paragraph(e_text, sect_value)],
        ]

        table = Table(data, colWidths=[8 * mm, 30 * mm, 125 * mm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), ALTIUSONE_GREY_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        return table

    def _build_section_fg(self):
        """Sections F-G: Occupation et transport avec checkboxes."""
        cert = self.cert

        sect_label = ParagraphStyle(
            'sect_label_fg', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=8, textColor=ALTIUSONE_GREEN,
        )

        # F. Activite - checkboxes
        cb_plein = Checkbox(cert.type_occupation == 'PLEIN_TEMPS', label="Plein temps")
        cb_partiel = Checkbox(cert.type_occupation == 'TEMPS_PARTIEL', label="Temps partiel")
        cb_horaire = Checkbox(cert.type_occupation == 'HORAIRE', label="A l'heure")

        taux_style = ParagraphStyle(
            'taux_style', parent=self.styles['value'],
            fontSize=8, alignment=TA_RIGHT,
        )
        taux = Paragraph(f"Taux: {cert.taux_occupation}%", taux_style)

        f_data = [[
            Paragraph("F.", sect_label),
            Paragraph("Activite:", sect_label),
            cb_plein, cb_partiel, cb_horaire, taux,
        ]]
        f_table = Table(f_data, colWidths=[8 * mm, 20 * mm, 30 * mm, 30 * mm, 30 * mm, 45 * mm])
        f_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))

        # G. Transport - checkboxes
        cb_public = Checkbox(cert.transport_public_disponible, label="Transport public disponible")
        cb_gratuit = Checkbox(cert.transport_gratuit_fourni, label="Transport gratuit fourni")

        g_data = [[
            Paragraph("G.", sect_label),
            Paragraph("Transport:", sect_label),
            cb_public, cb_gratuit,
        ]]
        g_table = Table(g_data, colWidths=[8 * mm, 22 * mm, 65 * mm, 65 * mm])
        g_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))

        return [f_table, g_table]

    def _build_chiffres(self):
        """Construit la table des chiffres 1-15."""
        cert = self.cert
        elements = []

        # Style pour les montants
        amt_style = ParagraphStyle(
            'amt', parent=self.styles['label'],
            fontSize=8, alignment=TA_RIGHT,
        )
        num_style = ParagraphStyle(
            'num', parent=self.styles['value'],
            fontSize=8,
        )
        lib_style = ParagraphStyle(
            'lib', parent=self.styles['label'],
            fontSize=8,
        )
        section_style = ParagraphStyle(
            'section_hdr', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=9, textColor=ALTIUSONE_GREEN,
        )
        total_num = ParagraphStyle(
            'total_num', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=9,
        )
        total_lib = ParagraphStyle(
            'total_lib', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=9,
        )
        total_amt = ParagraphStyle(
            'total_amt', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=9, alignment=TA_RIGHT,
        )

        def _row(numero, libelle, montant, indent=False, is_total=False):
            ns = total_num if is_total else num_style
            ls = total_lib if is_total else lib_style
            ams = total_amt if is_total else amt_style
            if indent:
                libelle = f"&nbsp;&nbsp;&nbsp;&nbsp;{libelle}"
            n = Paragraph(numero, ns)
            l = Paragraph(libelle, ls)
            m_str = self._fmt(montant) if montant is not None else ""
            m = Paragraph(m_str, ams)
            return [n, l, m]

        def _section_row(text):
            return [
                Paragraph("", section_style),
                Paragraph(text, section_style),
                Paragraph("CHF", section_style),
            ]

        # Build all rows
        data = []
        row_types = []  # Track row types for styling

        # REVENUS header
        data.append(_section_row("REVENUS"))
        row_types.append('section')

        # Chiffre 1
        data.append(_row("1.", "Salaire (y.c. allocations, commissions, primes)", cert.chiffre_1_salaire))
        row_types.append('normal')

        # Chiffre 2
        data.append(_row("2.", "Prestations en nature", None))
        row_types.append('normal')

        # 2.1
        total_21 = cert.chiffre_2_1_repas or Decimal('0')
        if cert.repas_midi_gratuit or cert.repas_soir_gratuit or total_21 > 0:
            data.append(_row("2.1", "Repas / Logement", total_21, indent=True))
            row_types.append('normal')

        # 2.2
        if cert.voiture_disponible or (cert.chiffre_2_2_voiture and cert.chiffre_2_2_voiture > 0):
            data.append(_row("2.2", "Part privee vehicule de service", cert.chiffre_2_2_voiture, indent=True))
            row_types.append('normal')

        # 2.3
        if cert.chiffre_2_3_autres and cert.chiffre_2_3_autres > 0:
            data.append(_row("2.3", "Autres prestations en nature", cert.chiffre_2_3_autres, indent=True))
            row_types.append('normal')

        # Chiffre 3
        data.append(_row("3.", "Prestations irregulieres (13eme, bonus, gratifications)", cert.chiffre_3_irregulier))
        row_types.append('normal')

        # Chiffre 4
        if cert.chiffre_4_capital and cert.chiffre_4_capital > 0:
            data.append(_row("4.", "Prestations en capital", cert.chiffre_4_capital))
            row_types.append('normal')

        # Chiffre 5
        if cert.chiffre_5_participations and cert.chiffre_5_participations > 0:
            data.append(_row("5.", "Droits de participation (actions, options)", cert.chiffre_5_participations))
            row_types.append('normal')

        # Chiffre 6
        if cert.chiffre_6_ca and cert.chiffre_6_ca > 0:
            data.append(_row("6.", "Indemnites conseil d'administration", cert.chiffre_6_ca))
            row_types.append('normal')

        # Chiffre 7
        if cert.chiffre_7_autres and cert.chiffre_7_autres > 0:
            data.append(_row("7.", "Autres prestations", cert.chiffre_7_autres))
            row_types.append('normal')

        # CHIFFRE 8: TOTAL BRUT
        data.append(_row("8.", "Salaire brut total (somme des chiffres 1 a 7)", cert.chiffre_8_total_brut, is_total=True))
        row_types.append('total_brut')

        # DEDUCTIONS header
        data.append(_section_row("DEDUCTIONS"))
        row_types.append('section')

        # Chiffre 9
        data.append(_row("9.", "Cotisations AVS/AI/APG/AC/AANP", cert.chiffre_9_cotisations))
        row_types.append('normal')

        # Chiffre 10
        data.append(_row("10.", "Prevoyance professionnelle", None))
        row_types.append('normal')
        data.append(_row("10.1", "Cotisations ordinaires", cert.chiffre_10_1_lpp_ordinaire, indent=True))
        row_types.append('normal')
        if cert.chiffre_10_2_lpp_rachat and cert.chiffre_10_2_lpp_rachat > 0:
            data.append(_row("10.2", "Rachats d'annees", cert.chiffre_10_2_lpp_rachat, indent=True))
            row_types.append('normal')

        # CHIFFRE 11: NET
        data.append(_row("11.", "Salaire net (chiffre 8 moins chiffres 9 et 10)", cert.chiffre_11_net, is_total=True))
        row_types.append('total_net')

        # FRAIS EFFECTIFS header
        data.append(_section_row("FRAIS EFFECTIFS"))
        row_types.append('section')

        # Chiffre 12
        if cert.chiffre_12_transport and cert.chiffre_12_transport > 0:
            data.append(_row("12.", "Frais de deplacement (trajet domicile-travail)", cert.chiffre_12_transport))
            row_types.append('normal')

        # Chiffre 13
        has_13 = any([
            cert.chiffre_13_1_1_repas_effectif,
            cert.chiffre_13_1_2_repas_forfait,
            cert.chiffre_13_2_nuitees,
            cert.chiffre_13_3_repas_externes,
        ])
        if has_13:
            data.append(_row("13.", "Frais de repas et nuitees", None))
            row_types.append('normal')
            if cert.chiffre_13_1_1_repas_effectif and cert.chiffre_13_1_1_repas_effectif > 0:
                data.append(_row("13.1.1", "Repas effectifs", cert.chiffre_13_1_1_repas_effectif, indent=True))
                row_types.append('normal')
            if cert.chiffre_13_1_2_repas_forfait and cert.chiffre_13_1_2_repas_forfait > 0:
                data.append(_row("13.1.2", "Repas forfaitaires", cert.chiffre_13_1_2_repas_forfait, indent=True))
                row_types.append('normal')
            if cert.chiffre_13_2_nuitees and cert.chiffre_13_2_nuitees > 0:
                data.append(_row("13.2", "Nuitees", cert.chiffre_13_2_nuitees, indent=True))
                row_types.append('normal')
            if cert.chiffre_13_3_repas_externes and cert.chiffre_13_3_repas_externes > 0:
                data.append(_row("13.3", "Repas externes", cert.chiffre_13_3_repas_externes, indent=True))
                row_types.append('normal')

        # Chiffre 14
        if cert.chiffre_14_autres_frais and cert.chiffre_14_autres_frais > 0:
            data.append(_row("14.", "Autres frais professionnels", cert.chiffre_14_autres_frais))
            row_types.append('normal')

        # Chiffre 15
        jours_str = str(cert.chiffre_15_jours_transport) if cert.chiffre_15_jours_transport else ""
        data.append([
            Paragraph("15.", num_style),
            Paragraph("Nombre de jours avec deplacement domicile-travail:", lib_style),
            Paragraph(jours_str, amt_style),
        ])
        row_types.append('normal')

        # Build table
        num_rows = len(data)
        table = Table(data, colWidths=[12 * mm, 120 * mm, 35 * mm])

        style_cmds = [
            ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]

        # Apply styles based on row type
        for i, rtype in enumerate(row_types):
            if rtype == 'section':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), ALTIUSONE_GREEN))
                style_cmds.append(('TEXTCOLOR', (0, i), (-1, i), ALTIUSONE_WHITE))
            elif rtype == 'total_brut':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), ALTIUSONE_GREEN_LIGHT))
                style_cmds.append(('LINEABOVE', (0, i), (-1, i), 1, ALTIUSONE_GREEN))
            elif rtype == 'total_net':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), ALTIUSONE_GREEN_LIGHT))
                style_cmds.append(('LINEABOVE', (0, i), (-1, i), 1, ALTIUSONE_GREEN))
                style_cmds.append(('LINEBELOW', (0, i), (-1, i), 2, ALTIUSONE_GREEN))
            elif i % 2 == 0 and rtype == 'normal':
                style_cmds.append(('BACKGROUND', (0, i), (-1, i), ALTIUSONE_GREY_LIGHT))

        table.setStyle(TableStyle(style_cmds))
        elements.append(table)
        return elements

    def _build_remarques(self):
        """Section I: Remarques."""
        elements = []

        sect_label = ParagraphStyle(
            'remarques_label', parent=self.styles['value'],
            fontName='Helvetica-Bold', fontSize=8, textColor=ALTIUSONE_GREEN,
        )
        remark_style = ParagraphStyle(
            'remark_text', parent=self.styles['label'],
            fontSize=7, leading=9,
        )

        elements.append(GreenLine(thickness=0.5))
        elements.append(make_spacer(2))
        elements.append(Paragraph("I. Remarques:", sect_label))

        if self.cert.remarques:
            # Limiter a 3 lignes, 90 car max
            lignes = self.cert.remarques.split('\n')[:3]
            for ligne in lignes:
                elements.append(Paragraph(ligne[:90], remark_style))

        return elements

    def _build_signature(self):
        """Section signature."""
        cert = self.cert
        elements = []

        elements.append(make_spacer(3))
        elements.append(GreenLine(thickness=0.5))
        elements.append(make_spacer(3))

        sig_style = ParagraphStyle(
            'sig', parent=self.styles['label'],
            fontSize=8,
        )

        # Lieu et date
        lieu = cert.lieu_signature or (self.adresse_client.localite if self.adresse_client else '')
        date_sig = cert.date_signature or date_class.today()
        lieu_date = f"{lieu}, le {date_sig.strftime('%d.%m.%Y')}"

        # Tel
        tel = ""
        if cert.telephone_signataire:
            tel = f"Tel.: {cert.telephone_signataire}"

        lieu_data = [[Paragraph(lieu_date, sig_style), Paragraph(tel, sig_style)]]
        lieu_table = Table(lieu_data, colWidths=[90 * mm, 75 * mm])
        lieu_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(lieu_table)
        elements.append(make_spacer(8))

        # Ligne de signature fine
        sig_line_style = ParagraphStyle(
            'sig_line', parent=self.styles['label'],
            fontSize=8,
        )
        elements.append(Paragraph("_" * 50, sig_line_style))
        elements.append(Paragraph("Signature de l'employeur / Timbre", sig_line_style))

        if cert.nom_signataire:
            elements.append(Paragraph(cert.nom_signataire, sig_style))

        return elements

    def _build_footer(self):
        """Pied de page: Formulaire 11 + date generation."""
        elements = []
        elements.append(make_spacer(5))
        footer_style = ParagraphStyle(
            'f11_footer', parent=self.styles['footer'],
            fontSize=6,
        )
        elements.append(Paragraph("Formulaire 11 - Certificat de salaire", footer_style))
        elements.append(Paragraph(
            f"Genere le {date_class.today().strftime('%d.%m.%Y')} - {self.client.raison_sociale}",
            footer_style,
        ))
        return elements

    def generer(self):
        """
        Genere le PDF du formulaire 11 et retourne les bytes.

        Returns:
            bytes: Contenu du PDF
        """
        buffer = BytesIO()
        logo_source = self.client.get_logo() if hasattr(self.client, 'get_logo') else None
        doc = create_salaire_doc(
            buffer,
            title="Formulaire 11 - Certificat de salaire",
            confidential=False,
            margins={'top': 16 * mm, 'bottom': 16 * mm, 'left': 12 * mm, 'right': 12 * mm},
            logo_source=logo_source,
        )

        elements = []

        # Titre
        elements.extend(self._build_titre())

        # Section A-B
        elements.append(self._build_section_ab())
        elements.append(make_spacer(3))

        # Section C-E
        elements.append(self._build_section_cde())
        elements.append(make_spacer(3))

        # Section F-G
        elements.extend(self._build_section_fg())
        elements.append(make_spacer(3))

        # Chiffres 1-15
        elements.extend(self._build_chiffres())
        elements.append(make_spacer(3))

        # Remarques
        elements.extend(self._build_remarques())

        # Signature
        elements.extend(self._build_signature())

        # Footer
        elements.extend(self._build_footer())

        build_doc(doc, elements)

        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

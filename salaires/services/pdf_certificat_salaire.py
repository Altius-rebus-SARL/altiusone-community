"""
Generateur PDF pour CertificatSalaire - Formulaire 11 officiel suisse.

Layout pixel-perfect basé sur le formulaire ESTV Form. 11 dfe 01.21.
Utilise ReportLab Canvas (pas Platypus) pour positionner chaque champ
exactement comme le formulaire officiel.

Labels trilingues officiels (DE – FR – IT) avec EN en sous-titre.

Structure officielle :
- A/B : Checkboxes Lohnausweis / Rentenbescheinigung
- C : N° AVS + Date de naissance
- D : Année
- E : Période (du/au)
- F : Checkbox transport gratuit
- G : Checkbox cantine/lunch-checks
- H : Adresse employé (bloc multilignes)
- Chiffres 1-8 : Revenus → Total brut
- Chiffres 9-10 : Déductions
- Chiffre 11 : Salaire net (→ déclaration d'impôt)
- Chiffre 12 : Retenue impôt source
- Chiffre 13 : Frais professionnels (6 sous-champs)
- Chiffre 14 : Autres prestations salariales accessoires
- Chiffre 15 : Remarques
- I : Lieu, date, signature, certification

Référence : https://www.estv.admin.ch/fr/certificat-de-salaire-et-attestation-de-rentes
"""
import io
from datetime import date as date_class
from decimal import Decimal

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdf_canvas

# ── Couleurs ESTV ──────────────────────────────────────────────────
ROSE_CLAIR = HexColor('#FCE8E0')  # Fond champs saisissables
GRIS_CLAIR = HexColor('#F2F2F2')  # Fond sections
GRIS_LIGNE = HexColor('#CCCCCC')  # Lignes de séparation
GRIS_TEXTE = HexColor('#666666')  # Texte secondaire
NOIR = black
BLANC = white

# ── Dimensions page A4 ────────────────────────────────────────────
PW, PH = A4  # 595.276 x 841.89 pts
ML = 15 * mm   # Marge gauche
MR = 12 * mm   # Marge droite
MT = 12 * mm   # Marge haut
CONTENT_W = PW - ML - MR

# ── Colonnes montants (droite) ─────────────────────────────────────
AMT_X = PW - MR - 32 * mm  # x début colonne montant
AMT_W = 30 * mm             # largeur champ montant
SIGN_X = PW - MR - 3 * mm   # position signe +/-/=

# ── Tailles de police ──────────────────────────────────────────────
FONT_LABEL = 5           # Labels trilingues DE/FR/IT
FONT_EN = 3.8            # Sous-titre anglais
FONT_NUM = 5.5           # Numéro de chiffre (1., 2.1, etc.)
FONT_FIELD = 7.5         # Valeur dans un champ (montants, dates, AVS)
FONT_BOLD_TITLE = 6      # Titres de section (chiffre 8, 11, 13, 14)
FONT_ART = 5             # "Art – Genre – Genere – Kind"

# ── Espacement vertical ───────────────────────────────────────────
LH = 4.8 * mm            # Hauteur de ligne standard
LH_ART = 3.5 * mm        # Espace supplémentaire pour champ Art


class CertificatSalairePDF:
    """Générateur PDF Formulaire 11 conforme ESTV."""

    def __init__(self, certificat, style_config=None):
        self.cert = certificat
        self.employe = certificat.employe
        self.client = certificat.employe.mandat.client
        self.adresse_client = self.client.adresse_siege
        self.devise_code = certificat.employe.mandat.devise_id or 'CHF'
        self.style_config = style_config

    def _fmt(self, val):
        """Montants entiers uniquement (conformité ESTV)."""
        if val is None or val == 0:
            return ''
        try:
            v = int(Decimal(str(val)).quantize(Decimal('1')))
            # Format suisse avec apostrophe
            s = f"{abs(v):,}".replace(',', "'")
            return f"-{s}" if v < 0 else s
        except Exception:
            return str(val)

    # ── Helpers de dessin ──────────────────────────────────────────

    def _checkbox(self, c, x, y, checked=False, size=3.5 * mm):
        """Dessine une case à cocher."""
        c.setStrokeColor(NOIR)
        c.setLineWidth(0.5)
        c.rect(x, y, size, size, fill=0)
        if checked:
            c.setStrokeColor(NOIR)
            c.setLineWidth(1)
            c.line(x + 0.8 * mm, y + 0.8 * mm,
                   x + size - 0.8 * mm, y + size - 0.8 * mm)
            c.line(x + 0.8 * mm, y + size - 0.8 * mm,
                   x + size - 0.8 * mm, y + 0.8 * mm)

    def _field_bg(self, c, x, y, w, h):
        """Dessine un fond rose clair pour un champ saisissable.
        Réinitialise toujours la couleur de remplissage à NOIR après dessin."""
        c.setFillColor(ROSE_CLAIR)
        c.rect(x, y, w, h, fill=1, stroke=0)
        c.setFillColor(NOIR)

    def _hline(self, c, x1, x2, y, color=GRIS_LIGNE, width=0.5):
        """Ligne horizontale."""
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x1, y, x2, y)

    def _amount_field(self, c, y, value, sign=''):
        """Dessine un champ montant aligné à droite avec fond rose."""
        self._field_bg(c, AMT_X, y - 1.5 * mm, AMT_W, 4.5 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        c.drawRightString(AMT_X + AMT_W - 1 * mm, y, self._fmt(value))
        if sign:
            c.setFont('Helvetica', FONT_NUM)
            c.drawString(SIGN_X, y, sign)

    # ── Sections du formulaire ─────────────────────────────────────

    def _draw_header(self, c):
        """Sections A-B : titre + checkboxes Lohnausweis/Rentenbescheinigung."""
        y = PH - MT
        cert = self.cert
        is_rente = getattr(cert, 'type_attestation', '') == 'RENTE'

        # A. Lohnausweis
        self._checkbox(c, ML, y - 4 * mm, checked=not is_rente)
        c.setFillColor(GRIS_CLAIR)
        c.rect(ML + 6 * mm, y - 5.5 * mm, 8 * mm, 7 * mm, fill=1, stroke=0)
        c.setFillColor(NOIR)
        c.setFont('Helvetica-Bold', 9)
        c.drawString(ML + 16 * mm, y - 2 * mm,
                     "Lohnausweis – Certificat de salaire – Certificato di salario")
        c.setFont('Helvetica', 5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 16 * mm, y - 5.5 * mm, "Salary certificate")
        c.setFillColor(NOIR)

        # B. Rentenbescheinigung
        y -= 9 * mm
        self._checkbox(c, ML, y - 4 * mm, checked=is_rente)
        c.setFillColor(GRIS_CLAIR)
        c.rect(ML + 6 * mm, y - 5.5 * mm, 8 * mm, 7 * mm, fill=1, stroke=0)
        c.setFillColor(NOIR)
        c.setFont('Helvetica-Bold', 8)
        c.drawString(ML + 16 * mm, y - 2 * mm,
                     "Rentenbescheinigung – Attestation de rentes – Attestazione di rendite")
        c.setFont('Helvetica', 5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 16 * mm, y - 5.5 * mm, "Pension statement")
        c.setFillColor(NOIR)

        return y - 7 * mm

    def _draw_section_cdefg(self, c, y_start):
        """Sections C-G : identité, période, checkboxes F/G."""
        emp = self.employe
        cert = self.cert
        y = y_start

        # ── C : N° AVS + Date de naissance ──
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "C")

        # Champ AVS (fond rose)
        avs_x = ML + 5 * mm
        self._field_bg(c, avs_x, y - 2 * mm, 50 * mm, 6 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        c.drawString(avs_x + 1 * mm, y, emp.avs_number or '')

        # Label sous le champ
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(avs_x, y - 5 * mm,
                     "AHV-Nr. – No AVS – N. AVS")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(avs_x, y - 7.5 * mm, "OASI no.")

        # Date de naissance
        geb_x = avs_x + 55 * mm
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(geb_x, y - 5 * mm,
                     "Geburtsdatum – Date de naissance – Data di nascita")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(geb_x, y - 7.5 * mm, "Date of birth")
        self._field_bg(c, geb_x, y - 2 * mm, 35 * mm, 6 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        if emp.date_naissance:
            c.drawString(geb_x + 1 * mm, y, emp.date_naissance.strftime('%d.%m.%Y'))

        # ── F : Transport gratuit (à droite de C) ──
        f_x = 130 * mm
        self._checkbox(c, f_x, y - 1 * mm,
                       checked=getattr(cert, 'transport_gratuit_fourni', False))
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(f_x + 5 * mm, y, "F")
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        f_label_x = f_x + 9 * mm
        c.drawString(f_label_x, y + 1 * mm,
                     "Unentgeltl. Beförderung Wohn-/Arbeitsort")
        c.drawString(f_label_x, y - 1.5 * mm,
                     "Transport gratuit dom. – lieu de travail")
        c.drawString(f_label_x, y - 4 * mm,
                     "Trasp. gratuito domic. – luogo di lavoro")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(f_label_x, y - 6.5 * mm,
                     "Free transport home – work place")

        # ── D : Année + E : Période ──
        y -= 13 * mm
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "D")
        self._field_bg(c, ML + 5 * mm, y - 2 * mm, 20 * mm, 6 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        c.drawString(ML + 6 * mm, y, str(cert.annee))
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 5 * mm,
                     "Jahr – Année – Anno")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(ML + 5 * mm, y - 7.5 * mm, "Year")

        # E : du/au
        e_x = ML + 30 * mm
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(e_x, y, "E")
        # du
        von_x = e_x + 5 * mm
        self._field_bg(c, von_x, y - 2 * mm, 22 * mm, 6 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        if cert.date_debut:
            c.drawString(von_x + 1 * mm, y,
                         cert.date_debut.strftime('%d.%m.%Y'))
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(von_x, y - 5 * mm, "von – du – da")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(von_x, y - 7.5 * mm, "from")

        # au
        bis_x = von_x + 27 * mm
        self._field_bg(c, bis_x, y - 2 * mm, 22 * mm, 6 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        if cert.date_fin:
            c.drawString(bis_x + 1 * mm, y,
                         cert.date_fin.strftime('%d.%m.%Y'))
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(bis_x, y - 5 * mm, "bis – au – a")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(bis_x, y - 7.5 * mm, "to")

        # ── G : Cantine / Lunch-checks (à droite de D/E) ──
        c.setFillColor(NOIR)
        self._checkbox(c, f_x, y - 1 * mm,
                       checked=getattr(cert, 'repas_midi_gratuit', False))
        c.setFont('Helvetica-Bold', 7)
        c.drawString(f_x + 5 * mm, y, "G")
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(f_label_x, y + 1 * mm,
                     "Kantinenverpflegung / Lunch-Checks")
        c.drawString(f_label_x, y - 1.5 * mm,
                     "Repas à la cantine / chèques-repas")
        c.drawString(f_label_x, y - 4 * mm,
                     "Mensa / buoni-pasto")
        c.setFont('Helvetica', FONT_EN)
        c.drawString(f_label_x, y - 6.5 * mm,
                     "Canteen meals / lunch checks")

        c.setFillColor(NOIR)
        return y - 11 * mm

    def _draw_section_h(self, c, y_start):
        """Section H : bloc adresse employé (cadre pointillé)."""
        emp = self.employe
        adr = emp.adresse

        # Cadre pointillé
        y = y_start
        h_height = 28 * mm
        c.setStrokeColor(GRIS_LIGNE)
        c.setLineWidth(0.5)
        c.setDash(3, 3)
        c.rect(ML, y - h_height, CONTENT_W, h_height, fill=0, stroke=1)
        c.setDash()

        # Label H
        c.setFont('Helvetica-Bold', 8)
        c.setFillColor(NOIR)
        c.drawRightString(PW - MR - 2 * mm, y - 4 * mm, "H")

        # Contenu adresse employeur (gauche)
        c.setFont('Helvetica', 8.5)
        line_y = y - 6 * mm
        client = self.client
        adr_client = self.adresse_client
        c.drawString(ML + 3 * mm, line_y, client.raison_sociale)
        line_y -= 4 * mm
        if adr_client:
            rue = adr_client.rue.strip()
            if adr_client.numero and adr_client.numero not in rue:
                rue = f"{rue} {adr_client.numero}"
            c.drawString(ML + 3 * mm, line_y, rue)
            line_y -= 4 * mm
            c.drawString(ML + 3 * mm, line_y,
                         f"{adr_client.npa or ''} {adr_client.localite or ''}")

        # Adresse employé (droite)
        emp_x = 110 * mm
        line_y = y - 6 * mm
        c.drawString(emp_x, line_y, f"{emp.prenom} {emp.nom}")
        line_y -= 4 * mm
        if adr:
            rue_emp = adr.rue.strip()
            if adr.numero and adr.numero not in rue_emp:
                rue_emp = f"{rue_emp} {adr.numero}"
            c.drawString(emp_x, line_y, rue_emp)
            line_y -= 4 * mm
            c.drawString(emp_x, line_y,
                         f"{adr.npa or ''} {adr.localite or ''}")

        return y - h_height - 2 * mm

    def _draw_chiffres(self, c, y_start):
        """Chiffres 1-15 : revenus, déductions, frais."""
        cert = self.cert
        y = y_start

        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawRightString(PW - MR, y + 3 * mm,
                          "Nur ganze Frankenbeträge")
        c.drawRightString(PW - MR, y,
                          "Que des montants entiers – Solo importi interi")
        c.setFont('Helvetica', FONT_EN)
        c.drawRightString(PW - MR, y - 2.5 * mm,
                          "Only whole amounts")
        c.setFillColor(NOIR)

        y -= 5 * mm

        def _line(num, label_de, label_fr='', label_en='', value=None,
                  sign='', bold=False, indent=0, art_field=False,
                  art_value='', label_it=''):
            nonlocal y
            x = ML + indent * mm
            font = 'Helvetica-Bold' if bold else 'Helvetica'

            # Numéro
            c.setFont(font, FONT_NUM)
            c.setFillColor(NOIR)
            c.drawString(x, y, num)

            # Labels : DE – FR – IT sur la ligne
            label_x = x + 7 * mm + indent * mm
            c.setFont(font, FONT_LABEL)
            label_main = label_de
            if label_fr:
                label_main += f" – {label_fr}"
            if label_it:
                label_main += f" – {label_it}"
            c.drawString(label_x, y, label_main[:120])

            # EN en dessous (plus petit, gris)
            if label_en:
                c.setFont('Helvetica', FONT_EN)
                c.setFillColor(GRIS_TEXTE)
                c.drawString(label_x, y - 2.5 * mm, label_en[:100])
                c.setFillColor(NOIR)

            # Champ "Art – Genre – Genere – Kind" si demandé
            if art_field:
                # Espace suffisant pour ne pas chevaucher le label EN
                art_offset = 5 * mm if label_en else 3.5 * mm
                y -= art_offset
                c.setFont('Helvetica', FONT_ART)
                c.setFillColor(GRIS_TEXTE)
                art_label_x = label_x + 2 * mm
                c.drawString(art_label_x, y,
                             "Art – Genre – Genere – Kind")
                if art_value:
                    self._field_bg(c, art_label_x + 30 * mm,
                                   y - 1 * mm, 55 * mm, 4 * mm)
                    c.setFont('Helvetica', 6)
                    c.drawString(art_label_x + 31 * mm, y,
                                 str(art_value)[:40])
                c.setFillColor(NOIR)

            # Montant
            if value is not None:
                self._amount_field(c, y, value, sign)
            elif sign:
                c.setFont('Helvetica', FONT_FIELD)
                c.setFillColor(NOIR)
                c.drawString(SIGN_X, y, sign)

            y -= LH

        def _separator(thick=False):
            nonlocal y
            self._hline(c, ML, PW - MR, y + 2 * mm,
                        color=NOIR if thick else GRIS_LIGNE,
                        width=1.0 if thick else 0.5)

        # ── REVENUS (chiffres 1-8) ─────────────────────────────────

        _line("1.", "Lohn", "Salaire", "Salary",
              cert.chiffre_1_salaire, '+', label_it="Salario")

        _separator()
        _line("2.", "Gehaltsnebenleistungen",
              "Prestations salariales accessoires", "Fringe benefits",
              label_it="Prestazioni accessorie al salario")
        _line("2.1", "Verpflegung, Unterkunft",
              "Pension, logement", "Room and board",
              cert.chiffre_2_1_repas, '+', indent=3,
              label_it="Vitto, alloggio")
        _line("2.2", "Privatanteil Geschäftsfahrzeug",
              "Part privée voit. de service",
              "Private use of company car",
              cert.chiffre_2_2_voiture, '+', indent=3,
              label_it="Parte privata auto aziendale")
        _line("2.3", "Andere", "Autres", "Others",
              cert.chiffre_2_3_autres, '+', indent=3,
              art_field=True,
              art_value=getattr(cert, 'chiffre_2_3_art', ''),
              label_it="Altri")

        _separator()
        _line("3.", "Unregelmässige Leistungen",
              "Prestations non périodiques", "Irregular benefits",
              cert.chiffre_3_irregulier, '+',
              art_field=True,
              art_value=getattr(cert, 'chiffre_3_art', ''),
              label_it="Prestazioni non periodiche")

        _separator()
        _line("4.", "Kapitalleistungen",
              "Prestations en capital", "Capital benefits",
              cert.chiffre_4_capital, '+',
              art_field=True,
              art_value=getattr(cert, 'chiffre_4_art', ''),
              label_it="Prestazioni in capitale")

        _line("5.", "Beteiligungsrechte gem. Beiblatt",
              "Droits de participation selon annexe",
              "Ownership rights per supplement",
              cert.chiffre_5_participations, '+',
              label_it="Diritti di partecipaz. secondo allegato")

        _line("6.", "Verwaltungsratsentschädigungen",
              "Indemnités des membres de l'admin.",
              "Board of directors' compensation",
              cert.chiffre_6_ca, '+',
              label_it="Indennità dei membri dell'amm.")

        _line("7.", "Andere Leistungen",
              "Autres prestations", "Other benefits",
              cert.chiffre_7_autres, '+',
              art_field=True,
              art_value=getattr(cert, 'chiffre_7_art', ''),
              label_it="Altre prestazioni")

        # ── Chiffre 8 : TOTAL BRUT ──
        _separator(thick=True)
        _line("8.", "Bruttolohn total / Rente",
              "Salaire brut total / Rente",
              "Gross salary total / Pension",
              cert.chiffre_8_total_brut, '=', bold=True,
              label_it="Salario lordo totale / Rendita")

        # ── DÉDUCTIONS (chiffres 9-11) ─────────────────────────────
        _separator()
        _line("9.", "Beiträge AHV/IV/EO/ALV/NBUV",
              "Cotisations AVS/AI/APG/AC/AANP",
              "Contributions OASI/DI/IC/UI/NBUV",
              cert.chiffre_9_cotisations, '–',
              label_it="Contributi AVS/AI/IPG/AD/AINF")

        _separator()
        _line("10.", "Berufliche Vorsorge",
              "Prévoyance professionnelle",
              "Company pension plan",
              label_it="Previdenza professionale")
        _line("10.1", "Ordentliche Beiträge",
              "Cotisations ordinaires", "Regular contributions",
              cert.chiffre_10_1_lpp_ordinaire, '–', indent=5,
              label_it="Contributi ordinari")
        _line("10.2", "Beiträge für den Einkauf",
              "Cotisations pour le rachat",
              "Purchasing contribution",
              cert.chiffre_10_2_lpp_rachat, '–', indent=5,
              label_it="Contributi di riscatto")

        # ── Chiffre 11 : NET ──
        _separator(thick=True)
        c.setFont('Helvetica-Bold', FONT_BOLD_TITLE)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "11.")
        c.drawString(ML + 8 * mm, y,
                     "Nettolohn – Salaire net – Salario netto")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y - 2.5 * mm,
                     "Net salary / Pension")
        c.setFillColor(NOIR)
        # Flèche
        c.setFont('Helvetica-Bold', 8)
        c.drawString(AMT_X - 10 * mm, y, "\u279E")
        self._amount_field(c, y, cert.chiffre_11_net, '=')
        y -= 3 * mm
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y,
                     "in die Steuererklärung übertragen – "
                     "A reporter sur la déclaration d'impôt – "
                     "Da riportare sulla dichiaraz. d'imposta")
        c.setFillColor(NOIR)
        y -= LH

        # ── Chiffre 12 : Impôt source ──
        _separator()
        _line("12.", "Quellensteuerabzug",
              "Retenue de l'impôt à la source",
              "Withholding tax deduction",
              getattr(cert, 'impot_source_annuel', None),
              label_it="Ritenuta d'imposta alla fonte")

        # ── Chiffre 13 : Frais ──
        _separator()
        c.setFont('Helvetica', FONT_NUM)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "13.")
        c.setFont('Helvetica', FONT_LABEL)
        c.drawString(ML + 8 * mm, y,
                     "Spesenvergütungen – Allocations pour frais – "
                     "Indennità per spese")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y - 2.5 * mm,
                     "Expenses reimbursement")
        y -= 3 * mm
        c.setFont('Helvetica', FONT_EN)
        c.drawString(ML + 8 * mm, y,
                     "Nicht im Bruttolohn (Ziffer 8) enthalten – "
                     "Non comprises dans le salaire brut (chiffre 8)")
        c.setFillColor(NOIR)
        y -= LH

        # 13.1 Frais effectifs
        c.setFont('Helvetica', FONT_LABEL)
        c.drawString(ML + 5 * mm, y,
                     "13.1  Effektive Spesen – Frais effectifs – "
                     "Spese effettive")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 2.5 * mm, "Actual expenses")
        c.setFillColor(NOIR)
        y -= LH
        _line("13.1.1", "Reise, Verpflegung, Übernachtung",
              "Voyage, repas, nuitées",
              "Trip, room and board",
              getattr(cert, 'chiffre_13_1_1_repas_effectif', None),
              indent=8,
              label_it="Viaggio, vitto, pernottamento")
        _line("13.1.2", "Übrige", "Autres", "Others",
              getattr(cert, 'chiffre_13_1_2_repas_forfait', None),
              indent=8, art_field=True,
              label_it="Altre")

        # 13.2 Forfaits
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(NOIR)
        c.drawString(ML + 5 * mm, y,
                     "13.2  Pauschalspesen – Frais forfaitaires – "
                     "Spese forfettarie")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 2.5 * mm, "Overall expenses")
        c.setFillColor(NOIR)
        y -= LH
        _line("13.2.1", "Repräsentation", "Représentation",
              "Representation",
              getattr(cert, 'chiffre_13_2_nuitees', None), indent=8,
              label_it="Rappresentanza")
        _line("13.2.2", "Auto", "Voiture", "Car",
              None, indent=8, label_it="Automobile")
        _line("13.2.3", "Übrige", "Autres", "Others",
              getattr(cert, 'chiffre_13_3_repas_externes', None),
              indent=8, art_field=True,
              label_it="Altre")

        # 13.3
        _line("13.3", "Beiträge an die Weiterbildung",
              "Contributions au perfectionnement",
              "Contributions to further education",
              None, indent=3,
              label_it="Contributi al perfezionamento")

        # ── Chiffre 14 : Autres prestations accessoires ──
        _separator()
        c.setFont('Helvetica', FONT_NUM)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "14.")
        c.setFont('Helvetica', FONT_LABEL)
        c.drawString(ML + 8 * mm, y,
                     "Weitere Gehaltsnebenleistungen – "
                     "Autres prest. salariales accessoires – "
                     "Altre prest. accessorie al salario")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y - 2.5 * mm,
                     "Further fringe benefits")
        c.setFillColor(NOIR)
        y -= LH
        # Ligne Art / Genre / Genere / Kind
        c.setFont('Helvetica', FONT_ART)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 55 * mm, y,
                     "Art – Genre – Genere – Kind")
        self._field_bg(c, ML + 85 * mm, y - 1 * mm, 80 * mm, 4 * mm)
        if getattr(cert, 'chiffre_14_autres_frais', None):
            c.setFont('Helvetica', 6)
            c.drawString(ML + 86 * mm, y,
                         str(cert.chiffre_14_autres_frais)[:50])
        c.setFillColor(NOIR)
        y -= LH

        # ── Chiffre 15 : Remarques ──
        _separator()
        c.setFont('Helvetica', FONT_NUM)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "15.")
        c.setFont('Helvetica', FONT_LABEL)
        c.drawString(ML + 8 * mm, y,
                     "Bemerkungen – Observations – Osservazioni")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y - 2.5 * mm, "Comments")
        c.setFillColor(NOIR)
        y -= 3 * mm
        # Lignes de remarques
        self._field_bg(c, ML + 25 * mm, y - 1 * mm,
                       CONTENT_W - 25 * mm, 4 * mm)
        if cert.remarques:
            c.setFont('Helvetica', 6)
            lignes = cert.remarques.split('\n')[:2]
            c.drawString(ML + 26 * mm, y,
                         lignes[0][:80] if lignes else '')
            if len(lignes) > 1:
                y -= 4.5 * mm
                self._field_bg(c, ML + 25 * mm, y - 1 * mm,
                               CONTENT_W - 25 * mm, 4 * mm)
                c.drawString(ML + 26 * mm, y, lignes[1][:80])
        y -= LH

        return y

    def _draw_section_i(self, c, y_start):
        """Section I : lieu, date, signature, certification."""
        cert = self.cert
        y = y_start - 2 * mm

        self._hline(c, ML, PW - MR, y + 2 * mm, NOIR, 0.8)

        # I. Ort und Datum
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "I")
        c.setFont('Helvetica', FONT_LABEL)
        c.drawString(ML + 5 * mm, y,
                     "Ort und Datum – Lieu et date – Luogo e data")
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 2.5 * mm, "Place and date")
        c.setFillColor(NOIR)

        # Champ lieu/date
        lieu = cert.lieu_signature or (
            self.adresse_client.localite if self.adresse_client else '')
        date_sig = cert.date_signature or date_class.today()
        self._field_bg(c, ML + 5 * mm, y - 7 * mm, 50 * mm, 5 * mm)
        c.setFont('Helvetica', FONT_FIELD)
        c.drawString(ML + 6 * mm, y - 6 * mm,
                     f"{lieu}, {date_sig.strftime('%d.%m.%Y')}")

        # Certification (à droite)
        cert_x = 100 * mm
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(NOIR)
        c.drawString(cert_x, y,
                     "Die Richtigkeit und Vollständigkeit bestätigt")
        c.drawString(cert_x, y - 2.5 * mm,
                     "inkl. genauer Anschrift und Telefonnr. des Arbeitgebers")
        y -= 5 * mm
        c.drawString(cert_x, y,
                     "Certifié exact et complet")
        c.drawString(cert_x, y - 2.5 * mm,
                     "y.c. adresse et no de téléphone exacts de l'employeur")
        y -= 5 * mm
        c.drawString(cert_x, y,
                     "Certificato esatto e completo")
        c.drawString(cert_x, y - 2.5 * mm,
                     "incl. indirizzo e no di telefono esatti del datore di lavoro")
        y -= 5 * mm
        c.setFont('Helvetica', FONT_EN)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(cert_x, y,
                     "Correct and complete incl. exact address and "
                     "phone no. of employer")
        c.setFillColor(NOIR)

        # Ligne de signature
        y -= 5 * mm
        self._hline(c, ML + 5 * mm, ML + 60 * mm, y, NOIR, 0.5)
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 3 * mm,
                     "Unterschrift – Signature – Firma")
        c.setFillColor(NOIR)

        if cert.nom_signataire:
            c.setFont('Helvetica', 7)
            c.drawString(ML + 5 * mm, y + 2 * mm, cert.nom_signataire)

        return y

    def _draw_footer(self, c):
        """Pied de page : numéro du formulaire."""
        c.setFont('Helvetica', FONT_LABEL)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML, 6 * mm, "Form. 11 dfe 01.21")

        # Texte vertical gauche (orientation 90°)
        c.saveState()
        c.translate(5 * mm, PH / 2)
        c.rotate(90)
        c.setFont('Helvetica', 4.5)
        c.drawCentredString(0, 0,
                            "Bitte die Wegleitung beachten – "
                            "Observer s.v.p. la directive – "
                            "Osservare la direttiva – "
                            "Please consider the guidance")
        c.restoreState()

    # ── Génération principale ──────────────────────────────────────

    def generer(self):
        """Génère le PDF Formulaire 11 et retourne les bytes."""
        buffer = io.BytesIO()
        c = pdf_canvas.Canvas(buffer, pagesize=A4)
        c.setTitle(
            f"Formulaire 11 - {self.employe.nom} "
            f"{self.employe.prenom} - {self.cert.annee}")

        # Dessiner toutes les sections
        y = self._draw_header(c)
        y = self._draw_section_cdefg(c, y)
        y = self._draw_section_h(c, y)
        y = self._draw_chiffres(c, y)
        self._draw_section_i(c, y)
        self._draw_footer(c)

        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

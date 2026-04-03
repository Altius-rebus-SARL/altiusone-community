"""
Generateur PDF pour CertificatSalaire - Formulaire 11 officiel suisse.

Layout pixel-perfect basé sur le formulaire ESTV Form. 11 dfe 01.21.
Utilise ReportLab Canvas (pas Platypus) pour positionner chaque champ
exactement comme le formulaire officiel.

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
            c.line(x + 0.8 * mm, y + 0.8 * mm, x + size - 0.8 * mm, y + size - 0.8 * mm)
            c.line(x + 0.8 * mm, y + size - 0.8 * mm, x + size - 0.8 * mm, y + 0.8 * mm)

    def _field_bg(self, c, x, y, w, h):
        """Dessine un fond rose clair pour un champ saisissable."""
        c.setFillColor(ROSE_CLAIR)
        c.rect(x, y, w, h, fill=1, stroke=0)

    def _hline(self, c, x1, x2, y, color=GRIS_LIGNE, width=0.5):
        """Ligne horizontale."""
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x1, y, x2, y)

    def _amount_field(self, c, y, value, sign=''):
        """Dessine un champ montant aligné à droite avec fond rose."""
        self._field_bg(c, AMT_X, y - 1 * mm, AMT_W, 5 * mm)
        c.setFillColor(NOIR)
        c.setFont('Helvetica', 8)
        c.drawRightString(AMT_X + AMT_W - 1 * mm, y, self._fmt(value))
        if sign:
            c.setFont('Helvetica', 7)
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
        c.setFont('Helvetica-Bold', 12)
        c.drawString(ML + 16 * mm, y - 4 * mm,
                     "Lohnausweis – Certificat de salaire – Salary certificate")

        # B. Rentenbescheinigung
        y -= 10 * mm
        self._checkbox(c, ML, y - 4 * mm, checked=is_rente)
        c.setFillColor(GRIS_CLAIR)
        c.rect(ML + 6 * mm, y - 5.5 * mm, 8 * mm, 7 * mm, fill=1, stroke=0)
        c.setFillColor(NOIR)
        c.setFont('Helvetica-Bold', 11)
        c.drawString(ML + 16 * mm, y - 4 * mm,
                     "Rentenbescheinigung – Attestation de rentes – Pension statement")

        return y - 8 * mm

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
        c.setFont('Helvetica', 8)
        c.drawString(avs_x + 1 * mm, y, emp.avs_number or '')

        # Label sous le champ
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(avs_x, y - 5 * mm, "AHV-Nr. – No AVS – OASI no.")

        # Date de naissance
        geb_x = avs_x + 55 * mm
        c.setFillColor(NOIR)
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(geb_x, y - 5 * mm, "Geburtsdatum – Date de naissance – Date of birth")
        self._field_bg(c, geb_x, y - 2 * mm, 35 * mm, 6 * mm)
        c.setFillColor(NOIR)
        c.setFont('Helvetica', 8)
        if emp.date_naissance:
            c.drawString(geb_x + 1 * mm, y, emp.date_naissance.strftime('%d.%m.%Y'))

        # ── F : Transport gratuit (à droite de C) ──
        f_x = 125 * mm
        self._checkbox(c, f_x, y - 1 * mm, checked=getattr(cert, 'transport_gratuit_fourni', False))
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(f_x + 5 * mm, y, "F")
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        f_label_x = f_x + 9 * mm
        c.drawString(f_label_x, y + 1 * mm, "Unentgeltliche Beförderung zwischen Wohn- und Arbeitsort")
        c.drawString(f_label_x, y - 2 * mm, "Transport gratuit entre le domicile et le lieu de travail")
        c.drawString(f_label_x, y - 5 * mm, "Free transport between living place and work place")

        # ── D : Année + E : Période ──
        y -= 12 * mm
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "D")
        self._field_bg(c, ML + 5 * mm, y - 2 * mm, 20 * mm, 6 * mm)
        c.setFont('Helvetica', 8)
        c.drawString(ML + 6 * mm, y, str(cert.annee))
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 5 * mm, "Jahr – Année – Year")

        # E : du/au
        e_x = ML + 30 * mm
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(e_x, y, "E")
        # du
        von_x = e_x + 5 * mm
        self._field_bg(c, von_x, y - 2 * mm, 22 * mm, 6 * mm)
        c.setFont('Helvetica', 8)
        if cert.date_debut:
            c.drawString(von_x + 1 * mm, y, cert.date_debut.strftime('%d.%m.%Y'))
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(von_x, y - 5 * mm, "von – du – from")

        # au
        bis_x = von_x + 27 * mm
        self._field_bg(c, bis_x, y - 2 * mm, 22 * mm, 6 * mm)
        c.setFillColor(NOIR)
        c.setFont('Helvetica', 8)
        if cert.date_fin:
            c.drawString(bis_x + 1 * mm, y, cert.date_fin.strftime('%d.%m.%Y'))
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(bis_x, y - 5 * mm, "bis – au – to")

        # ── G : Cantine / Lunch-checks (à droite de D/E) ──
        self._checkbox(c, f_x, y - 1 * mm, checked=getattr(cert, 'repas_midi_gratuit', False))
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(f_x + 5 * mm, y, "G")
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(f_label_x, y + 1 * mm, "Kantinenverpflegung/Lunch-Checks")
        c.drawString(f_label_x, y - 2 * mm, "Repas à la cantine/chèques-repas")
        c.drawString(f_label_x, y - 5 * mm, "Canteen meals/lunch checks")

        return y - 10 * mm

    def _draw_section_h(self, c, y_start):
        """Section H : bloc adresse employé (cadre pointillé)."""
        emp = self.employe
        adr = emp.adresse

        # Cadre pointillé
        y = y_start
        h_height = 30 * mm
        c.setStrokeColor(GRIS_LIGNE)
        c.setLineWidth(0.5)
        c.setDash(3, 3)
        c.rect(ML, y - h_height, CONTENT_W, h_height, fill=0, stroke=1)
        c.setDash()

        # Label H
        c.setFont('Helvetica-Bold', 8)
        c.setFillColor(NOIR)
        c.drawRightString(PW - MR - 2 * mm, y - 4 * mm, "H")

        # Contenu adresse
        c.setFont('Helvetica', 9)
        line_y = y - 6 * mm
        # Adresse de l'employeur (émetteur) en haut à gauche
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
            c.drawString(ML + 3 * mm, line_y, f"{adr_client.npa or ''} {adr_client.localite or ''}")
            line_y -= 4 * mm

        # Adresse de l'employé à droite
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
            c.drawString(emp_x, line_y, f"{adr.npa or ''} {adr.localite or ''}")

        return y - h_height - 3 * mm

    def _draw_chiffres(self, c, y_start):
        """Chiffres 1-15 : revenus, déductions, frais."""
        cert = self.cert
        y = y_start
        lh = 5.5 * mm  # hauteur de ligne standard

        c.setFont('Helvetica', 6)
        c.setFillColor(GRIS_TEXTE)
        c.drawRightString(PW - MR, y + 3 * mm, "Nur ganze Frankenbeträge")
        c.drawRightString(PW - MR, y, "Que des montants entiers")
        c.drawRightString(PW - MR, y - 3 * mm, "Only whole amounts")

        y -= 6 * mm

        def _line(num, label_de, label_fr='', label_en='', value=None, sign='',
                  bold=False, indent=0, art_field=False, art_value=''):
            nonlocal y
            x = ML + indent * mm
            font = 'Helvetica-Bold' if bold else 'Helvetica'

            # Numéro
            c.setFont(font, 7)
            c.setFillColor(NOIR)
            c.drawString(x, y, num)

            # Labels trilingues
            label_x = x + 8 * mm + indent * mm
            c.setFont(font, 6.5)
            label_text = label_de
            if label_fr:
                label_text += f" – {label_fr}"
            if label_en:
                label_text += f" – {label_en}"
            # Tronquer si trop long
            max_w = AMT_X - label_x - 5 * mm
            c.drawString(label_x, y, label_text[:120])

            # Champ "Art – Genre – Kind" si demandé
            if art_field:
                c.setFont('Helvetica', 6)
                c.setFillColor(GRIS_TEXTE)
                y -= 3.5 * mm
                art_label_x = label_x + 2 * mm
                c.drawString(art_label_x, y, "Art – Genre – Kind")
                if art_value:
                    self._field_bg(c, art_label_x + 25 * mm, y - 1 * mm, 60 * mm, 4 * mm)
                    c.setFillColor(NOIR)
                    c.setFont('Helvetica', 7)
                    c.drawString(art_label_x + 26 * mm, y, str(art_value)[:40])

            # Montant
            if value is not None:
                self._amount_field(c, y, value, sign)
            elif sign:
                c.setFont('Helvetica', 7)
                c.setFillColor(NOIR)
                c.drawString(SIGN_X, y, sign)

            y -= lh

        def _separator(thick=False):
            nonlocal y
            self._hline(c, ML, PW - MR, y + 2 * mm,
                        color=NOIR if thick else GRIS_LIGNE,
                        width=1.0 if thick else 0.5)

        # ── REVENUS (chiffres 1-8) ─────────────────────────────────

        _line("1.", "Lohn", "Salaire", "Salary", cert.chiffre_1_salaire, '+')

        _separator()
        _line("2.", "Gehaltsnebenleistungen", "Prestations salariales accessoires", "Fringe benefits")
        _line("2.1", "Verpflegung, Unterkunft", "Pension, logement", "Room and board",
              cert.chiffre_2_1_repas, '+', indent=3)
        _line("2.2", "Privatanteil Geschäftsfahrzeug", "Part privée voiture de service",
              "Personal use of the company car", cert.chiffre_2_2_voiture, '+', indent=3)
        _line("2.3", "Andere", "Autres", "Others", cert.chiffre_2_3_autres, '+', indent=3,
              art_field=True, art_value=getattr(cert, 'chiffre_2_3_art', ''))

        _separator()
        _line("3.", "Unregelmässige Leistungen", "Prestations non périodiques",
              "Irregular benefits", cert.chiffre_3_irregulier, '+',
              art_field=True, art_value=getattr(cert, 'chiffre_3_art', ''))

        _separator()
        _line("4.", "Kapitalleistungen", "Prestations en capital", "Capital benefits",
              cert.chiffre_4_capital, '+',
              art_field=True, art_value=getattr(cert, 'chiffre_4_art', ''))

        _line("5.", "Beteiligungsrechte gemäss Beiblatt",
              "Droits de participation selon annexe",
              "Ownership right in accordance with supplement",
              cert.chiffre_5_participations, '+')

        _line("6.", "Verwaltungsratsentschädigungen",
              "Indemnités des membres de l'administration",
              "Board of directors' compensation",
              cert.chiffre_6_ca, '+')

        _line("7.", "Andere Leistungen", "Autres prestations", "Other benefits",
              cert.chiffre_7_autres, '+',
              art_field=True, art_value=getattr(cert, 'chiffre_7_art', ''))

        # ── Chiffre 8 : TOTAL BRUT ──
        _separator(thick=True)
        _line("8.", "Bruttolohn total / Rente", "Salaire brut total / Rente",
              "Gross salary total / Pension", cert.chiffre_8_total_brut, '=', bold=True)

        # ── DÉDUCTIONS (chiffres 9-11) ─────────────────────────────
        _separator()
        _line("9.", "Beiträge AHV/IV/EO/ALV/NBUV",
              "Cotisations AVS/AI/APG/AC/AANP",
              "Contributions OASI/DI/IC/UI/NBUV",
              cert.chiffre_9_cotisations, '–')

        _separator()
        _line("10.", "Berufliche Vorsorge", "Prévoyance professionnelle", "Company pension plan")
        _line("10.1", "Ordentliche Beiträge", "Cotisations ordinaires",
              "Regular contributions", cert.chiffre_10_1_lpp_ordinaire, '–', indent=5)
        _line("10.2", "Beiträge für den Einkauf", "Cotisations pour le rachat",
              "Purchasing contribution", cert.chiffre_10_2_lpp_rachat, '–', indent=5)

        # ── Chiffre 11 : NET ──
        _separator(thick=True)
        c.setFont('Helvetica-Bold', 7.5)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "11.")
        c.drawString(ML + 8 * mm, y,
                     "Nettolohn/Rente – Salaire net/Rente – Net salary/Pension")
        # Flèche
        c.drawString(AMT_X - 12 * mm, y, "➡")
        self._amount_field(c, y, cert.chiffre_11_net, '=')
        y -= 3 * mm
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y,
                     "in die Steuererklärung übertragen – A reporter sur la déclaration d'impôt – "
                     "Transfer to the tax declaration")
        y -= lh

        # ── Chiffre 12 : Impôt source ──
        _separator()
        _line("12.", "Quellensteuerabzug",
              "Retenue de l'impôt à la source",
              "Withholding tax deduction",
              getattr(cert, 'chiffre_12_impot_source', None) or cert.impot_source_retenu)

        # ── Chiffre 13 : Frais ──
        _separator()
        c.setFont('Helvetica', 6.5)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "13.")
        c.drawString(ML + 8 * mm, y,
                     "Spesenvergütungen – Allocations pour frais – Expenses reimbursement")
        y -= 3 * mm
        c.setFont('Helvetica', 5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 8 * mm, y,
                     "Nicht im Bruttolohn (Ziffer 8) enthalten – Non comprises dans le salaire brut (chiffre 8)")
        y -= lh

        # 13.1 Frais effectifs
        c.setFont('Helvetica', 6)
        c.setFillColor(NOIR)
        c.drawString(ML + 5 * mm, y, "13.1  Effektive Spesen / Frais effectifs / Actual expenses")
        y -= lh
        _line("13.1.1", "Reise, Verpflegung, Übernachtung",
              "Voyage, repas, nuitées", "Trip, room and board",
              cert.chiffre_13_1_1_repas_effectif, indent=8)
        _line("13.1.2", "Übrige", "Autres", "Others",
              cert.chiffre_13_1_2_repas_forfait, indent=8,
              art_field=True)

        # 13.2 Forfaits
        c.setFont('Helvetica', 6)
        c.setFillColor(NOIR)
        c.drawString(ML + 5 * mm, y, "13.2  Pauschalspesen / Frais forfaitaires / Overall expenses")
        y -= lh
        _line("13.2.1", "Repräsentation", "Représentation", "Representation",
              getattr(cert, 'chiffre_13_2_1_representation', None), indent=8)
        _line("13.2.2", "Auto", "Voiture", "Car",
              getattr(cert, 'chiffre_13_2_2_auto', None), indent=8)
        _line("13.2.3", "Übrige", "Autres", "Others",
              getattr(cert, 'chiffre_13_2_3_autres', None), indent=8,
              art_field=True)

        # 13.3
        _line("13.3", "Beiträge an die Weiterbildung",
              "Contributions au perfectionnement",
              "Contributions to further education",
              getattr(cert, 'chiffre_13_3_formation', None), indent=3)

        # ── Chiffre 14 : Autres prestations accessoires ──
        _separator()
        c.setFont('Helvetica', 6.5)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "14.")
        c.drawString(ML + 8 * mm, y,
                     "Weitere Gehaltsnebenleistungen – Autres prestations salariales accessoires – "
                     "Further fringe benefits")
        y -= lh
        # Ligne Art / Genre / Kind
        c.setFont('Helvetica', 6)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 60 * mm, y, "Art – Genre – Kind")
        self._field_bg(c, ML + 85 * mm, y - 1 * mm, 80 * mm, 4 * mm)
        if getattr(cert, 'chiffre_14_autres', None):
            c.setFillColor(NOIR)
            c.setFont('Helvetica', 7)
            c.drawString(ML + 86 * mm, y, str(cert.chiffre_14_autres)[:50])
        y -= lh

        # ── Chiffre 15 : Remarques ──
        _separator()
        c.setFont('Helvetica', 6.5)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "15.")
        c.drawString(ML + 8 * mm, y,
                     "Bemerkungen – Observations – Comments")
        y -= 3 * mm
        # Lignes de remarques
        self._field_bg(c, ML + 25 * mm, y - 1 * mm, CONTENT_W - 25 * mm, 4 * mm)
        if cert.remarques:
            c.setFont('Helvetica', 7)
            c.setFillColor(NOIR)
            lignes = cert.remarques.split('\n')[:2]
            c.drawString(ML + 26 * mm, y, lignes[0][:80] if lignes else '')
            if len(lignes) > 1:
                y -= 4.5 * mm
                self._field_bg(c, ML + 25 * mm, y - 1 * mm, CONTENT_W - 25 * mm, 4 * mm)
                c.drawString(ML + 26 * mm, y, lignes[1][:80])
        y -= lh

        return y

    def _draw_section_i(self, c, y_start):
        """Section I : lieu, date, signature, certification."""
        y = y_start - 3 * mm
        cert = self.cert

        self._hline(c, ML, PW - MR, y + 2 * mm, NOIR, 0.8)

        # I. Ort und Datum
        c.setFont('Helvetica-Bold', 7)
        c.setFillColor(NOIR)
        c.drawString(ML, y, "I")
        c.setFont('Helvetica', 6.5)
        c.drawString(ML + 5 * mm, y, "Ort und Datum – Lieu et date – Place and date")

        # Champ lieu/date
        lieu = cert.lieu_signature or (self.adresse_client.localite if self.adresse_client else '')
        date_sig = cert.date_signature or date_class.today()
        self._field_bg(c, ML + 5 * mm, y - 6 * mm, 50 * mm, 5 * mm)
        c.setFont('Helvetica', 8)
        c.setFillColor(NOIR)
        c.drawString(ML + 6 * mm, y - 5 * mm, f"{lieu}, {date_sig.strftime('%d.%m.%Y')}")

        # Certification (à droite)
        cert_x = 100 * mm
        c.setFont('Helvetica', 5.5)
        c.setFillColor(NOIR)
        c.drawString(cert_x, y, "Die Richtigkeit und Vollständigkeit bestätigt")
        c.drawString(cert_x, y - 3 * mm, "inkl. genauer Anschrift und Telefonnummer des Arbeitgebers")
        y -= 6 * mm
        c.drawString(cert_x, y, "Certifié exact et complet")
        c.drawString(cert_x, y - 3 * mm, "y.c. adresse et numéro de téléphone exacts de l'employeur")
        y -= 6 * mm
        c.drawString(cert_x, y, "Correct and complete")
        c.drawString(cert_x, y - 3 * mm, "including exact address and telephone number of employer")

        # Ligne de signature
        y -= 8 * mm
        self._hline(c, ML + 5 * mm, ML + 60 * mm, y, NOIR, 0.5)
        c.setFont('Helvetica', 6)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML + 5 * mm, y - 3 * mm, "Unterschrift / Signature")

        if cert.nom_signataire:
            c.setFont('Helvetica', 7)
            c.setFillColor(NOIR)
            c.drawString(ML + 5 * mm, y + 2 * mm, cert.nom_signataire)

        return y

    def _draw_footer(self, c):
        """Pied de page : numéro du formulaire."""
        c.setFont('Helvetica', 5.5)
        c.setFillColor(GRIS_TEXTE)
        c.drawString(ML, 8 * mm, "Form. 11 dfe 01.21")

        # Texte vertical gauche (orientation 90°)
        c.saveState()
        c.translate(5 * mm, PH / 2)
        c.rotate(90)
        c.setFont('Helvetica', 5)
        c.drawCentredString(0, 0,
                            "Bitte die Wegleitung beachten – Observer s.v.p. la directive – "
                            "Please consider the guidance")
        c.restoreState()

    # ── Génération principale ──────────────────────────────────────

    def generer(self):
        """Génère le PDF Formulaire 11 et retourne les bytes."""
        buffer = io.BytesIO()
        c = pdf_canvas.Canvas(buffer, pagesize=A4)
        c.setTitle(f"Formulaire 11 - {self.employe.nom} {self.employe.prenom} - {self.cert.annee}")

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

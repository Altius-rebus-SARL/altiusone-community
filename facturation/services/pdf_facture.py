"""
Service de generation PDF pour les factures.

Extrait de Facture.generer_pdf() pour permettre la personnalisation
via le Document Studio (couleurs, polices, marges, textes, blocs).
"""
import io
import logging

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.pdfgen import canvas as pdf_canvas

from core.services.pdf_studio_styles import get_default_style_config, merge_style_config

logger = logging.getLogger(__name__)


class FacturePDF:
    """Generateur PDF pour les factures avec support de style configurable."""

    def __init__(self, facture, style_config=None, avec_qr_bill=False):
        self.facture = facture
        self.avec_qr_bill = avec_qr_bill
        self._devise_code = None

        defaults = get_default_style_config('FACTURE')
        self.style = merge_style_config(defaults, style_config or {})

        # Couleurs resolues
        self._color_primary = self._hex(self.style.get('couleur_primaire', '#088178'))
        self._color_accent = self._hex(self.style.get('couleur_accent', '#2c3e50'))
        self._color_text = self._hex(self.style.get('couleur_texte', '#333333'))

        # Police (ReportLab font families)
        self._font = self.style.get('police', 'Helvetica')
        FONT_BOLD_MAP = {
            'Helvetica': 'Helvetica-Bold',
            'Times-Roman': 'Times-Bold',
            'Courier': 'Courier-Bold',
        }
        FONT_OBLIQUE_MAP = {
            'Helvetica': 'Helvetica-Oblique',
            'Times-Roman': 'Times-Italic',
            'Courier': 'Courier-Oblique',
        }
        self._font_bold = FONT_BOLD_MAP.get(self._font, self._font + '-Bold')
        self._font_oblique = FONT_OBLIQUE_MAP.get(self._font, self._font)

        # Marges
        self._margin_left = self.style.get('marge_gauche', 20) * mm
        self._margin_right = self.style.get('marge_droite', 15) * mm
        self._margin_top = self.style.get('marge_haut', 20) * mm
        self._margin_bottom = self.style.get('marge_bas', 25) * mm

        # Textes et blocs
        self._textes = self.style.get('textes', {})
        self._blocs = self.style.get('blocs_visibles', {})

    @property
    def devise_code(self):
        """Code devise depuis le regime fiscal du mandat, fallback CHF."""
        if self._devise_code is None:
            try:
                self._devise_code = self.facture.mandat.config_tva.regime.devise_defaut.code
            except (AttributeError, Exception):
                self._devise_code = 'CHF'
        return self._devise_code

    @staticmethod
    def _hex(color_value):
        """Convertit une valeur de couleur en HexColor."""
        if isinstance(color_value, str):
            return HexColor(color_value)
        return color_value

    def generer(self):
        """Genere le PDF et retourne les bytes."""
        facture = self.facture
        width, height = A4

        # QR-Bill: generer le QR code si necessaire
        if self.avec_qr_bill:
            if not facture.qr_reference:
                facture.generer_qr_reference()
            try:
                facture.generer_qr_bill()
                facture.refresh_from_db(fields=['qr_code_image'])
            except Exception as e:
                logger.warning(f"Impossible de generer le QR-Bill: {e}")

        buffer = io.BytesIO()
        p = pdf_canvas.Canvas(buffer, pagesize=A4)

        y = self._draw_header(p, width, height)
        y = self._draw_emetteur(p, y)
        self._draw_destinataire(p, width, height)
        y = self._draw_info_facture(p, y, width, height)
        y = self._draw_lignes(p, y, width, height)
        y = self._draw_totaux(p, y, width)
        self._draw_conditions(p, y)

        if self.avec_qr_bill:
            p.showPage()
            self._draw_qr_bill_page(p, width, height)

        p.save()
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content

    def _draw_header(self, p, width, height):
        """Dessine l'en-tete de la facture."""
        y = height - self._margin_top

        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 18)
        p.drawString(self._margin_left, y, "FACTURE")

        p.setFont(self._font_bold, 12)
        p.drawRightString(width - self._margin_right, y, f"N° {self.facture.numero_facture}")

        p.setFillColor(self._color_text)
        return y

    def _draw_emetteur(self, p, y_start):
        """Dessine les informations de l'emetteur (gauche)."""
        y = y_start - 2 * cm

        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 10)
        p.drawString(self._margin_left, y, self.facture.mandat.client.raison_sociale)

        p.setFillColor(self._color_text)
        p.setFont(self._font, 9)
        y -= 0.45 * cm
        adresse = self.facture.mandat.client.adresse_siege
        if adresse:
            p.drawString(self._margin_left, y, f"{adresse.rue} {adresse.numero}")
            y -= 0.4 * cm
            if adresse.complement:
                p.drawString(self._margin_left, y, adresse.complement)
                y -= 0.4 * cm
            p.drawString(self._margin_left, y, f"{adresse.npa} {adresse.localite}")
            y -= 0.4 * cm
        if self.facture.mandat.client.tva_number:
            p.drawString(self._margin_left, y, f"N° TVA: {self.facture.mandat.client.tva_number}")

        return y

    def _draw_destinataire(self, p, width, height):
        """Dessine les informations du destinataire (droite)."""
        y_right = height - self._margin_top - 2 * cm
        x_right = 11.5 * cm

        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 9)
        p.drawString(x_right, y_right, "Adressée à:")
        y_right -= 0.5 * cm

        p.setFillColor(self._color_text)
        p.setFont(self._font, 9)
        p.drawString(x_right, y_right, self.facture.client.raison_sociale)
        y_right -= 0.4 * cm

        adresse_client = self.facture.client.adresse_correspondance or self.facture.client.adresse_siege
        if adresse_client:
            p.drawString(x_right, y_right, f"{adresse_client.rue} {adresse_client.numero}")
            y_right -= 0.4 * cm
            if adresse_client.complement:
                p.drawString(x_right, y_right, adresse_client.complement)
                y_right -= 0.4 * cm
            p.drawString(x_right, y_right, f"{adresse_client.npa} {adresse_client.localite}")
            y_right -= 0.4 * cm
        if self.facture.client.tva_number:
            p.drawString(x_right, y_right, f"N° TVA: {self.facture.client.tva_number}")

    def _draw_info_facture(self, p, y_start, width, height):
        """Dessine le bloc d'informations de la facture."""
        y = height - 8.5 * cm

        # Fond gris clair
        p.setFillColor(colors.Color(0.95, 0.95, 0.95))
        p.rect(self._margin_left, y - 1.2 * cm,
               width - self._margin_left - self._margin_right, 1.5 * cm, fill=1, stroke=0)
        p.setFillColor(self._color_text)

        y -= 0.1 * cm
        p.setFont(self._font, 9)
        p.drawString(self._margin_left + 0.3 * cm, y,
                     f"Date d'émission: {self.facture.date_emission.strftime('%d.%m.%Y')}")
        p.drawString(7 * cm, y,
                     f"Échéance: {self.facture.date_echeance.strftime('%d.%m.%Y')}")

        if self.facture.date_service_debut and self.facture.date_service_fin:
            p.drawString(12 * cm, y,
                         f"Période: {self.facture.date_service_debut.strftime('%d.%m.%Y')} - "
                         f"{self.facture.date_service_fin.strftime('%d.%m.%Y')}")

        # Introduction
        intro_text = self._textes.get('introduction') or self.facture.introduction
        if intro_text and self._blocs.get('introduction', True):
            y -= 1.2 * cm
            p.setFont(self._font, 9)
            intro_lines = self._wrap_text(intro_text, 100)
            for line in intro_lines[:3]:
                p.drawString(self._margin_left, y, line)
                y -= 0.4 * cm

        return y

    def _draw_lignes(self, p, y_start, width, height):
        """Dessine le tableau des lignes de facture."""
        y = y_start - 0.8 * cm

        col_widths = [8 * cm, 2 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm]

        def dessiner_entete_tableau(canvas, y_pos):
            r, g, b = self._color_primary.red, self._color_primary.green, self._color_primary.blue
            canvas.setFillColor(colors.Color(r, g, b))
            canvas.rect(self._margin_left, y_pos - 0.5 * cm, sum(col_widths), 0.7 * cm, fill=1, stroke=0)
            canvas.setFillColor(colors.white)

            canvas.setFont(self._font_bold, 9)
            x = self._margin_left + 0.2 * cm
            canvas.drawString(x, y_pos - 0.3 * cm, "Description")
            x += col_widths[0]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "Qté")
            x += col_widths[1]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "Prix unit.")
            x += col_widths[2]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "TVA")
            x += col_widths[3]
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, "Total HT")

            canvas.setFillColor(self._color_text)
            return y_pos - 0.9 * cm

        def nouvelle_page_suite(canvas, current_y):
            canvas.showPage()
            canvas.setFillColor(self._color_text)
            canvas.setFont(self._font, 8)
            canvas.drawString(self._margin_left, height - 1.5 * cm,
                              f"Facture {self.facture.numero_facture} - Suite")
            canvas.drawRightString(width - self._margin_right, height - 1.5 * cm,
                                   f"Page {canvas.getPageNumber()}")
            canvas.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
            canvas.line(self._margin_left, height - 1.8 * cm,
                        width - self._margin_right, height - 1.8 * cm)
            new_y = height - 2.5 * cm
            new_y = dessiner_entete_tableau(canvas, new_y)
            return new_y

        y = dessiner_entete_tableau(p, y)

        p.setFont(self._font, 8)
        row_height_single = 0.4 * cm
        row_height_double = 0.7 * cm
        max_desc_chars = 50
        alternate = False

        lignes_list = list(self.facture.lignes.all().order_by("ordre"))

        for ligne in lignes_list:
            desc_text = ligne.description
            if len(desc_text) <= max_desc_chars:
                desc_lines = [desc_text]
                current_row_height = row_height_single
            else:
                cut_point = desc_text[:max_desc_chars].rfind(' ')
                if cut_point == -1 or cut_point < max_desc_chars // 2:
                    cut_point = max_desc_chars
                line1 = desc_text[:cut_point].strip()
                line2 = desc_text[cut_point:].strip()
                if len(line2) > max_desc_chars:
                    line2 = line2[:max_desc_chars - 3] + "..."
                desc_lines = [line1, line2]
                current_row_height = row_height_double

            min_y = self._margin_bottom + 3.5 * cm
            if y - current_row_height < min_y:
                y = nouvelle_page_suite(p, y)
                alternate = False

            if alternate:
                p.setFillColor(colors.Color(0.96, 0.96, 0.96))
                p.rect(self._margin_left, y - current_row_height + 0.15 * cm,
                       sum(col_widths), current_row_height, fill=1, stroke=0)
                p.setFillColor(self._color_text)
            alternate = not alternate

            p.setFont(self._font, 8)
            x_desc = self._margin_left + 0.2 * cm
            y_desc = y
            for i, desc_line in enumerate(desc_lines):
                p.drawString(x_desc, y_desc, desc_line)
                if i == 0 and len(desc_lines) > 1:
                    y_desc -= 0.3 * cm

            x = self._margin_left + col_widths[0]
            qty_text = f"{ligne.quantite:.2f}".rstrip('0').rstrip('.')
            if ligne.unite:
                qty_text += f" {ligne.unite[:3]}"
            p.drawRightString(x - 0.2 * cm, y, qty_text)

            x += col_widths[1]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.prix_unitaire_ht:.2f}")

            x += col_widths[2]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.taux_tva:.1f}%")

            x += col_widths[3]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.montant_ht:.2f}")

            y -= current_row_height

        return y

    def _draw_totaux(self, p, y, width):
        """Dessine la section totaux."""
        col_widths = [8 * cm, 2 * cm, 2.5 * cm, 1.5 * cm, 2.5 * cm]
        y -= 0.2 * cm

        totaux_x = self._margin_left + col_widths[0] + col_widths[1]
        totaux_width = col_widths[2] + col_widths[3] + col_widths[4]

        p.setStrokeColor(colors.Color(0.7, 0.7, 0.7))
        p.line(totaux_x, y, totaux_x + totaux_width, y)
        y -= 0.35 * cm

        p.setFillColor(self._color_text)
        p.setFont(self._font, 8)
        label_x = totaux_x + 0.2 * cm
        value_x = self._margin_left + sum(col_widths) - 0.2 * cm

        # Sous-total HT
        p.drawString(label_x, y, "Sous-total HT:")
        devise = self.devise_code
        p.drawRightString(value_x, y, f"{self.facture.montant_ht:.2f} {devise}")
        y -= 0.35 * cm

        # Remise
        if self.facture.remise_pourcent and self.facture.remise_pourcent > 0:
            p.drawString(label_x, y, f"Remise ({self.facture.remise_pourcent}%):")
            p.drawRightString(value_x, y, f"-{self.facture.remise_montant:.2f} {devise}")
            y -= 0.35 * cm

        # TVA
        p.drawString(label_x, y, "TVA:")
        p.drawRightString(value_x, y, f"{self.facture.montant_tva:.2f} {devise}")
        y -= 0.35 * cm

        # Ligne avant total
        p.line(totaux_x, y + 0.1 * cm, totaux_x + totaux_width, y + 0.1 * cm)
        y -= 0.25 * cm

        # TOTAL TTC
        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 10)
        p.drawString(label_x, y, "TOTAL TTC:")
        p.drawRightString(value_x, y, f"{self.facture.montant_ttc:.2f} {devise}")

        # Montant paye
        if self.facture.montant_paye and self.facture.montant_paye > 0:
            p.setFillColor(self._color_text)
            y -= 0.4 * cm
            p.setFont(self._font, 8)
            p.drawString(label_x, y, "Déjà payé:")
            p.drawRightString(value_x, y, f"-{self.facture.montant_paye:.2f} {devise}")
            y -= 0.35 * cm
            p.setFont(self._font_bold, 9)
            p.drawString(label_x, y, "Reste à payer:")
            p.drawRightString(value_x, y, f"{self.facture.montant_restant:.2f} {devise}")

        return y

    def _draw_conditions(self, p, y):
        """Dessine les conditions et la conclusion."""
        y -= 0.5 * cm
        p.setFillColor(self._color_text)

        conditions_text = self._textes.get('conditions') or self.facture.conditions_paiement
        if conditions_text and self._blocs.get('conditions', True):
            p.setFont(self._font_bold, 8)
            p.drawString(self._margin_left, y, "Conditions de paiement:")
            y -= 0.3 * cm
            p.setFont(self._font, 7)
            cond_lines = self._wrap_text(conditions_text, 100)
            for line in cond_lines[:2]:
                p.drawString(self._margin_left, y, line)
                y -= 0.28 * cm

        conclusion_text = self._textes.get('conclusion') or self.facture.conclusion
        if conclusion_text and self._blocs.get('conclusion', True):
            y -= 0.2 * cm
            p.setFont(self._font_oblique, 7)
            concl_lines = self._wrap_text(conclusion_text, 100)
            for line in concl_lines[:2]:
                p.drawString(self._margin_left, y, line)
                y -= 0.28 * cm

    def _draw_qr_bill_page(self, p, width, height):
        """Dessine la page QR-Bill."""
        p.setFillColor(self._color_text)
        p.setFont(self._font, 9)
        p.drawString(self._margin_left, height - 1.5 * cm,
                     f"Facture {self.facture.numero_facture}")
        p.setFont(self._font_bold, 11)
        p.drawString(self._margin_left, height - 2.2 * cm, "Bulletin de versement")

        p.setFont(self._font, 9)
        p.drawString(self._margin_left, height - 3.2 * cm,
                     f"Montant à payer: {self.devise_code} {self.facture.montant_restant:.2f}")
        p.drawString(self._margin_left, height - 3.7 * cm,
                     f"Échéance: {self.facture.date_echeance.strftime('%d.%m.%Y')}")

        self.facture._ajouter_qr_bill(p, width, height)

    @staticmethod
    def _wrap_text(text, max_chars):
        """Decoupe un texte en lignes de max_chars caracteres."""
        if not text:
            return []
        words = text.replace('\n', ' ').split()
        lines = []
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 <= max_chars:
                current_line += (" " if current_line else "") + word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

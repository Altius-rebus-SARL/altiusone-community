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
        self._devise_cache = None
        self._regime_cache = None

        defaults = get_default_style_config('FACTURE')
        self.style = merge_style_config(defaults, style_config or {})

        # Couleurs resolues
        self._color_primary = self._hex(self.style.get('couleur_primaire', '#02312e'))
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
    def _regime(self):
        """Régime fiscal résolu (cache)."""
        if self._regime_cache is None:
            self._regime_cache = self.facture.regime_fiscal or getattr(
                self.facture.mandat, 'regime_fiscal', None
            ) or False  # False = "déjà cherché, pas trouvé"
        return self._regime_cache or None

    @property
    def _devise_obj(self):
        """Objet Devise résolu depuis la facture (cache)."""
        if self._devise_cache is None:
            try:
                self._devise_cache = self.facture.devise
            except Exception:
                from core.models import Devise
                self._devise_cache = Devise.objects.filter(code='CHF').first()
        return self._devise_cache

    @property
    def devise_code(self):
        """Code devise (CHF, EUR, XAF…)."""
        d = self._devise_obj
        return d.code if d else 'CHF'

    @property
    def _nom_taxe(self):
        """Nom de la taxe selon le régime (TVA, VAT, IVA…)."""
        r = self._regime
        return r.nom_taxe if r else 'TVA'

    def _fmt(self, value):
        """Formate un montant selon la devise de la facture (séparateurs dynamiques)."""
        from decimal import Decimal, InvalidOperation
        if value is None:
            return '0.00'
        try:
            val = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return f"{value:.2f}"
        d = self._devise_obj
        sep_milliers = d.separateur_milliers if d else "'"
        sep_decimal = d.separateur_decimal if d else '.'
        decimales = d.decimales if d else 2
        is_negative = val < 0
        val = abs(val)
        fmt_str = f"{{:.{decimales}f}}"
        parts = fmt_str.format(val).split('.')
        entier = parts[0]
        partie_dec = parts[1] if len(parts) > 1 else '00'
        result = ''
        for i, digit in enumerate(reversed(entier)):
            if i > 0 and i % 3 == 0:
                result = sep_milliers + result
            result = digit + result
        formatted = f"{result}{sep_decimal}{partie_dec}"
        if is_negative:
            formatted = f"-{formatted}"
        return formatted

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

        if self.avec_qr_bill and self._regime and self._regime.code == 'CH':
            p.showPage()
            self._draw_qr_bill_page(p, width, height)

        p.save()
        pdf_content = buffer.getvalue()
        buffer.close()
        return pdf_content

    def _get_entreprise(self):
        """Retourne l'entreprise émettrice (fiduciaire), avec cache."""
        if not hasattr(self, '_entreprise'):
            from core.models import Entreprise
            self._entreprise = Entreprise.objects.filter(est_defaut=True).first()
        return self._entreprise

    def _draw_header(self, p, width, height):
        """Dessine l'en-tete avec logo de l'entreprise."""
        y = height - self._margin_top
        entreprise = self._get_entreprise()

        # Logo de l'entreprise (gauche)
        logo_drawn = False
        if self._blocs.get('logo', True) and entreprise and entreprise.logo and entreprise.logo.name:
            try:
                from reportlab.lib.utils import ImageReader
                import io as _io

                # Lire le fichier logo (compatible S3 et local)
                logo_data = entreprise.logo.read()
                entreprise.logo.seek(0)

                logo_name = entreprise.logo.name.lower()
                if logo_name.endswith('.svg'):
                    # SVG → convertir via svglib
                    import tempfile, os
                    from svglib.svglib import svg2rlg
                    from reportlab.graphics import renderPDF

                    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp:
                        tmp.write(logo_data)
                        tmp_path = tmp.name
                    drawing = svg2rlg(tmp_path)
                    os.unlink(tmp_path)
                    if drawing:
                        logo_height = 1.5 * cm
                        scale = logo_height / drawing.height
                        logo_width = drawing.width * scale
                        if logo_width > 5 * cm:
                            logo_width = 5 * cm
                            scale = logo_width / drawing.width
                        drawing.width *= scale
                        drawing.height *= scale
                        drawing.scale(scale, scale)
                        renderPDF.draw(drawing, p, self._margin_left, y - logo_height + 0.3 * cm)
                        logo_drawn = True
                else:
                    # PNG/JPG → ImageReader
                    logo_reader = ImageReader(_io.BytesIO(logo_data))
                    logo_height = 1.5 * cm
                    logo_width = 4 * cm
                    p.drawImage(
                        logo_reader,
                        self._margin_left, y - logo_height + 0.3 * cm,
                        width=logo_width, height=logo_height,
                        preserveAspectRatio=True, mask='auto',
                    )
                    logo_drawn = True
            except Exception:
                pass

        # Titre dynamique selon le type
        TITRES = {'FACTURE': 'FACTURE', 'DEVIS': 'DEVIS', 'AVOIR': 'AVOIR', 'ACOMPTE': 'ACOMPTE'}
        titre = TITRES.get(self.facture.type_facture, 'FACTURE')
        title_x = self._margin_left + (4.5 * cm if logo_drawn else 0)
        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 18)
        p.drawString(title_x, y, titre)

        p.setFont(self._font_bold, 12)
        p.drawRightString(width - self._margin_right, y, f"N° {self.facture.numero_facture}")

        p.setFillColor(self._color_text)
        return y

    def _draw_emetteur(self, p, y_start):
        """Dessine les informations de l'émetteur = Entreprise (fiduciaire, gauche)."""
        y = y_start - 2 * cm
        entreprise = self._get_entreprise()

        if not entreprise:
            return y

        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 10)
        p.drawString(self._margin_left, y, entreprise.raison_sociale)

        p.setFillColor(self._color_text)
        p.setFont(self._font, 9)
        y -= 0.45 * cm

        adresse = getattr(entreprise, 'adresse', None)
        if adresse:
            if adresse.rue:
                rue_ligne = adresse.rue.strip()
                # Ajouter le numéro seulement s'il n'est pas déjà dans la rue
                if adresse.numero and adresse.numero not in rue_ligne:
                    rue_ligne = f"{rue_ligne} {adresse.numero}"
                p.drawString(self._margin_left, y, rue_ligne)
                y -= 0.4 * cm
            p.drawString(self._margin_left, y, f"{adresse.npa or ''} {adresse.localite or ''}")
            y -= 0.4 * cm
        elif entreprise.siege:
            p.drawString(self._margin_left, y, entreprise.siege)
            y -= 0.4 * cm

        # Identifiants légaux dynamiques (depuis IdentifiantLegal ou champs legacy)
        identifiants_affiches = False
        try:
            from core.models import IdentifiantLegal
            idents = IdentifiantLegal.objects.filter(
                entreprise=entreprise, is_active=True,
                type_identifiant__afficher_sur_facture=True,
            ).select_related('type_identifiant').order_by('type_identifiant__ordre')
            for ident in idents[:3]:
                p.drawString(self._margin_left, y, f"{ident.type_identifiant.code}: {ident.valeur}")
                y -= 0.4 * cm
                identifiants_affiches = True
        except Exception:
            pass
        # Fallback : champs legacy si pas d'identifiants en DB
        if not identifiants_affiches and entreprise.tva_number:
            p.drawString(self._margin_left, y, f"N° {self._nom_taxe}: {entreprise.tva_number}")
            y -= 0.4 * cm
        if entreprise.telephone:
            p.drawString(self._margin_left, y, f"Tél: {entreprise.telephone}")
            y -= 0.4 * cm
        if entreprise.email:
            p.drawString(self._margin_left, y, entreprise.email)

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
            rue_dest = adresse_client.rue.strip()
            if adresse_client.numero and adresse_client.numero not in rue_dest:
                rue_dest = f"{rue_dest} {adresse_client.numero}"
            p.drawString(x_right, y_right, rue_dest)
            y_right -= 0.4 * cm
            if adresse_client.complement:
                p.drawString(x_right, y_right, adresse_client.complement)
                y_right -= 0.4 * cm
            p.drawString(x_right, y_right, f"{adresse_client.npa} {adresse_client.localite}")
            y_right -= 0.4 * cm
        # Identifiants légaux du client
        client_idents_affiches = False
        try:
            from core.models import IdentifiantLegal
            client_idents = IdentifiantLegal.objects.filter(
                client=self.facture.client, is_active=True,
                type_identifiant__afficher_sur_facture=True,
            ).select_related('type_identifiant').order_by('type_identifiant__ordre')
            for ident in client_idents[:2]:
                p.drawString(x_right, y_right, f"{ident.type_identifiant.code}: {ident.valeur}")
                y_right -= 0.4 * cm
                client_idents_affiches = True
        except Exception:
            pass
        if not client_idents_affiches and self.facture.client.tva_number:
            p.drawString(x_right, y_right, f"N° {self._nom_taxe}: {self.facture.client.tva_number}")

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
            canvas.drawRightString(x - 0.2 * cm, y_pos - 0.3 * cm, self._nom_taxe)
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
            p.drawRightString(x - 0.2 * cm, y, self._fmt(ligne.prix_unitaire_ht))

            x += col_widths[2]
            p.drawRightString(x - 0.2 * cm, y, f"{ligne.taux_tva:.1f}%")

            x += col_widths[3]
            p.drawRightString(x - 0.2 * cm, y, self._fmt(ligne.montant_ht))

            y -= current_row_height

        return y

    def _draw_totaux(self, p, y, width):
        """Dessine la section totaux avec ventilation TVA multi-taux."""
        from collections import OrderedDict
        from decimal import Decimal

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
        devise = self.devise_code

        # Sous-total HT
        p.drawString(label_x, y, "Sous-total HT:")
        p.drawRightString(value_x, y, f"{self._fmt(self.facture.montant_ht)} {devise}")
        y -= 0.35 * cm

        # Remise
        if self.facture.remise_pourcent and self.facture.remise_pourcent > 0:
            p.drawString(label_x, y, f"Remise ({self.facture.remise_pourcent}%):")
            p.drawRightString(value_x, y, f"-{self._fmt(self.facture.remise_montant)} {devise}")
            y -= 0.35 * cm

        # Ventilation TVA par taux
        tva_par_taux = OrderedDict()
        for ligne in self.facture.lignes.all().order_by('taux_tva'):
            taux = ligne.taux_tva or Decimal('0')
            if taux not in tva_par_taux:
                tva_par_taux[taux] = {'base': Decimal('0'), 'tva': Decimal('0')}
            tva_par_taux[taux]['base'] += ligne.montant_ht
            tva_par_taux[taux]['tva'] += ligne.montant_tva

        if len(tva_par_taux) > 1:
            # Multi-taux : une ligne par taux
            tva_totale = Decimal('0')
            for taux, montants in tva_par_taux.items():
                if montants['tva'] > 0:
                    p.drawString(label_x, y,
                                 f"{self._nom_taxe} {taux:.1f}% (sur {self._fmt(montants['base'])}):")
                    p.drawRightString(value_x, y, f"{self._fmt(montants['tva'])} {devise}")
                    tva_totale += montants['tva']
                    y -= 0.35 * cm

            # Total TVA
            p.setFont(self._font_bold, 8)
            p.drawString(label_x, y, f"Total {self._nom_taxe}:")
            p.drawRightString(value_x, y, f"{self._fmt(tva_totale)} {devise}")
            p.setFont(self._font, 8)
            y -= 0.35 * cm
        else:
            # Taux unique : ligne simple
            p.drawString(label_x, y, f"{self._nom_taxe}:")
            p.drawRightString(value_x, y, f"{self._fmt(self.facture.montant_tva)} {devise}")
            y -= 0.35 * cm

        # Ligne avant total
        p.line(totaux_x, y + 0.1 * cm, totaux_x + totaux_width, y + 0.1 * cm)
        y -= 0.25 * cm

        # TOTAL TTC
        p.setFillColor(self._color_accent)
        p.setFont(self._font_bold, 10)
        p.drawString(label_x, y, "TOTAL TTC:")
        p.drawRightString(value_x, y, f"{self._fmt(self.facture.montant_ttc)} {devise}")

        # Montant paye
        if self.facture.montant_paye and self.facture.montant_paye > 0:
            p.setFillColor(self._color_text)
            y -= 0.4 * cm
            p.setFont(self._font, 8)
            p.drawString(label_x, y, "Déjà payé:")
            p.drawRightString(value_x, y, f"-{self._fmt(self.facture.montant_paye)} {devise}")
            y -= 0.35 * cm
            p.setFont(self._font_bold, 9)
            p.drawString(label_x, y, "Reste à payer:")
            p.drawRightString(value_x, y, f"{self._fmt(self.facture.montant_restant)} {devise}")

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

        # Mentions légales dynamiques (générées selon le régime fiscal)
        mentions = self.facture.mentions_legales_generees
        if mentions and mentions.strip():
            y -= 0.4 * cm
            p.setFont(self._font, 6)
            p.setFillColor(HexColor('#999999'))
            for line in mentions.strip().split('\n')[:5]:
                p.drawString(self._margin_left, y, line.strip())
                y -= 0.22 * cm
            p.setFillColor(self._color_text)

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

"""
Styles partages pour les generateurs PDF du module salaires.

Fournit une palette de couleurs, des styles de paragraphe, des helpers de formatage
et des factories de document/table reutilisables par les 4 generateurs.
"""
import os
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ==============================================================================
# Palette de couleurs
# ==============================================================================

ALTIUSONE_GREEN = HexColor('#088178')
ALTIUSONE_GREEN_LIGHT = HexColor('#e8f5f3')
ALTIUSONE_DARK = HexColor('#2c3e50')
ALTIUSONE_GREY = HexColor('#666666')
ALTIUSONE_GREY_LIGHT = HexColor('#f8f9fa')
ALTIUSONE_BORDER = HexColor('#dee2e6')
ALTIUSONE_RED = HexColor('#c0392b')
ALTIUSONE_GREEN_AMOUNT = HexColor('#27ae60')
ALTIUSONE_WHITE = colors.white

PAGE_WIDTH, PAGE_HEIGHT = A4

# ==============================================================================
# Logo
# ==============================================================================

LOGO_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'static', 'chartes', 'logo.svg'
)


def get_logo_image(width=3 * cm, height=None):
    """
    Charge le logo SVG et retourne un Image flowable ReportLab.
    Retourne None si le fichier n'existe pas ou si svglib n'est pas disponible.
    """
    if not os.path.isfile(LOGO_PATH):
        return None
    try:
        from svglib.svglib import svg2rlg
        drawing = svg2rlg(LOGO_PATH)
        if drawing is None:
            return None
        # Calculer le ratio pour la largeur demandee
        scale = width / drawing.width
        drawing.width = width
        drawing.height = drawing.height * scale
        drawing.scale(scale, scale)
        if height is not None:
            scale_h = height / drawing.height
            drawing.height = height
            drawing.scale(1, scale_h)
        return drawing
    except Exception:
        return None


# ==============================================================================
# Formatage suisse
# ==============================================================================

def format_montant_suisse(montant):
    """Formate un montant au format suisse: 1'234.56"""
    if montant is None:
        return ""
    val = Decimal(str(montant))
    if val == 0:
        return ""
    return f"{val:,.2f}".replace(',', "'")


def format_montant_chf(montant):
    """Formate un montant avec prefixe CHF: CHF 1'234.56"""
    formatted = format_montant_suisse(montant)
    if not formatted:
        return ""
    return f"CHF {formatted}"


# ==============================================================================
# Styles de paragraphe
# ==============================================================================

def get_salaires_styles():
    """Factory retournant tous les ParagraphStyle pour les PDF salaires."""
    base = getSampleStyleSheet()

    styles = {
        'doc_title': ParagraphStyle(
            'doc_title',
            parent=base['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            textColor=ALTIUSONE_DARK,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
            spaceBefore=0,
        ),
        'doc_subtitle': ParagraphStyle(
            'doc_subtitle',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=ALTIUSONE_GREY,
            alignment=TA_CENTER,
            spaceAfter=6 * mm,
        ),
        'section_title': ParagraphStyle(
            'section_title',
            parent=base['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            textColor=ALTIUSONE_GREEN,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        'label': ParagraphStyle(
            'label',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=ALTIUSONE_GREY,
            leading=12,
        ),
        'value': ParagraphStyle(
            'value',
            parent=base['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=ALTIUSONE_DARK,
            leading=12,
        ),
        'amount_positive': ParagraphStyle(
            'amount_positive',
            parent=base['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=ALTIUSONE_GREEN_AMOUNT,
            alignment=TA_RIGHT,
            leading=12,
        ),
        'amount_negative': ParagraphStyle(
            'amount_negative',
            parent=base['Normal'],
            fontName='Helvetica-Bold',
            fontSize=9,
            textColor=ALTIUSONE_RED,
            alignment=TA_RIGHT,
            leading=12,
        ),
        'total_label': ParagraphStyle(
            'total_label',
            parent=base['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=ALTIUSONE_DARK,
            leading=14,
        ),
        'total_amount': ParagraphStyle(
            'total_amount',
            parent=base['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=ALTIUSONE_DARK,
            alignment=TA_RIGHT,
            leading=14,
        ),
        'footer': ParagraphStyle(
            'footer',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=7,
            textColor=ALTIUSONE_GREY,
            alignment=TA_CENTER,
            leading=9,
        ),
        'body_justify': ParagraphStyle(
            'body_justify',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            alignment=TA_JUSTIFY,
            textColor=ALTIUSONE_DARK,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        ),
        'body_left': ParagraphStyle(
            'body_left',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=15,
            alignment=TA_LEFT,
            textColor=ALTIUSONE_DARK,
        ),
        'employer_name': ParagraphStyle(
            'employer_name',
            parent=base['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=ALTIUSONE_DARK,
            leading=16,
        ),
        'employer_detail': ParagraphStyle(
            'employer_detail',
            parent=base['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=ALTIUSONE_GREY,
            leading=12,
        ),
        'confidential': ParagraphStyle(
            'confidential',
            parent=base['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=7,
            textColor=ALTIUSONE_GREY,
            alignment=TA_CENTER,
            leading=9,
        ),
    }
    return styles


# ==============================================================================
# Ligne verte decorative (flowable)
# ==============================================================================

class GreenLine(Flowable):
    """Ligne horizontale verte decorative."""

    def __init__(self, width=None, thickness=1.5):
        super().__init__()
        self._line_width = width
        self._thickness = thickness

    def wrap(self, avail_width, avail_height):
        self.width = self._line_width or avail_width
        self.height = self._thickness + 2 * mm
        return self.width, self.height

    def draw(self):
        self.canv.setStrokeColor(ALTIUSONE_GREEN)
        self.canv.setLineWidth(self._thickness)
        self.canv.line(0, mm, self.width, mm)


# ==============================================================================
# Document factory avec header/footer
# ==============================================================================

def _build_header_footer(canvas, doc, title="", confidential=True):
    """Dessine header/footer brande sur chaque page."""
    canvas.saveState()
    width, height = A4

    # --- Header: ligne verte fine en haut ---
    canvas.setStrokeColor(ALTIUSONE_GREEN)
    canvas.setLineWidth(2)
    canvas.line(15 * mm, height - 10 * mm, width - 15 * mm, height - 10 * mm)

    # Logo en haut a gauche (petit)
    logo = get_logo_image(width=1.8 * cm)
    if logo:
        logo.drawOn(canvas, 15 * mm, height - 9.5 * mm - 0.3 * cm)

    # Titre en haut au centre
    if title:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(ALTIUSONE_GREY)
        canvas.drawCentredString(width / 2, height - 9 * mm, title)

    # --- Footer ---
    canvas.setStrokeColor(ALTIUSONE_GREEN)
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 12 * mm, width - 15 * mm, 12 * mm)

    # Numero de page
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(ALTIUSONE_GREY)
    canvas.drawRightString(width - 15 * mm, 8 * mm, f"Page {doc.page}")

    # Mention confidentiel
    if confidential:
        canvas.setFont("Helvetica-Oblique", 6)
        canvas.drawCentredString(
            width / 2, 8 * mm,
            "Ce document est confidentiel et destine uniquement a son destinataire."
        )

    canvas.restoreState()


def create_salaire_doc(buffer, title="", confidential=True, margins=None):
    """
    Factory pour SimpleDocTemplate avec header/footer integre.

    Args:
        buffer: BytesIO buffer
        title: Titre affiche dans le header
        confidential: Afficher mention de confidentialite dans le footer
        margins: dict avec top, bottom, left, right en unites ReportLab (defaut 20mm)

    Returns:
        SimpleDocTemplate configure
    """
    m = margins or {}
    top = m.get('top', 18 * mm)
    bottom = m.get('bottom', 18 * mm)
    left = m.get('left', 15 * mm)
    right = m.get('right', 15 * mm)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=top,
        bottomMargin=bottom,
        leftMargin=left,
        rightMargin=right,
        title=title,
    )

    def on_page(canvas, doc_inner):
        _build_header_footer(canvas, doc_inner, title=title, confidential=confidential)

    doc._on_page = on_page
    return doc


def build_doc(doc, elements):
    """Build le document avec le callback header/footer."""
    on_page = getattr(doc, '_on_page', None)
    if on_page:
        doc.build(elements, onFirstPage=on_page, onLaterPages=on_page)
    else:
        doc.build(elements)


# ==============================================================================
# Helpers de style Table
# ==============================================================================

def get_section_table_style():
    """Style de table pour les sections d'information (fond gris clair, bordure subtile)."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ALTIUSONE_GREY_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
        ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), ALTIUSONE_GREY),
        ('TEXTCOLOR', (1, 0), (-1, -1), ALTIUSONE_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])


def get_header_table_style():
    """Style pour header de table avec fond vert et texte blanc."""
    return [
        ('BACKGROUND', (0, 0), (-1, 0), ALTIUSONE_GREEN),
        ('TEXTCOLOR', (0, 0), (-1, 0), ALTIUSONE_WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
    ]


def get_alternating_row_colors(num_rows, start_row=1):
    """Retourne les commandes TableStyle pour les rangees alternees."""
    cmds = []
    for i in range(start_row, num_rows):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0, i), (-1, i), ALTIUSONE_GREY_LIGHT))
    return cmds


def get_total_row_style(row_index=-1):
    """Style pour la rangee TOTAL (fond vert clair, texte bold)."""
    return [
        ('BACKGROUND', (0, row_index), (-1, row_index), ALTIUSONE_GREEN_LIGHT),
        ('FONTNAME', (0, row_index), (-1, row_index), 'Helvetica-Bold'),
        ('FONTSIZE', (0, row_index), (-1, row_index), 10),
        ('TEXTCOLOR', (0, row_index), (-1, row_index), ALTIUSONE_DARK),
        ('TOPPADDING', (0, row_index), (-1, row_index), 6),
        ('BOTTOMPADDING', (0, row_index), (-1, row_index), 6),
    ]


def get_data_table_style(num_rows):
    """Style complet pour table de donnees avec header vert, alternating rows et grid."""
    style_cmds = get_header_table_style()
    style_cmds += get_alternating_row_colors(num_rows)
    style_cmds += [
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ('BOX', (0, 0), (-1, -1), 0.5, ALTIUSONE_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, ALTIUSONE_BORDER),
    ]
    return TableStyle(style_cmds)


# ==============================================================================
# Helpers flowables
# ==============================================================================

def make_spacer(height_mm=5):
    """Cree un Spacer de hauteur donnee en mm."""
    return Spacer(1, height_mm * mm)

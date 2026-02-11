# apps/modelforms/services/qr_service.py
"""
Service de génération de QR codes pour les formulaires publics.
"""
import base64
import io

import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import RoundedModuleDrawer


def generate_qr_code(url):
    """Génère un QR code PNG en bytes pour l'URL donnée."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)

    qr_image = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(),
        fill_color="black",
        back_color="white",
    )

    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    return buffer.getvalue()


def get_qr_code_base64(url):
    """Retourne le QR code en data URI pour inclusion inline dans le HTML."""
    png_bytes = generate_qr_code(url)
    b64 = base64.b64encode(png_bytes).decode('utf-8')
    return f"data:image/png;base64,{b64}"

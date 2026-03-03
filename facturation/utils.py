# facturation/utils.py
"""
Utilitaires pour la facturation, notamment la génération de QR-Bill suisses.

Le QR-Bill est obligatoire en Suisse depuis le 30 septembre 2022.
Format: Swiss Payment Standards (ISO 20022)
"""
import io
import qrcode
from decimal import Decimal
from django.core.files.base import ContentFile


def calculer_checksum_mod97(reference):
    """
    Calcule le checksum MOD 97-10 pour une référence QR.
    Utilisé pour les références QR structurées (QRR).
    """
    # Remplacer les lettres par des chiffres (A=10, B=11, etc.)
    reference_num = ""
    for char in reference.upper():
        if char.isdigit():
            reference_num += char
        elif char.isalpha():
            reference_num += str(ord(char) - 55)

    # Ajouter "00" à la fin pour le calcul
    reference_num += "00"

    # Calculer MOD 97
    checksum = 98 - (int(reference_num) % 97)
    return f"{checksum:02d}"


def generer_reference_qr(facture):
    """
    Génère une référence QR structurée (QRR) pour une facture.

    Format QRR (27 caractères):
    - 6 chiffres: Identifiant client
    - 20 chiffres: Référence facture
    - 1 chiffre: Checksum
    """
    # Identifiant basé sur le mandat (6 chiffres)
    mandat_id = str(facture.mandat.id.int % 1000000).zfill(6)

    # Référence facture (basée sur UUID, 20 chiffres)
    facture_ref = str(facture.id.int % 100000000000000000000).zfill(20)

    # Référence sans checksum (26 caractères)
    reference_base = mandat_id + facture_ref

    # Calculer le checksum (1 chiffre)
    checksum = str(sum(int(d) for d in reference_base) % 10)

    return reference_base + checksum


def formater_reference_qr(reference):
    """
    Formate une référence QR pour l'affichage (groupes de 5 caractères).
    Ex: "123456789012345678901234567" -> "12 34567 89012 34567 89012 34567"
    """
    # Supprimer les espaces existants
    ref = reference.replace(" ", "")

    # Grouper par 5 caractères
    groups = []
    for i in range(0, len(ref), 5):
        groups.append(ref[i:i + 5])

    return " ".join(groups)


def generer_qr_code_image(facture):
    """
    Génère l'image QR code pour un QR-Bill suisse.

    Le QR code contient les informations de paiement selon le standard
    Swiss Payment Standards.

    Returns:
        ContentFile: Image PNG du QR code
    """
    # Récupérer les informations nécessaires
    client = facture.mandat.client

    # IBAN QR (doit commencer par CH ou LI)
    iban = facture.qr_iban or ""
    if not iban:
        # Essayer de récupérer l'IBAN depuis le compte bancaire du mandat
        compte_bancaire = getattr(facture.mandat, 'compte_bancaire_principal', None)
        if compte_bancaire:
            iban = compte_bancaire.iban

    # Adresse du créditeur (celui qui émet la facture)
    adresse_crediteur = client.adresse_siege
    nom_crediteur = client.raison_sociale[:70] if client.raison_sociale else ""

    rue_crediteur = ""
    numero_crediteur = ""
    npa_crediteur = ""
    localite_crediteur = ""
    pays_crediteur = "CH"

    if adresse_crediteur:
        rue_crediteur = (adresse_crediteur.rue or "")[:70]
        numero_crediteur = (adresse_crediteur.numero or "")[:16]
        npa_crediteur = (adresse_crediteur.code_postal or "")[:16]
        localite_crediteur = (adresse_crediteur.localite or "")[:35]
        pays_crediteur = str(adresse_crediteur.pays.code) if adresse_crediteur.pays else "CH"

    # Adresse du débiteur (client de la facture)
    client_facture = facture.client
    adresse_debiteur = client_facture.adresse_siege

    nom_debiteur = client_facture.raison_sociale[:70] if client_facture.raison_sociale else ""

    rue_debiteur = ""
    numero_debiteur = ""
    npa_debiteur = ""
    localite_debiteur = ""
    pays_debiteur = "CH"

    if adresse_debiteur:
        rue_debiteur = (adresse_debiteur.rue or "")[:70]
        numero_debiteur = (adresse_debiteur.numero or "")[:16]
        npa_debiteur = (adresse_debiteur.code_postal or "")[:16]
        localite_debiteur = (adresse_debiteur.localite or "")[:35]
        pays_debiteur = str(adresse_debiteur.pays.code) if adresse_debiteur.pays else "CH"

    # Montant
    montant = f"{facture.montant_ttc:.2f}"

    # Devise
    devise = "CHF"

    # Référence QR
    reference = facture.qr_reference or ""

    # Type de référence
    if reference.startswith("RF"):
        type_reference = "SCOR"  # Référence Creditor Reference (ISO 11649)
    elif reference:
        type_reference = "QRR"  # Référence QR structurée
    else:
        type_reference = "NON"  # Sans référence

    # Informations supplémentaires
    info_supplementaire = f"Facture {facture.numero_facture}"[:140]

    # Construire le payload QR selon Swiss QR Bill Standard
    # Séparateur: retour à la ligne (\r\n)
    sep = "\r\n"

    qr_data = sep.join([
        "SPC",  # Header - Swiss Payments Code
        "0200",  # Version
        "1",  # Coding Type (UTF-8)
        iban,  # IBAN
        "S",  # Address Type (S=Structured, K=Combined)
        nom_crediteur,  # Name
        rue_crediteur + " " + numero_crediteur,  # Address Line 1
        npa_crediteur + " " + localite_crediteur,  # Address Line 2 (NPA + Localité)
        "",  # Address Line 2 (vide pour type S)
        "",  # Address Line 2 (vide pour type S)
        pays_crediteur,  # Country
        "",  # Ultimate Creditor - Address Type (vide si pas d'ultimate creditor)
        "",  # Ultimate Creditor - Name
        "",  # Ultimate Creditor - Street
        "",  # Ultimate Creditor - Building Number
        "",  # Ultimate Creditor - Postal Code
        "",  # Ultimate Creditor - City
        "",  # Ultimate Creditor - Country
        montant,  # Amount
        devise,  # Currency
        "S",  # Debtor Address Type
        nom_debiteur,  # Debtor Name
        rue_debiteur + " " + numero_debiteur,  # Debtor Street
        npa_debiteur + " " + localite_debiteur,  # Debtor City
        "",  # Debtor Country (vide pour type S)
        "",  # Debtor Country (vide pour type S)
        pays_debiteur,  # Debtor Country
        type_reference,  # Reference Type
        reference,  # Reference
        info_supplementaire,  # Unstructured Message
        "EPD",  # Trailer - End Payment Data
        "",  # Alternative Scheme Parameter 1 (optionnel)
        "",  # Alternative Scheme Parameter 2 (optionnel)
    ])

    # Générer le QR code
    qr = qrcode.QRCode(
        version=None,  # Auto-déterminer la version
        error_correction=qrcode.constants.ERROR_CORRECT_M,  # Niveau M requis par Swiss QR
        box_size=10,
        border=0,  # Pas de bordure (ajoutée séparément)
    )

    qr.add_data(qr_data)
    qr.make(fit=True)

    # Créer l'image
    img = qr.make_image(fill_color="black", back_color="white")

    # Sauvegarder dans un buffer
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)

    # Retourner comme ContentFile
    filename = f"qr_facture_{facture.numero_facture}.png"
    return ContentFile(buffer.read(), name=filename)


def generer_qr_bill_complet(facture):
    """
    Génère le QR-Bill complet (avec le récépissé).

    Le QR-Bill se compose de:
    - Section de paiement (à gauche): informations de paiement
    - Section QR (au centre): QR code
    - Récépissé (à droite): version simplifiée

    Dimensions standard:
    - Récépissé: 62 x 105 mm
    - Section de paiement: 148 x 105 mm
    - Total: 210 x 105 mm (A6 paysage)
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors

    # Dimensions
    receipt_width = 62 * mm
    payment_width = 148 * mm
    bill_height = 105 * mm

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(receipt_width + payment_width, bill_height))

    # ===== RÉCÉPISSÉ (gauche) =====
    x = 5 * mm
    y = bill_height - 5 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Récépissé")

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x, y, "Compte / Payable à")

    y -= 3 * mm
    c.setFont("Helvetica", 8)
    if facture.qr_iban:
        c.drawString(x, y, facture.qr_iban)
        y -= 3 * mm

    client = facture.mandat.client
    c.drawString(x, y, client.raison_sociale[:30])

    if client.adresse_siege:
        y -= 3 * mm
        c.drawString(x, y, f"{client.adresse_siege.code_postal} {client.adresse_siege.localite}"[:30])

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x, y, "Référence")
    y -= 3 * mm
    c.setFont("Helvetica", 8)
    c.drawString(x, y, formater_reference_qr(facture.qr_reference or "")[:30])

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x, y, "Payable par")
    y -= 3 * mm
    c.setFont("Helvetica", 8)
    c.drawString(x, y, facture.client.raison_sociale[:30])

    # Montant
    y -= 10 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x, y, "Monnaie")
    c.drawString(x + 15 * mm, y, "Montant")
    y -= 3 * mm
    c.setFont("Helvetica", 8)
    c.drawString(x, y, "CHF")
    c.drawString(x + 15 * mm, y, f"{facture.montant_ttc:,.2f}")

    # Point d'acceptation
    y = 10 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(x, y, "Point de dépôt")

    # Ligne de séparation verticale (pointillés)
    c.setDash(1, 2)
    c.line(receipt_width, 0, receipt_width, bill_height)
    c.setDash()

    # ===== SECTION DE PAIEMENT (droite) =====
    x = receipt_width + 5 * mm
    y = bill_height - 5 * mm

    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "Section paiement")

    # QR Code (au centre)
    qr_x = receipt_width + 5 * mm
    qr_y = 35 * mm
    qr_size = 46 * mm  # Taille standard Swiss QR

    # Placeholder pour QR code
    c.setStrokeColor(colors.black)
    c.rect(qr_x, qr_y, qr_size, qr_size)
    c.setFont("Helvetica", 8)
    c.drawCentredString(qr_x + qr_size / 2, qr_y + qr_size / 2, "QR Code")

    # Informations à droite du QR
    info_x = qr_x + qr_size + 5 * mm
    y = bill_height - 5 * mm

    c.setFont("Helvetica-Bold", 8)
    c.drawString(info_x, y, "Monnaie")
    c.drawString(info_x + 20 * mm, y, "Montant")

    y -= 4 * mm
    c.setFont("Helvetica", 10)
    c.drawString(info_x, y, "CHF")
    c.drawString(info_x + 20 * mm, y, f"{facture.montant_ttc:,.2f}")

    y -= 8 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(info_x, y, "Compte / Payable à")

    y -= 3 * mm
    c.setFont("Helvetica", 8)
    if facture.qr_iban:
        c.drawString(info_x, y, facture.qr_iban)
        y -= 3 * mm
    c.drawString(info_x, y, client.raison_sociale)

    if client.adresse_siege:
        y -= 3 * mm
        c.drawString(info_x, y, f"{client.adresse_siege.rue} {client.adresse_siege.numero}")
        y -= 3 * mm
        c.drawString(info_x, y, f"{client.adresse_siege.code_postal} {client.adresse_siege.localite}")

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(info_x, y, "Référence")
    y -= 3 * mm
    c.setFont("Helvetica", 8)
    c.drawString(info_x, y, formater_reference_qr(facture.qr_reference or ""))

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(info_x, y, "Informations supplémentaires")
    y -= 3 * mm
    c.setFont("Helvetica", 8)
    c.drawString(info_x, y, f"Facture {facture.numero_facture}")

    y -= 6 * mm
    c.setFont("Helvetica-Bold", 6)
    c.drawString(info_x, y, "Payable par")
    y -= 3 * mm
    c.setFont("Helvetica", 8)
    c.drawString(info_x, y, facture.client.raison_sociale)

    if facture.client.adresse_siege:
        y -= 3 * mm
        c.drawString(info_x, y, f"{facture.client.adresse_siege.code_postal} {facture.client.adresse_siege.localite}")

    c.save()
    buffer.seek(0)

    return ContentFile(buffer.read(), name=f"qr_bill_{facture.numero_facture}.pdf")

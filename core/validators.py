# core/validators.py
"""
Fonctions de validation réutilisables — IBAN, BIC, numéros suisses.

Basé sur le toolkit OCR de Paul, enrichi avec checksum ISO 13616.
"""
import re
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# IBAN
# ---------------------------------------------------------------------------

_IBAN_FORMAT_RE = re.compile(r'^[A-Z]{2}\d{2}[A-Z0-9]{4,30}$')

# Longueurs IBAN par pays (principaux partenaires suisses)
_IBAN_LENGTHS = {
    'CH': 21, 'LI': 21, 'DE': 22, 'FR': 27, 'IT': 27, 'AT': 20,
    'ES': 24, 'NL': 18, 'BE': 16, 'LU': 20, 'GB': 22, 'PT': 25,
}


def clean_iban(iban: str) -> str:
    """Nettoie un IBAN : supprime espaces/tirets, majuscules, corrige O→0."""
    if not iban:
        return ''
    # Supprimer espaces, tirets, points
    cleaned = re.sub(r'[\s\-.]', '', iban).upper()
    # Corriger les O en 0 dans la partie numérique (après les 2 lettres pays)
    if len(cleaned) > 2:
        prefix = cleaned[:2]
        rest = cleaned[2:].replace('O', '0')
        cleaned = prefix + rest
    return cleaned


def validate_iban_format(iban: str) -> bool:
    """Vérifie le format IBAN (regex + longueur pays si connue)."""
    if not iban or not _IBAN_FORMAT_RE.match(iban):
        return False
    country = iban[:2]
    expected_len = _IBAN_LENGTHS.get(country)
    if expected_len and len(iban) != expected_len:
        return False
    return True


def validate_iban_checksum(iban: str) -> bool:
    """
    Vérifie le checksum IBAN (ISO 13616 modulo 97).

    Déplace les 4 premiers caractères à la fin, convertit les lettres
    en chiffres (A=10…Z=35) et vérifie que modulo 97 == 1.
    """
    if len(iban) < 5:
        return False
    rearranged = iban[4:] + iban[:4]
    numeric = ''
    for char in rearranged:
        if char.isalpha():
            numeric += str(ord(char) - 55)  # A=10, B=11, …, Z=35
        else:
            numeric += char
    try:
        return int(numeric) % 97 == 1
    except (ValueError, OverflowError):
        return False


def validate_iban(iban: str) -> bool:
    """Validation complète : format + checksum."""
    return validate_iban_format(iban) and validate_iban_checksum(iban)


def is_qr_iban(iban: str) -> bool:
    """Vérifie si c'est un QR-IBAN suisse (IID 30000-31999)."""
    if not iban or not iban.startswith('CH') or len(iban) < 9:
        return False
    try:
        iid = int(iban[4:9])
        return 30000 <= iid <= 31999
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# BIC / SWIFT
# ---------------------------------------------------------------------------

_BIC_RE = re.compile(r'^[A-Z]{4}[A-Z]{2}[A-Z2-9]{2}([A-Z0-9]{3})?$')

_VALID_COUNTRY_CODES = {
    'AD', 'AE', 'AL', 'AT', 'AU', 'BE', 'BG', 'CA', 'CH', 'CY', 'CZ',
    'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GE', 'GR', 'HR', 'HU',
    'IE', 'IS', 'IT', 'JP', 'LI', 'LT', 'LU', 'LV', 'MC', 'MD', 'ME',
    'MK', 'MT', 'NL', 'NO', 'PL', 'PT', 'RO', 'RS', 'SE', 'SI', 'SK',
    'SM', 'TR', 'UA', 'US', 'VG', 'XK',
}


def validate_bic(bic: str) -> bool:
    """Valide un code BIC/SWIFT (8 ou 11 caractères)."""
    if not bic:
        return False
    bic = bic.replace(' ', '').upper()
    if not _BIC_RE.match(bic):
        return False
    return bic[4:6] in _VALID_COUNTRY_CODES

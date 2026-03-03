# analytics/text_analysis.py
"""
Service d'analyse de texte NLP pour les documents.

Extrait des informations structurées à partir du texte OCR des documents.
"""
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedEntity:
    """Entité extraite d'un texte."""
    type: str  # MONTANT, DATE, IBAN, TVA_NUMBER, PHONE, EMAIL, etc.
    value: Any
    raw_text: str
    confidence: float
    position: Tuple[int, int]  # (start, end)


class TextAnalyzer:
    """
    Analyseur de texte pour extraction d'entités.

    Utilise des expressions régulières et des heuristiques pour
    extraire des informations structurées du texte OCR.
    """

    # Patterns pour la Suisse
    PATTERNS = {
        # Montants CHF
        'montant_chf': [
            r'CHF\s*([\d\'\s]+[\.,]\d{2})',
            r'([\d\'\s]+[\.,]\d{2})\s*CHF',
            r'Fr\.\s*([\d\'\s]+[\.,]\d{2})',
            r'Francs?\s*([\d\'\s]+[\.,]\d{2})',
        ],

        # IBAN suisse
        'iban': [
            r'(CH\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{1})',
            r'(LI\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{1})',
        ],

        # Numéro TVA suisse (IDE)
        'tva_number': [
            r'(CHE[\-\s]?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})\s*(?:TVA|MWST)?',
            r'(?:TVA|MWST|IDE)[:\s]*(CHE[\-\s]?\d{3}[\.\s]?\d{3}[\.\s]?\d{3})',
            r'(CHE\d{9})',
        ],

        # Dates (formats suisses)
        'date': [
            r'(\d{1,2}[\./]\d{1,2}[\./]\d{2,4})',
            r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
            r'(\d{1,2}\s+(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4})',
        ],

        # Numéro de facture
        'numero_facture': [
            r'(?:Facture|Invoice|Rechnung)\s*(?:n[°o]?|Nr\.?|#)?\s*[:.]?\s*([A-Z0-9\-/]+)',
            r'(?:N[°o]|Nr\.?)\s*(?:de\s+)?(?:facture|invoice)?\s*[:.]?\s*([A-Z0-9\-/]+)',
            r'(?:Référence|Reference|Referenz)\s*[:.]?\s*([A-Z0-9\-/]+)',
        ],

        # Email
        'email': [
            r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
        ],

        # Téléphone suisse
        'telephone': [
            r'(\+41\s?\d{2}\s?\d{3}\s?\d{2}\s?\d{2})',
            r'(0\d{2}\s?\d{3}\s?\d{2}\s?\d{2})',
            r'(\d{3}\s?\d{3}\s?\d{2}\s?\d{2})',
        ],

        # Code postal suisse
        'code_postal': [
            r'(?:CH[\-\s]?)?(\d{4})\s+([A-Za-zÀ-ÿ\-\s]+)',
        ],

        # Taux TVA
        'taux_tva': [
            r'(?:TVA|MWST|MwSt)\s*(?:à|au|:)?\s*(\d+[\.,]?\d*)\s*%',
            r'(\d+[\.,]?\d*)\s*%\s*(?:TVA|MWST)',
        ],

        # Période (mois/année)
        'periode': [
            r'(?:Période|Period|Zeitraum)\s*[:.]?\s*(\d{1,2}[\./]\d{4})',
            r'(?:Mois|Month|Monat)\s*[:.]?\s*(\d{1,2}[\./]\d{4})',
        ],
    }

    # Mots-clés pour classification de documents
    DOCUMENT_KEYWORDS = {
        'FACTURE_VENTE': ['facture', 'invoice', 'rechnung', 'à payer', 'montant dû'],
        'FACTURE_ACHAT': ['facture', 'fournisseur', 'supplier', 'lieferant', 'achat'],
        'DEVIS': ['devis', 'offre', 'quotation', 'angebot', 'estimation'],
        'RELEVE_BANQUE': ['relevé', 'extrait', 'kontoauszug', 'bank statement', 'solde'],
        'FICHE_SALAIRE': ['salaire', 'bulletin', 'lohnabrechnung', 'salary', 'brut', 'net'],
        'CERTIFICAT_SALAIRE': ['certificat de salaire', 'lohnausweis', 'wage statement'],
        'CONTRAT': ['contrat', 'contract', 'vertrag', 'agreement', 'convention'],
        'ATTESTATION': ['attestation', 'bescheinigung', 'certificate', 'confirmation'],
    }

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile les patterns regex pour performance."""
        self._compiled_patterns = {}
        for entity_type, patterns in self.PATTERNS.items():
            self._compiled_patterns[entity_type] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        """
        Extrait toutes les entités d'un texte.

        Args:
            text: Texte à analyser

        Returns:
            Liste d'entités extraites
        """
        if not text:
            return []

        entities = []

        for entity_type, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    raw = match.group(0)
                    value = self._parse_value(entity_type, match)

                    if value is not None:
                        entities.append(ExtractedEntity(
                            type=entity_type.upper(),
                            value=value,
                            raw_text=raw,
                            confidence=self._calculate_confidence(entity_type, raw),
                            position=(match.start(), match.end())
                        ))

        # Dédupliquer les entités similaires
        entities = self._deduplicate_entities(entities)

        return entities

    def _parse_value(self, entity_type: str, match) -> Any:
        """Parse et normalise la valeur extraite."""
        try:
            if entity_type == 'montant_chf':
                raw = match.group(1)
                # Nettoyer le montant
                clean = raw.replace("'", "").replace(" ", "").replace(",", ".")
                return Decimal(clean)

            elif entity_type == 'iban':
                # Normaliser l'IBAN (sans espaces)
                return match.group(1).replace(" ", "")

            elif entity_type == 'tva_number':
                # Normaliser le numéro TVA
                raw = match.group(1)
                clean = re.sub(r'[\s\.\-]', '', raw)
                return clean

            elif entity_type == 'date':
                return self._parse_date(match.group(1))

            elif entity_type == 'taux_tva':
                raw = match.group(1).replace(",", ".")
                return float(raw)

            elif entity_type in ['email', 'telephone', 'numero_facture']:
                return match.group(1).strip()

            elif entity_type == 'code_postal':
                return {
                    'npa': match.group(1),
                    'localite': match.group(2).strip()
                }

            else:
                return match.group(1) if match.lastindex else match.group(0)

        except Exception as e:
            logger.debug(f"Erreur parsing {entity_type}: {e}")
            return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse une date en différents formats."""
        formats = [
            '%d.%m.%Y', '%d/%m/%Y', '%d.%m.%y', '%d/%m/%y',
            '%d %B %Y', '%d %b %Y',
        ]

        # Mois en français
        mois_fr = {
            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
        }

        # Remplacer les mois en français
        date_lower = date_str.lower()
        for mois, num in mois_fr.items():
            if mois in date_lower:
                date_str = date_lower.replace(mois, num)
                break

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        return None

    def _calculate_confidence(self, entity_type: str, raw_text: str) -> float:
        """Calcule un score de confiance pour l'extraction."""
        # Logique simple basée sur la qualité du match
        base_confidence = 0.7

        # Bonus si le format est parfait
        if entity_type == 'iban' and len(raw_text.replace(" ", "")) == 21:
            return 0.95
        if entity_type == 'tva_number' and 'CHE' in raw_text.upper():
            return 0.9
        if entity_type == 'email' and '@' in raw_text:
            return 0.9

        return base_confidence

    def _deduplicate_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Supprime les doublons et garde le meilleur match."""
        seen = {}

        for entity in entities:
            key = f"{entity.type}:{entity.value}"
            if key not in seen or entity.confidence > seen[key].confidence:
                seen[key] = entity

        return list(seen.values())

    def classify_document(self, text: str) -> Tuple[str, float]:
        """
        Classifie un document selon son contenu.

        Returns:
            Tuple (type_document, confidence)
        """
        if not text:
            return 'AUTRE', 0.0

        text_lower = text.lower()
        scores = {}

        for doc_type, keywords in self.DOCUMENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[doc_type] = score / len(keywords)

        if not scores:
            return 'AUTRE', 0.0

        best_type = max(scores, key=scores.get)
        return best_type, scores[best_type]

    def extract_invoice_data(self, text: str) -> Dict[str, Any]:
        """
        Extrait les données spécifiques d'une facture.

        Returns:
            Dict avec montant_ht, montant_tva, montant_ttc, date, numero, etc.
        """
        entities = self.extract_entities(text)
        data = {
            'numero_facture': None,
            'date_facture': None,
            'montant_ht': None,
            'montant_tva': None,
            'montant_ttc': None,
            'taux_tva': None,
            'iban': None,
            'tva_fournisseur': None,
            'email': None,
            'telephone': None,
        }

        # Regrouper par type
        by_type = {}
        for e in entities:
            if e.type not in by_type:
                by_type[e.type] = []
            by_type[e.type].append(e)

        # Extraire les valeurs
        if 'NUMERO_FACTURE' in by_type:
            data['numero_facture'] = by_type['NUMERO_FACTURE'][0].value

        if 'DATE' in by_type:
            data['date_facture'] = by_type['DATE'][0].value

        if 'MONTANT_CHF' in by_type:
            montants = sorted([e.value for e in by_type['MONTANT_CHF']], reverse=True)
            if len(montants) >= 1:
                data['montant_ttc'] = montants[0]
            if len(montants) >= 2:
                data['montant_ht'] = montants[1]
            if len(montants) >= 3:
                data['montant_tva'] = montants[2]

        if 'TAUX_TVA' in by_type:
            data['taux_tva'] = by_type['TAUX_TVA'][0].value

        if 'IBAN' in by_type:
            data['iban'] = by_type['IBAN'][0].value

        if 'TVA_NUMBER' in by_type:
            data['tva_fournisseur'] = by_type['TVA_NUMBER'][0].value

        if 'EMAIL' in by_type:
            data['email'] = by_type['EMAIL'][0].value

        if 'TELEPHONE' in by_type:
            data['telephone'] = by_type['TELEPHONE'][0].value

        return data

    def extract_salary_data(self, text: str) -> Dict[str, Any]:
        """
        Extrait les données d'une fiche de salaire.
        """
        entities = self.extract_entities(text)
        data = {
            'periode': None,
            'salaire_brut': None,
            'salaire_net': None,
            'avs_ai_apg': None,
            'ac': None,
            'lpp': None,
        }

        # Chercher les montants spécifiques avec contexte
        text_lower = text.lower()

        # Patterns spécifiques pour salaires
        patterns = {
            'salaire_brut': [r'(?:salaire\s+)?brut[:\s]*([\d\'\s]+[\.,]\d{2})', r'bruttolohn[:\s]*([\d\'\s]+[\.,]\d{2})'],
            'salaire_net': [r'(?:salaire\s+)?net[:\s]*([\d\'\s]+[\.,]\d{2})', r'nettolohn[:\s]*([\d\'\s]+[\.,]\d{2})'],
            'avs_ai_apg': [r'avs[\s/]?ai[\s/]?apg[:\s]*([\d\'\s]+[\.,]\d{2})', r'ahv[\s/]?iv[\s/]?eo[:\s]*([\d\'\s]+[\.,]\d{2})'],
            'ac': [r'(?:assurance\s+)?chômage|ac[:\s]*([\d\'\s]+[\.,]\d{2})', r'alv[:\s]*([\d\'\s]+[\.,]\d{2})'],
        }

        for field, pats in patterns.items():
            for pat in pats:
                match = re.search(pat, text, re.IGNORECASE)
                if match:
                    try:
                        raw = match.group(1)
                        clean = raw.replace("'", "").replace(" ", "").replace(",", ".")
                        data[field] = Decimal(clean)
                        break
                    except Exception:
                        pass

        return data


# Instance singleton
text_analyzer = TextAnalyzer()

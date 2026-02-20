# comptabilite/services/camt053_parser_service.py
"""
Service de parsing des releves bancaires au format camt.053 (ISO 20022).

Supporte les versions 02 a 08 du namespace camt.053.
Utilise uniquement xml.etree.ElementTree (aucune dependance externe).
"""
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CamtEntry:
    booking_date: Optional[date] = None
    value_date: Optional[date] = None
    amount: Decimal = Decimal('0')
    currency: str = 'CHF'
    credit_debit: str = ''  # CRDT ou DBIT
    counterparty_name: str = ''
    counterparty_iban: str = ''
    reference: str = ''
    remittance_info: str = ''
    end_to_end_id: str = ''
    bank_reference: str = ''


@dataclass
class CamtStatement:
    statement_id: str = ''
    iban: str = ''
    currency: str = 'CHF'
    opening_balance: Decimal = Decimal('0')
    closing_balance: Decimal = Decimal('0')
    entries: list = field(default_factory=list)
    error: Optional[str] = None


class Camt053ParserService:
    """Service pour parser les fichiers camt.053 (releves bancaires ISO 20022)."""

    # Namespaces supportes (versions 02 a 08)
    SUPPORTED_NAMESPACES = [
        f'urn:iso:std:iso:20022:tech:xsd:camt.053.001.{v:02d}'
        for v in range(2, 9)
    ]

    @staticmethod
    def parse(xml_content):
        """
        Parse un fichier XML camt.053.

        Args:
            xml_content: bytes ou str du contenu XML

        Returns:
            CamtStatement avec les entries parsees
        """
        try:
            if isinstance(xml_content, str):
                xml_content = xml_content.encode('utf-8')
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return CamtStatement(error=f"XML invalide: {e}")

        ns = Camt053ParserService._detect_namespace(root)
        if not ns:
            return CamtStatement(error="Namespace camt.053 non reconnu")

        nsmap = {'ns': ns}

        # Trouver le BkToCstmrStmt -> Stmt
        stmt_elem = root.find('.//ns:BkToCstmrStmt/ns:Stmt', nsmap)
        if stmt_elem is None:
            return CamtStatement(error="Element Stmt non trouve dans le fichier")

        statement = CamtStatement()

        # Statement ID
        stmt_id = stmt_elem.findtext('ns:Id', '', nsmap)
        statement.statement_id = stmt_id

        # IBAN du compte
        acct = stmt_elem.find('ns:Acct/ns:Id/ns:IBAN', nsmap)
        if acct is not None and acct.text:
            statement.iban = acct.text.strip()

        # Devise du compte
        ccy = stmt_elem.find('ns:Acct/ns:Ccy', nsmap)
        if ccy is not None and ccy.text:
            statement.currency = ccy.text.strip()

        # Balances
        for bal_elem in stmt_elem.findall('ns:Bal', nsmap):
            bal_type = bal_elem.findtext('ns:Tp/ns:CdOrPrtry/ns:Cd', '', nsmap)
            amt_elem = bal_elem.find('ns:Amt', nsmap)
            cd_elem = bal_elem.findtext('ns:CdtDbtInd', '', nsmap)

            if amt_elem is not None and amt_elem.text:
                try:
                    amount = Decimal(amt_elem.text)
                    if cd_elem == 'DBIT':
                        amount = -amount

                    if bal_type == 'OPBD':
                        statement.opening_balance = amount
                    elif bal_type == 'CLBD':
                        statement.closing_balance = amount
                except InvalidOperation:
                    pass

        # Entries (Ntry)
        for ntry_elem in stmt_elem.findall('ns:Ntry', nsmap):
            entry = Camt053ParserService._parse_entry(ntry_elem, nsmap)
            if entry:
                statement.entries.append(entry)

        return statement

    @staticmethod
    def _detect_namespace(root):
        """Auto-detecte la version du namespace camt.053."""
        tag = root.tag
        if '{' in tag:
            ns = tag.split('}')[0].lstrip('{')
            for supported in Camt053ParserService.SUPPORTED_NAMESPACES:
                if ns == supported:
                    return ns
            # Verifier aussi dans le document element
            doc_elem = root.find(f'{{{ns}}}BkToCstmrStmt')
            if doc_elem is not None:
                return ns

        # Chercher dans les enfants
        for supported_ns in Camt053ParserService.SUPPORTED_NAMESPACES:
            if root.find(f'{{{supported_ns}}}BkToCstmrStmt') is not None:
                return supported_ns

        return None

    @staticmethod
    def _parse_entry(ntry_elem, nsmap):
        """Parse un element Ntry (entry) du camt.053."""
        entry = CamtEntry()

        # Montant
        amt_elem = ntry_elem.find('ns:Amt', nsmap)
        if amt_elem is not None and amt_elem.text:
            try:
                entry.amount = Decimal(amt_elem.text)
            except InvalidOperation:
                return None
            entry.currency = amt_elem.get('Ccy', 'CHF')

        # Credit/Debit
        entry.credit_debit = ntry_elem.findtext('ns:CdtDbtInd', '', nsmap)

        # Dates
        booking_date_str = ntry_elem.findtext('ns:BookgDt/ns:Dt', '', nsmap)
        if booking_date_str:
            try:
                entry.booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        value_date_str = ntry_elem.findtext('ns:ValDt/ns:Dt', '', nsmap)
        if value_date_str:
            try:
                entry.value_date = datetime.strptime(value_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        # Reference bancaire
        entry.bank_reference = ntry_elem.findtext('ns:AcctSvcrRef', '', nsmap)

        # Transaction details (TxDtls)
        tx_dtls = ntry_elem.find('ns:NtryDtls/ns:TxDtls', nsmap)
        if tx_dtls is not None:
            # End-to-end ID
            entry.end_to_end_id = tx_dtls.findtext(
                'ns:Refs/ns:EndToEndId', '', nsmap
            )

            # Counterparty (RltdPties)
            if entry.credit_debit == 'DBIT':
                # Debit -> on cherche le crediteur
                party = tx_dtls.find('ns:RltdPties/ns:Cdtr', nsmap)
                party_acct = tx_dtls.find('ns:RltdPties/ns:CdtrAcct/ns:Id/ns:IBAN', nsmap)
            else:
                # Credit -> on cherche le debiteur
                party = tx_dtls.find('ns:RltdPties/ns:Dbtr', nsmap)
                party_acct = tx_dtls.find('ns:RltdPties/ns:DbtrAcct/ns:Id/ns:IBAN', nsmap)

            if party is not None:
                name = party.findtext('ns:Nm', '', nsmap)
                if name:
                    entry.counterparty_name = name

            if party_acct is not None and party_acct.text:
                entry.counterparty_iban = party_acct.text.strip()

            # Remittance info
            ustrd = tx_dtls.findtext('ns:RmtInf/ns:Ustrd', '', nsmap)
            strd_ref = tx_dtls.findtext(
                'ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref', '', nsmap
            )
            if strd_ref:
                entry.reference = strd_ref
            if ustrd:
                entry.remittance_info = ustrd

        return entry

    @staticmethod
    def generate_ecritures(statement, mandat, journal, compte_banque, exercice, user):
        """
        Cree une PieceComptable + EcritureComptable en BROUILLON
        a partir d'un CamtStatement parse.

        Args:
            statement: CamtStatement parse
            mandat: Instance Mandat
            journal: Instance Journal
            compte_banque: Instance Compte (compte bancaire)
            exercice: Instance ExerciceComptable
            user: Utilisateur createur

        Returns:
            dict avec 'piece' et 'ecritures_count'
        """
        from comptabilite.models import PieceComptable, EcritureComptable, TypePieceComptable

        # Trouver ou creer le type REL_BNQ
        type_piece, _ = TypePieceComptable.objects.get_or_create(
            code='REL_BNQ',
            defaults={
                'libelle': 'Relevé bancaire',
                'categorie': 'BANQUE',
                'prefixe_numero': 'RB',
                'is_active': True,
            }
        )

        # Creer la piece comptable
        numero = journal.get_next_numero()
        piece = PieceComptable.objects.create(
            mandat=mandat,
            journal=journal,
            numero_piece=numero,
            date_piece=date.today(),
            libelle=f"Import relevé {statement.iban} - {statement.statement_id}",
            type_piece=type_piece,
            statut='BROUILLON',
            created_by=user,
        )

        # Creer les ecritures
        ecritures_count = 0
        for i, entry in enumerate(statement.entries, start=1):
            libelle_parts = []
            if entry.counterparty_name:
                libelle_parts.append(entry.counterparty_name)
            if entry.remittance_info:
                libelle_parts.append(entry.remittance_info)
            if entry.reference:
                libelle_parts.append(f"Ref: {entry.reference}")
            libelle = ' - '.join(libelle_parts) or f"Mouvement bancaire {entry.bank_reference}"

            montant_debit = entry.amount if entry.credit_debit == 'DBIT' else Decimal('0')
            montant_credit = entry.amount if entry.credit_debit == 'CRDT' else Decimal('0')

            EcritureComptable.objects.create(
                mandat=mandat,
                exercice=exercice,
                journal=journal,
                piece=piece,
                numero_piece=numero,
                numero_ligne=i,
                date_ecriture=entry.booking_date or date.today(),
                date_valeur=entry.value_date,
                compte=compte_banque,
                libelle=libelle[:500],
                montant_debit=montant_debit,
                montant_credit=montant_credit,
                devise_id=entry.currency,
                statut='BROUILLON',
            )
            ecritures_count += 1

        # Recalculer l'equilibre
        piece.calculer_equilibre()
        piece.save()

        return {
            'piece_id': str(piece.id),
            'numero_piece': piece.numero_piece,
            'ecritures_count': ecritures_count,
        }

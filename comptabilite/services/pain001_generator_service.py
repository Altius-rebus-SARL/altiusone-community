# comptabilite/services/pain001_generator_service.py
"""
Service de generation de fichiers pain.001 (ordres de paiement ISO 20022).

Format: pain.001.001.09
Utilise uniquement xml.etree.ElementTree + xml.dom.minidom (aucune dependance externe).
"""
import logging
import uuid
import xml.dom.minidom
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

PAIN001_NS = 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.09'


@dataclass
class Payment:
    creditor_name: str = ''
    creditor_iban: str = ''
    creditor_bic: str = ''
    amount: Decimal = Decimal('0')
    currency: str = 'CHF'
    creditor_address_line: str = ''
    creditor_country: str = 'CH'
    reference: str = ''
    reference_type: str = 'NON'  # QRR, SCOR, NON
    remittance_info: str = ''
    execution_date: Optional[date] = None
    piece_id: Optional[str] = None


@dataclass
class PaymentOrder:
    debtor_name: str = ''
    debtor_iban: str = ''
    debtor_bic: str = ''
    debtor_address_line: str = ''
    debtor_country: str = 'CH'
    payments: list = field(default_factory=list)
    message_id: str = ''


class Pain001GeneratorService:
    """Service pour generer des fichiers pain.001 (ordres de paiement)."""

    @staticmethod
    def generate(order):
        """
        Genere un fichier XML pain.001 complet.

        Args:
            order: PaymentOrder avec la liste des paiements

        Returns:
            bytes du XML genere
        """
        if not order.message_id:
            order.message_id = f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"

        root = ET.Element('Document', xmlns=PAIN001_NS)
        cstmr_cdt_trf = ET.SubElement(root, 'CstmrCdtTrfInitn')

        # Group Header
        grp_hdr = ET.SubElement(cstmr_cdt_trf, 'GrpHdr')
        ET.SubElement(grp_hdr, 'MsgId').text = order.message_id
        ET.SubElement(grp_hdr, 'CreDtTm').text = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        ET.SubElement(grp_hdr, 'NbOfTxs').text = str(len(order.payments))

        # Calcul du total
        total = sum(p.amount for p in order.payments)
        ET.SubElement(grp_hdr, 'CtrlSum').text = str(total.quantize(Decimal('0.01')))

        initg_pty = ET.SubElement(grp_hdr, 'InitgPty')
        ET.SubElement(initg_pty, 'Nm').text = order.debtor_name[:70]

        # Grouper les paiements par devise
        payments_by_currency = defaultdict(list)
        for payment in order.payments:
            payments_by_currency[payment.currency].append(payment)

        pmt_inf_id = 0
        for currency, payments in payments_by_currency.items():
            pmt_inf_id += 1
            pmt_inf = ET.SubElement(cstmr_cdt_trf, 'PmtInf')
            ET.SubElement(pmt_inf, 'PmtInfId').text = f"{order.message_id}-{pmt_inf_id}"
            ET.SubElement(pmt_inf, 'PmtMtd').text = 'TRF'
            ET.SubElement(pmt_inf, 'NbOfTxs').text = str(len(payments))

            ctrl_sum = sum(p.amount for p in payments)
            ET.SubElement(pmt_inf, 'CtrlSum').text = str(ctrl_sum.quantize(Decimal('0.01')))

            # Payment Type
            pmt_tp_inf = ET.SubElement(pmt_inf, 'PmtTpInf')
            svc_lvl = ET.SubElement(pmt_tp_inf, 'SvcLvl')
            # SEPA pour EUR, NURG (non-urgent) pour CHF et autres
            if currency == 'EUR':
                ET.SubElement(svc_lvl, 'Cd').text = 'SEPA'
            else:
                ET.SubElement(svc_lvl, 'Cd').text = 'NURG'

            # Date d'execution (prendre la premiere ou aujourd'hui)
            exec_date = payments[0].execution_date or date.today()
            ET.SubElement(pmt_inf, 'ReqdExctnDt').text = exec_date.isoformat()

            # Debtor
            dbtr = ET.SubElement(pmt_inf, 'Dbtr')
            ET.SubElement(dbtr, 'Nm').text = order.debtor_name[:70]
            if order.debtor_address_line:
                dbtr_addr = ET.SubElement(dbtr, 'PstlAdr')
                ET.SubElement(dbtr_addr, 'Ctry').text = order.debtor_country
                ET.SubElement(dbtr_addr, 'AdrLine').text = order.debtor_address_line[:70]

            # Debtor Account
            dbtr_acct = ET.SubElement(pmt_inf, 'DbtrAcct')
            dbtr_acct_id = ET.SubElement(dbtr_acct, 'Id')
            ET.SubElement(dbtr_acct_id, 'IBAN').text = order.debtor_iban.replace(' ', '')

            # Debtor Agent (BIC)
            dbtr_agt = ET.SubElement(pmt_inf, 'DbtrAgt')
            dbtr_agt_fin = ET.SubElement(dbtr_agt, 'FinInstnId')
            if order.debtor_bic:
                ET.SubElement(dbtr_agt_fin, 'BICFI').text = order.debtor_bic

            # Transactions
            for payment in payments:
                Pain001GeneratorService._add_payment_transaction(
                    pmt_inf, payment, exec_date
                )

        # Generer le XML formatte
        xml_bytes = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        dom = xml.dom.minidom.parseString(xml_bytes)
        return dom.toprettyxml(indent='  ', encoding='utf-8')

    @staticmethod
    def _add_payment_transaction(pmt_inf, payment, execution_date):
        """Ajoute un CdtTrfTxInf a un PmtInf."""
        cdt_trf = ET.SubElement(pmt_inf, 'CdtTrfTxInf')

        # Payment ID
        pmt_id = ET.SubElement(cdt_trf, 'PmtId')
        end_to_end_id = payment.piece_id or uuid.uuid4().hex[:16]
        ET.SubElement(pmt_id, 'EndToEndId').text = end_to_end_id

        # Amount
        amt = ET.SubElement(cdt_trf, 'Amt')
        instd_amt = ET.SubElement(amt, 'InstdAmt', Ccy=payment.currency)
        instd_amt.text = str(payment.amount.quantize(Decimal('0.01')))

        # Creditor Agent (BIC)
        if payment.creditor_bic:
            cdtr_agt = ET.SubElement(cdt_trf, 'CdtrAgt')
            cdtr_agt_fin = ET.SubElement(cdtr_agt, 'FinInstnId')
            ET.SubElement(cdtr_agt_fin, 'BICFI').text = payment.creditor_bic

        # Creditor
        cdtr = ET.SubElement(cdt_trf, 'Cdtr')
        ET.SubElement(cdtr, 'Nm').text = payment.creditor_name[:70]
        if payment.creditor_address_line:
            cdtr_addr = ET.SubElement(cdtr, 'PstlAdr')
            ET.SubElement(cdtr_addr, 'Ctry').text = payment.creditor_country
            ET.SubElement(cdtr_addr, 'AdrLine').text = payment.creditor_address_line[:70]

        # Creditor Account
        cdtr_acct = ET.SubElement(cdt_trf, 'CdtrAcct')
        cdtr_acct_id = ET.SubElement(cdtr_acct, 'Id')
        ET.SubElement(cdtr_acct_id, 'IBAN').text = payment.creditor_iban.replace(' ', '')

        # Remittance Information
        if payment.reference and payment.reference_type in ('QRR', 'SCOR'):
            rmt_inf = ET.SubElement(cdt_trf, 'RmtInf')
            strd = ET.SubElement(rmt_inf, 'Strd')
            cdtr_ref_inf = ET.SubElement(strd, 'CdtrRefInf')
            tp = ET.SubElement(cdtr_ref_inf, 'Tp')
            cd_or_prtry = ET.SubElement(tp, 'CdOrPrtry')
            ET.SubElement(cd_or_prtry, 'Prtry').text = payment.reference_type
            ET.SubElement(cdtr_ref_inf, 'Ref').text = payment.reference
        elif payment.remittance_info:
            rmt_inf = ET.SubElement(cdt_trf, 'RmtInf')
            ET.SubElement(rmt_inf, 'Ustrd').text = payment.remittance_info[:140]

    @staticmethod
    def from_pieces_comptables(piece_ids, compte_bancaire):
        """
        Construit un PaymentOrder a partir de PieceComptable de type FAC_ACH.

        Args:
            piece_ids: Liste d'IDs de PieceComptable
            compte_bancaire: Instance CompteBancaire (debiteur)

        Returns:
            PaymentOrder
        """
        from comptabilite.models import PieceComptable

        pieces = PieceComptable.objects.filter(
            id__in=piece_ids,
            type_piece__code='FAC_ACH',
            statut='VALIDE',
        ).select_related('type_piece')

        # Résoudre le pays depuis le compte bancaire ou le mandat
        pays = 'CH'
        if hasattr(compte_bancaire, 'titulaire_adresse') and compte_bancaire.titulaire_adresse:
            pays = getattr(compte_bancaire.titulaire_adresse, 'pays', 'CH') or 'CH'

        order = PaymentOrder(
            debtor_name=compte_bancaire.titulaire_nom,
            debtor_iban=compte_bancaire.iban,
            debtor_bic=compte_bancaire.bic_swift,
            debtor_country=str(pays),
        )

        if compte_bancaire.titulaire_adresse:
            addr = compte_bancaire.titulaire_adresse
            order.debtor_address_line = f"{addr}"

        skipped = []

        for piece in pieces:
            # Valider le montant
            amount = piece.montant_ttc or Decimal('0')
            if amount <= 0:
                skipped.append({
                    'piece': piece.numero_piece,
                    'raison': f"Montant invalide ({amount})",
                })
                continue

            # Devise depuis le mandat ou fallback devise base
            devise_code = 'CHF'
            if hasattr(piece, 'mandat') and piece.mandat_id:
                devise_code = piece.mandat.devise_id or 'CHF'

            payment = Payment(
                creditor_name=piece.tiers_nom or 'Fournisseur inconnu',
                amount=amount,
                currency=str(devise_code),
                remittance_info=f"{piece.numero_piece} - {piece.libelle}"[:140],
                execution_date=date.today(),
                piece_id=str(piece.id),
            )

            # Chercher l'IBAN dans les metadata OCR si disponible
            if piece.metadata_ocr and isinstance(piece.metadata_ocr, dict):
                raw_iban = piece.metadata_ocr.get('iban', '')
                if raw_iban:
                    from core.validators import clean_iban, validate_iban
                    cleaned = clean_iban(raw_iban)
                    if validate_iban(cleaned):
                        payment.creditor_iban = cleaned
                    else:
                        skipped.append({
                            'piece': piece.numero_piece,
                            'raison': f"IBAN OCR invalide: {raw_iban}",
                        })
                        continue

                payment.reference = piece.metadata_ocr.get('reference', '')
                ref_type = piece.metadata_ocr.get('reference_type', 'NON')
                if ref_type in ('QRR', 'SCOR', 'NON'):
                    payment.reference_type = ref_type

            # Un paiement sans IBAN créancier n'a pas de sens
            if not payment.creditor_iban:
                skipped.append({
                    'piece': piece.numero_piece,
                    'raison': "Aucun IBAN créancier",
                })
                continue

            order.payments.append(payment)

        if skipped:
            logger.warning(
                "pain.001: %d pièce(s) ignorée(s): %s",
                len(skipped),
                "; ".join(f"{s['piece']}: {s['raison']}" for s in skipped),
            )

        order._skipped = skipped
        return order

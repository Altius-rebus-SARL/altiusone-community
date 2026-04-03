"""
Générateur XML Swissdec ELM pour CertificatSalaire (Lohnausweis / Formulaire 11).

Conforme au standard Swissdec ELM v5 (namespace 20200220).
Génère un XML standalone pour export/archivage des certificats de salaire.
Pour la transmission électronique via le réseau Swissdec, des éléments
supplémentaires (Insurances, SalaryTotals, etc.) seraient nécessaires.

Mapping complet Form 11 → XML :
  z1  → Income
  z2  → FringeBenefits (FoodLodging, CompanyCar, Other)
  z3  → SporadicBenefits
  z4  → CapitalPayment
  z5  → OwnershipRight
  z6  → BoardOfDirectorsRemuneration
  z7  → OtherBenefits
  z8  → GrossIncome
  z9  → AHV-ALV-NBUV-AVS-AC-AANP-Contribution
  z10 → BVG-LPP-Contribution (Regular, Purchase)
  z11 → NetIncome
  z12 → DeductionAtSource
  z13 → Charges (Effective, LumpSum, Education)
  z14 → OtherFringeBenefits
  z15 → Remark

Référence : https://www.swissdec.ch
"""
import io
from decimal import Decimal
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

NS = 'http://www.swissdec.ch/schema/sd/20200220/SalaryDeclaration'
SCHEMA_VERSION = '5.0'


def _fmt_amount(val):
    """Formate un montant avec exactement 2 décimales (exigence Swissdec)."""
    if val is None:
        return None
    d = Decimal(str(val)).quantize(Decimal('0.01'))
    if d == 0:
        return None
    return str(d)


def _add_amount(parent, tag, val):
    """Ajoute un élément montant si la valeur est non-nulle."""
    formatted = _fmt_amount(val)
    if formatted:
        SubElement(parent, tag).text = formatted
        return True
    return False


def _add_sort_sum(parent, tag, val, text=''):
    """Ajoute un élément SortSumType (Text + Sum) si non-nul."""
    formatted = _fmt_amount(val)
    if formatted:
        el = SubElement(parent, tag)
        if text:
            SubElement(el, 'Text').text = str(text)[:100]
        SubElement(el, 'Sum').text = formatted
        return True
    return False


class CertificatSalaireXML:
    """Générateur XML Swissdec ELM pour un certificat de salaire."""

    def __init__(self, certificat):
        self.cert = certificat
        self.employe = certificat.employe
        self.client = certificat.employe.mandat.client
        self.adresse_client = self.client.adresse_siege

    def _build_company_description(self, company):
        """CompanyDescription : identification de l'employeur."""
        desc = SubElement(company, 'CompanyDescription')

        # Nom
        name = SubElement(desc, 'Name')
        SubElement(name, 'HR-RC-Name').text = self.client.raison_sociale

        # Adresse
        adr = self.adresse_client
        if adr:
            address = SubElement(desc, 'Address')
            rue = adr.rue.strip()
            if adr.numero and adr.numero not in rue:
                rue = f"{rue} {adr.numero}"
            SubElement(address, 'Street').text = rue
            SubElement(address, 'ZIP-Code').text = str(adr.npa or adr.code_postal or '')
            SubElement(address, 'City').text = adr.localite or ''

        # IDE/UID si disponible
        ide = getattr(self.client, 'ide_number', '') or ''
        if ide:
            # Normaliser au format CHE sans ponctuation
            uid = ide.replace('.', '').replace('-', '').replace(' ', '')
            if len(uid) >= 12:
                SubElement(desc, 'UID-EHRA').text = uid

    def _build_person_particulars(self, person):
        """Particulars : identification de l'employé."""
        emp = self.employe
        particulars = SubElement(person, 'Particulars')

        # N° AVS
        si = SubElement(particulars, 'Social-InsuranceIdentification')
        avs = emp.avs_number or ''
        if avs:
            # Le format Swissdec attend le numéro sans points pour SV-AS-Number
            avs_clean = avs.replace('.', '')
            SubElement(si, 'SV-AS-Number').text = avs_clean
        else:
            SubElement(si, 'unknown')

        # Matricule
        if emp.matricule:
            SubElement(particulars, 'EmployeeNumber').text = emp.matricule

        # Identité
        SubElement(particulars, 'Lastname').text = emp.nom
        SubElement(particulars, 'Firstname').text = emp.prenom

        # Sexe
        sexe_map = {'M': 'M', 'F': 'F', 'X': 'M'}
        SubElement(particulars, 'Sex').text = sexe_map.get(emp.sexe, 'M')

        # Date de naissance
        if emp.date_naissance:
            SubElement(particulars, 'DateOfBirth').text = (
                emp.date_naissance.isoformat())

        # Nationalité
        nationality = SubElement(particulars, 'Nationality')
        nat_code = str(getattr(emp, 'nationalite', 'CH') or 'CH')
        SubElement(nationality, 'ISOCode').text = nat_code[:2].upper()

        # État civil
        civil_map = {
            'CELIBATAIRE': 'single',
            'MARIE': 'married',
            'DIVORCE': 'divorced',
            'VEUF': 'widowed',
            'SEPARE': 'separated',
        }
        etat = getattr(emp, 'etat_civil', '')
        SubElement(particulars, 'CivilStatus').text = (
            civil_map.get(etat, 'unknown'))

        # Adresse employé
        adr = emp.adresse
        if adr:
            address = SubElement(particulars, 'Address')
            rue_emp = adr.rue.strip()
            if adr.numero and adr.numero not in rue_emp:
                rue_emp = f"{rue_emp} {adr.numero}"
            SubElement(address, 'Street').text = rue_emp
            SubElement(address, 'ZIP-Code').text = str(
                adr.npa or adr.code_postal or '')
            SubElement(address, 'City').text = adr.localite or ''
            pays = str(getattr(adr, 'pays', 'CH') or 'CH')
            if pays and pays != 'CH':
                SubElement(address, 'Country').text = pays[:2].upper()

        # Canton de résidence
        canton = getattr(adr, 'canton', '') if adr else ''
        if canton:
            SubElement(particulars, 'ResidenceCanton').text = str(canton)[:2]

    def _build_tax_salary(self, tax_salaries):
        """TaxSalary : les chiffres 1-15 du formulaire 11."""
        cert = self.cert
        ts = SubElement(tax_salaries, 'TaxSalary')

        # Période (E)
        period = SubElement(ts, 'Period')
        SubElement(period, 'from').text = cert.date_debut.isoformat()
        SubElement(period, 'until').text = cert.date_fin.isoformat()

        # F - Transport gratuit
        if getattr(cert, 'transport_gratuit_fourni', False):
            SubElement(ts, 'FreeTransport')

        # G - Cantine / Lunch-checks
        if getattr(cert, 'repas_midi_gratuit', False):
            SubElement(ts, 'CanteenLunchCheck')

        # z1 - Salaire
        _add_amount(ts, 'Income', cert.chiffre_1_salaire)

        # z2 - Prestations en nature
        has_2 = any([
            cert.chiffre_2_1_repas,
            cert.chiffre_2_2_voiture,
            cert.chiffre_2_3_autres,
        ])
        if has_2:
            fb = SubElement(ts, 'FringeBenefits')
            _add_amount(fb, 'FoodLodging', cert.chiffre_2_1_repas)
            _add_amount(fb, 'CompanyCar', cert.chiffre_2_2_voiture)
            _add_sort_sum(fb, 'Other', cert.chiffre_2_3_autres,
                          getattr(cert, 'autres_prestations_nature_detail', ''))

        # z3 - Prestations irrégulières
        _add_sort_sum(ts, 'SporadicBenefits', cert.chiffre_3_irregulier,
                      getattr(cert, 'chiffre_3_art', ''))

        # z4 - Prestations en capital
        _add_sort_sum(ts, 'CapitalPayment', cert.chiffre_4_capital,
                      getattr(cert, 'chiffre_4_art', ''))

        # z5 - Droits de participation
        _add_amount(ts, 'OwnershipRight', cert.chiffre_5_participations)

        # z6 - Conseil d'administration
        _add_amount(ts, 'BoardOfDirectorsRemuneration', cert.chiffre_6_ca)

        # z7 - Autres prestations
        _add_sort_sum(ts, 'OtherBenefits', cert.chiffre_7_autres,
                      getattr(cert, 'autres_prestations_detail', ''))

        # z8 - Total brut (obligatoire)
        _add_amount(ts, 'GrossIncome', cert.chiffre_8_total_brut)

        # z9 - Cotisations AVS/AI/APG/AC/AANP
        _add_amount(ts, 'AHV-ALV-NBUV-AVS-AC-AANP-Contribution',
                    cert.chiffre_9_cotisations)

        # z10 - Prévoyance professionnelle
        has_10 = any([
            cert.chiffre_10_1_lpp_ordinaire,
            cert.chiffre_10_2_lpp_rachat,
        ])
        if has_10:
            bvg = SubElement(ts, 'BVG-LPP-Contribution')
            _add_amount(bvg, 'Regular', cert.chiffre_10_1_lpp_ordinaire)
            _add_amount(bvg, 'Purchase', cert.chiffre_10_2_lpp_rachat)

        # z11 - Salaire net (obligatoire)
        _add_amount(ts, 'NetIncome', cert.chiffre_11_net)

        # z12 - Impôt à la source
        _add_amount(ts, 'DeductionAtSource',
                    getattr(cert, 'impot_source_annuel', None))

        # z13 - Frais professionnels
        has_13_eff = any([
            getattr(cert, 'chiffre_13_1_1_repas_effectif', 0),
            getattr(cert, 'chiffre_13_1_2_repas_forfait', 0),
        ])
        has_13_lump = any([
            getattr(cert, 'chiffre_13_2_nuitees', 0),
            getattr(cert, 'chiffre_13_3_repas_externes', 0),
        ])
        if has_13_eff or has_13_lump:
            charges = SubElement(ts, 'Charges')
            if has_13_eff:
                effective = SubElement(charges, 'Effective')
                _add_amount(effective, 'TravelFoodAccommodation',
                            cert.chiffre_13_1_1_repas_effectif)
                _add_sort_sum(effective, 'Other',
                              cert.chiffre_13_1_2_repas_forfait)
            if has_13_lump:
                lump = SubElement(charges, 'LumpSum')
                _add_amount(lump, 'Representation',
                            cert.chiffre_13_2_nuitees)
                _add_sort_sum(lump, 'Other',
                              cert.chiffre_13_3_repas_externes)

        # z14 - Autres prestations accessoires
        detail_14 = getattr(cert, 'autres_frais_detail', '')
        if detail_14:
            SubElement(ts, 'OtherFringeBenefits').text = str(detail_14)[:200]

        # z15 - Remarques
        if cert.remarques:
            SubElement(ts, 'Remark').text = cert.remarques[:500]

    def generer(self, pretty=True):
        """Génère le XML ELM et retourne les bytes UTF-8."""
        root = Element('SalaryDeclaration')
        root.set('xmlns', NS)
        root.set('schemaVersion', SCHEMA_VERSION)

        # Company
        company = SubElement(root, 'Company')
        self._build_company_description(company)

        # Staff > Person
        staff = SubElement(company, 'Staff')
        person = SubElement(staff, 'Person')
        self._build_person_particulars(person)

        # TaxSalaries
        tax_salaries = SubElement(person, 'TaxSalaries')
        self._build_tax_salary(tax_salaries)

        # GeneralSalaryDeclarationDescription
        gen = SubElement(root, 'GeneralSalaryDeclarationDescription')
        from datetime import datetime
        SubElement(gen, 'CreationDate').text = (
            datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        SubElement(gen, 'AccountingPeriod').text = str(self.cert.annee)

        # Sérialiser
        xml_bytes = tostring(root, encoding='unicode', xml_declaration=False)
        xml_str = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_bytes}'

        if pretty:
            dom = parseString(xml_str)
            xml_str = dom.toprettyxml(indent='  ', encoding='UTF-8')
            return xml_str

        return xml_str.encode('utf-8')

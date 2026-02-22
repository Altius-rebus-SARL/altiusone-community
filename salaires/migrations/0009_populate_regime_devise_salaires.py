# salaires/migrations/0009_populate_regime_devise_salaires.py
"""
Populate regime_fiscal and devise on salaires models from related objects.
"""
from django.db import migrations


def populate_taux_cotisation(apps, schema_editor):
    """Populate TauxCotisation with CH regime and CHF devise for existing rows."""
    TauxCotisation = apps.get_model('salaires', 'TauxCotisation')
    RegimeFiscal = apps.get_model('tva', 'RegimeFiscal')
    Devise = apps.get_model('core', 'Devise')

    regime_ch = RegimeFiscal.objects.filter(code='CH').first()
    devise_chf = Devise.objects.filter(code='CHF').first()

    if regime_ch:
        TauxCotisation.objects.filter(regime_fiscal__isnull=True).update(
            regime_fiscal=regime_ch
        )
    if devise_chf:
        TauxCotisation.objects.filter(devise__isnull=True).update(
            devise=devise_chf
        )


def populate_fiche_salaire(apps, schema_editor):
    """Populate FicheSalaire.devise from employe.devise_salaire."""
    FicheSalaire = apps.get_model('salaires', 'FicheSalaire')
    Employe = apps.get_model('salaires', 'Employe')

    for fiche in FicheSalaire.objects.filter(devise__isnull=True).select_related():
        try:
            employe = Employe.objects.get(pk=fiche.employe_id)
            if employe.devise_salaire_id:
                fiche.devise_id = employe.devise_salaire_id
                fiche.save(update_fields=['devise'])
        except Exception:
            pass


def populate_certificat_salaire(apps, schema_editor):
    """Populate CertificatSalaire regime_fiscal and devise from employe."""
    CertificatSalaire = apps.get_model('salaires', 'CertificatSalaire')
    Employe = apps.get_model('salaires', 'Employe')
    Mandat = apps.get_model('core', 'Mandat')

    for cert in CertificatSalaire.objects.filter(devise__isnull=True).select_related():
        try:
            employe = Employe.objects.get(pk=cert.employe_id)
            # Devise from employe
            if employe.devise_salaire_id:
                cert.devise_id = employe.devise_salaire_id
            # Regime from employe or mandat
            if not cert.regime_fiscal_id:
                if employe.regime_fiscal_id:
                    cert.regime_fiscal_id = employe.regime_fiscal_id
                else:
                    mandat = Mandat.objects.get(pk=employe.mandat_id)
                    if mandat.regime_fiscal_id:
                        cert.regime_fiscal_id = mandat.regime_fiscal_id
            cert.save(update_fields=['devise', 'regime_fiscal'])
        except Exception:
            pass


def populate_declaration_cotisations(apps, schema_editor):
    """Populate DeclarationCotisations regime_fiscal and devise from mandat."""
    DeclarationCotisations = apps.get_model('salaires', 'DeclarationCotisations')
    Mandat = apps.get_model('core', 'Mandat')

    for decl in DeclarationCotisations.objects.filter(devise__isnull=True).select_related():
        try:
            mandat = Mandat.objects.get(pk=decl.mandat_id)
            if mandat.devise_id:
                decl.devise_id = mandat.devise_id
            if not decl.regime_fiscal_id and mandat.regime_fiscal_id:
                decl.regime_fiscal_id = mandat.regime_fiscal_id
            decl.save(update_fields=['devise', 'regime_fiscal'])
        except Exception:
            pass


def populate_certificat_travail(apps, schema_editor):
    """Populate CertificatTravail.regime_fiscal from employe's mandat."""
    CertificatTravail = apps.get_model('salaires', 'CertificatTravail')
    Employe = apps.get_model('salaires', 'Employe')
    Mandat = apps.get_model('core', 'Mandat')

    for cert in CertificatTravail.objects.filter(regime_fiscal__isnull=True).select_related():
        try:
            employe = Employe.objects.get(pk=cert.employe_id)
            mandat = Mandat.objects.get(pk=employe.mandat_id)
            if mandat.regime_fiscal_id:
                cert.regime_fiscal_id = mandat.regime_fiscal_id
                cert.save(update_fields=['regime_fiscal'])
        except Exception:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('salaires', '0008_add_regime_devise_salaires'),
    ]

    operations = [
        migrations.RunPython(
            populate_taux_cotisation,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_fiche_salaire,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_certificat_salaire,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_declaration_cotisations,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_certificat_travail,
            reverse_code=migrations.RunPython.noop,
        ),
    ]

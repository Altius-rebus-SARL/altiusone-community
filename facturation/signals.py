# apps/facturation/signals.py
from decimal import Decimal

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from .models import Facture, LigneFacture, Paiement, TimeTracking, ZoneGeographique


@receiver(post_save, sender=LigneFacture)
def recalculer_facture(sender, instance, **kwargs):
    """Recalcule les totaux de la facture après ajout/modif ligne"""
    instance.facture.calculer_totaux()


@receiver(post_save, sender=Facture)
def generer_qr_bill(sender, instance, created, **kwargs):
    """Génère le QR-Bill lors de la validation de la facture (Suisse uniquement)"""
    if instance.statut == 'EMISE' and not instance.qr_reference:
        # QR-Bill uniquement pour les mandats suisses
        regime = instance.regime_fiscal
        if not regime:
            regime = getattr(instance.mandat, 'regime_fiscal', None)
        if regime and regime.code != 'CH':
            return

        instance.generer_qr_reference()

        # Générer l'image QR code
        try:
            from facturation.utils import generer_qr_code_image
            qr_image = generer_qr_code_image(instance)
            if qr_image:
                instance.qr_code_image.save(qr_image.name, qr_image, save=True)
        except Exception as e:
            # Log l'erreur mais ne pas bloquer la sauvegarde
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erreur génération QR code facture {instance.numero_facture}: {e}")


@receiver(post_save, sender=Facture)
def comptabiliser_facture(sender, instance, **kwargs):
    """Crée l'écriture comptable quand la facture est émise"""
    if instance.statut == 'EMISE' and not instance.ecriture_comptable:
        from comptabilite.models import EcritureComptable, Journal, Compte, PieceComptable

        journal = Journal.objects.filter(
            mandat=instance.mandat,
            type_journal='VTE'
        ).first()

        if journal:
            numero_piece = journal.get_next_numero()

            # Créer la pièce comptable
            piece = PieceComptable.objects.create(
                mandat=instance.mandat,
                journal=journal,
                numero_piece=numero_piece,
                date_piece=instance.date_emission,
                libelle=f"Facture {instance.numero_facture}",
                statut='VALIDE'
            )

            # Compte client (débiteur)
            compte_client = Compte.objects.filter(
                plan_comptable__mandat=instance.mandat,
                numero='1100'  # Créances clients
            ).first()

            # Résolution dynamique du compte TVA via config_tva
            compte_tva = None
            code_tva_ventes = '200'  # Fallback
            try:
                config_tva = instance.mandat.config_tva
                if config_tva and config_tva.compte_tva_due:
                    compte_tva = config_tva.compte_tva_due
                # Chercher le code TVA ventes du régime
                if config_tva and config_tva.regime:
                    from tva.models import CodeTVA
                    code_obj = CodeTVA.objects.filter(
                        regime=config_tva.regime,
                        categorie='CHIFFRE_AFFAIRES',
                        actif=True,
                    ).first()
                    if code_obj:
                        code_tva_ventes = code_obj.code
            except Exception:
                pass

            if not compte_tva:
                compte_tva = Compte.objects.filter(
                    plan_comptable__mandat=instance.mandat,
                    numero='2200'  # TVA due (fallback)
                ).first()

            if compte_client:
                # Débit: Créance client (TTC)
                EcritureComptable.objects.create(
                    mandat=instance.mandat,
                    exercice=instance.mandat.exercices.filter(
                        statut='OUVERT'
                    ).first(),
                    journal=journal,
                    numero_piece=numero_piece,
                    numero_ligne=1,
                    date_ecriture=instance.date_emission,
                    compte=compte_client,
                    compte_auxiliaire=instance.client.ide_number,
                    libelle=f"Facture {instance.numero_facture} - {instance.client.raison_sociale}",
                    montant_debit=instance.montant_ttc,
                    piece_justificative=None,
                    statut='VALIDE'
                )

                # Crédits: Ventes par ligne et TVA
                ligne_num = 2
                for ligne in instance.lignes.all():
                    compte_produit = ligne.prestation.compte_produit if ligne.prestation else None
                    if not compte_produit:
                        compte_produit = Compte.objects.filter(
                            plan_comptable__mandat=instance.mandat,
                            numero__startswith='70'
                        ).first()

                    if compte_produit:
                        # Crédit: Vente HT
                        EcritureComptable.objects.create(
                            mandat=instance.mandat,
                            exercice=instance.mandat.exercices.filter(
                                statut='OUVERT'
                            ).first(),
                            journal=journal,
                            numero_piece=numero_piece,
                            numero_ligne=ligne_num,
                            date_ecriture=instance.date_emission,
                            compte=compte_produit,
                            libelle=ligne.description[:255],
                            montant_credit=ligne.montant_ht,
                            statut='VALIDE'
                        )
                        ligne_num += 1

                # Crédit: TVA due
                if instance.montant_tva > 0 and compte_tva:
                    EcritureComptable.objects.create(
                        mandat=instance.mandat,
                        exercice=instance.mandat.exercices.filter(
                            statut='OUVERT'
                        ).first(),
                        journal=journal,
                        numero_piece=numero_piece,
                        numero_ligne=ligne_num,
                        date_ecriture=instance.date_emission,
                        compte=compte_tva,
                        libelle=f"TVA sur facture {instance.numero_facture}",
                        montant_credit=instance.montant_tva,
                        code_tva=code_tva_ventes,
                        montant_tva=instance.montant_tva,
                        statut='VALIDE'
                    )

                instance.ecriture_comptable = piece
                instance.save(update_fields=['ecriture_comptable'])


@receiver(post_save, sender=Paiement)
def comptabiliser_paiement(sender, instance, created, **kwargs):
    """Crée l'écriture comptable de paiement"""
    if created and instance.valide and not instance.ecriture_comptable:
        from comptabilite.models import EcritureComptable, Journal, Compte

        journal = Journal.objects.filter(
            mandat=instance.facture.mandat,
            type_journal='BNQ'
        ).first()

        if journal:
            numero_piece = journal.get_next_numero()

            compte_banque = Compte.objects.filter(
                plan_comptable__mandat=instance.facture.mandat,
                numero='1020'  # Compte banque
            ).first()

            compte_client = Compte.objects.filter(
                plan_comptable__mandat=instance.facture.mandat,
                numero='1100'  # Créances clients
            ).first()

            if compte_banque and compte_client:
                # Débit: Banque
                EcritureComptable.objects.create(
                    mandat=instance.facture.mandat,
                    exercice=instance.facture.mandat.exercices.filter(
                        statut='OUVERT'
                    ).first(),
                    journal=journal,
                    numero_piece=numero_piece,
                    numero_ligne=1,
                    date_ecriture=instance.date_paiement,
                    compte=compte_banque,
                    libelle=f"Paiement facture {instance.facture.numero_facture}",
                    montant_debit=instance.montant,
                    statut='VALIDE'
                )

                # Crédit: Client
                ecriture_client = EcritureComptable.objects.create(
                    mandat=instance.facture.mandat,
                    exercice=instance.facture.mandat.exercices.filter(
                        statut='OUVERT'
                    ).first(),
                    journal=journal,
                    numero_piece=numero_piece,
                    numero_ligne=2,
                    date_ecriture=instance.date_paiement,
                    compte=compte_client,
                    compte_auxiliaire=instance.facture.client.ide_number,
                    libelle=f"Paiement facture {instance.facture.numero_facture}",
                    montant_credit=instance.montant,
                    statut='VALIDE'
                )

                instance.ecriture_comptable = ecriture_client
                instance.save(update_fields=['ecriture_comptable'])


@receiver(post_save, sender=Facture)
def alerter_facture_en_retard(sender, instance, **kwargs):
    """Alerte quand une facture dépasse l'échéance"""
    from datetime import date
    from core.models import Notification

    if instance.statut in ['EMISE', 'ENVOYEE', 'RELANCEE']:
        if instance.date_echeance < date.today() and instance.montant_restant > 0:
            if instance.statut != 'EN_RETARD':
                instance.statut = 'EN_RETARD'
                instance.save(update_fields=['statut'])

                # Notifier le responsable
                Notification.objects.create(
                    destinataire=instance.mandat.responsable,
                    type_notification='WARNING',
                    titre='Facture en retard',
                    message=f"La facture {instance.numero_facture} est en retard de paiement.",
                    lien_action=f'/factures/{instance.id}/',
                    lien_texte='Voir la facture',
                    mandat=instance.mandat
                )


@receiver(post_save, sender=TimeTracking)
def decompter_budget_operation(sender, instance, **kwargs):
    """Recalcule le coût réel de l'opération depuis tous les temps passés"""
    if instance.operation_id and instance.montant_ht:
        from django.db.models import Sum
        from projets.models import Operation

        total = TimeTracking.objects.filter(
            operation=instance.operation, is_active=True
        ).aggregate(total=Sum('montant_ht'))['total'] or Decimal('0')
        Operation.objects.filter(pk=instance.operation_id).update(cout_reel=total)
        # Refresh and cascade: position → mandat
        instance.operation.refresh_from_db()
        instance.operation.position.recalculer_budget_reel()


@receiver(post_save, sender=TimeTracking)
def auto_detecter_zone(sender, instance, **kwargs):
    """Auto-détecte la zone géographique si coordonnées définies et zone vide"""
    if instance.coordonnees and not instance.zone_geographique_id:
        zone = ZoneGeographique.objects.filter(
            is_active=True,
            geometrie__contains=instance.coordonnees,
        ).first()
        if zone:
            TimeTracking.objects.filter(pk=instance.pk).update(
                zone_geographique=zone
            )

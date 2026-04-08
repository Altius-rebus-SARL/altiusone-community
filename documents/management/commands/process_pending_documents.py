"""
Commande pour rattraper les documents en attente d'OCR.

Traite tous les documents avec statut 'UPLOAD' ou 'ERREUR' qui n'ont
pas été OCR'd (par exemple si OCR_SERVICE_ENABLED était False au moment
de l'upload, ou si le worker Celery était down).

Usage:
  python manage.py process_pending_documents              # Traite tout
  python manage.py process_pending_documents --limit 50   # Max 50 documents
  python manage.py process_pending_documents --dry-run    # Compter sans traiter
  python manage.py process_pending_documents --errors     # Relancer les erreurs aussi
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Traite les documents en attente d\'OCR (UPLOAD ou ERREUR)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit', type=int, default=0,
            help='Nombre max de documents à traiter (0 = tous)'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Compter les documents sans les traiter'
        )
        parser.add_argument(
            '--errors', action='store_true',
            help='Inclure les documents en erreur'
        )
        parser.add_argument(
            '--sync', action='store_true',
            help='Traiter de manière synchrone (sans Celery)'
        )

    def handle(self, *args, **options):
        from documents.models import Document
        from django.db.models import Q

        statuts = ['UPLOAD']
        if options['errors']:
            statuts.append('ERREUR')

        queryset = Document.objects.filter(
            statut_traitement__in=statuts
        ).order_by('date_upload')

        total = queryset.count()
        self.stdout.write(f"Documents en attente: {total} ({', '.join(statuts)})")

        if total == 0:
            self.stdout.write(self.style.SUCCESS('Aucun document à traiter'))
            return

        if options['dry_run']:
            # Stats par type
            by_mime = {}
            for doc in queryset[:100]:
                mime = doc.mime_type or 'inconnu'
                by_mime[mime] = by_mime.get(mime, 0) + 1
            for mime, count in sorted(by_mime.items(), key=lambda x: -x[1]):
                self.stdout.write(f"  {mime}: {count}")
            return

        limit = options['limit'] or total
        docs = queryset[:limit]

        self.stdout.write(f"Traitement de {min(limit, total)} documents...")

        if options['sync']:
            # Traitement synchrone (pour debug)
            from documents.tasks import traiter_document_ocr
            success = 0
            errors = 0
            for i, doc in enumerate(docs, 1):
                try:
                    result = traiter_document_ocr(str(doc.id))
                    if result.get('status') == 'success':
                        success += 1
                    else:
                        errors += 1
                    if i % 10 == 0:
                        self.stdout.write(f"  {i}/{min(limit, total)}...")
                except Exception as e:
                    errors += 1
                    self.stderr.write(f"  Erreur {doc.id}: {e}")
            self.stdout.write(self.style.SUCCESS(
                f"Terminé: {success} succès, {errors} erreurs"
            ))
        else:
            # Traitement async via Celery
            from documents.tasks import traiter_document_ocr
            queued = 0
            for doc in docs:
                traiter_document_ocr.delay(str(doc.id))
                queued += 1
            self.stdout.write(self.style.SUCCESS(
                f"{queued} tâches Celery lancées"
            ))

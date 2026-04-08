# core/ai/classifier.py
"""
Classification de documents par similarité vectorielle.

Principe : on compare l'embedding du document avec des embeddings
de référence (textes descriptifs) pour chaque type de document.
Le type avec la plus haute similarité gagne.

Avantages vs LLM :
- ~50ms vs ~3s (60x plus rapide)
- Déterministe (même document → même résultat)
- Pas de dépendance Ollama pour la classification

La métrique de distance est configurable (cosine par défaut).
"""
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Textes de référence par type de document.
# Chaque type a une description qui sera vectorisée et mise en cache.
# Plus la description est riche, meilleure est la classification.
DOCUMENT_TYPE_REFERENCES = {
    'FACTURE_ACHAT': (
        "Facture fournisseur facture achat fournisseur marchandise fourniture "
        "montant total HT TTC TVA taux date échéance paiement 30 jours "
        "numéro de facture référence commande bon de livraison "
        "conditions de paiement net à payer veuillez payer"
    ),
    'FACTURE_VENTE': (
        "Facture client facture vente prestation honoraires service rendu "
        "montant total HT TTC TVA émise envoyée numéro facture "
        "encaissement recette chiffre affaires client destinataire "
        "merci de régler sous 30 jours QR-facture bulletin versement"
    ),
    'CONTRAT_TRAVAIL': (
        "Contrat de travail contrat d'engagement emploi embauche "
        "CDI CDD durée indéterminée déterminée apprentissage stage "
        "employé employeur salaire mensuel brut taux d'occupation "
        "fonction poste département date d'entrée préavis vacances "
        "horaire hebdomadaire lieu de travail période d'essai"
    ),
    'CONTRAT_BAIL': (
        "Contrat de bail location appartement immeuble local commercial "
        "loyer mensuel charges locatives locataire bailleur propriétaire "
        "surface habitable caution garantie dépôt état des lieux "
        "durée résiliation préavis logement"
    ),
    'CONTRAT': (
        "Contrat accord convention mandat prestation de services "
        "conditions générales parties contractantes signataires "
        "obligations droits durée résiliation entrée en vigueur "
        "clause confidentialité responsabilité"
    ),
    'FICHE_SALAIRE': (
        "Fiche de salaire bulletin de paie décompte salaire mensuel "
        "salaire brut salaire net cotisations sociales déductions "
        "AVS AI APG AC LPP LAA IJM assurance maladie impôt à la source "
        "employé période mois heures travaillées allocations familiales "
        "13ème salaire gratification bonus"
    ),
    'CERTIFICAT_SALAIRE': (
        "Certificat de salaire annuel formulaire 11 AFC administration "
        "fédérale des contributions déclaration d'impôt revenu annuel "
        "salaire brut annuel cotisations annuelles frais professionnels "
        "part privée véhicule repas attestation employeur année fiscale"
    ),
    'RELEVE_BANQUE': (
        "Relevé bancaire relevé de compte extrait de compte bancaire "
        "IBAN solde initial solde final débit crédit mouvement "
        "virement versement retrait prélèvement intérêts frais bancaires "
        "date valeur opérations transactions banque"
    ),
    'EXTRAIT_BANCAIRE': (
        "Extrait bancaire relevé de compte courant épargne banque "
        "IBAN solde débit crédit opérations entrées sorties "
        "date valeur montant libellé référence intérêts"
    ),
    'DECLARATION_TVA': (
        "Déclaration TVA décompte TVA taxe sur la valeur ajoutée "
        "AFC administration fédérale des contributions chiffre d'affaires "
        "impôt préalable TVA due créance remboursement trimestriel "
        "semestriel taux normal réduit spécial 8.1% 2.6%"
    ),
    'DEVIS': (
        "Devis estimation offre de prix proposition commerciale "
        "prix unitaire quantité montant total prestations articles "
        "conditions validité 30 jours sans engagement client"
    ),
    'OFFRE': (
        "Offre commerciale proposition de services tarif forfait "
        "prestations délai livraison garantie conditions client "
        "acceptation commande engagement"
    ),
    'ATTESTATION': (
        "Attestation certificat confirmation déclaration sur l'honneur "
        "domicile résidence travail employeur autorité commune "
        "document officiel tampon signature"
    ),
    'CORRESPONDANCE': (
        "Lettre courrier correspondance communication écrite "
        "objet concerne référence à votre courrier du "
        "destinataire expéditeur madame monsieur salutations"
    ),
    'COURRIER': (
        "Courrier lettre postal envoi réception recommandé "
        "accusé de réception destinataire expéditeur objet "
        "référence dossier numéro"
    ),
    'EMAIL': (
        "Email courriel message électronique envoi réception "
        "objet de re sujet pièce jointe destinataire copie "
        "expéditeur date heure cordialement"
    ),
    'AUTRE': (
        "Document divers autre type non classifié inclassable "
        "général informationnel pièce justificative annexe"
    ),
}


class EmbeddingClassifier:
    """
    Classifie des textes par similarité vectorielle avec des embeddings de référence.

    Les embeddings de référence sont calculés une seule fois (lazy)
    et gardés en cache mémoire.
    """

    def __init__(self, references: Optional[Dict[str, str]] = None, metric: str = 'cosine'):
        """
        Args:
            references: Dict {label: texte_description}. Si None, utilise DOCUMENT_TYPE_REFERENCES.
            metric: Mesure de similarité ('cosine', 'l2', 'l1'). Défaut: cosine.
        """
        self._references = references or DOCUMENT_TYPE_REFERENCES
        self._metric = metric
        self._reference_embeddings: Optional[Dict[str, List[float]]] = None
        self._embedding_service = None

    @property
    def _service(self):
        if self._embedding_service is None:
            from core.ai.embeddings import embedding_service
            self._embedding_service = embedding_service
        return self._embedding_service

    @property
    def metric(self) -> str:
        return self._metric

    @metric.setter
    def metric(self, value: str):
        """Permet de changer la métrique à runtime."""
        self._metric = value

    def _ensure_reference_embeddings(self):
        """Génère les embeddings de référence si pas encore fait."""
        if self._reference_embeddings is not None:
            return

        logger.info(f"Calcul des embeddings de référence ({len(self._references)} types)...")
        self._reference_embeddings = {}

        texts = list(self._references.values())
        labels = list(self._references.keys())
        embeddings = self._service.generate_embeddings_batch(texts)

        for label, emb in zip(labels, embeddings):
            if emb is not None:
                self._reference_embeddings[label] = emb
            else:
                logger.warning(f"Embedding de référence échoué pour {label}")

        logger.info(f"{len(self._reference_embeddings)} embeddings de référence calculés")

    def classify(
        self,
        text: str,
        top_k: int = 3,
        metric: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Classifie un texte en le comparant aux embeddings de référence.

        Args:
            text: Texte à classifier (contenu du document)
            top_k: Nombre de résultats à retourner
            metric: Métrique de distance (surcharge l'instance). None = self._metric.

        Returns:
            Liste de (type_document, score) triée par score décroissant.
            Le score est une similarité (1 = identique).
        """
        self._ensure_reference_embeddings()

        if not self._reference_embeddings:
            logger.error("Aucun embedding de référence disponible")
            return [('AUTRE', 0.0)]

        # Embedding du texte à classifier
        text_embedding = self._service.generate_embedding(text[:8000])
        if text_embedding is None:
            return [('AUTRE', 0.0)]

        effective_metric = metric or self._metric

        # Calculer la similarité avec chaque référence
        scores = []
        for label, ref_embedding in self._reference_embeddings.items():
            similarity = self._service.compute_similarity(
                text_embedding, ref_embedding, metric=effective_metric
            )
            scores.append((label, similarity))

        # Trier par score décroissant
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def classify_best(
        self,
        text: str,
        min_confidence: float = 0.3,
        metric: Optional[str] = None,
    ) -> Tuple[str, float]:
        """
        Retourne le meilleur type avec son score.

        Args:
            text: Texte à classifier
            min_confidence: Score minimum pour accepter la classification
            metric: Métrique de distance (optionnel)

        Returns:
            (type_document, confidence). Retourne ('AUTRE', 0.0) si sous le seuil.
        """
        results = self.classify(text, top_k=1, metric=metric)
        if not results:
            return ('AUTRE', 0.0)

        best_type, best_score = results[0]
        if best_score < min_confidence:
            return ('AUTRE', best_score)

        return (best_type, best_score)

    def reset_cache(self):
        """Force le recalcul des embeddings de référence."""
        self._reference_embeddings = None


# Singleton — classificateur de documents par défaut (cosine)
document_classifier = EmbeddingClassifier(metric='cosine')

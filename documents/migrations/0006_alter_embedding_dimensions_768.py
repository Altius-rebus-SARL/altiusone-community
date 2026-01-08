# Generated for AltiusOne AI SDK migration (768D embeddings)
from django.db import migrations


class Migration(migrations.Migration):
    """
    Migration pour changer les dimensions des vecteurs de 1536 a 768.

    Le SDK AltiusOne AI genere des embeddings de 768 dimensions,
    optimises pour la recherche semantique multilingue (FR/DE/IT/EN).

    Cette migration:
    1. Supprime les anciens embeddings (incompatibles)
    2. Modifie les colonnes vector de 1536 a 768 dimensions
    3. Recree les index HNSW

    IMPORTANT: Apres cette migration, executer la tache de reindexation:
    python manage.py shell -c "from documents.tasks import reindexer_tous_documents; reindexer_tous_documents.delay()"
    """

    dependencies = [
        ('documents', '0005_documentembedding_textchunkembedding'),
    ]

    operations = [
        # 1. Supprimer les anciens index HNSW (necessaire avant modification de colonne)
        migrations.RunSQL(
            sql="""
            DROP INDEX IF EXISTS document_embedding_hnsw_idx;
            DROP INDEX IF EXISTS chunk_embedding_hnsw_idx;
            """,
            reverse_sql="",  # Index recrees dans l'etape suivante
        ),

        # 2. Vider les tables d'embeddings existants (incompatibles avec nouvelles dimensions)
        migrations.RunSQL(
            sql="""
            -- Sauvegarder les statistiques avant suppression
            DO $$
            DECLARE
                doc_count INTEGER;
                chunk_count INTEGER;
            BEGIN
                SELECT COUNT(*) INTO doc_count FROM document_embeddings;
                SELECT COUNT(*) INTO chunk_count FROM text_chunk_embeddings;
                RAISE NOTICE 'Suppression de % embeddings de documents et % embeddings de chunks', doc_count, chunk_count;
            END $$;

            -- Supprimer les embeddings existants
            TRUNCATE TABLE text_chunk_embeddings;
            TRUNCATE TABLE document_embeddings CASCADE;
            """,
            reverse_sql="-- Pas de restauration possible",
        ),

        # 3. Modifier les colonnes vector de 1536 a 768 dimensions
        migrations.RunSQL(
            sql="""
            -- Modifier la colonne embedding dans document_embeddings
            ALTER TABLE document_embeddings
            ALTER COLUMN embedding TYPE vector(768);

            -- Modifier la dimension par defaut
            ALTER TABLE document_embeddings
            ALTER COLUMN dimensions SET DEFAULT 768;

            -- Modifier la colonne embedding dans text_chunk_embeddings
            ALTER TABLE text_chunk_embeddings
            ALTER COLUMN embedding TYPE vector(768);
            """,
            reverse_sql="""
            -- Retour a 1536 dimensions
            ALTER TABLE document_embeddings
            ALTER COLUMN embedding TYPE vector(1536);

            ALTER TABLE document_embeddings
            ALTER COLUMN dimensions SET DEFAULT 1536;

            ALTER TABLE text_chunk_embeddings
            ALTER COLUMN embedding TYPE vector(1536);
            """,
        ),

        # 4. Mettre a jour les valeurs de model_used pour reflechir le nouveau modele
        migrations.RunSQL(
            sql="""
            -- Mettre a jour le model par defaut
            ALTER TABLE document_embeddings
            ALTER COLUMN model_used SET DEFAULT 'altiusone-768';

            ALTER TABLE text_chunk_embeddings
            ALTER COLUMN model_used SET DEFAULT 'altiusone-768';

            -- Ajouter un commentaire sur le changement
            COMMENT ON COLUMN document_embeddings.embedding IS 'Vecteur 768D genere par AltiusOne AI SDK';
            COMMENT ON COLUMN text_chunk_embeddings.embedding IS 'Vecteur 768D genere par AltiusOne AI SDK';
            """,
            reverse_sql="""
            ALTER TABLE document_embeddings
            ALTER COLUMN model_used SET DEFAULT 'openai-small';

            ALTER TABLE text_chunk_embeddings
            ALTER COLUMN model_used SET DEFAULT 'openai-small';
            """,
        ),

        # 5. Recreer les index HNSW avec les nouvelles dimensions
        migrations.RunSQL(
            sql="""
            -- Index HNSW pour recherche rapide de similarite cosinus sur documents
            CREATE INDEX document_embedding_hnsw_idx
            ON document_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);

            -- Index HNSW pour recherche rapide sur les chunks
            CREATE INDEX chunk_embedding_hnsw_idx
            ON text_chunk_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS document_embedding_hnsw_idx;
            DROP INDEX IF EXISTS chunk_embedding_hnsw_idx;
            """,
        ),

        # 6. Ajouter une table de log pour tracer la migration
        migrations.RunSQL(
            sql="""
            -- Log de la migration
            DO $$
            BEGIN
                RAISE NOTICE 'Migration terminee: embeddings 768D AltiusOne AI';
                RAISE NOTICE 'Executez la reindexation: python manage.py shell -c "from documents.tasks import reindexer_tous_documents; reindexer_tous_documents.delay()"';
            END $$;
            """,
            reverse_sql="",
        ),
    ]

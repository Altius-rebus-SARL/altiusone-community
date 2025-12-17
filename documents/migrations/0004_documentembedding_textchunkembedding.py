# Generated manually for PGVector embeddings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Migration pour ajouter les modèles d'embeddings vectoriels (PGVector).

    Prérequis:
    - Extension pgvector installée dans PostgreSQL
    - CREATE EXTENSION IF NOT EXISTS vector;
    """

    dependencies = [
        ('documents', '0003_alter_categoriedocument_created_at_and_more'),
    ]

    operations = [
        # S'assurer que l'extension pgvector est activée
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),

        # Créer la table document_embeddings
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS document_embeddings (
                document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
                embedding vector(1536),
                model_used VARCHAR(50) DEFAULT 'openai-small',
                dimensions INTEGER DEFAULT 1536,
                text_hash VARCHAR(64) NOT NULL,
                text_length INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Index HNSW pour recherche rapide de similarité cosinus
            CREATE INDEX IF NOT EXISTS document_embedding_hnsw_idx
            ON document_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);

            -- Index sur le modèle utilisé
            CREATE INDEX IF NOT EXISTS document_embeddings_model_idx
            ON document_embeddings(model_used);

            -- Commentaire sur la table
            COMMENT ON TABLE document_embeddings IS 'Embeddings vectoriels pour recherche sémantique des documents';
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS document_embedding_hnsw_idx;
            DROP INDEX IF EXISTS document_embeddings_model_idx;
            DROP TABLE IF EXISTS document_embeddings;
            """,
        ),

        # Créer la table text_chunk_embeddings pour les documents longs
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS text_chunk_embeddings (
                id SERIAL PRIMARY KEY,
                document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                chunk_start INTEGER NOT NULL,
                chunk_end INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding vector(1536),
                model_used VARCHAR(50) DEFAULT 'openai-small',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

                UNIQUE(document_id, chunk_index)
            );

            -- Index HNSW pour recherche rapide sur les chunks
            CREATE INDEX IF NOT EXISTS chunk_embedding_hnsw_idx
            ON text_chunk_embeddings
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);

            -- Index sur le document
            CREATE INDEX IF NOT EXISTS text_chunk_embeddings_document_idx
            ON text_chunk_embeddings(document_id);

            -- Commentaire sur la table
            COMMENT ON TABLE text_chunk_embeddings IS 'Embeddings de chunks pour documents longs - recherche sémantique granulaire';
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS chunk_embedding_hnsw_idx;
            DROP INDEX IF EXISTS text_chunk_embeddings_document_idx;
            DROP TABLE IF EXISTS text_chunk_embeddings;
            """,
        ),

        # Fonction pour mettre à jour updated_at automatiquement
        migrations.RunSQL(
            sql="""
            CREATE OR REPLACE FUNCTION update_document_embeddings_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;

            DROP TRIGGER IF EXISTS update_document_embeddings_updated_at_trigger ON document_embeddings;

            CREATE TRIGGER update_document_embeddings_updated_at_trigger
            BEFORE UPDATE ON document_embeddings
            FOR EACH ROW
            EXECUTE FUNCTION update_document_embeddings_updated_at();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS update_document_embeddings_updated_at_trigger ON document_embeddings;
            DROP FUNCTION IF EXISTS update_document_embeddings_updated_at();
            """,
        ),
    ]

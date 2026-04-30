from django.db import migrations


def create_pgvector_product_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_product_vector (
                product_id uuid PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                embedding vector(384) NOT NULL,
                embedding_model varchar(120) NOT NULL,
                text_hash char(64) NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS market_product_vector_embedding_hnsw_idx
            ON market_product_vector
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS market_product_vector_model_updated_idx
            ON market_product_vector (embedding_model, updated_at DESC)
            """
        )


def drop_pgvector_product_index(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS market_product_vector")


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0015_add_product_attributes'),
    ]

    operations = [
        migrations.RunPython(create_pgvector_product_index, drop_pgvector_product_index),
    ]

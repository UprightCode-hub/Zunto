from django.db import migrations


def ensure_pgvector_extension(connection):
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
            )
            if not bool(cursor.fetchone()[0]):
                return False
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            return True
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        return False


def create_dimension_ready_pgvector_tables(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    if not ensure_pgvector_extension(schema_editor.connection):
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            ALTER TABLE IF EXISTS market_product_vector
            ADD COLUMN IF NOT EXISTS embedding_dimensions integer NOT NULL DEFAULT 384
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_product_vector_768 (
                product_id uuid PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                embedding vector(768) NOT NULL,
                embedding_dimensions integer NOT NULL DEFAULT 768,
                embedding_model varchar(120) NOT NULL,
                text_hash char(64) NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS market_product_vector_768_embedding_hnsw_idx
            ON market_product_vector_768
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS market_product_vector_768_model_updated_idx
            ON market_product_vector_768 (embedding_model, embedding_dimensions, updated_at DESC)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS market_product_vector_model_dims_updated_idx
            ON market_product_vector (embedding_model, embedding_dimensions, updated_at DESC)
            """
        )


def drop_dimension_ready_pgvector_tables(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS market_product_vector_768")
        cursor.execute("DROP INDEX IF EXISTS market_product_vector_model_dims_updated_idx")


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('market', '0020_product_locked_image_fields'),
    ]

    operations = [
        migrations.RunPython(
            create_dimension_ready_pgvector_tables,
            drop_dimension_ready_pgvector_tables,
        ),
    ]

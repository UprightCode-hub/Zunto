from django.db import migrations


PGVECTOR_UNAVAILABLE_MESSAGE = (
    "The PostgreSQL pgvector extension is not available on this database. "
    "Render Postgres must be PostgreSQL 13+ with the vector extension available. "
    "Check the Render Postgres database/plan before deploying Zunto's vector index."
)

PGVECTOR_PERMISSION_MESSAGE = (
    "Unable to enable the PostgreSQL pgvector extension with "
    "`CREATE EXTENSION IF NOT EXISTS vector`. The current database user may not "
    "have permission to create extensions. Check that the Render Postgres role "
    "owns the database or has permission to create the vector extension. "
    "Original database error: {error}"
)


def ensure_pgvector_extension(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
        )
        if not bool(cursor.fetchone()[0]):
            raise RuntimeError(PGVECTOR_UNAVAILABLE_MESSAGE)

        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        except Exception as exc:
            raise RuntimeError(PGVECTOR_PERMISSION_MESSAGE.format(error=exc)) from exc

        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
        )
        if not bool(cursor.fetchone()[0]):
            raise RuntimeError(
                "CREATE EXTENSION completed, but pg_extension does not list vector. "
                "Check the Render Postgres role and extension state."
            )


def ensure_pgvector_extension_and_tables(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return

    ensure_pgvector_extension(schema_editor.connection)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS market_product_vector (
                product_id uuid PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
                embedding vector(384) NOT NULL,
                embedding_dimensions integer NOT NULL DEFAULT 384,
                embedding_model varchar(120) NOT NULL,
                text_hash char(64) NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cursor.execute(
            """
            ALTER TABLE IF EXISTS market_product_vector
            ADD COLUMN IF NOT EXISTS embedding_dimensions integer NOT NULL DEFAULT 384
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
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS market_product_vector_model_dims_updated_idx
            ON market_product_vector (embedding_model, embedding_dimensions, updated_at DESC)
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


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('market', '0021_pgvector_dimension_ready_indexes'),
    ]

    operations = [
        migrations.RunPython(
            ensure_pgvector_extension_and_tables,
            migrations.RunPython.noop,
        ),
    ]

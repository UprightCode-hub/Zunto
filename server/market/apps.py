# server/market/apps.py
from django.apps import AppConfig


class MarketConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "market"

    def ready(self):
        import market.signals  # noqa: F401
        self._register_sqlite_vec_loader()

    # ------------------------------------------------------------------ #
    # sqlite-vec: load the extension on every new SQLite connection.       #
    # Django creates fresh connections per-thread, per-request, and in     #
    # management commands — none of them survive across process boundaries. #
    # connection_created is the only reliable hook that fires before any    #
    # SQL runs on that connection.                                          #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _register_sqlite_vec_loader():
        import logging
        from django.db.backends.signals import connection_created

        logger = logging.getLogger(__name__)

        def _load_vec(sender, connection, **kwargs):
            """Auto-load sqlite-vec on every new SQLite connection."""
            if connection.vendor != "sqlite":
                return
            try:
                import sqlite_vec

                raw = connection.connection          # the actual sqlite3.Connection
                raw.enable_load_extension(True)
                sqlite_vec.load(raw)
                raw.enable_load_extension(False)
            except Exception as exc:
                logger.warning(
                    "sqlite-vec failed to load on new connection: %s", exc
                )
                # best-effort: make sure extension loading is disabled again
                try:
                    connection.connection.enable_load_extension(False)
                except Exception:
                    pass

        connection_created.connect(_load_vec)
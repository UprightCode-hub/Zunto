from django.urls import path

urlpatterns = []

try:
    from ninja import NinjaAPI
    from assistant.ninja_api import router as assistant_router

    api = NinjaAPI(title="Assistant Ninja API", version="1.0")
    api.add_router("/", assistant_router)

    urlpatterns = [
        path('', api.urls),
    ]
except Exception:
    # Keep project bootable even when django-ninja is not installed yet.
    urlpatterns = []

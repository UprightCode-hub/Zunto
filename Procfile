web: daphne ZuntoProject.asgi:application --port $PORT --bind 0.0.0.0
worker: celery -A ZuntoProject worker --loglevel=info
beat: celery -A ZuntoProject beat --loglevel=info
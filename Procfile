web: gunicorn --pythonpath app views:app
worker: celery -A app.tasks worker -B --loglevel=info

web: gunicorn --pythonpath app views:app
worker: celery worker -A app.celery

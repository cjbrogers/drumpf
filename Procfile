web: gunicorn --pythonpath app views.py
worker: celery worker -A app.celery

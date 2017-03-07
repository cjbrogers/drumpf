web: gunicorn --pythonpath app views:app
worker: celery worker --app=tasks.app

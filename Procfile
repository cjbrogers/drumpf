web: gunicorn --pythonpath app views:app
worker: celery worker --pythonpath app --app=tasks.app

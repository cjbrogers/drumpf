web: gunicorn --pythonpath app views:app
worker: python --pythonpath app tasks.py celery worker -B -l info

from celery import Celery
app = Celery('tasks')
import os
app.conf.update(BROKER_URL=os.environ['RABBITMQ_BIGWIG_URL'])

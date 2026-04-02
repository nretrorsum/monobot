# import os
#
# from celery import Celery
#
# CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
# CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
#
# celery_app = Celery(
#     "monobot",
#     broker=CELERY_BROKER_URL,
#     backend=CELERY_RESULT_BACKEND,
# )
#
# celery_app.conf.beat_scheduler = "redbeat.RedBeatScheduler"
# celery_app.conf.redbeat_redis_url = CELERY_BROKER_URL
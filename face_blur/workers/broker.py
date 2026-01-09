from taskiq_aio_pika import AioPikaBroker
from taskiq_redis import RedisAsyncResultBackend

from face_blur.core.config import settings

broker = AioPikaBroker(settings.rabbitmq_url).with_result_backend(
    RedisAsyncResultBackend(settings.redis_url)
)

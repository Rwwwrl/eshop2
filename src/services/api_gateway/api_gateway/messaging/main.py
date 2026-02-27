from faststream.rabbit import RabbitBroker

from api_gateway.settings import settings

broker = RabbitBroker(url=settings.rabbitmq_url)

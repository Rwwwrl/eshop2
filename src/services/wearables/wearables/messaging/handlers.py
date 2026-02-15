from wearables.messaging.main import broker


@broker.task
async def hello_world_task() -> str:
    return "Hello from TaskIQ!"

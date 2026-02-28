# FastStream Step-by-Step Guides

## Adding FastStream to a New Service

1. Add dependencies: `poetry add 'faststream[rabbit,cli]'`
2. Add `myeshop-messaging-contracts`, `myeshop-rabbitmq-topology` path dependencies
3. Mix `FaststreamSettingsMixin` into the service `Settings` class
4. Add `rabbitmq_url` to `env.yaml`
5. Add `RABBITMQ_URL` to the service's ExternalSecret (mapped from `rabbitmq-url` GCP secret)
6. Create `messaging/__init__.py`, `messaging/main.py`, `messaging/handlers.py`
7. Copy broker + `AsgiFastStream` setup from an existing service (e.g., `hello_world`)
8. Define message types in `messaging_contracts/` (or reuse existing ones)
9. Add exchange + bindings in `rabbitmq_topology/entities.py`
10. Add k8s manifests: `base/messaging/deployment.yaml`, `kustomization.yaml`, plus environment overlays
11. Add `test_broker` fixture to service `tests/conftest.py`
12. Create `processed_message` expand migration: `poetry run alembic -c alembic.ini revision --head expand@head -m "add processed_message table"`
13. Add `ProcessedMessage` to `autocleared_sqlmodel_tables` in `tests/conftest.py`

## Adding a New Message Type

1. Define the message class in `messaging_contracts/` (inherit `Event` or `AsyncCommand`), assign a unique `code: ClassVar[int]`
2. Import the new module in `messaging_contracts/__init__.py` to trigger registration
3. Add exchange in `rabbitmq_topology/resources.py` using `get_exchange_name()`
4. Add binding(s) to connect the exchange to consumer queue(s)
5. Run `RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply`
6. Add handler with `message_type_filter()` in the consumer service

## Idempotent Handler Setup for New Services

1. Create an expand migration for `processed_message` table:
   ```bash
   cd src/services/<service>
   poetry run alembic -c alembic.ini revision --head expand@head -m "add processed_message table"
   ```
2. The migration creates the table defined by `libs.faststream_ext.models.ProcessedMessage` (id, logical_id with unique constraint, created_at, updated_at)
3. Add `ProcessedMessage` to `autocleared_sqlmodel_tables` in `tests/conftest.py`:
   ```python
   from libs.faststream_ext.models import ProcessedMessage

   @pytest.fixture(scope="session")
   def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
       return [ProcessedMessage]  # add alongside other tables
   ```
4. Worker `main.py` must init the DB engine and bind `Session` in lifespan (see Worker Setup in SKILL.md)

## Local Development

```bash
# Start RabbitMQ
docker compose up -d rabbitmq

# Apply topology
RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply

# RabbitMQ management UI
open http://localhost:25672  # guest/guest

# Run worker
FASTSTREAM_CLI_RICH_MODE=none poetry run faststream run <service>.messaging.main:app
```

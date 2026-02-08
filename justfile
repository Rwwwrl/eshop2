import 'justfile.local'

[group('run')]
run-api-gateway:
    cd src/services/api_gateway && poetry run uvicorn api_gateway.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 75

[group('run')]
run-hello-world:
    cd src/services/hello_world && poetry run uvicorn hello_world.main:app --host 0.0.0.0 --port 8001

[group('run')]
run-wearables:
    cd src/services/wearables && poetry run uvicorn wearables.main:app --host 0.0.0.0 --port 8002 --timeout-keep-alive 75


[group('test')]
test:
    poetry run pytest -s -c pytest.ini


[group('infra')]
infra-up:
    docker compose -p eshop2 up -d

[group('infra')]
infra-down:
    docker compose -p eshop2 down

[group('infra')]
infra-restart:
    docker compose -p eshop2 restart


[group('db')]
alembic-autogenerate message:
    cd src/services/wearables && poetry run alembic revision --autogenerate -m "{{message}}"

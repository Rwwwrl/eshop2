import 'justfile.local'


[group('test')]
test:
    poetry run pytest -s


[group('infra')]
up-infra:
    docker compose -f docker-compose.yaml -p eshop2 up -d

[group('infra')]
down-infra:
    docker compose -f docker-compose.yaml -p eshop2 down

[group('infra')]
restart-infra:
    docker compose -f docker-compose.yaml -p eshop2 restart

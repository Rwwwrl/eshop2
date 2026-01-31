import 'justfile.local'

[group('docker')]
dbuild:
    docker build -t api-gateway:latest src/services/api_gateway
    docker build -t hello-world:latest src/services/hello_world



[group('kuber-dev')]
kapply-dev:
	kubectl apply -k deploy/k8s/hello-world/dev
	kubectl apply -k deploy/k8s/api-gateway/dev

[group('kuber-dev')]
kdelete-dev:
	kubectl delete -k deploy/k8s/hello-world/dev
	kubectl delete -k deploy/k8s/api-gateway/dev

[group('kuber-dev')]
krestart-deployments-dev:
	kubectl rollout restart deployment/api-gateway
	kubectl rollout restart deployment/hello-world

-include Makefile.local

# ------------------------------------------------------------------------------
# Docker
# ------------------------------------------------------------------------------

dbuild: dbuild_api_gateway dbuild_hello_world_service

dbuild_api_gateway:
	docker build -t api-gateway:latest src/services/api_gateway

dbuild_hello_world_service:
	docker build -t hello-world-service:latest src/services/hello_world_service

# ------------------------------------------------------------------------------
# Kubernetes
# ------------------------------------------------------------------------------

kapply:
	kubectl apply --recursive -f deploy/k8s/

krestartdeployments:
	ls deploy/k8s/*/deployment.yaml | xargs -I {} kubectl rollout restart -f {}

kdelete:
	kubectl delete -f deploy/k8s/ --recursive

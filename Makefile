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
	kubectl apply -k deploy/k8s/overlays/dev

kdelete:
	kubectl delete -k deploy/k8s/overlays/dev

krestartdeployments:
	kubectl rollout restart deployment/api-gateway deployment/hello-world-service

kbuild:
	kubectl kustomize deploy/k8s/overlays/dev

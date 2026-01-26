-include Makefile.local

# ------------------------------------------------------------------------------
# Docker
# ------------------------------------------------------------------------------

dbuild: dbuild_api_gateway dbuild_hello_world

dbuild_api_gateway:
	docker build -t api-gateway:latest src/services/api_gateway

dbuild_hello_world:
	docker build -t hello-world:latest src/services/hello_world

# ------------------------------------------------------------------------------
# Kubernetes
# ------------------------------------------------------------------------------

kapply:
	kubectl apply -k deploy/k8s/overlays/dev

kdelete:
	kubectl delete -k deploy/k8s/overlays/dev

krestartdeployments:
	kubectl rollout restart deployment/api-gateway deployment/hello-world

kbuild:
	kubectl kustomize deploy/k8s/overlays/dev

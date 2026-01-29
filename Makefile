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

kapply: kapply_api_gateway kapply_hello_world

kapply_api_gateway:
	kubectl apply -k deploy/k8s/api-gateway/dev

kapply_hello_world:
	kubectl apply -k deploy/k8s/hello-world/dev

kdelete: kdelete_api_gateway kdelete_hello_world

kdelete_api_gateway:
	kubectl delete -k deploy/k8s/api-gateway/dev

kdelete_hello_world:
	kubectl delete -k deploy/k8s/hello-world/dev

krestartdeployments:
	kubectl rollout restart deployment/api-gateway deployment/hello-world

kbuild: kbuild_api_gateway kbuild_hello_world

kbuild_api_gateway:
	kustomize build deploy/k8s/api-gateway/dev

kbuild_hello_world:
	kustomize build deploy/k8s/hello-world/dev

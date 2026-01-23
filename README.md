# MyEshop Backend

Learning project for building microservices architecture with Kubernetes.

## Services

- `api_gateway` - public-facing, receives user requests (LoadBalancer)
- `hello_world` - internal service (ClusterIP)

## Requirements

- minikube
- docker

## Deploy to Minikube

```bash
eval $(minikube docker-env)
make dbuild
make kapply
```

## Restart Deployments

```bash
make krestartdeployments
```

## Delete Deploy

```bash
make kdelete
```

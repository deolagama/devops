# Exercise 10 – Multi-Node Kubernetes Cluster with Multiple Applications and ReplicaSets

## Objective

Deploy two Flask microservices (**Product Catalog** and **Shopping Cart**) on a **3-node Minikube cluster** using Deployments (ReplicaSets) and **pod anti-affinity**, so that every replica of an application runs on a different node. Expose both services with NodePort Services, test the APIs, and observe how the cluster behaves when a node is stopped.

## Scenario

An online store needs high availability for critical services such as product browsing and cart management.

| Service         | Application | Replicas |
|-----------------|-------------|----------|
| Product Catalog | AppA        | 2        |
| Shopping Cart   | AppB        | 3        |

Replicas are spread across multiple nodes so that the failure of a single node does not take a service down.

## Environment

| Item              | Value                                  |
|-------------------|----------------------------------------|
| OS                | macOS (Darwin 12.7.6)                  |
| Shell             | VS Code integrated terminal (bash)     |
| Kubernetes        | v1.37.0                                |
| Minikube          | v1.39.0                                |
| Minikube Driver   | Docker (Docker Desktop for Mac)        |
| Node Runtime      | containerd (Minikube default)          |
| Applications      | Python 3.9 + Flask                     |

### Prerequisites (macOS)

```bash
brew install minikube kubectl
```

Install and **start Docker Desktop** before beginning (check with `docker info`).

## Project Structure

```
10-Multi-Node-Kubernetes-Cluster/
├── README.md
├── product_catalog.py
├── shopping_cart.py
├── Dockerfile.product
├── Dockerfile.shopping
├── product_catalog_deployment.yaml
├── shopping_cart_deployment.yaml
├── product_catalog_service.yaml
├── shopping_cart_service.yaml
└── images/
    ├── 01-cluster-nodes.png
    ├── 02-docker-build.png
    ├── 03-minikube-images.png
    ├── 04-deploy-services.png
    ├── 05-pods-across-nodes.png
    ├── 06a-tunnel-product-catalog.png
    ├── 06b-tunnel-shopping-cart.png
    ├── 07-api-testing.png
    ├── 08-node-stop.png
    └── 09-node-restart.png
```

---

## 1. Clean Up and Start the Multi-Node Cluster

Remove any existing Minikube clusters:

```bash
minikube delete --all
```

Start a 3-node cluster in a profile named `devops-multinode`:

```bash
minikube start --nodes 3 -p devops-multinode --driver=docker
```

Verify the nodes:

```bash
kubectl get nodes
```

All three nodes (one control-plane and two workers) are in the `Ready` state.

![Cluster Nodes](images/01-cluster-nodes.png)

---

## 2. Create the Applications

Two Flask applications live in the exercise folder.

**Product Catalog** (`product_catalog.py`) exposes `GET /products`, which returns a static list of three products.

**Shopping Cart** (`shopping_cart.py`) exposes:

- `GET /cart` – view the cart
- `POST /cart` – add an item to the cart

Both applications listen on **port 80**.

---

## 3. Dockerize the Applications

Each application has its own Dockerfile (`Dockerfile.product` and `Dockerfile.shopping`), both based on `python:3.9-slim` with Flask installed.

Build the images:

```bash
docker build -t product-catalog:latest -f Dockerfile.product .
docker build -t shopping-cart:latest -f Dockerfile.shopping .
docker images
```

![Docker Build](images/02-docker-build.png)

---

## 4. Load the Images into Minikube

In a multi-node cluster, images built on the host are not automatically available on every node. Load them into all nodes of the profile:

```bash
minikube -p devops-multinode image load product-catalog:latest
minikube -p devops-multinode image load shopping-cart:latest
```

Verify the images inside the Minikube cluster:

```bash
minikube -p devops-multinode image ls
```

The output lists the Kubernetes system images (kube-apiserver, kube-scheduler, etcd, coredns, pause, etc.) along with the two application images, `product-catalog:latest` and `shopping-cart:latest`.

> The Minikube nodes run **containerd**, not Docker, so `minikube ssh -- docker images` will not work inside a node. Use `image ls` instead, or `minikube -p devops-multinode ssh -n devops-multinode-m02 -- sudo crictl images` to inspect one specific node.

![Docker Images in Minikube](images/03-minikube-images.png)

---

## 5. Deploy the Applications

Two Deployments are created:

- `product-catalog` with `replicas: 2`
- `shopping-cart` with `replicas: 3`

Both use `imagePullPolicy: Never` so Kubernetes uses the locally loaded images instead of pulling from a registry.

Each Deployment also defines a `podAntiAffinity` rule:

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app: product-catalog
      topologyKey: "kubernetes.io/hostname"
```

This rule forbids two pods of the same application from being scheduled on the same node. Because the Shopping Cart has 3 replicas and the cluster has 3 nodes, each node runs exactly one cart pod.

Apply the Deployments:

```bash
kubectl apply -f product_catalog_deployment.yaml
kubectl apply -f shopping_cart_deployment.yaml
```

---

## 6. Expose the Services

Both applications are exposed using NodePort Services:

```bash
kubectl apply -f product_catalog_service.yaml
kubectl apply -f shopping_cart_service.yaml
```

Check everything that was created (Deployments, ReplicaSets, Services):

```bash
kubectl get deployments,rs,svc
```

![Deployments and Services](images/04-deploy-services.png)

---

## 7. Verify Pod Distribution

```bash
kubectl get pods -o wide
```

Result:

- The two `product-catalog` pods run on `devops-multinode-m02` and `devops-multinode-m03`.
- The three `shopping-cart` pods are spread across the control-plane node, `m02`, and `m03`.
- All pods are `Running` with `READY 1/1` and have unique IP addresses.

No two replicas of the same application share a node, so the anti-affinity rule is working as intended.

![Pods Across Nodes](images/05-pods-across-nodes.png)

---

## 8. Access the Services

Because the Docker driver is used on macOS, each service needs its own tunnel, and **the terminal must stay open while the tunnel is running**. Open two new Terminal windows (or tabs, `Cmd + T`).

**Terminal 2:**

```bash
minikube -p devops-multinode service product-catalog-service --url
```

![Product Catalog Tunnel](images/06a-tunnel-product-catalog.png)

**Terminal 3:**

```bash
minikube -p devops-multinode service shopping-cart-service --url
```

![Shopping Cart Tunnel](images/06b-tunnel-shopping-cart.png)

> The port numbers (`56362`, `54630` in this example) are random and will be different on your machine. Use the URLs printed in your own terminals in the next step.

---

## 9. Test the APIs

Run these from the **original terminal** (replace the ports with your own):

```bash
# Product catalog: should return 3 products
curl http://127.0.0.1:56362/products

# Cart: should be empty at first
curl http://127.0.0.1:54630/cart

# Add an item (Laptop)
curl -X POST http://127.0.0.1:54630/cart \
  -H "Content-Type: application/json" \
  -d '{"id": 1, "name": "Laptop", "quantity": 1}'

# Cart again: should now show the Laptop
curl http://127.0.0.1:54630/cart
```

Results:

- `/products` returns Laptop, Phone, and Headphones.
- The cart is initially empty: `[]`.
- After the POST request, Laptop is added with `quantity = 1`.
- The final `GET /cart` returns the Laptop item.

![API Testing](images/07-api-testing.png)

> **Note:** The cart is stored in each pod's memory, and the Shopping Cart has 3 replicas. A request can be routed to any of them, so after a POST a later GET may occasionally return `[]` if it lands on a different pod. A shared store (e.g. Redis or a database) would fix this in a real application.

---

## 10. Fault Tolerance Demo

Stop one of the worker nodes:

```bash
minikube -p devops-multinode node stop devops-multinode-m02
```

Check the pods and nodes again:

```bash
kubectl get pods -o wide
kubectl get nodes
```

Result:

- Minikube reports `Successfully stopped node devops-multinode-m02`.
- The pods still appear as `Running` on `m02` for a while, alongside the pods on `m03` and the control-plane node.
- After about a minute, `kubectl get nodes` shows `m02` as `NotReady`.

Kubernetes does not react to a node failure instantly. The node controller first waits for the node to be marked `NotReady`, and by default pods on an unreachable node are evicted only after a grace period of about **5 minutes**. Pods on the remaining nodes continue to serve traffic during this time, so the services stay available.

![Node Stop and Pod Distribution](images/08-node-stop.png)

Bring the node back afterwards:

```bash
minikube -p devops-multinode node start devops-multinode-m02
kubectl get nodes
```

![Node Restart](images/09-node-restart.png)

---

## 11. How Kubernetes Works Here

```
kubectl apply
   ↓
Kubernetes API Server
   ↓
etcd (desired state: Deployment)
   ↓
Deployment Controller → ReplicaSet
   ↓
Scheduler (applies podAntiAffinity rule)
   ↓
Different Worker Nodes
   ↓
Kubelet
   ↓
Container Runtime
   ↓
Flask Containers
```

- The Deployment creates a ReplicaSet, which keeps the desired number of pods running.
- The Scheduler places each pod on a node that satisfies the `podAntiAffinity` rule.
- Kubelet on each node starts the containers through the container runtime.
- The NodePort Services route traffic to all healthy pods matching the `app` label.

---

## 12. Commands Used

```bash
minikube delete --all
minikube start --nodes 3 -p devops-multinode --driver=docker
kubectl get nodes

docker build -t product-catalog:latest -f Dockerfile.product .
docker build -t shopping-cart:latest -f Dockerfile.shopping .

minikube -p devops-multinode image load product-catalog:latest
minikube -p devops-multinode image load shopping-cart:latest
minikube -p devops-multinode image ls

kubectl apply -f product_catalog_deployment.yaml
kubectl apply -f shopping_cart_deployment.yaml
kubectl apply -f product_catalog_service.yaml
kubectl apply -f shopping_cart_service.yaml

kubectl get deployments,rs,svc
kubectl get pods -o wide

minikube -p devops-multinode service product-catalog-service --url
minikube -p devops-multinode service shopping-cart-service --url

minikube -p devops-multinode node stop devops-multinode-m02
minikube -p devops-multinode node start devops-multinode-m02
```

### Cleanup

```bash
minikube delete -p devops-multinode
```

---

## 13. Result

A 3-node Minikube cluster was created and two Flask applications were deployed on it: the Product Catalog with 2 replicas and the Shopping Cart with 3 replicas.

The pod anti-affinity rules placed every replica of an application on a different node. Both services were exposed with NodePort Services and tested successfully with `curl`. Stopping a worker node showed that the remaining nodes continue to host running pods, demonstrating the high availability that a multi-node setup provides.

---

## 14. Notes

- The `--force` flag is not needed on macOS. It is only required when running Minikube as root on Linux.
- The Shopping Cart Deployment originally used the namespace `devops-exercise`, which does not exist. It was changed to `default`.
- `minikube start` may warn that the local `kubectl` (1.21.4) is much older than the cluster (1.37.0). Basic commands still work, but you can upgrade with `brew upgrade kubectl`, or run `minikube kubectl -- get pods -A` instead.
- The registry add-on is not needed, since `minikube image load` copies images to every node.
- On macOS with the Docker driver, NodePorts are not reachable directly on `localhost`; use `minikube service ... --url` (a tunnel) as shown above.
- With `requiredDuringScheduling` anti-affinity and 3 nodes, if a node stays down long enough for its pods to be evicted, the replacement cart pod cannot be placed anywhere else and stays `Pending` until the node returns.

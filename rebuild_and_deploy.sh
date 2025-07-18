#!/usr/bin/env bash
# Rebuild local Docker images for the socket server and MPI engine,
# load them into the local Kind cluster, and restart the corresponding
# Kubernetes Deployments so that they point to the freshly-built images.
#
# Usage:
#   ./rebuild_and_deploy.sh [VERSION]
#
# If VERSION is omitted, the current timestamp "YYYYMMDDHHMMSS" is used.

set -euo pipefail

# ---------------------------
# Configuration
# ---------------------------
SOCKET_DEPLOY_NAME="socket-server"
MPI_DEPLOY_NAME="engine-mpi"
SPARK_DEPLOY_NAME="engine-spark"

SOCKET_IMAGE_REPO="socket-server"
MPI_IMAGE_REPO="engine-mpi"
SPARK_IMAGE_REPO="engine-spark"

VERSION="${1:-$(date +%Y%m%d%H%M%S)}"

SOCKET_IMAGE_TAG="${SOCKET_IMAGE_REPO}:${VERSION}"
MPI_IMAGE_TAG="${MPI_IMAGE_REPO}:${VERSION}"
SPARK_IMAGE_TAG="${SPARK_IMAGE_REPO}:${VERSION}"

# ---------------------------
# Helper functions
# ---------------------------
function info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
function error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }

# ---------------------------
# Delete old deployments (optional)
# ---------------------------
info "Deleting existing deployments (if any) …"
kubectl delete deployment "${SOCKET_DEPLOY_NAME}" "${MPI_DEPLOY_NAME}" "${SPARK_DEPLOY_NAME}" --ignore-not-found=true || true

# ---------------------------
# Build Docker images
# ---------------------------
info "Building Docker images with tag: ${VERSION} …"
docker build -t "${SOCKET_IMAGE_TAG}" -f socket-server/Dockerfile.server socket-server/
docker build -t "${MPI_IMAGE_TAG}"    -f mpi/Dockerfile.mpi mpi/
docker build -t "${SPARK_IMAGE_TAG}"   -f spark/Dockerfile.spark spark/

# ---------------------------
# Load images into the local Kind cluster
# ---------------------------
info "Loading images into Kind …"
kind load docker-image "${SOCKET_IMAGE_TAG}"
kind load docker-image "${MPI_IMAGE_TAG}"
kind load docker-image "${SPARK_IMAGE_TAG}"

# ---------------------------
# (Re)apply manifests
# ---------------------------
info "Applying Kubernetes manifests …"
# Services first (idempotent)
kubectl apply -f socket-server/socket_server_deployment.yaml
kubectl apply -f mpi/mpi-service.yaml
kubectl apply -f mpi/mpi_deployment.yaml
kubectl apply -f spark/spark-service.yaml
kubectl apply -f spark/spark_deployment.yaml

# ---------------------------
# Update the Deployments with the freshly built images
# ---------------------------
info "Updating Deployments with new image tags …"
kubectl set image deployment/"${SOCKET_DEPLOY_NAME}" "${SOCKET_DEPLOY_NAME}"="${SOCKET_IMAGE_TAG}" --record
kubectl set image deployment/"${MPI_DEPLOY_NAME}"    "${MPI_DEPLOY_NAME}"="${MPI_IMAGE_TAG}"       --record
kubectl set image deployment/"${SPARK_DEPLOY_NAME}"  "${SPARK_DEPLOY_NAME}"="${SPARK_IMAGE_TAG}"     --record

# ---------------------------
# Wait for the roll-outs to complete
# ---------------------------
info "Waiting for roll-outs to finish …"
kubectl rollout status deployment/"${SOCKET_DEPLOY_NAME}"
kubectl rollout status deployment/"${MPI_DEPLOY_NAME}"
kubectl rollout status deployment/"${SPARK_DEPLOY_NAME}"

# ---------------------------
# Show pod status
# ---------------------------
info "Current pod status:"
kubectl get pods -o wide

# ---------------------------
# Restart port-forward for MPI service (local 6600 -> service 6600)
# ---------------------------
info "Restarting port-forward for engine-mpi on localhost:6600 …"
# Mata quaisquer port-forwards anteriores possivelmente iniciados manualmente
pkill -f 'kubectl port-forward svc/engine-mpi' || true
PF_PID_FILE="${TMPDIR:-/tmp}/kpf_engine_mpi.pid"
if [[ -f "$PF_PID_FILE" ]] && kill -0 "$(cat "$PF_PID_FILE")" 2>/dev/null; then
  kill "$(cat "$PF_PID_FILE")" || true
fi
kubectl port-forward svc/engine-mpi 6600:6600 --address 0.0.0.0 >/dev/null 2>&1 &
echo $! > "$PF_PID_FILE"

# ---------------------------
# Restart port-forward for Spark service (local 6500 -> service 6500)
# ---------------------------
info "Restarting port-forward for engine-spark on localhost:6500 …"
pkill -f 'kubectl port-forward svc/engine-spark' || true
PF_PID_FILE_SPARK="${TMPDIR:-/tmp}/kpf_engine_spark.pid"
if [[ -f "$PF_PID_FILE_SPARK" ]] && kill -0 "$(cat "$PF_PID_FILE_SPARK")" 2>/dev/null; then
  kill "$(cat "$PF_PID_FILE_SPARK")" || true
fi
kubectl port-forward svc/engine-spark 6500:6500 --address 0.0.0.0 >/dev/null 2>&1 &
echo $! > "$PF_PID_FILE_SPARK"

info "Done! The cluster is now running the new images (tag: ${VERSION})."

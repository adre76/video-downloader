#!/bin/bash
# Interrompe o script se qualquer comando falhar
set -e

# --- Variáveis ---
# Altere estas variáveis se quiser usar um nome de imagem ou usuário diferente
DOCKERHUB_USERNAME="andrepereira21"
IMAGE_NAME="downloader"
IMAGE_TAG="latest"

FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

# --- Execução ---
echo "=> Fazendo login no Docker Hub..."
#docker login #Login não necessário com Docker Desktop instalado

echo "=> Removendo projeto antigo no Kubernetes (se existir)..."
kubectl delete all --all -n video-downloader

echo "=> Atualizando o repositório local..."
git pull origin main

echo "=> Construindo a imagem Docker: ${FULL_IMAGE_NAME}"
docker build -t "${FULL_IMAGE_NAME}" .

echo "=> Publicando a imagem no Docker Hub..."
docker push "${FULL_IMAGE_NAME}"

echo "✅ Imagem construída e publicada com sucesso!"
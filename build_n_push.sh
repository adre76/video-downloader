#!/bin/bash
# Interrompe o script se qualquer comando falhar
set -e

# --- Cores para o terminal ---
# Define códigos de cores para usar com 'echo -e'
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
NC='\033[0m' # No Color (reseta a cor para o padrão)

# --- Variáveis ---
# Altere estas variáveis se quiser usar um nome de imagem ou usuário diferente
DOCKERHUB_USERNAME="andrepereira21"
IMAGE_NAME="downloader"
IMAGE_TAG="latest"

FULL_IMAGE_NAME="${DOCKERHUB_USERNAME}/${IMAGE_NAME}:${IMAGE_TAG}"

# --- Execução ---
#echo "=> Fazendo login no Docker Hub..."
#docker login #Login não necessário com Docker Desktop instalado

echo
echo -e "${YELLOW}=> Removendo projeto antigo no Kubernetes (se existir)..."
kubectl delete all --all -n video-downloader
echo

echo -e "${YELLOW}=> Atualizando o repositório local..."
git pull origin main
echo

echo -e "${YELLOW}=> Construindo a imagem Docker: ${FULL_IMAGE_NAME}"
sudo docker build -t "${FULL_IMAGE_NAME}" .
echo


echo -e "${YELLOW}=> Publicando a imagem no Docker Hub..."
sudo docker push "${FULL_IMAGE_NAME}"
echo

echo -e "${GREEN}✅ Imagem construída e publicada com sucesso!"
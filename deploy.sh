#!/bin/bash
# Interrompe o script se qualquer comando falhar
set -e

# --- Cores para o terminal ---
YELLOW='\033[1;33m'
GREEN='\033[1;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color (reseta a cor)

# --- Variáveis ---
NAMESPACE="video-downloader"
HOST="downloader.local"

# --- Execução ---
echo # Linha em branco
echo -e "${YELLOW}=> Passo 1: Aplicando manifestos do Kubernetes ---${NC}"
kubectl apply -f kubernetes/01-namespace.yaml
kubectl apply -f kubernetes/02-pvc.yaml
kubectl apply -f kubernetes/03-deployment.yaml
kubectl apply -f kubernetes/04-service.yaml
kubectl apply -f kubernetes/05-ingress.yaml
echo -e "${GREEN}   Manifestos aplicados com sucesso.${NC}"
echo # Linha em branco

echo -e "${YELLOW}=> Passo 2: Aguardando o Deployment ficar disponível ---${NC}"
echo "   Isso pode levar alguns minutos enquanto a imagem do contêiner é baixada..."
kubectl wait --for=condition=available deployment/video-downloader-deployment -n $NAMESPACE --timeout=300s
echo
echo -e "${GREEN}✅ Deploy concluído e aplicação pronta!${NC}"
echo

# --- Instruções de Acesso ---
echo "--------------------------------------------------"
echo -e "${CYAN}🎉 APLICAÇÃO PRONTA PARA ACESSO 🎉${NC}"
echo "--------------------------------------------------"
echo
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
echo -e "${YELLOW}--- Passo 1: Aplicando manifestos do Kubernetes ---${NC}"
kubectl apply -f kubernetes/01-namespace.yaml
kubectl apply -f kubernetes/02-pvc.yaml
kubectl apply -f kubernetes/03-deployment.yaml
kubectl apply -f kubernetes/04-service.yaml
kubectl apply -f kubernetes/05-ingress.yaml
echo -e "${GREEN}   Manifestos aplicados com sucesso.${NC}"
echo # Linha em branco

echo -e "${YELLOW}--- Passo 2: Aguardando o Deployment ficar disponível ---${NC}"
echo "   Isso pode levar alguns minutos enquanto a imagem do contêiner é baixada..."
kubectl wait --for=condition=available deployment/video-downloader-deployment -n $NAMESPACE --timeout=300s
echo
echo -e "${GREEN}✅ Deploy concluído e aplicação pronta!${NC}"
echo

# --- Instruções de Acesso ---
echo "--------------------------------------------------"
echo -e "${CYAN}🎉 APLICAÇÃO PRONTA PARA ACESSO 🎉${NC}"
echo "--------------------------------------------------"
echo "Para acessar a aplicação, você precisa mapear o host '$HOST' para o IP do seu Ingress Controller."
echo
echo "1. Encontre o IP do Ingress (geralmente o IP de um dos nós do seu cluster RKE2):"
echo -e "   ${YELLOW}kubectl get nodes -o wide${NC}"
echo
echo "2. Edite seu arquivo 'hosts' no seu computador:"
echo "   - Linux/Mac: /etc/hosts"
echo "   - Windows: C:\\Windows\\System32\\drivers\\etc\\hosts"
echo "   Adicione a linha: ${GREEN}<IP_DO_NÓ> $HOST${NC}"
echo
echo "3. Após salvar o arquivo hosts, acesse no seu navegador:"
echo -e "   ➡️  ${GREEN}http://$HOST${NC}"
echo "--------------------------------------------------"
echo
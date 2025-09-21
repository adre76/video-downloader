#!/bin/bash

# Interrompe o script se qualquer comando falhar
set -e

# --- Variáveis ---
NAMESPACE="video-downloader"
HOST="downloader.local"

# --- Início do Script ---
echo "🚀 Iniciando o deploy do Video Downloader com Ingress..."

# 1. Cria o Namespace
echo "1. Criando o namespace '$NAMESPACE'..."
kubectl apply -f kubernetes/01-namespace.yaml

# 2. Cria o PersistentVolumeClaim (PVC)
echo "2. Criando o PersistentVolumeClaim (PVC)..."
kubectl apply -f kubernetes/02-pvc.yaml

# 3. Cria o Deployment
echo "3. Criando o Deployment (isso irá acionar o binding do PVC)..."
kubectl apply -f kubernetes/03-deployment.yaml

# 4. Cria o Serviço do tipo ClusterIP
echo "4. Criando o Serviço (Service)..."
kubectl apply -f kubernetes/04-service.yaml

# 5. Cria o Ingress para expor a aplicação
echo "5. Criando o Ingress para o host '$HOST'..."
kubectl apply -f kubernetes/05-ingress.yaml

# --- Verificações e Espera (ORDEM CORRIGIDA) ---
echo ""
echo "--- Aguardando recursos ficarem prontos ---"

# 1. Aguarda o Deployment ficar totalmente disponível.
#    Esta é a verificação mais importante. Se o pod está 'Running', o PVC obrigatoriamente estará 'Bound'.
echo "   Aguardando o Deployment ficar disponível..."
kubectl wait --for=condition=available deployment/video-downloader-deployment -n $NAMESPACE --timeout=300s
echo "   ✅ Deployment disponível!"

# 2. (Verificação de sanidade) Confirma que o PVC está vinculado.
#    Neste ponto, ele já deve estar 'Bound'. Usamos um timeout curto.
echo "   Verificando o status do PVC..."
kubectl wait --for=condition=Bound pvc/video-downloader-pvc -n $NAMESPACE --timeout=10s
echo "   ✅ PVC vinculado com sucesso!"

echo ""
echo "✅ Deploy concluído com sucesso!"
echo "--------------------------------------------------"

# --- Instruções de Acesso ---
echo "下一步: Para acessar a aplicação, você precisa mapear '$HOST' para o IP do seu Ingress Controller."
echo ""
echo "1. Encontre o IP do seu Ingress Controller com um dos seguintes comandos:"
echo "   kubectl get svc --all-namespaces | grep -i nginx   (Procure por EXTERNAL-IP)"
echo "   # Ou, se o EXTERNAL-IP estiver <pending>, use o IP de um dos nós do cluster:"
echo "   kubectl get nodes -o wide"
echo ""
echo "2. Edite seu arquivo hosts no seu computador (ex: /etc/hosts no Linux/Mac, C:\\Windows\\System32\\drivers\\etc\\hosts no Windows):"
echo "   Adicione a linha: <IP_DO_INGRESS> $HOST"
echo ""
echo "3. Após salvar o arquivo hosts, acesse a aplicação no seu navegador:"
echo "   🎉 http://$HOST"
echo "--------------------------------------------------"
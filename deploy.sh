#!/bin/bash

# Define o namespace para facilitar
NAMESPACE="video-downloader"

# --- Início do Script ---
echo "🚀 Iniciando o deploy do Video Downloader..."

# Passo 1: Criar o Namespace
echo "1. Criando o namespace '$NAMESPACE'..."
kubectl apply -f kubernetes/01-namespace.yaml

# Aguarda um momento para o namespace ser totalmente provisionado
sleep 2

# Passo 2: Criar o PersistentVolumeClaim (PVC)
echo "2. Criando o PersistentVolumeClaim (PVC)..."
kubectl apply -f kubernetes/02-pvc.yaml

# Aguarda o PVC ser vinculado ('Bound') a um volume.
# Este é um passo crucial para evitar que o Pod falhe ao tentar montar um volume que não está pronto.
echo "   Aguardando o PVC 'video-downloader-pvc' ser vinculado (Bound)..."
kubectl wait --for=condition=Bound pvc/video-downloader-pvc -n $NAMESPACE --timeout=120s
if [ $? -ne 0 ]; then
  echo "❌ Erro: O PVC não foi vinculado a tempo. Verifique a configuração do seu StorageClass 'local-path'."
  exit 1
fi
echo "   ✅ PVC vinculado com sucesso!"

# Passo 3: Criar o Deployment
echo "3. Criando o Deployment..."
kubectl apply -f kubernetes/03-deployment.yaml

# Passo 4: Criar o Serviço (Service)
echo "4. Criando o Serviço (Service) para expor a aplicação..."
kubectl apply -f kubernetes/04-service.yaml

# Aguarda o deployment ficar pronto
echo "   Aguardando o deployment ficar disponível..."
kubectl wait --for=condition=available deployment/video-downloader-deployment -n $NAMESPACE --timeout=180s

echo "✅ Deploy concluído com sucesso!"
echo "--------------------------------------------------"

# --- Informações de Acesso ---
echo "🔍 Buscando informações de acesso..."

# Pega o IP de um dos nós do cluster.
# Em um ambiente de produção, você usaria um Ingress ou LoadBalancer.
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
# Pega a porta NodePort alocada pelo serviço.
NODE_PORT=$(kubectl get svc video-downloader-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')

echo "🎉 Aplicação acessível em:"
echo "   http://$NODE_IP:$NODE_PORT"
echo "--------------------------------------------------"

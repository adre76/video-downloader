
#!/bin/bash

# Interrompe o script se qualquer comando falhar
set -e

# --- Variáveis ---
NAMESPACE="video-downloader"

# --- Início do Script ---
echo "🚀 Iniciando o deploy do Video Downloader..."

# 1. Cria o Namespace para organizar os recursos.
echo "1. Criando o namespace '$NAMESPACE'..."
kubectl apply -f kubernetes/01-namespace.yaml

# 2. Cria a Solicitação de Volume Persistente (PVC).
#    O PVC ficará no estado 'Pending' até que um Pod o solicite.
echo "2. Criando o PersistentVolumeClaim (PVC)..."
kubectl apply -f kubernetes/02-pvc.yaml

# 3. Cria o Deployment. A criação do Pod irá acionar o provisionamento do PVC.
echo "3. Criando o Deployment (isso irá acionar o binding do PVC)..."
kubectl apply -f kubernetes/03-deployment.yaml

# 4. Cria o Serviço para expor o Deployment.
echo "4. Criando o Serviço (Service)..."
kubectl apply -f kubernetes/04-service.yaml

# --- Verificações e Espera ---

# 5. Aguarda o PVC ser vinculado ('Bound'). Agora isso deve funcionar, pois o Pod do Deployment o solicitou.
echo "   Aguardando o PVC 'video-downloader-pvc' ser vinculado (Bound)..."
kubectl wait --for=condition=Bound pvc/video-downloader-pvc -n $NAMESPACE --timeout=180s
if [ $? -ne 0 ]; then
  echo "❌ Erro: O PVC não foi vinculado a tempo. Verifique os eventos do PVC com 'kubectl describe pvc ...'."
  exit 1
fi
echo "   ✅ PVC vinculado com sucesso!"

# 6. Aguarda o Deployment ficar totalmente disponível (pods rodando e prontos).
echo "   Aguardando o Deployment ficar disponível..."
kubectl wait --for=condition=available deployment/video-downloader-deployment -n $NAMESPACE --timeout=300s
echo "   ✅ Deployment disponível!"

echo ""
echo "✅ Deploy concluído com sucesso!"
echo "--------------------------------------------------"

# --- Informações de Acesso ---
echo "🔍 Buscando informações de acesso..."

# Pega o IP de um dos nós do cluster.
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

# Pega a porta NodePort alocada pelo serviço.
NODE_PORT=$(kubectl get svc video-downloader-service -n $NAMESPACE -o jsonpath='{.spec.ports[0].nodePort}')

echo "🎉 Aplicação acessível em:"
echo "   http://$NODE_IP:$NODE_PORT"
echo "--------------------------------------------------"

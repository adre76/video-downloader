#!/bin/bash

# Este script cria a estrutura de diretórios e todos os arquivos para o projeto video-downloader.

# --- Cria a estrutura de pastas ---
echo "🚀 Criando a estrutura de pastas do projeto..."
mkdir -p app/templates
mkdir -p kubernetes


# --- Cria os arquivos da aplicação ---

echo "📄 Criando app/requirements.txt..."
cat > app/requirements.txt << 'EOF'
Flask==2.2.2
gunicorn==20.1.0
yt-dlp==2023.07.06
EOF

echo "📄 Criando app/templates/index.html..."
cat > app/templates/index.html << 'EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Video Downloader</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; color: #333; margin: 2em; }
        .container { max-width: 800px; margin: auto; background: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #5c67f2; }
        input[type="url"], textarea { width: 95%; padding: 10px; margin-bottom: 10px; border: 1px solid #ddd; border-radius: 4px; }
        textarea { height: 100px; }
        button { background-color: #5c67f2; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #4a54c4; }
        .loader { display: none; margin: 1em 0; }
        .error { color: red; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Insira o Link do Vídeo</h1>
        <form action="/fetch" method="post" id="urlForm">
            <input type="url" id="url" name="url" placeholder="https://www.youtube.com/watch?v=..." required>
            <br>
            <label for="cookies">Credenciais (Cookies - Opcional)</label><br>
            <textarea id="cookies" name="cookies" placeholder="Cole o conteúdo do seu arquivo de cookies aqui (necessário para posts privados)"></textarea>
            <br>
            <button type="submit">Buscar Opções de Download</button>
        </form>
        <div class="loader" id="loader">Buscando informações, por favor aguarde...</div>
        <div class="error" id="error-message"></div>
    </div>

    <script>
        document.getElementById('urlForm').addEventListener('submit', function() {
            document.getElementById('loader').style.display = 'block';
            document.getElementById('error-message').innerText = '';
        });
    </script>
</body>
</html>
EOF

echo "📄 Criando app/templates/download_options.html..."
cat > app/templates/download_options.html << 'EOF'
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Opções de Download</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f4f9; color: #333; margin: 2em; }
        .container { max-width: 800px; margin: auto; background: #fff; padding: 2em; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #5c67f2; }
        table { width: 100%; border-collapse: collapse; margin-top: 1em; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f2f2f2; }
        button { background-color: #28a745; color: white; padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background-color: #218838; }
        a { color: #007bff; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Escolha o Formato</h1>
        <p><strong>Vídeo:</strong> {{ title }}</p>
        <p><strong>Plataforma:</strong> {{ platform }}</p>
        <hr>
        <table>
            <thead>
                <tr>
                    <th>Resolução</th>
                    <th>Extensão</th>
                    <th>FPS</th>
                    <th>Codecs (Vídeo/Áudio)</th>
                    <th>Ação</th>
                </tr>
            </thead>
            <tbody>
                {% for format in formats %}
                <tr>
                    <td>{{ format.resolution if format.resolution else 'Áudio Apenas' }}</td>
                    <td>{{ format.ext }}</td>
                    <td>{{ format.fps if format.fps else 'N/A' }}</td>
                    <td>{{ format.vcodec if format.vcodec != 'none' else '' }} / {{ format.acodec if format.acodec != 'none' else '' }}</td>
                    <td>
                        <form action="/download" method="post">
                            <input type="hidden" name="url" value="{{ url }}">
                            <input type="hidden" name="format_id" value="{{ format.format_id }}">
                            <input type="hidden" name="cookies" value="{{ cookies_data }}">
                            <input type="hidden" name="filename" value="{{ filename }}.{{format.ext}}">
                            <button type="submit">Download</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        <br>
        <a href="/">Voltar</a>
    </div>
</body>
</html>
EOF

echo "📄 Criando app/app.py..."
cat > app/app.py << 'EOF'
import os
import json
import uuid
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
import yt_dlp

# --- Configuração ---
# O diretório onde os vídeos serão salvos temporariamente.
# No Kubernetes, este caminho será montado a partir de um Persistent Volume.
DOWNLOAD_FOLDER = '/app/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Cria a instância da aplicação Flask
app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
# Chave secreta para mensagens flash (não crítico para esta app, mas é uma boa prática)
app.secret_key = os.urandom(24)

# --- Funções Auxiliares ---

def get_video_info(url, cookies_data=None):
    """
    Usa yt-dlp para extrair informações e formatos de um vídeo.
    Retorna um dicionário com os dados ou None em caso de erro.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    # Se credenciais (cookies) forem fornecidas, salva em um arquivo temporário
    # e informa ao yt-dlp para usá-lo.
    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w') as f:
            f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"Erro ao buscar informações: {e}")
        return None
    finally:
        # Garante a remoção do arquivo de cookie temporário
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)


def sanitize_filename(title):
    """
    Remove caracteres inválidos de um título para criar um nome de arquivo seguro.
    """
    # Remove caracteres que são problemáticos em sistemas de arquivos
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    # Substitui espaços por underscores e limita o tamanho
    return sanitized.replace(' ', '_')[:100]


# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """ Rota principal, exibe o formulário para inserir a URL. """
    return render_template('index.html')


@app.route('/fetch', methods=['POST'])
def fetch_formats():
    """
    Recebe a URL do formulário, busca as opções de download e exibe na página
    de opções.
    """
    video_url = request.form.get('url')
    cookies_data = request.form.get('cookies')

    if not video_url:
        flash("URL é obrigatória!", "error")
        return redirect(url_for('index'))

    # Busca informações do vídeo
    info = get_video_info(video_url, cookies_data)

    if not info:
        # Exibe uma mensagem de erro na página inicial
        return render_template('index.html', error="Não foi possível obter informações do vídeo. Verifique a URL ou as credenciais.")

    # Filtra e organiza os formatos para exibição
    formats = []
    for f in info.get('formats', []):
        # Apenas formatos com URL de download e codecs válidos
        if f.get('url') and f.get('vcodec') != 'none' or f.get('acodec') != 'none':
            formats.append({
                'format_id': f.get('format_id'),
                'ext': f.get('ext'),
                'resolution': f.get('resolution'),
                'fps': f.get('fps'),
                'vcodec': f.get('vcodec'),
                'acodec': f.get('acodec')
            })

    # Cria um nome de arquivo seguro a partir do título do vídeo
    filename = sanitize_filename(info.get('title', 'video'))

    return render_template(
        'download_options.html',
        title=info.get('title'),
        platform=info.get('extractor_key'),
        formats=formats,
        url=video_url,
        cookies_data=cookies_data,
        filename=filename
    )


@app.route('/download', methods=['POST'])
def download_video():
    """
    Recebe o formato escolhido, faz o download para o volume persistente
    e depois envia o arquivo para o navegador do usuário.
    """
    video_url = request.form.get('url')
    format_id = request.form.get('format_id')
    cookies_data = request.form.get('cookies')
    filename = request.form.get('filename', f'video_{uuid.uuid4()}.mp4')

    # Gera um caminho completo e único para o arquivo
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)

    ydl_opts = {
        'format': format_id,
        'outtmpl': output_path, # Define o caminho/nome do arquivo de saída
        'quiet': True,
        'no_warnings': True
    }

    # Usa o arquivo de cookies se as credenciais foram fornecidas
    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w') as f:
            f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file

    try:
        # Executa o download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Envia o arquivo para o usuário e o remove do servidor em seguida
        return send_from_directory(
            app.config['DOWNLOAD_FOLDER'],
            filename,
            as_attachment=True # Força o navegador a baixar em vez de exibir
        )
    except Exception as e:
        print(f"Erro no download: {e}")
        return "Ocorreu um erro durante o download.", 500
    finally:
        # Garante a remoção do arquivo de vídeo e do cookie após o envio
        if os.path.exists(output_path):
            os.remove(output_path)
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)


if __name__ == '__main__':
    # Para testes locais, não use em produção
    app.run(debug=True, host='0.0.0.0', port=5000)
EOF

# --- Cria os arquivos de deploy ---

echo "📄 Criando Dockerfile..."
cat > Dockerfile << 'EOF'
# Estágio 1: Base com Python
# Usamos uma imagem slim para manter o tamanho final menor.
FROM python:3.9-slim

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker.
COPY app/requirements.txt .

# Instala as dependências Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação para o diretório de trabalho.
COPY app/ .

# Cria o diretório de downloads que será usado pelo volume do Kubernetes.
# O RUN chown garante que o usuário que roda o gunicorn tenha permissão de escrita.
# O Gunicorn roda por padrão com o usuário 'nobody' (uid 65534)
RUN mkdir -p /app/downloads && chown -R 65534:65534 /app/downloads

# Expõe a porta que o Gunicorn irá escutar.
EXPOSE 8000

# Define o comando para iniciar a aplicação quando o contêiner for executado.
# --bind 0.0.0.0:8000: Faz o Gunicorn escutar em todas as interfaces de rede na porta 8000.
# --workers 3: Um bom ponto de partida para o número de processos.
# app:app: Informa ao Gunicorn para carregar o objeto 'app' do arquivo 'app.py'.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]
EOF

echo "📄 Criando kubernetes/01-namespace.yaml..."
cat > kubernetes/01-namespace.yaml << 'EOF'
apiVersion: v1
kind: Namespace
metadata:
  name: video-downloader
EOF

echo "📄 Criando kubernetes/02-pvc.yaml..."
cat > kubernetes/02-pvc.yaml << 'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: video-downloader-pvc
  namespace: video-downloader
spec:
  # Usa o storage class que você especificou.
  storageClassName: local-path
  accessModes:
    # ReadWriteOnce significa que o volume pode ser montado como leitura/escrita por um único nó.
    - ReadWriteOnce
  resources:
    requests:
      # Solicita 5GiB de espaço. Ajuste conforme sua necessidade.
      storage: 5Gi
EOF

echo "📄 Criando kubernetes/03-deployment.yaml..."
cat > kubernetes/03-deployment.yaml << 'EOF'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: video-downloader-deployment
  namespace: video-downloader
spec:
  replicas: 1
  selector:
    matchLabels:
      app: video-downloader
  template:
    metadata:
      labels:
        app: video-downloader
    spec:
      containers:
      - name: downloader-app
        # A imagem que você enviou para o Docker Hub.
        image: andrepereira21/downloader:latest
        imagePullPolicy: Always # Sempre busca a imagem mais recente
        ports:
        - containerPort: 8000
        volumeMounts:
        - name: download-storage
          # Monta o volume no diretório que a aplicação Flask espera.
          mountPath: /app/downloads
        resources:
          requests:
            cpu: "100m" # 0.1 CPU
            memory: "128Mi" # 128 Mebibytes
          limits:
            cpu: "500m" # 0.5 CPU
            memory: "512Mi"
      volumes:
      - name: download-storage
        # Vincula este volume à PVC que criamos anteriormente.
        persistentVolumeClaim:
          claimName: video-downloader-pvc
EOF

echo "📄 Criando kubernetes/04-service.yaml..."
cat > kubernetes/04-service.yaml << 'EOF'
apiVersion: v1
kind: Service
metadata:
  name: video-downloader-service
  namespace: video-downloader
spec:
  # NodePort expõe o serviço em uma porta estática em cada nó do cluster.
  type: NodePort
  selector:
    # Seleciona os pods gerenciados pelo nosso deployment.
    app: video-downloader
  ports:
  - protocol: TCP
    # A porta dentro do cluster.
    port: 80
    # A porta que o nosso contêiner está escutando.
    targetPort: 8000
    # O Kubernetes alocará uma porta aleatória entre 30000-32767.
    # Você pode especificar uma aqui se quiser, mas é melhor deixar em branco.
    # nodePort: 30007
EOF

echo "📄 Criando deploy.sh..."
cat > deploy.sh << 'EOF'
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
EOF

# --- Finalização ---

echo "🔧 Tornando deploy.sh executável..."
chmod +x deploy.sh

echo "✅ Projeto 'video-downloader' criado com sucesso!"
echo "Agora você pode navegar para a pasta 'video-downloader' e seguir os próximos passos (build, push, deploy)."

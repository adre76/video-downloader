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

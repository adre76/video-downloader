import os
import uuid
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for
import yt_dlp

# --- Configuração ---
# O diretório onde os vídeos serão salvos temporariamente.
DOWNLOAD_FOLDER = '/app/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Cria a instância da aplicação Flask. Esta linha estava faltando.
app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
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
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)

def sanitize_filename(title):
    """
    Remove caracteres inválidos de um título para criar um nome de arquivo seguro.
    """
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
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

    info = get_video_info(video_url, cookies_data)

    if not info:
        return render_template('index.html', error="Não foi possível obter informações do vídeo. Verifique a URL ou as credenciais.")

    formats = []
    for f in info.get('formats', []):
        if f.get('url') and (f.get('vcodec') != 'none' or f.get('acodec') != 'none'):
            formats.append({
                'format_id': f.get('format_id'),
                'ext': f.get('ext'),
                'resolution': f.get('resolution'),
            })

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
    Recebe o formato escolhido, faz o download (e conversão, se necessário)
    e envia o arquivo para o navegador do usuário.
    """
    video_url = request.form.get('url')
    format_id = request.form.get('format_id')
    cookies_data = request.form.get('cookies')
    filename = request.form.get('filename', f'video_{uuid.uuid4()}')

    filename_base, _ = os.path.splitext(filename)
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_base)

    ydl_opts = {}
    if format_id == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path + '.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        final_filename = filename_base + '.mp3'
    else:
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path + '.%(ext)s',
        }
        final_filename = filename

    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w') as f:
            f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        downloaded_file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename)

        return send_from_directory(
            app.config['DOWNLOAD_FOLDER'],
            final_filename,
            as_attachment=True
        )
    except Exception as e:
        print(f"Erro no download: {e}")
        return "Ocorreu um erro durante o download.", 500
    finally:
        if 'final_filename' in locals() and os.path.exists(os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename)):
             os.remove(os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename))
        # Limpeza do arquivo original se a conversão para mp3 aconteceu (ex: .m4a)
        temp_files = [f for f in os.listdir(app.config['DOWNLOAD_FOLDER']) if f.startswith(filename_base)]
        for temp_file in temp_files:
            if temp_file != final_filename:
                os.remove(os.path.join(app.config['DOWNLOAD_FOLDER'], temp_file))
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
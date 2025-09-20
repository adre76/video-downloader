import os
import uuid
import json
import yt_dlp
from flask import Flask, request, render_template, send_from_directory, jsonify

# --- Configuração ---
DOWNLOAD_FOLDER = '/app/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.secret_key = os.urandom(24)

def get_video_info(url, cookies_data=None):
    """Usa yt-dlp para extrair informações e formatos de um vídeo."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }

    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info
    except Exception as e:
        print(f"Erro ao buscar informações: {e}")
        return {'error': str(e)}
    finally:
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)

def sanitize_filename(title):
    """Cria um nome de arquivo seguro a partir de um título."""
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    return sanitized.replace(' ', '_')[:100]


# --- Rotas da Aplicação ---

@app.route('/')
def index():
    """Rota principal que exibe a interface."""
    return render_template('index.html')

@app.route('/fetch', methods=['POST'])
def fetch_formats():
    """
    Recebe uma URL via AJAX, busca os formatos de vídeo/áudio
    e retorna uma lista em formato JSON.
    """
    video_url = request.form.get('url')
    cookies_data = request.form.get('cookies')

    if not video_url:
        return jsonify({'error': 'URL é obrigatória!'}), 400

    info = get_video_info(video_url, cookies_data)

    if info.get('error'):
        error_message = info['error']
        if 'ERROR:' in error_message:
            error_message = error_message.split('ERROR:')[1].strip()
        return jsonify({'error': error_message}), 500

    formats = []
    for f in info.get('formats', []):
        if f.get('url') and (f.get('vcodec') != 'none' or f.get('acodec') != 'none'):
            format_note = f.get('format_note', f.get('resolution', 'Áudio'))
            if f.get('vcodec') == 'none':
                format_note = f"Áudio Apenas ({f.get('acodec')})"

            formats.append({
                'format_id': f.get('format_id'),
                'ext': f.get('ext'),
                'note': format_note,
            })

    filename = sanitize_filename(info.get('title', 'video'))
    
    response_data = {
        'title': info.get('title'),
        'platform': info.get('extractor_key'),
        'formats': formats,
        'url': video_url,
        'cookies_data': cookies_data,
        'filename': filename
    }
    return jsonify(response_data)

@app.route('/download', methods=['POST'])
def download_video():
    video_url = request.form.get('url')
    format_id = request.form.get('format_id')
    cookies_data = request.form.get('cookies')
    filename = request.form.get('filename', f'video_{uuid.uuid4()}')

    filename_base, _ = os.path.splitext(filename)
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_base)

    ydl_opts = {}
    cookie_file = None # Definir antes do try para estar disponível no finally

    try:
        if format_id == 'mp3':
            final_filename = filename_base + '.mp3'
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path, # yt-dlp adicionará a extensão correta
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            }
        else:
            # --- MUDANÇAS PRINCIPAIS AQUI ---
            # Força a saída para .mp4, que é um formato universal
            final_filename = filename_base + '.mp4' 
            ydl_opts = {
                # Pede o formato de vídeo escolhido + o melhor áudio disponível.
                # Se não puder juntar, pega o melhor formato completo.
                'format': f'{format_id}+bestaudio/best',
                'outtmpl': output_path,
                # Garante que, se os arquivos forem juntados, o resultado será um .mp4
                'merge_output_format': 'mp4',
            }

        if cookies_data:
            cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write(cookies_data)
            ydl_opts['cookiefile'] = cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # O nome do arquivo agora é previsível
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], final_filename, as_attachment=True)
    
    except Exception as e:
        print(f"Erro no download: {e}")
        return "Ocorreu um erro durante o download.", 500
    
    finally:
        # Lógica de limpeza aprimorada para remover todos os arquivos temporários
        temp_files = [f for f in os.listdir(app.config['DOWNLOAD_FOLDER']) if f.startswith(filename_base)]
        for temp_file in temp_files:
            try:
                os.remove(os.path.join(app.config['DOWNLOAD_FOLDER'], temp_file))
            except OSError as e:
                print(f"Erro ao deletar arquivo temporário {temp_file}: {e}")
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
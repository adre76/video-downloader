import os
import uuid
import json
import yt_dlp
import traceback # Importamos a biblioteca de traceback
from flask import Flask, request, render_template, send_from_directory, jsonify

# --- Configuração ---
DOWNLOAD_FOLDER = '/app/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.secret_key = os.urandom(24)

def get_video_info(url, cookies_data=None):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w', encoding='utf-8') as f: f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        print(f"Erro ao buscar informações: {e}")
        return {'error': str(e)}
    finally:
        if cookie_file and os.path.exists(cookie_file): os.remove(cookie_file)

def sanitize_filename(title):
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    return sanitized.replace(' ', '_')[:100]

# --- Rotas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch', methods=['POST'])
def fetch_formats():
    video_url = request.form.get('url')
    cookies_data = request.form.get('cookies')
    if not video_url: return jsonify({'error': 'URL é obrigatória!'}), 400

    info = get_video_info(video_url, cookies_data)
    if info.get('error'):
        error_message = info['error']
        if 'ERROR:' in error_message: error_message = error_message.split('ERROR:')[1].strip()
        return jsonify({'error': error_message}), 500

    formats = []
    for f in info.get('formats', []):
        if f.get('url') and (f.get('vcodec') != 'none' or f.get('acodec') != 'none'):
            format_note = f.get('format_note', f.get('resolution', 'Áudio'))
            if f.get('vcodec') == 'none': format_note = f"Áudio Apenas ({f.get('acodec')})"
            formats.append({'format_id': f.get('format_id'), 'ext': f.get('ext'), 'note': format_note})

    filename = sanitize_filename(info.get('title', 'video'))
    return jsonify({
        'title': info.get('title'), 'platform': info.get('extractor_key'), 'formats': formats,
        'url': video_url, 'cookies_data': cookies_data, 'filename': filename
    })

@app.route('/download', methods=['POST'])
def download_video():
    video_url = request.form.get('url')
    format_id = request.form.get('format_id')
    cookies_data = request.form.get('cookies')
    filename = request.form.get('filename', f'video_{uuid.uuid4()}')

    filename_base, _ = os.path.splitext(filename)
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_base)

    ydl_opts = {}
    cookie_file = None
    final_filepath = None

    try:
        if format_id == 'mp3':
            ydl_opts = {
                'format': 'bestaudio/best', 'outtmpl': output_path,
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            }
        else:
            ydl_opts = {
                'format': f'{format_id}+bestaudio/best', 'outtmpl': output_path, 'merge_output_format': 'mp4',
            }

        if cookies_data:
            cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
            with open(cookie_file, 'w', encoding='utf-8') as f: f.write(cookies_data)
            ydl_opts['cookiefile'] = cookie_file

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            # A chave correta para o caminho do arquivo após o download é 'requested_downloads'
            # que é uma lista. Pegamos o primeiro item.
            downloaded_file = info.get('requested_downloads')[0]
            final_filepath = downloaded_file.get('filepath')

        if final_filepath and os.path.exists(final_filepath):
            final_filename = os.path.basename(final_filepath)
            return send_from_directory(app.config['DOWNLOAD_FOLDER'], final_filename, as_attachment=True)
        else:
            raise FileNotFoundError("O arquivo final não foi encontrado após o download pelo yt-dlp.")

    except Exception as e:
        # --- LOG DETALHADO ADICIONADO AQUI ---
        tb_str = traceback.format_exc()
        print(f"--- ERRO DETALHADO NO DOWNLOAD ---")
        print(f"Exceção: {e}")
        print(f"Traceback:\n{tb_str}")
        print(f"------------------------------------")
        return "Ocorreu um erro durante o download.", 500
    finally:
        if final_filepath and os.path.exists(final_filepath):
            os.remove(final_filepath)
        
        temp_files = [f for f in os.listdir(app.config['DOWNLOAD_FOLDER']) if f.startswith(filename_base)]
        for temp_file in temp_files:
            try:
                os.remove(os.path.join(app.config['DOWNLOAD_FOLDER'], temp_file))
            except OSError: pass 
        
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
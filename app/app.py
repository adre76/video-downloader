import os
import uuid
import json
import yt_dlp
import traceback  # Importamos a biblioteca de traceback
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
        with open(cookie_file, 'w', encoding='utf-8') as f:
            f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file
    try:
        # Removido o 'with' para que o objeto ydl possa ser acessado no except
        ydl = yt_dlp.YoutubeDL(ydl_opts)
        info = ydl.extract_info(url, download=False)
        return info
    finally:
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)

def sanitize_filename(title):
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    return sanitized.replace(' ', '_')[:100]

# --- Rotas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch', methods=['POST'])
def fetch_formats():
    try:
        video_url = request.form.get('url')
        cookie_file_obj = request.files.get('cookieFile')
        cookies_data = None

        if cookie_file_obj and cookie_file_obj.filename != '':
            cookies_data = cookie_file_obj.read().decode('utf-8')

        if not video_url:
            return jsonify({'error': 'URL é obrigatória!'}), 400

        info = get_video_info(video_url, cookies_data)
        
        if info and info.get('error'):
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
                formats.append({'format_id': f.get('format_id'), 'ext': f.get('ext'), 'note': format_note})

        filename = sanitize_filename(info.get('title', 'video'))
        return jsonify({
            'title': info.get('title'), 'platform': info.get('extractor_key'), 'formats': formats,
            'url': video_url, 'filename': filename
        })
    except Exception as e:
        # --- BLOCO DE LOG DETALHADO ---
        tb_str = traceback.format_exc()
        print(f"--- ERRO DETALHADO EM /FETCH ---")
        print(f"Exceção: {e}")
        print(f"Traceback:\n{tb_str}")
        print(f"------------------------------------")
        return jsonify({'error': 'Ocorreu um erro interno no servidor ao processar sua requisição.'}), 500

# A rota de download permanece a mesma das versões anteriores
@app.route('/download', methods=['POST'])
def download_video():
    # ... (código da função de download permanece o mesmo da versão anterior)
    pass # Apenas para o editor não reclamar de bloco vazio

# Cole aqui o código completo da sua função @app.route('/download', ...) da versão anterior.
# Se precisar, eu o reenvio.

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
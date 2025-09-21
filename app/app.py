import os
import uuid
import json
import yt_dlp
import traceback
import threading
import time
from flask import Flask, request, render_template, send_from_directory, jsonify, Response, stream_with_context

# --- Configuração ---
DOWNLOAD_FOLDER = '/app/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.secret_key = os.urandom(24)

# Dicionário em memória para armazenar o estado das tarefas de download
# Em um ambiente de produção real, seria melhor usar um sistema como Redis.
DOWNLOAD_TASKS = {}

def sanitize_filename(title):
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    return sanitized.replace(' ', '_')[:100]

# --- Rota para buscar formatos (sem alterações) ---
@app.route('/fetch', methods=['POST'])
def fetch_formats():
    video_url = request.form.get('url')
    cookie_file_obj = request.files.get('cookieFile')
    cookies_data = None
    if cookie_file_obj:
        cookies_data = cookie_file_obj.read().decode('utf-8')

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
        'url': video_url, 'filename': filename
    })

# --- Lógica de Download em Background ---

def download_worker(task_id, ydl_opts, video_url):
    """Função que executa o download em uma thread separada."""
    
    def log_hook(d):
        """Hook do yt-dlp para capturar o progresso."""
        if d['status'] == 'downloading':
            # Formata a linha de log de progresso
            log_line = f"    baixando: {d['_percent_str']} de {d['_total_bytes_str']} a {d['_speed_str']}"
            DOWNLOAD_TASKS[task_id]['log'].append(log_line)
        elif d['status'] == 'finished':
            log_line = f"Download concluído, processando..."
            DOWNLOAD_TASKS[task_id]['log'].append(log_line)

    ydl_opts['progress_hooks'] = [log_hook]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_file = info.get('requested_downloads')[0]
            final_filepath = downloaded_file.get('filepath')
            
            if final_filepath and os.path.exists(final_filepath):
                final_filename = os.path.basename(final_filepath)
                DOWNLOAD_TASKS[task_id]['status'] = 'complete'
                DOWNLOAD_TASKS[task_id]['result'] = final_filename
            else:
                raise FileNotFoundError("Arquivo final não encontrado.")

    except Exception as e:
        tb_str = traceback.format_exc()
        error_log = f"ERRO: Falha no processo de download.\n{e}\n{tb_str}"
        DOWNLOAD_TASKS[task_id]['log'].append(error_log)
        DOWNLOAD_TASKS[task_id]['status'] = 'error'

@app.route('/start-download', methods=['POST'])
def start_download():
    """Inicia o processo de download em background e retorna um ID de tarefa."""
    task_id = str(uuid.uuid4())
    
    video_url = request.form.get('url')
    format_id = request.form.get('format_id')
    filename = request.form.get('filename')
    cookie_file_obj = request.files.get('cookieFile')
    
    filename_base, _ = os.path.splitext(filename)
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_base)
    
    ydl_opts = {}
    if format_id == 'mp3':
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': output_path,
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]}
    else:
        ydl_opts = {'format': f'{format_id}+bestaudio/best', 'outtmpl': output_path, 'merge_output_format': 'mp4'}

    if cookie_file_obj:
        cookies_data = cookie_file_obj.read().decode('utf-8')
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{task_id}.txt')
        with open(cookie_file, 'w', encoding='utf-8') as f: f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file

    DOWNLOAD_TASKS[task_id] = {'status': 'running', 'log': ['Configurando o download...'], 'result': None}
    
    # Inicia a thread
    thread = threading.Thread(target=download_worker, args=(task_id, ydl_opts, video_url))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/download-stream/<task_id>')
def download_stream(task_id):
    """Transmite o log de uma tarefa de download para o cliente."""
    def generate():
        last_index = 0
        while True:
            if task_id not in DOWNLOAD_TASKS:
                yield "data: ERRO: Tarefa não encontrada.\n\n"
                break
            
            task = DOWNLOAD_TASKS[task_id]
            
            # Envia novas linhas de log
            if len(task['log']) > last_index:
                for i in range(last_index, len(task['log'])):
                    yield f"data: {task['log'][i]}\n\n"
                last_index = len(task['log'])
            
            # Verifica se a tarefa terminou
            if task['status'] == 'complete':
                yield f"data: DOWNLOAD_URL:/get-file/{task_id}/{task['result']}\n\n"
                break
            elif task['status'] == 'error':
                yield f"data: ERRO: O download falhou. Verifique o log.\n\n"
                break
            
            time.sleep(0.5)

    return Response(stream_with_context(generate()), content_type='text/event-stream')

@app.route('/get-file/<task_id>/<filename>')
def get_file(task_id, filename):
    """Envia o arquivo finalizado para o usuário e limpa os dados."""
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    
    @after_this_request
    def cleanup(response):
        # Limpa o arquivo e os dados da tarefa após a requisição ser completada
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            
            cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{task_id}.txt')
            if os.path.exists(cookie_file):
                os.remove(cookie_file)
            
            if task_id in DOWNLOAD_TASKS:
                del DOWNLOAD_TASKS[task_id]
        except Exception as e:
            print(f"Erro na limpeza da tarefa {task_id}: {e}")
        return response

    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)
    
# --- Funções auxiliares e rota de índice ---
@app.route('/')
def index():
    return render_template('index.html')
    
# Esta função auxiliar é necessária para a limpeza pós-download
from flask import after_this_request
# As funções get_video_info e sanitize_filename já estão no topo

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
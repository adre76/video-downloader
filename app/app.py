import os
import uuid
import json
import yt_dlp
import traceback
import threading
import time
from flask import Flask, request, render_template, send_from_directory, jsonify, Response, stream_with_context, after_this_request

# --- Configuração ---
DOWNLOAD_FOLDER = '/app/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

app = Flask(__name__)
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
app.secret_key = os.urandom(24)

def sanitize_filename(title):
    sanitized = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
    return sanitized.replace(' ', '_')[:100]

def get_video_info(url, cookies_data=None):
    ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'cachedir': False}
    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w', encoding='utf-8') as f: f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        return {'error': str(e)}
    finally:
        if cookie_file and os.path.exists(cookie_file): os.remove(cookie_file)

# --- Rotas da Aplicação ---
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

        if not video_url: return jsonify({'error': 'URL é obrigatória!'}), 400

        info = get_video_info(video_url, cookies_data)
        if info.get('error'):
            error_message = info['error']
            if 'ERROR:' in error_message: error_message = error_message.split('ERROR:')[1].strip()
            return jsonify({'error': error_message}), 500

        formats = []
        unique_formats = set()
        for f in info.get('formats', []):
            if f.get('url') and (f.get('vcodec') != 'none' or f.get('acodec') != 'none'):
                format_note = f.get('format_note', f.get('resolution', 'Áudio'))
                if f.get('vcodec') == 'none':
                    format_note = f"Áudio Apenas ({f.get('acodec')})"
                
                unique_key = f"{format_note}-{f.get('ext')}"
                if unique_key in unique_formats: continue
                
                unique_formats.add(unique_key)
                formats.append({'format_id': f.get('format_id'), 'ext': f.get('ext'), 'note': format_note})

        filename = sanitize_filename(info.get('title', 'video'))
        return jsonify({
            'title': info.get('title'), 'platform': info.get('extractor_key'), 'formats': formats,
            'url': video_url, 'filename': filename
        })
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"--- ERRO DETALHADO EM /FETCH ---\n{tb_str}------------------------------------")
        return jsonify({'error': 'Ocorreu um erro interno no servidor.'}), 500

def download_worker(task_id, ydl_opts, video_url):
    status_file = os.path.join(DOWNLOAD_FOLDER, f"{task_id}.json")

    def update_status_file(new_log_line=None, status=None, result=None):
        # Esta função agora lê, atualiza e escreve o arquivo de status de forma segura
        try:
            with open(status_file, 'r+') as f:
                data = json.load(f)
                if new_log_line: data['log'].append(new_log_line)
                if status: data['status'] = status
                if result: data['result'] = result
                f.seek(0)
                json.dump(data, f)
                f.truncate()
        except (IOError, json.JSONDecodeError) as e:
            print(f"Erro ao atualizar o arquivo de status para a tarefa {task_id}: {e}")

    def log_hook(d):
        if d['status'] == 'downloading':
            log_line = f"    Baixando: {d['_percent_str']} de {d['_total_bytes_str']} a {d['_speed_str']}"
            update_status_file(new_log_line=log_line)
        elif d['status'] == 'finished':
            if 'total_bytes' in d:
                update_status_file(new_log_line="Download da parte concluído, processando...")
        elif d['status'] == 'processing' and 'Merger' in d.get('postprocessor'):
             update_status_file(new_log_line="Juntando vídeo e áudio com ffmpeg...")
        elif d['status'] == 'error':
             update_status_file(new_log_line=f"ERRO: {d.get('msg', 'Falha no download')}")

    ydl_opts['progress_hooks'] = [log_hook]
    ydl_opts['quiet'] = False
    ydl_opts['cachedir'] = False

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            downloaded_file = info.get('requested_downloads')[0]
            final_filepath = downloaded_file.get('filepath')
            
            if final_filepath and os.path.exists(final_filepath):
                final_filename = os.path.basename(final_filepath)
                update_status_file(status='complete', result=final_filename)
            else:
                raise FileNotFoundError("Arquivo final não encontrado.")
    except Exception as e:
        tb_str = traceback.format_exc()
        error_log = f"ERRO: Falha no processo de download.\n{tb_str}"
        update_status_file(new_log_line=error_log, status='error')

@app.route('/start-download', methods=['POST'])
def start_download():
    task_id = str(uuid.uuid4())
    status_file = os.path.join(DOWNLOAD_FOLDER, f"{task_id}.json")

    initial_status = {'status': 'running', 'log': ['Iniciando download...'], 'result': None}
    with open(status_file, 'w') as f: json.dump(initial_status, f)

    video_url = request.form.get('url')
    format_id = request.form.get('format_id')
    filename = request.form.get('filename')
    cookie_file_obj = request.files.get('cookieFile')
    
    filename_base, _ = os.path.splitext(filename)
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_base)
    
    ydl_opts = {}
    if format_id == 'mp3':
        ydl_opts = {'format': 'bestaudio/best', 'outtmpl': output_path + '.%(ext)s',
                    'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]}
    else:
        ydl_opts = {'format': f'{format_id}+bestaudio/best', 'outtmpl': output_path + '.%(ext)s',
                    'merge_output_format': 'mp4'}

    if cookie_file_obj and cookie_file_obj.filename != '':
        cookies_data = cookie_file_obj.read().decode('utf-8')
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{task_id}.txt')
        with open(cookie_file, 'w', encoding='utf-8') as f: f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file
    
    thread = threading.Thread(target=download_worker, args=(task_id, ydl_opts, video_url))
    thread.daemon = True
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/download-stream/<task_id>')
def download_stream(task_id):
    def generate():
        status_file = os.path.join(DOWNLOAD_FOLDER, f"{task_id}.json")
        retries = 5
        while not os.path.exists(status_file) and retries > 0:
            time.sleep(0.2)
            retries -= 1

        if not os.path.exists(status_file):
            yield "data: ERRO: Tarefa não encontrada ou expirou.\n\n"
            return

        last_index = 0
        while True:
            try:
                with open(status_file, 'r') as f:
                    task = json.load(f)
            except (IOError, json.JSONDecodeError):
                time.sleep(0.5)
                continue

            if len(task['log']) > last_index:
                for i in range(last_index, len(task['log'])):
                    yield f"data: {task['log'][i]}\n\n"
                last_index = len(task['log'])
            
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
    file_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
    
    @after_this_request
    def cleanup(response):
        try:
            if os.path.exists(file_path): os.remove(file_path)
            
            cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{task_id}.txt')
            if os.path.exists(cookie_file): os.remove(cookie_file)

            status_file = os.path.join(DOWNLOAD_FOLDER, f"{task_id}.json")
            if os.path.exists(status_file): os.remove(status_file)

        except Exception as e:
            print(f"Erro na limpeza da tarefa {task_id}: {e}")
        return response
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
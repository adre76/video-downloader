import os
import uuid
import subprocess
import chardet
from flask import Flask, request, render_template, send_from_directory, flash, redirect, url_for, Response, stream_with_context

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

# --- Rotas da Aplicação ---

@app.route('/')
def index():
    return render_template('index.html')

def run_yt_dlp_and_stream(command):
    """Executa um comando yt-dlp como subprocesso e transmite a saída."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=False # Lidar com bytes para detectar a codificação
    )
    for line_bytes in iter(process.stdout.readline, b''):
        # Detecta a codificação da linha e a decodifica para string
        encoding = chardet.detect(line_bytes)['encoding'] or 'utf-8'
        line_str = line_bytes.decode(encoding, errors='replace').strip()
        
        # Envia a linha formatada como um Server-Sent Event
        yield f"data: {line_str}\n\n"
    
    process.stdout.close()
    return_code = process.wait()
    if return_code:
        yield f"data: ERRO: O processo terminou com o código {return_code}\n\n"
    yield "data: PROCESSO_CONCLUIDO\n\n"

@app.route('/stream-fetch', methods=['POST'])
def stream_fetch():
    """Rota que inicia o processo de busca de formatos e transmite o log."""
    video_url = request.form.get('url')
    if not video_url:
        return Response("URL é obrigatória!", status=400)
    
    # Comando para listar formatos em JSON
    command = ['yt-dlp', '--dump-json', video_url]
    
    # Retorna uma resposta de streaming
    return Response(stream_with_context(run_yt_dlp_and_stream(command)), content_type='text/event-stream')

# As rotas /fetch e /download anteriores podem ser removidas ou adaptadas
# para trabalhar com a nova interface de streaming, mas por enquanto,
# a nova rota /stream-fetch é o foco. As rotas antigas podem ser mantidas
# para referência ou removidas para simplificar. Por enquanto, vamos deixá-las
# mas a nova interface não as usará.

# ... (Mantenha as rotas /fetch e /download antigas aqui por enquanto) ...
# @app.route('/fetch', ... etc ...
# @app.route('/download', ... etc ...

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
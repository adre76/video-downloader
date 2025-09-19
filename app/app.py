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

    # Remove a extensão do nome do arquivo para o yt-dlp adicionar a correta.
    filename_base, _ = os.path.splitext(filename)
    output_path = os.path.join(app.config['DOWNLOAD_FOLDER'], filename_base)

    ydl_opts = {}
    # Se o formato for 'mp3', configura o yt-dlp para extrair e converter o áudio.
    if format_id == 'mp3':
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path + '.%(ext)s', # Permite que o yt-dlp use a extensão original antes de converter
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192', # Qualidade do MP3
            }],
        }
        # A extensão final será .mp3, então ajustamos o nome do arquivo para envio
        final_filename = filename_base + '.mp3'
    else:
        # Lógica original para baixar um formato específico de vídeo/áudio.
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path + '.%(ext)s',
        }
        # O nome final do arquivo terá a extensão original
        final_filename = filename

    # Usa o arquivo de cookies se as credenciais foram fornecidas
    cookie_file = None
    if cookies_data:
        cookie_file = os.path.join(app.config['DOWNLOAD_FOLDER'], f'cookies_{uuid.uuid4()}.txt')
        with open(cookie_file, 'w') as f:
            f.write(cookies_data)
        ydl_opts['cookiefile'] = cookie_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # O caminho completo do arquivo baixado (com a extensão correta)
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
        # Garante a remoção de todos os arquivos temporários
        if 'final_filename' in locals() and os.path.exists(os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename)):
             os.remove(os.path.join(app.config['DOWNLOAD_FOLDER'], final_filename))
        if cookie_file and os.path.exists(cookie_file):
            os.remove(cookie_file)
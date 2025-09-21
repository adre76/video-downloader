# Usa uma versão mais recente do Python, como 3.11
FROM python:3.11-slim

# Instala o ffmpeg, necessário para a conversão para mp3.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copia o arquivo de dependências.
COPY app/requirements.txt .

# Instala as dependências Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação.
COPY app/ .

# Cria o diretório de downloads com as permissões corretas.
RUN mkdir -p /app/downloads && chown -R www-data:www-data /app/downloads
# Gunicorn geralmente roda como o usuário 'www-data' em imagens oficiais.

# Expõe a porta que o Gunicorn irá escutar.
EXPOSE 8000

# Define o usuário para rodar a aplicação para maior segurança.
USER www-data

# Define o comando para iniciar a aplicação.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]
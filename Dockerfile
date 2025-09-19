# Estágio 1: Base com Python
FROM python:3.9-slim

# Instala o ffmpeg, necessário para a conversão para mp3.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker.
COPY app/requirements.txt .

# Instala as dependências Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação para o diretório de trabalho.
COPY app/ .

# Cria o diretório de downloads
RUN mkdir -p /app/downloads && chown -R 65534:65534 /app/downloads

# Expõe a porta que o Gunicorn irá escutar.
EXPOSE 8000

# Define o comando para iniciar a aplicação.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]

# Estágio 1: Base com Python
# Usamos uma imagem slim para manter o tamanho final menor.
FROM python:3.9-slim

# Define o diretório de trabalho dentro do contêiner.
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker.
COPY app/requirements.txt .

# Instala as dependências Python.
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código da aplicação para o diretório de trabalho.
COPY app/ .

# Cria o diretório de downloads que será usado pelo volume do Kubernetes.
# O RUN chown garante que o usuário que roda o gunicorn tenha permissão de escrita.
# O Gunicorn roda por padrão com o usuário 'nobody' (uid 65534)
RUN mkdir -p /app/downloads && chown -R 65534:65534 /app/downloads

# Expõe a porta que o Gunicorn irá escutar.
EXPOSE 8000

# Define o comando para iniciar a aplicação quando o contêiner for executado.
# --bind 0.0.0.0:8000: Faz o Gunicorn escutar em todas as interfaces de rede na porta 8000.
# --workers 3: Um bom ponto de partida para o número de processos.
# app:app: Informa ao Gunicorn para carregar o objeto 'app' do arquivo 'app.py'.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "app:app"]

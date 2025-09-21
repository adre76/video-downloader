# 🚀 Downloader Pro

Um downloader de vídeos para Instagram, YouTube e TikTok com uma interface web moderna, empacotado em Docker e pronto para deploy em um ambiente Kubernetes/Rancher.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-black?logo=flask&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-blue?logo=docker&logoColor=white)
![Kubernetes](https://img.shields.io/badge/Kubernetes-blue?logo=kubernetes&logoColor=white)
![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)

---

### 📺 Demonstração

> 🚧 **Nota:** Grave um GIF ou tire um screenshot da aplicação funcionando e substitua a URL abaixo para que a imagem apareça aqui. Ferramentas como [ScreenToGif](https://www.screentogif.com/) (Windows) ou Kap (Mac) são ótimas para isso.

![Downloader Pro Screenshot](URL_DA_SUA_IMAGEM_OU_GIF_AQUI)

---

### ✨ Funcionalidades

* **Suporte Multiplataforma**: Baixe vídeos do Instagram, YouTube, TikTok e centenas de outros sites suportados pela `yt-dlp`.
* **Detecção Automática**: A aplicação identifica a plataforma de origem a partir da URL.
* **Seleção de Formato**: Exibe uma lista de formatos de vídeo e áudio disponíveis para o usuário escolher.
* **Conversão para MP3**: Opção dedicada para baixar apenas o áudio e convertê-lo para o formato MP3.
* **Suporte a Conteúdo Privado**: Permite o upload de um arquivo de cookies para baixar vídeos privados ou que exigem login.
* **Log em Tempo Real**: Uma interface reativa que mostra o progresso do download em tempo real.
* **Pronto para a Nuvem**: Totalmente containerizado com Docker e orquestrado com Kubernetes, utilizando Ingress para exposição de serviço.

---

### 🛠️ Tecnologias Utilizadas

* **Backend**: Python 3.11 com [Flask](https://flask.palletsprojects.com/)
* **Servidor Web**: [Gunicorn](https://gunicorn.org/)
* **Motor de Download**: [yt-dlp](https://github.com/yt-dlp/yt-dlp)
* **Containerização**: [Docker](https://www.docker.com/)
* **Orquestração**: [Kubernetes](https://kubernetes.io/) (testado em ambiente RKE2/Rancher)
* **Armazenamento**: `local-path` StorageClass para Volumes Persistentes
* **Exposição de Serviço**: [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)

---

### 📂 Estrutura do Projeto
video-downloader/
├── app/
│   ├── app.py                 # Lógica principal da aplicação Flask
│   ├── templates/
│   │   └── index.html         # Frontend da aplicação
│   └── requirements.txt       # Dependências Python
├── kubernetes/
│   ├── 01-namespace.yaml
│   ├── 02-pvc.yaml
│   ├── 03-deployment.yaml
│   ├── 04-service.yaml
│   └── 05-ingress.yaml
├── Dockerfile                 # Define a imagem Docker da aplicação
├── build_and_push.sh          # Script para construir e publicar a imagem Docker
└── deploy.sh                  # Script para fazer o deploy no Kubernetes
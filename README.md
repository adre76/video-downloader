# Video Downloader

![Banner do Projeto](https://private-us-east-1.manuscdn.com/sessionFile/rPQNfNvHKK14DAA0WwFgXO/sandbox/dT0urwT9KQiez4WDHPd78C-images_1758486641930_na1fn_L2hvbWUvdWJ1bnR1L3ZpZGVvX2Rvd25sb2FkZXJfYmFubmVy.png?Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9wcml2YXRlLXVzLWVhc3QtMS5tYW51c2Nkbi5jb20vc2Vzc2lvbkZpbGUvclBRTmZOdkhLSzE0REFBMFd3RmdYTy9zYW5kYm94L2RUMHVyd1Q5S1FpZXo0V0RIUGQ3OEMtaW1hZ2VzXzE3NTg0ODY2NDE5MzBfbmExZm5fTDJodmJXVXZkV0oxYm5SMUwzWnBaR1Z2WDJSdmQyNXNiMkZrWlhKZlltRnVibVZ5LnBuZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc5ODc2MTYwMH19fV19&Key-Pair-Id=K2HSFNDJXOU9YS&Signature=LDrOy1KH5qhJ1Zr9s-21PlVTj0X~lTggi-o-fAb3n12Wf0bf2Vw53jkQvRKZmzZsyU8GwI3EQdThx8wOGreK-R-GbPvPBmr9aolgz3svxo9jo2tDQgQ-T8VGVl2GO9xbRov27W8QiZtq2jdV4KUJCz5PQ~B~o-xWVbCrY98J-3ne-Dc9PwVQV9Vvs3u1I9avka2-U7MyW6iVC8f6BuK2zNsOtTGXmt1jhWkfwpH9r0RsuuDZJcufZnLkXXl961TJF1AFitNzuTq8gCIZflqYmwKScRwHt5oluwHKmcifOF1TL1YVwl5Ns-JCxWLhS92EytzkNt~PtH6GpiAR2dqYSQ__)

## Visão Geral

Este projeto é um poderoso e flexível downloader de vídeos, construído para facilitar o download de conteúdo de diversas plataformas. Utilizando a robustez do `yt-dlp` e a escalabilidade do Kubernetes, ele oferece uma solução eficiente para gerenciar seus downloads de vídeo e áudio.

## Funcionalidades

- **Download Versátil:** Suporte a uma ampla gama de sites e plataformas de vídeo através do `yt-dlp`.
- **Orquestração com Kubernetes:** Implantação e gerenciamento facilitados em ambientes de contêiner.
- **Automação:** Scripts `build_n_push.sh` e `deploy.sh` para automatizar o ciclo de vida da aplicação.
- **Contêiner Leve:** Imagem Docker otimizada baseada em Python 3.11.

## Tecnologias Utilizadas

- **Python:** Linguagem principal de desenvolvimento.
- **yt-dlp:** Ferramenta essencial para o download de vídeos.
- **Docker:** Para conteinerização da aplicação.
- **Kubernetes:** Para orquestração e escalabilidade.
- **Shell Script:** Para automação de build e deploy.

## Como Usar

### Pré-requisitos

Certifique-se de ter as seguintes ferramentas instaladas:

- Docker
- kubectl (para implantação no Kubernetes)
- Git

### Instalação e Execução Local (Docker)

1. Clone o repositório:
   ```bash
   git clone https://github.com/adre76/video-downloader.git
   cd video-downloader
   ```

2. Construa a imagem Docker:
   ```bash
   ./build_n_push.sh
   ```
   (Este script também fará o push para um registro, se configurado)

3. Execute o contêiner (exemplo):
   ```bash
   docker run -it --rm video-downloader:latest <URL_DO_VIDEO>
   ```

### Implantação no Kubernetes

1. Certifique-se de que seu cluster Kubernetes esteja configurado e `kubectl` esteja autenticado.

2. Edite os arquivos em `kubernetes/` conforme necessário para seu ambiente (ex: Ingress, Service, Deployment).

3. Execute o script de deploy:
   ```bash
   ./deploy.sh
   ```

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues e pull requests.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

## Contato

Para dúvidas ou sugestões, entre em contato com adre76 via GitHub.


ARG OLLAMA_VERSION=0.9.1-rc0
FROM ollama/ollama:${OLLAMA_VERSION}

LABEL author="mlamamra@dawan.fr"
LABEL created="2025-06-11"
LABEL stack="ollama"
LABEL stack.version="0.9"

RUN useradd -m -U ollama
USER ollama
WORKDIR /home/ollama

RUN mkdir -p /home/ollama/.ollama

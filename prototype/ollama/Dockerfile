FROM ollama/ollama:latest

RUN ollama serve & server_pid=$!; \
    until ollama list >/dev/null 2>&1; do sleep 2; done; \
    ollama pull bge-m3; \
    kill "$server_pid"
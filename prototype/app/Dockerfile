FROM python:3.14.6-slim

WORKDIR /app

# copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ .

EXPOSE 8501

CMD until python -u rag_init.py; do \
		echo 'Waiting for Qdrant/LiteLLM initialization dependencies...'; \
		sleep 2; \
	done; \
	exec streamlit run app.py --server.port=8501 --server.address=0.0.0.0
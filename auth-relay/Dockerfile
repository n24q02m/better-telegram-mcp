FROM python:3.13-slim-bookworm

RUN pip install --no-cache-dir starlette uvicorn

WORKDIR /app
COPY server.py .

EXPOSE 8080

USER nobody
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]

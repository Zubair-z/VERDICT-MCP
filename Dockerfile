FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir mcp pyyaml coverage fastapi uvicorn pydantic pytest pytest-cov

COPY . .

EXPOSE 8000

CMD ["python", "-m", "verdict_mcp.api_server"]

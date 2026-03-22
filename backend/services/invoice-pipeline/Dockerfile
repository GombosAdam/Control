FROM python:3.11-slim
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Install common package
COPY common /common
RUN pip install /common

# Install service dependencies
COPY services/invoice-pipeline/pyproject.toml .
RUN pip install .

# Copy service code
COPY services/invoice-pipeline/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]

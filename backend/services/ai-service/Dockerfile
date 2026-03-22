FROM python:3.11-slim
WORKDIR /app

# Install common package
COPY common /common
RUN pip install /common

# Install service dependencies
COPY services/ai-service/pyproject.toml .
RUN pip install .

# Copy service code
COPY services/ai-service/ .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

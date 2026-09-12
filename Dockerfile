# FinModel AI — container image for the Streamlit dashboard.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8501

WORKDIR /app

# Build tools for any dependency without a prebuilt wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first for better layer caching.
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the application source.
COPY . .

EXPOSE 8501

# Fail the container health check if the package cannot be imported.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import core, config, ui.analysis" || exit 1

# Launch the dashboard. Set OPENAI_API_KEY at runtime to enable the LLM agent.
CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]

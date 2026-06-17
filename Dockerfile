FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system prediction-desk \
    && adduser --system --ingroup prediction-desk prediction-desk

COPY pyproject.toml README.md alembic.ini ./
COPY alembic ./alembic
COPY src ./src
COPY scripts ./scripts
COPY sample_data ./sample_data

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

USER prediction-desk

EXPOSE 8000

CMD ["uvicorn", "prediction_desk.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

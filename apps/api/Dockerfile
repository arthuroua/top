FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
COPY app ./app
COPY scripts ./scripts
RUN chmod +x ./scripts/docker-entrypoint.sh ./scripts/create-migration.sh

EXPOSE 8000

ENTRYPOINT ["./scripts/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

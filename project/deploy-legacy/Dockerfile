FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/project/backend
COPY project/backend/pyproject.toml ./
COPY project/backend/app ./app
RUN pip install --no-cache-dir .
COPY project/backend/main.py project/backend/config.py project/backend/mcp_client.py project/backend/models.py ./
COPY project/backend/routes ./routes
COPY project/backend/services ./services
COPY project/test_voice.html project/MySherpas-prototype.html project/mobile.html /srv/project/
COPY project/videos /srv/project/videos
COPY cases /srv/cases
COPY assets /srv/assets
RUN useradd --create-home app && mkdir -p /srv/project/backend/data && chown app:app /srv/project/backend/data
USER app
ENV DATABASE_URL=sqlite:////srv/project/backend/data/app.db
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

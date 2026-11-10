FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings_production
WORKDIR /app
COPY requirements-lock.txt ./
RUN python -m pip install --no-cache-dir -r requirements-lock.txt
COPY manage.py gunicorn.conf.py ./
COPY config/ ./config/
COPY items/ ./items/
COPY templates/ ./templates/
RUN DJANGO_SETTINGS_MODULE=config.settings_build python manage.py collectstatic --noinput \
    && useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--config", "gunicorn.conf.py"]

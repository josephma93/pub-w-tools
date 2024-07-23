FROM python:3.12-slim AS build

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

RUN chown -R appuser:appgroup /app

USER appuser

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

ARG PORT=3002
ENV PORT $PORT
EXPOSE $PORT

CMD ["sh", "-c", "flask run --host=0.0.0.0 --port=${PORT}"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl --fail http://localhost:${PORT}/apidocs || exit 1
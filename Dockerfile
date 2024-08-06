FROM python:3.12-slim AS build

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

RUN chown -R appuser:appgroup /app

USER appuser

ARG PORT=3002
ARG LOGGING_LEVEL=INFO

ENV PORT $PORT
ENV LOGGING_LEVEL $LOGGING_LEVEL
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

EXPOSE $PORT

# Use gunicorn to run the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:${PORT}", "app:app"]
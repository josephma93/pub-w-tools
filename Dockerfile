FROM python:3.12-slim AS build

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

RUN chown -R appuser:appgroup /app

USER appuser

ARG PORT=3002
ENV PORT $PORT
EXPOSE $PORT

ARG LOGGING_LEVEL=INFO
ENV LOGGING_LEVEL $LOGGING_LEVEL

CMD ["python", "app.py"]
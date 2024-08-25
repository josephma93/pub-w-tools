#!/bin/sh
exec gunicorn -w 4 -k gevent --timeout 120 -b 0.0.0.0:${PORT} wsgi:app
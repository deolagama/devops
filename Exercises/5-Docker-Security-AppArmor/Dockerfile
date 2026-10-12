FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN python -m pip install --no-cache-dir flask

EXPOSE 5000

CMD ["python", "app.py"]
# Базовый образ
FROM python:3.11-alpine
WORKDIR /app
RUN mkdir -p ./app/alembic/versions
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt
COPY ./app /app
RUN cd /app

CMD ["python", "main.py"]

FROM python:3.12-slim

WORKDIR /app

COPY ./requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src ./src

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.setup.main:app", "--host", "0.0.0.0", "--port", "8000", "--root-path", "/api"]

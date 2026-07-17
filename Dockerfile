FROM python:3.14-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.14-slim AS runner

WORKDIR /app


COPY --from=builder /root/.local /root/.local

COPY . .

ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY rinse ./rinse
COPY examples ./examples
RUN pip install --no-cache-dir .

ENV RINSE_DB=/data/rinse.db
VOLUME /data
EXPOSE 8000

CMD ["rinse", "serve", "--host", "0.0.0.0", "--port", "8000"]

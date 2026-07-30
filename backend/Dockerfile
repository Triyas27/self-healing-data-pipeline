FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Shell form (not exec array) so $PORT actually expands -- Render and most
# host platforms inject their own port via this env var at runtime, and the
# container has to bind to whatever that is, not a fixed 8000.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Render는 PORT 환경변수를 주입한다
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

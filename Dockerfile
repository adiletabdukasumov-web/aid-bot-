FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# база и логи; на хостинге примонтируй сюда постоянный диск (volume)
ENV DATA_DIR=/app/data
CMD ["python", "bot.py"]

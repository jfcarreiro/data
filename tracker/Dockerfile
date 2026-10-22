FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY tracker ./tracker
COPY config ./config
EXPOSE 8000
CMD ["python", "-m", "tracker", "--config", "config/house.yaml", "--db", "/data/tracker.db"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 13400

CMD ["gunicorn", "-b", "0.0.0.0:13400", "-w", "2", "app:app"]

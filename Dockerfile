# Use more specific Python version to avoid rebuilding the image layers unnecessarily
FROM python:3.9.22
COPY requirements.txt .
RUN pip install --user -r requirements.txt
RUN python -m playwright install chromium
RUN python -m playwright install-deps

WORKDIR /app

RUN mkdir -p /app/data && chmod -R 777 /app/data

COPY *.py ./

CMD ["python", "scheduler.py"]

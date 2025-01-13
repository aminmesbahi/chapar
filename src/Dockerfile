FROM python:3.9-slim

WORKDIR /app

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

ENV PYTHONIOENCODING=utf8
ENV LANG=C.UTF-8

EXPOSE 5000

CMD ["python", "chapar.py", "newsletter0-ltr"]
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ .

ENV PYTHONIOENCODING=utf8
ENV LANG=C.UTF-8
ENV CHAPAR_TEMPLATE=newsletter0-ltr

RUN useradd -r -u 1001 -g root chapar && chown -R chapar /app
USER chapar

EXPOSE 5000

CMD ["sh", "-c", "python chapar.py ${CHAPAR_TEMPLATE}"]
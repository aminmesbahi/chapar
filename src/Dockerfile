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
# Set CHAPAR_MODE=api to run the web API, or leave unset/batch to run the batch emailer
ENV CHAPAR_MODE=api

RUN useradd -r -u 1001 -g root chapar && chown -R chapar /app
USER chapar

EXPOSE 5000

CMD ["sh", "-c", "if [ \"$CHAPAR_MODE\" = 'api' ]; then gunicorn --bind 0.0.0.0:5000 --workers 2 chapar_api:app; else python chapar.py ${CHAPAR_TEMPLATE}; fi"]
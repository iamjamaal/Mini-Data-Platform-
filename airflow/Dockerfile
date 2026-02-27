FROM apache/airflow:2.8.1-python3.11

USER root
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
USER airflow


RUN pip install --no-cache-dir \
    minio==7.2.3 \
    psycopg2-binary==2.9.9 \
    pandas==2.1.4 && \
    sed -i 's/from datetime import datetime$/from datetime import datetime, timezone/' \
        /home/airflow/.local/lib/python3.11/site-packages/flask_session/sessions.py && \
    sed -i 's/datetime\.utcnow()/datetime.now(timezone.utc)/g' \
        /home/airflow/.local/lib/python3.11/site-packages/flask_session/sessions.py

COPY --chmod=755 entrypoint.sh /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
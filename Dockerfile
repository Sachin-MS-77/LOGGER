FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY ulpf ./ulpf
COPY docs ./docs
ENV PYTHONPATH=/app AEGIS_DATA_DIR=/var/lib/aegis AEGIS_HOST=0.0.0.0 AEGIS_SYSLOG_HOST=0.0.0.0
VOLUME ["/var/lib/aegis"]
EXPOSE 8765 5514/tcp 5514/udp 6514/tcp
RUN mkdir -p /var/lib/aegis && chown -R 65532:65532 /var/lib/aegis
USER 65532:65532
CMD ["python", "-m", "ulpf.app"]

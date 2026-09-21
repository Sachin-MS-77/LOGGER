FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY ulpf ./ulpf
COPY docs ./docs
ENV PYTHONPATH=/app LOGFLUX_DATA_DIR=/var/lib/logflux LOGFLUX_HOST=0.0.0.0 LOGFLUX_SYSLOG_HOST=0.0.0.0
VOLUME ["/var/lib/logflux"]
EXPOSE 8765 5514/tcp 5514/udp 6514/tcp
RUN mkdir -p /var/lib/logflux && chown -R 65532:65532 /var/lib/logflux
USER 65532:65532
CMD ["python", "-m", "ulpf.app"]

# Use base image with alphafusion-core pre-installed (includes all shared functionality)
FROM alphafusion-baseimage:latest

WORKDIR /app

# Copy alphafusion-issuetracker application code
COPY alphafusion-issuetracker /app/alphafusion-issuetracker

# Install Flask and web dependencies
RUN pip install --no-cache-dir \
    Flask>=3.0.0 \
    Flask-WTF>=1.2.0 \
    Flask-Talisman>=1.1.0 \
    Flask-Limiter>=3.5.0 \
    marshmallow>=3.20.0 \
    authlib>=1.2.0 \
    requests>=2.31.0

# Copy config mapping file
COPY alphafusion-issuetracker/config_mapping.json /app/config_mapping.json

# Copy non-sensitive configs from alphafusion-config/
# Note: Credentials should be pre-encrypted on host before build
COPY alphafusion-config/ /app/alphafusion-config-source/

# Run config copier to copy configs to container filesystem
RUN python /usr/local/bin/copy_configs_to_container.py \
    --source-config-dir=/app/alphafusion-config-source \
    --source-credentials-dir=/app/.credentials \
    --target-config-dir=/app/config \
    --target-credentials-dir=/app/.credentials \
    --mapping-file=/app/config_mapping.json || \
    echo "WARNING: Config copying failed (credentials may not be available)"

# Set proper file permissions
RUN chmod -R 755 /app/config && \
    chmod -R 700 /app/.credentials && \
    chown -R appuser:appuser /app/config /app/.credentials || true

# Set Python path
ENV PYTHONPATH=/app/alphafusion-issuetracker
ENV FLASK_APP=apps.web.app
ENV FLASK_PORT=6001

# SecureConfigLoader configuration
ENV ALPHAFUSION_CONFIG_MAPPING=/app/config_mapping.json
ENV ALPHAFUSION_CONFIG_DIR=/app/config
ENV ALPHAFUSION_CREDENTIALS_DIR=/app/.credentials

# Logging configuration - logs will be written to /app/logs (volume-mounted)
ENV ALPHAFUSION_LOG_DIR=/app/logs

# Create non-root user for security and set proper ownership
RUN mkdir -p /app/.credentials /app/logs && \
    groupadd -r appuser && useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY alphafusion-issuetracker/scripts/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose Flask port
EXPOSE 6001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD wget --quiet --tries=1 --spider --timeout=5 http://127.0.0.1:6001/api/health || exit 1

# Switch to non-root user
USER appuser

# Run the Flask app
WORKDIR /app/alphafusion-issuetracker
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "apps.web.app"]


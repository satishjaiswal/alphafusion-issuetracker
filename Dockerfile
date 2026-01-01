# Use base image with alphafusion-core pre-installed (includes all shared functionality)
FROM alphafusion-baseimage:latest

WORKDIR /app

# Copy alphafusion-issuetracker application code
COPY alphafusion-issuetracker /app/alphafusion-issuetracker

# Create credentials directory structure
# Credentials will be copied from mounted volume to container filesystem at startup
RUN mkdir -p /app/.credentials/integrations /app/alphafusion-issuetracker/scripts

# Install Flask and web dependencies
RUN pip install --no-cache-dir \
    Flask>=3.0.0 \
    Flask-WTF>=1.2.0 \
    Flask-Talisman>=1.1.0 \
    Flask-Limiter>=3.5.0 \
    marshmallow>=3.20.0 \
    authlib>=1.2.0 \
    requests>=2.31.0

# Set Python path
ENV PYTHONPATH=/app/alphafusion-issuetracker
ENV FLASK_APP=apps.web.app
ENV FLASK_PORT=6001

# SecureConfigLoader configuration
ENV ALPHAFUSION_CONFIG_MAPPING=/app/alphafusion-issuetracker/config_mapping.json
ENV ALPHAFUSION_CREDENTIALS_DIR=/app/.credentials

# Logging configuration - logs will be written to /app/logs (volume-mounted)
ENV ALPHAFUSION_LOG_DIR=/app/logs

# Create non-root user for security and set proper ownership for credentials
RUN mkdir -p /app/.credentials /app/logs && \
    groupadd -r appuser && useradd -r -g appuser -u 1000 appuser && \
    chown -R appuser:appuser /app

# Copy entrypoint script
COPY alphafusion-issuetracker/scripts/entrypoint.sh /app/entrypoint.sh
COPY alphafusion-issuetracker/scripts/copy_credentials.py /app/alphafusion-issuetracker/scripts/copy_credentials.py
RUN chmod +x /app/entrypoint.sh /app/alphafusion-issuetracker/scripts/copy_credentials.py

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


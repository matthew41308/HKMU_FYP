# src/Dockerfile  ──────────────────────────────────────────────────────────
# syntax = docker/dockerfile:1.2
FROM python:3.11.11-bookworm

#Mount secret files from render
RUN --mount=type=secret,id=ssh_key,dst=/etc/secrets/ssh_key cat /etc/secrets/ssh_key
RUN --mount=type=secret,id=ssh_key_pub,dst=/etc/secrets/ssh_key.pub cat /etc/secrets/ssh_key.pub

WORKDIR /project
COPY src/ ./HKMU_FYP
RUN pip install --no-cache-dir -r src/requirements.txt

# ----- extras (java) ------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Make the code importable
ENV PYTHONPATH="./src" \
    PYTHONUNBUFFERED=1          \
    PORT=8080                   \
    DB_SSH_KEY=/etc/secrets/ssh_key \
    DB_TUNNEL_PORT=5432

# ----- entry point --------------------------------------------------------
RUN chmod +x src/entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["src/entrypoint.sh"]
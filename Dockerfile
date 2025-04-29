# src/Dockerfile  ──────────────────────────────────────────────────────────
# syntax = docker/dockerfile:1.2
FROM python:3.11.11-bookworm

WORKDIR /project
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ----- extras (java) ------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ----- entry point --------------------------------------------------------
RUN chmod +x entrypoint.sh  
EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
# syntax=docker/dockerfile:1.5
FROM python:3.11-bookworm

# ─── PlantUML version (change when you need a newer one) ──────────────────
ARG  PLANTUML_VERSION=1.2025.2
ENV  PLANTUML_JAR_PATH=/opt/plantuml.jar

WORKDIR /project

# ─── OS packages ----------------------------------------------------------
    RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends \
        curl \
        netcat-openbsd \        
        openjdk-17-jre-headless && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# ─── PlantUML jar ---------------------------------------------------------
RUN curl -fsSL \
        "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-${PLANTUML_VERSION}.jar" \
        -o "${PLANTUML_JAR_PATH}"

# ─── Python deps ----------------------------------------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─── Source ---------------------------------------------------------------
COPY . .

# ─── Entrypoint -----------------------------------------------------------
RUN chmod +x entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
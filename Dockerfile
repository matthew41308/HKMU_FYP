# src/Dockerfile  ──────────────────────────────────────────────────────────
# syntax = docker/dockerfile:1.2
FROM python:3.11.11-bookworm

WORKDIR /project
ENV PLANTUML_JAR_PATH=/opt/plantuml.jar
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        graphviz \
        openjdk-17-jdk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN curl -L "https://github.com/plantuml/plantuml/releases/download/v${PLANTUML_VERSION}/plantuml-${PLANTUML_VERSION}.jar" \
        -o "${PLANTUML_JAR_PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .



# ----- entry point --------------------------------------------------------
RUN chmod +x entrypoint.sh  
EXPOSE 8080
ENTRYPOINT ["./entrypoint.sh"]
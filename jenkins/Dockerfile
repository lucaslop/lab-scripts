# Uma unica instancia de Jenkins que roda os DOIS jobs deste laboratorio:
# o job de build (Jenkinsfile deste repositorio) e o job de deploy
# (Jenkinsfile do repositorio irmao, lab-folio-helm) -- por isso ela leva
# docker, kubectl e helm juntos, mesmo o job de build so precisando do
# docker.
FROM jenkins/jenkins:lts-jdk17

USER root

# Instala o cliente Docker (só o cliente — o daemon é o da sua máquina,
# acessado pelo socket montado no docker run)
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg lsb-release \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
        https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Instala o kubectl, para inspecionar o cluster quando precisar depurar
RUN curl -fsSLo /usr/local/bin/kubectl \
      "https://dl.k8s.io/release/v1.31.0/bin/linux/$(dpkg --print-architecture)/kubectl" \
    && chmod +x /usr/local/bin/kubectl

# Instala o helm — é ele quem de fato implanta o CronJob (Jenkinsfile do
# repositorio lab-folio-helm, estágio 3: "helm upgrade --install"),
# exatamente como no Senado
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 \
      | bash

USER jenkins

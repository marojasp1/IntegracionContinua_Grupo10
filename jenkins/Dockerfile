# Imagen de Jenkins para el proyecto Turnos EPS.
# Parte de la imagen oficial LTS y agrega lo que el pipeline necesita:
# Python 3 (pruebas), Docker CLI + Compose (construir y levantar contenedores)
# y los plugins listados en plugins.txt.
FROM jenkins/jenkins:lts-jdk17

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv python3-pip ca-certificates curl gnupg \
 && install -m 0755 -d /etc/apt/keyrings \
 && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
 && echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
      > /etc/apt/sources.list.d/docker.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
 && rm -rf /var/lib/apt/lists/*
USER jenkins

# Plugins (se instalan al construir la imagen, no a mano)
COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

# Configuración como código (usuario admin, job del pipeline)
COPY casc/ /var/jenkins_home/casc/
ENV CASC_JENKINS_CONFIG=/var/jenkins_home/casc/jenkins.yaml
# Se omite el asistente inicial porque JCasC ya deja Jenkins configurado
ENV JAVA_OPTS="-Djenkins.install.runSetupWizard=false"

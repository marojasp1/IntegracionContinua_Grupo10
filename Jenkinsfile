// Pipeline de integración continua - Turnos EPS (Grupo 10)
// Entrega 2 (Escenario 5): Jenkins como gestor de operaciones.
// Cada cambio en el repositorio dispara: pruebas unitarias -> construcción
// de las imágenes Docker -> despliegue temporal con Docker Compose ->
// prueba de humo contra los dos contenedores -> limpieza.
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '15'))
        disableConcurrentBuilds()
    }

    triggers {
        // Revisa GitHub cada 5 minutos. Si se configura el webhook de GitHub
        // (plugin GitHub), el disparo es inmediato y esto queda de respaldo.
        pollSCM('H/5 * * * *')
    }

    environment {
        COMPOSE_PROJECT_NAME = "turnos-ci-${env.BUILD_NUMBER}"
        APP_PORT = '5050'   // puerto distinto al de desarrollo (5000)
        COMPOSE_FILE = 'docker-compose.yml:docker-compose.ci.yml'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'mkdir -p reports'
                sh 'git log -1 --pretty="format:%h %an: %s"'
            }
        }

        stage('Análisis estático y pruebas unitarias') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -q -r app/requirements.txt -r requirements-dev.txt
                    flake8 app tests
                    pytest -q --junitxml=reports/junit.xml
                '''
            }
            post {
                always { junit testResults: 'reports/junit.xml', allowEmptyResults: true }
            }
        }

        stage('Construir imágenes Docker') {
            steps {
                sh 'docker compose version'
                sh 'docker compose build --pull'
            }
        }

        stage('Desplegar entorno de prueba') {
            steps {
                // docker-compose.ci.yml hace únicos por build los nombres de
                // contenedores y red, para no chocar con otros entornos.
                sh 'docker compose up -d --wait --wait-timeout 120'
                sh 'docker compose ps'
            }
        }

        stage('Prueba de humo (web <-> db)') {
            steps {
                sh 'bash -o pipefail -c \'./scripts/smoke_test.sh "$COMPOSE_PROJECT_NAME" | tee reports/smoke.txt\''
            }
        }
    }

    post {
        always {
            sh 'mkdir -p reports'
            sh 'docker compose logs --no-color > reports/compose_logs.txt 2>&1 || true'
            sh 'docker compose down -v --remove-orphans || true'
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }
        success { echo 'Pipeline OK: la versión puede integrarse a main.' }
        failure { echo 'Pipeline FALLÓ: revisar la etapa en rojo antes de integrar.' }
    }
}

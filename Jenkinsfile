// Pipeline de BUILD -- constroi e publica a imagem. Nao faz deploy: quem
// implanta e o Jenkinsfile do outro repositorio, lab-folio-helm/Jenkinsfile,
// exatamente como no Senado o build (rvbi-scripts/JenkinsfileHelm) e o
// deploy (helm-rvbi-scripts/JenkinsfileHelm) sao dois jobs, dois repos.
pipeline {
    agent any

    environment {
        REGISTRY       = 'localhost:5000'          // registry local do laboratório
        IMAGEM         = 'lab-folio'
        TAG            = "${env.BUILD_NUMBER}"
        HOST_WORKSPACE = '/var/lib/docker/volumes/d38d71be9a6b1e11c1988ca9f30c77f032fce2c4d4923ad9eda2355710ed6b98/_data/workspace/lab-folio-scripts'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {

        stage('1. Baixar o codigo') {
            steps {
                checkout scm
                sh 'echo "Commit: $(git rev-parse --short HEAD)"'
            }
        }

        stage('2. Verificar segredos') {
            steps {
                sh '''
                    if git ls-files | grep -E "(^|/)\\.env$"; then
                        echo "ERRO: arquivo .env versionado!"
                        exit 1
                    fi
                    echo "Nenhum segredo versionado. OK."
                '''
            }
        }

        stage('3. Validar sintaxe') {
            steps {
                sh 'docker run --rm -v "$HOST_WORKSPACE":/src -w /src python:3.12-slim \
                        python -m compileall -q lib scripts && echo "Sintaxe OK"'
            }
        }

        stage('4. Testar conexao com o FOLIO') {
            steps {
                sh '''
                    docker run --rm --env-file "$HOST_WORKSPACE/config/.env" \
                        -v "$HOST_WORKSPACE":/src -w /src python:3.12-slim sh -c \
                        "pip install --quiet -r requirements.txt && \
                         python -c \\"from lib.folio import conectar; conectar(); print('Conexao OK')\\""
                '''
            }
        }

        stage('5. Construir a imagem') {
            steps {
                sh """
                    docker build -t ${REGISTRY}/${IMAGEM}:${TAG} \
                                 -t ${REGISTRY}/${IMAGEM}:latest ${HOST_WORKSPACE}
                """
            }
        }

        stage('6. Publicar no registry') {
            steps {
                sh """
                    docker push ${REGISTRY}/${IMAGEM}:${TAG}
                    docker push ${REGISTRY}/${IMAGEM}:latest
                """
            }
        }
    }

    post {
        success {
            echo "Build ${TAG} concluido. Imagem: ${REGISTRY}/${IMAGEM}:${TAG}"
            echo "Proximo passo: dispare o job do repositorio lab-folio-helm (deploy), informando a tag ${TAG}."
        }
        failure { echo "Build ${TAG} FALHOU. Veja o log acima." }
        always  { sh 'docker image prune -f || true' }
    }
}
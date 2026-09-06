// Pipeline de BUILD -- constroi e publica a imagem. Nao faz deploy: quem
// implanta e o Jenkinsfile do outro repositorio, lab-folio-helm/Jenkinsfile,
// exatamente como no Senado o build (rvbi-scripts/JenkinsfileHelm) e o
// deploy (helm-rvbi-scripts/JenkinsfileHelm) sao dois jobs, dois repos.
pipeline {
    agent any

    environment {
        REGISTRY  = 'localhost:5000'          // registry local do laboratório
        IMAGEM    = 'lab-folio'
        TAG       = "${env.BUILD_NUMBER}"
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
                // Falha o build se alguem commitou um .env por engano.
                // No Senado esta etapa vale ouro.
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
                sh 'docker run --rm -v "$PWD":/src -w /src python:3.12-slim \
                        python -m compileall -q lib scripts && echo "Sintaxe OK"'
            }
        }

        stage('4. Testar conexao com o FOLIO') {
            steps {
                // Teste de fumaca real: loga na API de demonstracao.
                // Se o FOLIO estiver fora do ar ou a credencial mudou,
                // o build para aqui em vez de publicar uma imagem quebrada.
                sh '''
                    docker run --rm --env-file config/.env \
                        -v "$PWD":/src -w /src python:3.12-slim sh -c \
                        "pip install --quiet -r requirements.txt && \
                         python -c \\"from lib.folio import conectar; conectar(); print('Conexao OK')\\""
                '''
            }
        }

        stage('5. Construir a imagem') {
            steps {
                sh """
                    docker build -t ${REGISTRY}/${IMAGEM}:${TAG} \
                                 -t ${REGISTRY}/${IMAGEM}:latest .
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

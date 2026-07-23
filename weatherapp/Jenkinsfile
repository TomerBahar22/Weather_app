pipeline {
    agent { label 'worker' }

    environment {
        IMAGE_NAME = "tomerbahar2/weather_app-web"
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    stages {
        stage('Lint') {
            steps {
                sh 'pylint app.py --fail-under=5.0'
            }
        }

        stage('Build') {
            steps {
                sh "docker build -t ${IMAGE_NAME}:${IMAGE_TAG} ."
            }
        }

        stage('Run & Check') {
            steps {
                sh "docker run -d --name weather-test -p 8000:8000 ${IMAGE_NAME}:${IMAGE_TAG}"
                sh 'sleep 5'
                sh 'curl -f http://localhost:8000'
            }
        }

        stage('Push to Docker Hub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: '6fb338fc-73a1-43ad-973d-11bce70ebbce',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh 'echo $DOCKER_PASS | docker login -u $DOCKER_USER --password-stdin'
                    sh "docker push ${IMAGE_NAME}:${IMAGE_TAG}"
                    sh "docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:latest"
                    sh "docker push ${IMAGE_NAME}:latest"
                }
            }
        }

        stage('Deploy') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: 'e90d2e9b-aedf-433e-b600-3de7f6159376',
                    keyFileVariable: 'SSH_KEY'
                )]) {
                    sh '''
                        ssh -i "$SSH_KEY" -o StrictHostKeyChecking=accept-new ubuntu@172.31.33.73 "
                            cd ~/Weather_app &&
                            docker compose pull web &&
                            docker compose up -d
                        "
                    '''
                    }
            }
        }
    }

    post {
        always {
            sh '''
                docker stop weather-test || true
                docker rm weather-test || true
                docker rmi ${IMAGE_NAME}:${IMAGE_TAG} || true
                docker rmi ${IMAGE_NAME}:latest || true
                docker logout || true
            '''
        }
    }
}
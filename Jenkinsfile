pipeline {
    agent { label 'worker' }

    environment {
        IMAGE_NAME = "yourdockerhubuser/weather-app"
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
                    credentialsId: 'dockerhub-creds',
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
    }

    post {
        always {
            sh 'docker stop weather-test || true'
            sh 'docker rm weather-test || true'
        }
    }
}
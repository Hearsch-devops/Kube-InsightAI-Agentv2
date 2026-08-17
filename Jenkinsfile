
pipeline {

    agent any

    environment {
        IMAGE_NAME = "95337/calccast-agent"
        MCP_IMAGE = "95337/calccast-mcp"
        WEATHER_IMAGE = "95337/calccast-weather"
        FRONTEND_IMAGE = "95337/calccast-frontend"
        IMAGE_TAG  = "${BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out CalcCast source code...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python dependencies...'

                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running CalcCast tests...'

                sh '''
                    . .venv/bin/activate

                    if [ -d "tests" ] && [ "$(find tests -name "*.py" | wc -l)" -gt 0 ]; then
                        pytest -v
                    else
                        echo "No tests found. Skipping pytest."
                    fi
                '''
            }
        }

        stage('Build application Image') {
            steps {
                echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"

                sh '''
                    docker build \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        -t ${IMAGE_NAME}:latest \
                        .
                '''
            }
        }

        stage('Build MCP Image') {
            steps {
                echo "Building MCP image: ${MCP_IMAGE}:${IMAGE_TAG}"

                sh '''
                    docker build \
                        -f Dockerfile.mcp \
                        -t ${MCP_IMAGE}:${IMAGE_TAG} \
                        -t ${MCP_IMAGE}:latest \
                        .
                '''
            }
        }

        stage('Prepare Weather CA') {
            steps {
                echo 'Preparing trusted CA bundle for Weather MCP...'

                sh '''
                    cp /etc/ssl/certs/ca-certificates.crt ./ca-certificates.crt
                '''
            }
        }

        stage('Build Weather Image') {
            steps {
                echo "Building Weather MCP image: ${WEATHER_IMAGE}:${IMAGE_TAG}"

                sh '''
                    docker build \
                        -f Dockerfile.weather \
                        -t ${WEATHER_IMAGE}:${IMAGE_TAG} \
                        -t ${WEATHER_IMAGE}:latest \
                        .
                '''
            }
        }

        stage('Build Frontend Image') {
            steps {
                echo "Building Frontend image: ${FRONTEND_IMAGE}:${IMAGE_TAG}"

                sh '''
                    docker build \
                        -f Dockerfile.frontend \
                        -t ${FRONTEND_IMAGE}:${IMAGE_TAG} \
                        -t ${FRONTEND_IMAGE}:latest \
                        .
                '''
            }
        }

        stage('Docker Login') {
            steps {
                echo 'Logging into Docker Hub...'

                withCredentials([
                    usernamePassword(
                        credentialsId: 'docker_login',
                        usernameVariable: 'DOCKER_USER',
                        passwordVariable: 'DOCKER_PASS'
                    )
                ]) {

                    sh '''
                        echo "$DOCKER_PASS" | docker login \
                            -u "$DOCKER_USER" \
                            --password-stdin
                    '''
                }
            }
        }

        stage('Push Frontend Image') {
            steps {
                echo "Pushing ${FRONTEND_IMAGE}:${IMAGE_TAG}..."

                sh '''
                    docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                '''
            }
        }

        stage('Push Docker Image') {
            steps {
                echo "Pushing ${IMAGE_NAME}:${IMAGE_TAG}..."

                sh '''
                    docker push ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        stage('Push MCP Image') {
            steps {

                sh '''
                    docker push ${MCP_IMAGE}:${IMAGE_TAG}
                '''
            }
        }

        stage('Push Weather Image') {
            steps {
                echo "Pushing ${WEATHER_IMAGE}:${IMAGE_TAG}..."

                sh '''
                    docker push ${WEATHER_IMAGE}:${IMAGE_TAG}
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                sh '''
                    sed -i "s|calccast-agent:.*|calccast-agent:${BUILD_NUMBER}|" Kubernetes-manifests/agent.yaml
                    sed -i "s|calccast-mcp:.*|calccast-mcp:${BUILD_NUMBER}|" Kubernetes-manifests/calculator-mcp.yaml
                    sed -i "s|calccast-weather:.*|calccast-weather:${BUILD_NUMBER}|" Kubernetes-manifests/weather-mcp.yaml
                    sed -i "s|calccast-frontend:.*|calccast-frontend:${BUILD_NUMBER}|" Kubernetes-manifests/frontend.yaml

                    kubectl apply -f Kubernetes-manifests/
                '''
            }
        }
    }

    post {

        success {
            echo "========================================"
            echo "CalcCast CI completed successfully!"
            echo "Application: 95337/calccast-agent:${BUILD_NUMBER}"
            echo "MCP:         95337/calccast-mcp:${BUILD_NUMBER}"
            echo "Weather MCP: 95337/calccast-weather:${BUILD_NUMBER}"
            echo "Frontend:    95337/calccast-frontend:${BUILD_NUMBER}"
            echo "========================================"
        }

        failure {
            echo "CalcCast CI pipeline failed."
        }

        always {
            sh 'docker logout || true'
            sh '''
                rm -f ca-certificates.crt || true
                docker logout || true
            '''
        }
    }
}


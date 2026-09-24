pipeline {

    agent any

    environment {
        IMAGE_NAME     = "95337/kube-insightaiv2-agent"
        FRONTEND_IMAGE = "95337/kube-insightaiv2-frontend"
        IMAGE_TAG      = "${BUILD_NUMBER}"
        PROJECT_NAME   = "kube-insight-ai"
    }

    stages {

        stage('Checkout') {
            steps {
                echo 'Checking out Kube-InsightAI source code...'
                checkout scm
            }
        }

        stage('Install Dependencies') {
            steps {
                echo 'Installing Python dependencies...'

                sh '''
                    set -eu

                    python3 -m venv .venv
                    . .venv/bin/activate

                    python -m pip install --upgrade pip
                    python -m pip install -r requirements.txt
                '''
            }
        }

        stage('Test') {
            steps {
                echo 'Running tests...'

                sh '''
                    set -eu
                    . .venv/bin/activate

                    if [ -d "tests" ] && [ "$(find tests -name "*.py" | wc -l)" -gt 0 ]; then
                        pytest -v
                    else
                        echo "No tests found. Skipping pytest."
                    fi
                '''
            }
        }

        stage('Build RAG Knowledge Base') {
            steps {
                echo 'Building Kubernetes RAG knowledge base...'

                withCredentials([
                    string(
                        credentialsId: 'llmfoundry_token',
                        variable: 'LLMFOUNDRY_TOKEN'
                    )
                ]) {
                    sh '''
                        set -eu

                        . .venv/bin/activate

                        export PROJECT_NAME="$PROJECT_NAME"

                        cd retrieval-augmented-generation
                        python -m rag.vector_store
                    '''
                }
            }
        }

        stage('Build Application Image') {
            steps {
                echo "Building backend image: ${IMAGE_NAME}:${IMAGE_TAG}"

                sh '''
                    set -eu

                    docker build \
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
                        .
                '''
            }
        }

        stage('Build Frontend Image') {
            steps {
                echo "Building dashboard image: ${FRONTEND_IMAGE}:${IMAGE_TAG}"

                sh '''
                    set -eu

                    docker build \
                        -f Dockerfile.frontend \
                        -t ${FRONTEND_IMAGE}:${IMAGE_TAG} \
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
                        set -eu

                        echo "$DOCKER_PASS" | docker login \
                            --username "$DOCKER_USER" \
                            --password-stdin
                    '''
                }
            }
        }

        stage('Push Application Image') {
            steps {
                echo "Pushing backend image: ${IMAGE_NAME}:${IMAGE_TAG}"

                sh '''
                    set -eu
                    docker push ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        stage('Push Frontend Image') {
            steps {
                echo "Pushing dashboard image: ${FRONTEND_IMAGE}:${IMAGE_TAG}"

                sh '''
                    set -eu
                    docker push ${FRONTEND_IMAGE}:${IMAGE_TAG}
                '''
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo 'Deploying Kube-InsightAI V2 to Kubernetes...'

                sh '''
                    set -eu

                    # Replace image placeholders with the current build number.
                    sed -i "s|BUILD_TAG|${IMAGE_TAG}|g" \
                        kubernetes-manifests/agent.yaml \
                        kubernetes-manifests/frontend.yaml

                    # Create namespace.
                    kubectl apply \
                        -f kubernetes-manifests/namespace.yaml

                    # Apply ServiceAccount and RBAC permissions.
                    kubectl apply \
                        -f kubernetes-manifests/kube-insightai-rbac.yaml

                    # Deploy backend.
                    kubectl apply \
                        -f kubernetes-manifests/agent.yaml

                    # Deploy frontend.
                    kubectl apply \
                        -f kubernetes-manifests/frontend.yaml

                    # Wait for backend rollout.
                    kubectl rollout status \
                        deployment/kube-insightaiv2-agent \
                        -n kube-insightaiv2 \
                        --timeout=180s

                    # Wait for frontend rollout.
                    kubectl rollout status \
                        deployment/kube-insightaiv2-frontend \
                        -n kube-insightaiv2 \
                        --timeout=180s
                '''
            }
        }
    }

    post {

        success {
            echo "========================================"
            echo "Kube-InsightAI CI/CD completed!"
            echo "Backend:  ${IMAGE_NAME}:${IMAGE_TAG}"
            echo "Frontend: ${FRONTEND_IMAGE}:${IMAGE_TAG}"
            echo "========================================"
        }

        failure {
            echo "Kube-InsightAI pipeline failed."
        }

        always {
            sh '''
                docker logout || true
                rm -f ca-certificates.crt || true
            '''
        }
    }
}

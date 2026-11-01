// Experiment 1: CI/CD pipeline - build, test, containerise and deploy MediCare+ to Kubernetes
pipeline {
  agent any
  environment {
    REGISTRY   = 'localhost:5000'
    IMAGE      = "${REGISTRY}/medicare-hms"
    VERSION    = "1.0.${BUILD_NUMBER}"
    KUBECONFIG = '/var/lib/jenkins/.kube/config'
  }
  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '15'))
  }
  triggers { githubPush() }   // GitHub webhook -> http://<jenkins>:8080/github-webhook/
  stages {
    stage('Checkout') {
      steps {
        checkout scm
        sh 'git log -1 --pretty="Commit %h by %an: %s"'
      }
    }
    stage('Unit Tests') {
      steps {
        sh '''
          python3 -m venv .venv && . .venv/bin/activate
          pip install -q -r requirements.txt pytest
          mkdir -p reports && pytest -q --junitxml=reports/junit.xml tests
        '''
      }
      post { always { junit 'reports/junit.xml' } }
    }
    stage('Build Docker Image') {
      steps { sh 'docker build -t $IMAGE:$VERSION -t $IMAGE:latest .' }
    }
    stage('Push to Registry') {
      steps { sh 'docker push $IMAGE:$VERSION && docker push $IMAGE:latest' }
    }
    stage('Deploy to Kubernetes') {
      steps {
        sh '''
          kubectl apply -f k8s/00-namespace.yaml
          bash scripts/create-secrets.sh
          kubectl apply -f k8s/10-postgres.yaml -f k8s/30-networkpolicy.yaml
          kubectl -n medicare rollout status statefulset/postgres --timeout=180s
          sed -e "s#IMAGE_PLACEHOLDER#$IMAGE:$VERSION#" -e "s#VERSION_PLACEHOLDER#$VERSION#" k8s/20-app.yaml | kubectl apply -f -
          kubectl -n medicare rollout status deployment/medicare-web --timeout=180s
        '''
      }
    }
    stage('Smoke Test') {
      steps {
        sh '''
          for i in $(seq 1 20); do curl -fs http://localhost:30080/api/health && break; sleep 3; done
          echo; curl -fs http://localhost:30080/api/version; echo
          kubectl -n medicare get deploy,pods,svc -o wide
        '''
      }
    }
  }
  post {
    success { echo "MediCare+ ${VERSION} deployed. Open http://<EC2-public-IP>:30080" }
    failure { echo 'Pipeline failed - see the stage logs above.' }
  }
}

pipeline {
    agent any

    stages {
        stage('SonarQube Analysis') {
            steps {
                sh 'sonar-scanner -Dsonar.projectKey=share-your-experience -Dsonar.sources=. -Dsonar.host.url=http://localhost:9000 -Dsonar.token=sqp_3b96deb7444886a165ec71f3e8dfa2c412ec1b14'
            }
        }
        stage('Docker image creation') {
            steps {
                sh 'docker build -t hamou99/inward-backend-flask .'
            }
        }
        stage('Docker image deployment') {
            steps {
                withCredentials([string(credentialsId: 'dockerhubpassword', variable: 'dockerhubpassword')]) {
                    sh 'docker login -u hamou99 -p ${dockerhubpassword}'   
                }
                sh 'docker push hamou99/inward-backend-flask:latest'
            }
        }
    }
}

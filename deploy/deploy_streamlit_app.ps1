# Script to deploy Streamlit app to GCP Cloud Run
# Prerequisites:
# 1. Google Cloud SDK installed
# 2. Docker installed
# 3. GCP project created
# 4. GCP authentication configured

# Configuration variables
$PROJECT_ID = "198756542688"  # Replace with your GCP project ID
$REGION = "us-central1"          # Replace with your preferred region
$SERVICE_NAME = "team5-genai-mscads-streamlit-app"  # Name for your Cloud Run service
$GCP_DOCKER_REPO = "team5-genai-mscads"
$IMAGE_NAME = "streamlit-app"    # Name for your Docker image

# GCP Authentication
Write-Host "Setting up GCP authentication..."

# Check if already authenticated
$current_account = gcloud auth list --filter=status:ACTIVE --format="value(account)"
if ($current_account) {
    Write-Host "Already authenticated as: $current_account"
    $use_existing = Read-Host "Do you want to use the existing account? (Y/N)"
    if ($use_existing -eq "N") {
        # Option 1: Interactive browser login
        Write-Host "Starting interactive browser login..."
        gcloud auth login --no-launch-browser
        
        # Option 2: Service account authentication (uncomment and use if needed)
        # $service_account_key = "path/to/your/service-account-key.json"
        # gcloud auth activate-service-account --key-file=$service_account_key
    }
} else {
    Write-Host "No active account found. Please choose authentication method:"
    Write-Host "1. Interactive browser login (recommended for development)"
    Write-Host "2. Service account authentication (recommended for CI/CD)"
    $auth_choice = Read-Host "Enter your choice (1 or 2)"
    
    switch ($auth_choice) {
        "1" {
            Write-Host "Starting interactive browser login..."
            gcloud auth login --no-launch-browser
        }
        "2" {
            $service_account_key = Read-Host "Enter the path to your service account key file"
            if (Test-Path $service_account_key) {
                gcloud auth activate-service-account --key-file=$service_account_key
            } else {
                Write-Error "Service account key file not found at: $service_account_key"
                exit 1
            }
        }
        default {
            Write-Error "Invalid choice"
            exit 1
        }
    }
}

# Set the project
Write-Host "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Get the project and
$PROJECT_NAME = gcloud projects list --filter="PROJECT_NUMBER=$PROJECT_ID" --format="value(projectId)"

# Enable required APIs
Write-Host "Enabling required GCP APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Verify you have the right IAM role
# Need at least the Artifact Registry Writer role
gcloud projects add-iam-policy-binding $PROJECT_ID --member="user:prinupmathew@uchicago.edu" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding $PROJECT_NAME --member="user:prinupmathew@uchicago.edu" --role="roles/artifactregistry.writer"


# Build the Docker image
# make sure the current folder is src\app
Write-Host "Building Docker image..."
docker build -f .\Dockerfile -t us-central1-docker.pkg.dev/$PROJECT_NAME/$GCP_DOCKER_REPO/$IMAGE_NAME .

# Check if the repo exists in your project
gcloud artifacts repositories list --project=$PROJECT_NAME --location=us-central1

# Create a Docker repository
gcloud artifacts repositories create $GCP_DOCKER_REPO --project=$PROJECT_NAME --repository-format=docker --location=us-central1 --description="Docker images for my apps"

# Delete a Docker repository (BE CAREFUL)
gcloud artifacts repositories delete $GCP_DOCKER_REPO --project=$PROJECT_NAME --location=us-central1

# Configure Docker to use gcloud as a credential helper
gcloud auth configure-docker us-central1-docker.pkg.dev

# Push the image to Google Container Registry
Write-Host "Pushing image to Google Container Registry..."
$DOCKER_REP_IMAGE_REF="us-central1-docker.pkg.dev/$PROJECT_NAME/$GCP_DOCKER_REPO/$($IMAGE_NAME):latest"
docker push $DOCKER_REP_IMAGE_REF

# Deploy to Cloud Run with environment variables
Write-Host "Deploying to Cloud Run..."
#gcloud run deploy $SERVICE_NAME `
#    --image us-central1-docker.pkg.dev/pmathew-32027-genai-midterm/team5-genai-mscads/streamlit-app `
#    --platform managed `
#    --region $REGION `
#    --allow-unauthenticated `
#    --port 8501 `
#    --project=$PROJECT_NAME `
#    --set-env-vars=STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true `
#    --set-env-vars=STREAMLIT_SERVER_PORT=8501 `
#    --set-env-vars=STREAMLIT_SERVER_ENABLE_CORS=false `
#    --set-env-vars=STREAMLIT_SERVER_HEADLESS=true

gcloud run deploy $SERVICE_NAME `
    --image us-central1-docker.pkg.dev/pmathew-32027-genai-midterm/team5-genai-mscads/streamlit-app `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --port 8501 `
    --project=$PROJECT_NAME `
    --env-vars-file .env.yaml

Write-Host "Deployment completed successfully!"
Write-Host "Your Streamlit app is now running on Cloud Run."


# Show logs for the latest deployed revision
gcloud app logs read `
  --project=$PROJECT_NAME `
  --service=$SERVICE_NAME `
  --limit 50 `
  --format="yaml"
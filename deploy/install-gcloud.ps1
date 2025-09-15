# Script to install Google Cloud SDK on Windows
Write-Host "Starting Google Cloud SDK installation process..."

# Check if gcloud is already installed
try {
    $gcloudVersion = gcloud --version
    Write-Host "Google Cloud SDK is already installed:"
    Write-Host $gcloudVersion
    exit 0
} catch {
    Write-Host "Google Cloud SDK not found. Proceeding with installation..."
}

# Download the Google Cloud SDK installer
# https://cloud.google.com/sdk/docs/install
Write-Host "Downloading Google Cloud SDK installer..."
(New-Object Net.WebClient).DownloadFile("https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe", "$env:Temp\GoogleCloudSDKInstaller.exe")

# Run the installer
Write-Host "Running Google Cloud SDK installer..."
& "$env:Temp\GoogleCloudSDKInstaller.exe"

# Verify installation
Write-Host "`nVerifying installation..."
try {
    $gcloudVersion = gcloud --version
    Write-Host "`nGoogle Cloud SDK successfully installed:"
    Write-Host $gcloudVersion
    
    # Initialize gcloud
    Write-Host "`nInitializing Google Cloud SDK..."
    gcloud init
    
    Write-Host "`nInstallation and initialization completed successfully!"
    Write-Host "You can now use the deployment script (test.ps1) to deploy your Streamlit app."
} catch {
    Write-Error "Installation verification failed. Please try installing manually from:"
    Write-Host "https://cloud.google.com/sdk/docs/install"
}

# Instructions for manual installation if needed
Write-Host "`nIf the automatic installation fails, you can install manually:"
Write-Host "1. Download the installer from: https://cloud.google.com/sdk/docs/install"
Write-Host "2. Run the installer and follow the prompts"
Write-Host "3. Open a new PowerShell window and run 'gcloud init'" 
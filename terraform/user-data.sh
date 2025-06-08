#!/bin/bash
# Terraform User Data Script for FusionSolar Management Deployment

set -e

# Log all output
exec > >(tee /var/log/fusionsolar-setup.log)
exec 2>&1

echo "Starting FusionSolar Management setup at $(date)"

# Update system
yum update -y

# Install required packages
yum install -y docker git

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add ec2-user to docker group
usermod -a -G docker ec2-user

# Create application directory
mkdir -p /opt/fusionsolar-management
cd /opt/fusionsolar-management

# Create directories
mkdir -p data logs

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  fusionsolar-management:
    build: .
    restart: unless-stopped
    environment:
      # Storage configuration
      - FUSIONSOLAR_STORAGE_TYPE=s3
      - FUSIONSOLAR_S3_BUCKET_NAME=${s3_bucket_name}
      - FUSIONSOLAR_S3_REGION=${aws_region}
      
      # AWS Secrets Manager
      - USE_SECRETS_MANAGER=true
      - AWS_REGION=${aws_region}
      
      # Location settings (default to Karlovo, Bulgaria)
      - FUSIONSOLAR_LOCATION_LATITUDE=42.6420
      - FUSIONSOLAR_LOCATION_LONGITUDE=24.8083
      - FUSIONSOLAR_LOCATION_NAME=Karlovo
      - FUSIONSOLAR_LOCATION_COUNTRY=Bulgaria
      
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# Create environment file template
cat > .env.template << 'EOF'
# FusionSolar credentials - UPDATE THESE!
FUSIONSOLAR_USERNAME=your_username_here
FUSIONSOLAR_PASSWORD=your_password_here

# Telegram notifications - UPDATE THESE!
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Price thresholds
PRICE_THRESHOLD=15.04
LOW_POWER_SETTING=5.000
HIGH_POWER_SETTING=no limit

# Storage configuration
FUSIONSOLAR_STORAGE_TYPE=s3
FUSIONSOLAR_S3_BUCKET_NAME=${s3_bucket_name}
FUSIONSOLAR_S3_REGION=${aws_region}

# AWS Secrets Manager
USE_SECRETS_MANAGER=true
AWS_REGION=${aws_region}

# Location settings
FUSIONSOLAR_LOCATION_LATITUDE=42.6420
FUSIONSOLAR_LOCATION_LONGITUDE=24.8083
FUSIONSOLAR_LOCATION_NAME=Karlovo
FUSIONSOLAR_LOCATION_COUNTRY=Bulgaria
EOF

# Create a simple script to deploy the application
cat > deploy.sh << 'EOF'
#!/bin/bash
# Deploy script for FusionSolar Management

echo "Building and starting FusionSolar Management..."

# Check if source code is available
if [ ! -f "Dockerfile" ]; then
    echo "Error: Source code not found. Please copy your application files to $(pwd)"
    echo "Required files: Dockerfile, *.py files, requirements.txt"
    exit 1
fi

# Build and start the application
docker-compose up --build -d

# Show status
docker-compose ps

echo "Application deployed successfully!"
echo "To view logs: docker-compose logs -f"
echo "To stop: docker-compose down"
EOF

chmod +x deploy.sh

# Create systemd service for automatic startup
cat > /etc/systemd/system/fusionsolar-management.service << EOF
[Unit]
Description=FusionSolar Management Service
After=docker.service
Requires=docker.service

[Service]
Type=forking
RemainAfterExit=yes
WorkingDirectory=/opt/fusionsolar-management
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0
User=root

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
chown -R ec2-user:ec2-user /opt/fusionsolar-management

# Create README for next steps
cat > /opt/fusionsolar-management/README.md << 'EOF'
# FusionSolar Management Deployment

## Setup Instructions

1. Copy your application source code to this directory:
   ```bash
   # Copy files: *.py, Dockerfile, requirements.txt, etc.
   ```

2. Configure your environment variables:
   ```bash
   cp .env.template .env
   nano .env  # Update with your actual credentials
   ```

3. Deploy the application:
   ```bash
   ./deploy.sh
   ```

## Alternative: Use AWS Secrets Manager

Instead of using environment variables, you can store secrets in AWS Secrets Manager:

1. Create a secret named "FusionSolarSecrets" with your credentials
2. The application will automatically use these secrets

## Monitoring

- View logs: `docker-compose logs -f`
- Check status: `docker-compose ps`
- System logs: `/var/log/fusionsolar-setup.log`

## Service Management

- Start: `sudo systemctl start fusionsolar-management`
- Stop: `sudo systemctl stop fusionsolar-management`
- Enable auto-start: `sudo systemctl enable fusionsolar-management`
EOF

echo "FusionSolar Management setup completed at $(date)"
echo "Next steps:"
echo "1. Copy application source code to /opt/fusionsolar-management/"
echo "2. Configure environment variables or AWS Secrets Manager"
echo "3. Run ./deploy.sh to start the application"
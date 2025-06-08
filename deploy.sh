#!/bin/bash

# FusionSolar Management Deployment Script
# This script deploys the application to the EC2 instance

set -e  # Exit on any error

# Configuration - Use environment variables from Terraform or defaults
INSTANCE_ID="${INSTANCE_ID:-i-06828cdc5fc69824d}"
S3_BUCKET="${S3_BUCKET:-fusionsolar-management}"
APP_DIR="/home/ec2-user/fusionsolar-management"
TEMP_DIR="/tmp/fusionsolar-deployment-$(date +%s)"

echo "✅ Using instance: $INSTANCE_ID"
echo "✅ Using S3 bucket: $S3_BUCKET"

echo "🚀 Starting deployment to EC2 instance..."

# Check if AWS CLI is available
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if we can connect to the instance
echo "📡 Testing connection to EC2 instance..."
if ! aws ssm describe-instance-information --filters "Key=InstanceIds,Values=$INSTANCE_ID" --query 'InstanceInformationList[0].InstanceId' --output text &> /dev/null; then
    echo "❌ Cannot connect to instance $INSTANCE_ID. Check your AWS credentials and Session Manager permissions."
    exit 1
fi

echo "✅ Connection to EC2 instance verified"

# Create temporary directory and package the application
echo "📦 Packaging application..."
mkdir -p "$TEMP_DIR"
tar --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.serverless' \
    --exclude='terraform' \
    --exclude='lambda' \
    --exclude='.idea' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='data' \
    -czf "$TEMP_DIR/app.tar.gz" .

# Upload to S3 temporarily
S3_KEY="deployments/app-$(date +%s).tar.gz"

echo "☁️ Uploading to S3..."
aws s3 cp "$TEMP_DIR/app.tar.gz" "s3://$S3_BUCKET/$S3_KEY"

# Deploy on the instance
echo "🔄 Deploying on EC2 instance..."

# Create a temporary script file
DEPLOY_SCRIPT="$TEMP_DIR/deploy_script.sh"
cat > "$DEPLOY_SCRIPT" << EOF
#!/bin/bash
set -e
cd /home/ec2-user

# Download the new version
aws s3 cp s3://$S3_BUCKET/deployments/\$(aws s3 ls s3://$S3_BUCKET/deployments/ | sort | tail -1 | awk '{print \$4}') /tmp/app.tar.gz

# Stop the current application
if [ -d "fusionsolar-management" ]; then
    cd fusionsolar-management
    if [ -f "docker-compose.yml" ]; then
        sudo /usr/local/bin/docker-compose down || true
    fi
    cd ..
fi

# Backup current version if it exists
if [ -d "fusionsolar-management" ]; then
    sudo mv fusionsolar-management fusionsolar-management-backup-\$(date +%s)
fi

# Extract new version
mkdir -p fusionsolar-management
cd fusionsolar-management
tar -xzf /tmp/app.tar.gz
rm /tmp/app.tar.gz

# Build and start the application
echo "Building Docker image..."
sudo /usr/local/bin/docker-compose build --no-cache

echo "Starting application..."
sudo /usr/local/bin/docker-compose up -d

echo "Checking application status..."
sudo /usr/local/bin/docker-compose ps

echo "Deployment completed successfully!"
EOF

# Upload script to S3 and execute it
SCRIPT_S3_KEY="scripts/deploy-$(date +%s).sh"
aws s3 cp "$DEPLOY_SCRIPT" "s3://$S3_BUCKET/$SCRIPT_S3_KEY"

aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["aws s3 cp s3://'$S3_BUCKET'/'$SCRIPT_S3_KEY' /tmp/deploy.sh","chmod +x /tmp/deploy.sh","/tmp/deploy.sh"]' \
    --output table

echo "📋 Deployment command sent. Checking status in 30 seconds..."
sleep 30

# Check deployment status
echo "📊 Checking application status..."
STATUS_COMMANDS="cd /home/ec2-user/fusionsolar-management && sudo /usr/local/bin/docker-compose ps && sudo /usr/local/bin/docker-compose logs --tail=20"

aws ssm send-command \
    --instance-ids "$INSTANCE_ID" \
    --document-name "AWS-RunShellScript" \
    --parameters commands="$STATUS_COMMANDS" \
    --output table

# Cleanup
rm -rf "$TEMP_DIR"
echo "🧹 Cleaned up temporary files"

echo "✅ Deployment completed! Use the following command to check logs:"
echo "aws ssm start-session --target $INSTANCE_ID"
echo "Then run: cd fusionsolar-management && sudo docker-compose logs -f"

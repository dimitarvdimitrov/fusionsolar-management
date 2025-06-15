# FusionSolar Power Adjustment

This repository contains tools for managing FusionSolar power systems based on electricity price data.

## TODO

- Set up alerts to fire when a job hasn't ran in the past X hours (we need prices 6h before end of day).

## Building a Docker Image

```bash
docker build -t fusionsolar_fusionsolar:latest .
```

## Deployment

The application is designed to run as AWS Lambda functions for automated, serverless operation.

### AWS Lambda Deployment

The application consists of two Lambda functions deployed using the Serverless Framework:

1. **priceFetcher** - Fetches electricity prices for the next day (runs every hour at 30 minutes past)
2. **priceAnalyzer** - Analyzes prices and adjusts power settings (runs every hour on the hour)

#### Prerequisites

- AWS CLI configured with appropriate credentials
- Docker installed (for building container images)
- Serverless Framework: `npm install -g serverless`

#### Deployment Steps

1. **Install prerequisites:**
   ```bash
   # For macOS with Homebrew:
   brew install node
   npm install -g serverless
   
   # For Ubuntu/Debian:
   sudo apt update && sudo apt install nodejs npm
   npm install -g serverless
   ```

2. **Build and deploy the Lambda functions:**
   ```bash
   npm install
   serverless deploy
   ```

3. **The deployment will:**
   - Build a Docker container image with all dependencies (including Playwright)
   - Push the image to AWS ECR
   - Create Lambda functions using the container image
   - Set up scheduled triggers (EventBridge rules)
   - Configure IAM permissions for S3 and Secrets Manager access

#### Configuration

The Lambda functions use environment variables + AWS SecretsManager for configuration. Environment vars are in serverless.yml.

#### Testing and Management

```bash
# Test deployed functions
serverless invoke -f priceFetcher
serverless invoke -f priceAnalyzer

# View logs
serverless logs -f priceFetcher
serverless logs -f priceAnalyzer -t  # stream logs

# Deploy individual functions
serverless deploy function -f priceFetcher

# Remove all resources
serverless remove
```

#### Scheduled Execution

The Lambda functions run automatically:
- **priceFetcher**: Every hour at 30 minutes past (`cron(30 * * * ? *)`)
- **priceAnalyzer**: Every hour on the hour (`cron(0 * * * ? *)`)

#### Container-Based Deployment

The Lambda functions use container images instead of zip packages to support complex dependencies like Playwright:

- **Base Image**: Ubuntu 22.04 (for GLIBC compatibility with Playwright)
- **Dependencies**: Python 3, Playwright with Chromium, all Python packages
- **Size**: Optimized for Lambda's 10GB container limit

### Local Development

You can still run the application locally for development and testing:

#### One-time Execution

```bash
python price_analyzer.py
```

#### Continuous Operation

```bash
python scheduler.py
```

## Storage Options

The application supports multiple storage options for price data:

### Local File Storage

By default, the application stores price data on the local filesystem.

### AWS S3 Storage

You can configure the application to store price data in an AWS S3 bucket. To use S3 storage:

1. Install the required dependency: `pip install boto3`
2. Set the `FUSIONSOLAR_STORAGE_TYPE` environment variable to `s3`
3. Configure S3 credentials and bucket settings (see Environment Variables below)

### Example Usage

To see examples of using both storage options, refer to the `storage_example.py` script:

```bash
python storage_example.py
```

## Configuration

All configuration settings and secrets are centralized in the `config.py` file. You can modify the following settings:

- FusionSolar credentials
- Telegram notification settings
- Price thresholds and power limits
- File storage paths
- Timezone settings
- Storage type (local or S3)
- S3 configuration (bucket name, region, credentials)

### Environment Variables

The application also supports configuration via environment variables:

- `FUSIONSOLAR_SCREENSHOT_DIR`: Directory for storing screenshots (default: `/tmp/fusionsolar_management/screenshots`)
- `FUSIONSOLAR_PRICE_STORAGE_DIR`: Directory for storing price history (default: `/tmp/fusionsolar_management/prices`)
- `FUSIONSOLAR_STORAGE_TYPE`: Storage type to use (`local` or `s3`, default: `local`)
- `FUSIONSOLAR_S3_BUCKET_NAME`: S3 bucket name (default: `fusionsolar-management`)
- `FUSIONSOLAR_S3_REGION`: AWS region for S3 (default: `eu-central-1`)
- `FUSIONSOLAR_S3_ACCESS_KEY_ID`: AWS access key ID for S3 authentication
- `FUSIONSOLAR_S3_SECRET_ACCESS_KEY`: AWS secret access key for S3 authentication

## AWS Secrets Manager Integration

The application supports retrieving sensitive configuration values from AWS Secrets Manager. When running in AWS Lambda or any environment with proper AWS credentials, you can securely store sensitive data like passwords and API keys in Secrets Manager instead of hardcoding them or using environment variables.

### Setup

1. Ensure the application has the required permissions to access Secrets Manager. When running in Lambda, you need to add the `secretsmanager:GetSecretValue` permission to your Lambda execution role.

2. Store your secrets in AWS Secrets Manager. You can create individual secrets or a single JSON secret with multiple values:

   ```bash
   # Create a secret with individual values
   aws secretsmanager create-secret --name FUSIONSOLAR_USERNAME --secret-string "your-username"
   aws secretsmanager create-secret --name FUSIONSOLAR_PASSWORD --secret-string "your-password"

   # Or create a JSON secret with multiple values
   aws secretsmanager create-secret --name FusionSolarSecrets --secret-string '{"FUSIONSOLAR_USERNAME":"your-username","FUSIONSOLAR_PASSWORD":"your-password","TELEGRAM_BOT_TOKEN":"your-bot-token"}'
   ```

3. Configuration priority:
   - The application first checks for values in environment variables
   - If not found, it looks in AWS Secrets Manager
   - If still not found, it uses the default values specified in the code

### Available Secrets

You can store any of the following configuration values in Secrets Manager:

- `FUSIONSOLAR_USERNAME`: FusionSolar username
- `FUSIONSOLAR_PASSWORD`: FusionSolar password
- `TELEGRAM_BOT_TOKEN`: Telegram bot token for notifications
- `TELEGRAM_CHAT_ID`: Telegram chat ID for sending notifications
- `PRICE_THRESHOLD`: Price threshold for power adjustment
- `LOW_POWER_SETTING`: Power setting when price is above threshold
- `HIGH_POWER_SETTING`: Power setting when price is below threshold
- `FUSIONSOLAR_S3_ACCESS_KEY_ID`: AWS access key ID for S3
- `FUSIONSOLAR_S3_SECRET_ACCESS_KEY`: AWS secret access key for S3

### Controlling Secrets Manager Usage

- To disable Secrets Manager integration, set the environment variable `USE_SECRETS_MANAGER` to `false`
- You can specify the AWS region for Secrets Manager using the `AWS_REGION` environment variable (default: `eu-central-1`)

### Example: Lambda Environment Variables

When deploying to AWS Lambda, you might set the following environment variables:

```
USE_SECRETS_MANAGER=true
AWS_REGION=eu-central-1
```

With this configuration, the application will retrieve sensitive values from AWS Secrets Manager and fall back to environment variables or default values if needed.

## Testing

The project includes a test suite to verify functionality. Tests are located in the `tests/` directory.
The tests can be run locally without requiring AWS credentials or production configuration.

### Running Tests

To run all tests:

```bash
# Install test dependencies (if not already installed)
pip install -r requirements.txt

# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_daylight.py

# Run specific test
pytest tests/test_daylight.py::TestDaylightCalculations::test_morning_is_daylight
```

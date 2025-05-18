# FusionSolar AWS Lambda Deployment

This directory contains configuration for deploying the FusionSolar Power Adjustment system as AWS Lambda functions using the Serverless Framework.

## Overview

The system is split into two Lambda functions:

1. **Price Fetcher Lambda**: Fetches electricity prices for the next day
2. **Price Analyzer Lambda**: Analyzes prices and adjusts power settings

## Quick Start

For a quick deployment, follow these steps:

```bash
# 1. Install prerequisites (Node.js, npm, Serverless Framework)
# For macOS with Homebrew:
brew install node
npm install -g serverless

# 2. Navigate to the lambda directory and install dependencies
cd fusionsolar/lambda
npm install

# 4. deploy
serverless deploy

# Or use the npm script
npm run deploy
```

## Prerequisites

Before deploying, make sure you have:

1. **Node.js and npm** installed
   ```bash
   # For macOS with Homebrew:
   brew install node
   
   # For Ubuntu/Debian:
   sudo apt update
   sudo apt install nodejs npm
   ```

2. **Serverless Framework** installed globally:
   ```bash
   npm install -g serverless
   # Verify installation
   serverless --version
   ```

3. **AWS CLI** installed and configured with appropriate credentials
   ```bash
   # Configure AWS credentials if not already done
   aws configure
   ```

4. **Python 3.9** or later
   ```bash
   # Check version
   python --version
   ```

## Project Setup

```bash
# Navigate to the lambda directory
cd fusionsolar/lambda

# Install dependencies
npm install

# Install required Serverless plugins
npm install --save-dev serverless-python-requirements
```

## Configuration

The Lambda functions use environment variables for configuration. You can set these in several ways:

1. Using a `.env` file (recommended for local development):
   ```
   FUSIONSOLAR_USERNAME=your_actual_username
   FUSIONSOLAR_PASSWORD=your_actual_password
   TELEGRAM_BOT_TOKEN=your_actual_token
   TELEGRAM_CHAT_ID=your_actual_chat_id
   ```

2. In the `serverless.yml` file directly (not recommended for secrets)
3. Using environment variables when deploying
4. Using AWS Parameter Store or Secrets Manager for sensitive values

Required configuration variables:

- `FUSIONSOLAR_USERNAME`: Your FusionSolar username
- `FUSIONSOLAR_PASSWORD`: Your FusionSolar password
- `PRICE_THRESHOLD`: Price threshold in EUR/MWh (default: 15.04)
- `LOW_POWER_SETTING`: Power limit when prices are high (default: "5.000")
- `HIGH_POWER_SETTING`: Power limit when prices are low (default: "no limit")
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID
- `FUSIONSOLAR_STORAGE_TYPE`: Storage type ("local" or "s3")

If using S3 storage:
- `FUSIONSOLAR_S3_BUCKET_NAME`: S3 bucket name
- `FUSIONSOLAR_S3_REGION`: S3 region
- `FUSIONSOLAR_S3_ACCESS_KEY_ID`: S3 access key
- `FUSIONSOLAR_S3_SECRET_ACCESS_KEY`: S3 secret key

## Deployment

### Deploying with Serverless Framework

Deploy to AWS:

```bash
# Deploy to the default region (eu-central-1)
serverless deploy
# Or use the npm script
npm run deploy

# Or deploy to a specific region
serverless deploy --region eu-west-1
```

Alternatively, you can set environment variables directly:

```bash
# Set environment variables for sensitive configuration
export FUSIONSOLAR_USERNAME="your-username"
export FUSIONSOLAR_PASSWORD="your-password"
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Deploy
serverless deploy
```

### Deploying Individual Functions

You can deploy a single function if you need to update just one part:

```bash
# Deploy only the price fetcher
serverless deploy function -f priceFetcher

# Deploy only the price analyzer
serverless deploy function -f priceAnalyzer
```

## Testing

### Invoking Functions

You can test your Lambda functions:

```bash
# Invoke the deployed functions
serverless invoke -f priceFetcher
serverless invoke -f priceAnalyzer

# Test locally before deploying
serverless invoke local -f priceFetcher
serverless invoke local -f priceAnalyzer
```

### Viewing Logs

You can use the Serverless Framework to view logs from your Lambda functions:

```bash
# View logs for the price fetcher
serverless logs -f priceFetcher

# View logs for the price analyzer
serverless logs -f priceAnalyzer

# Stream logs in real-time
serverless logs -f priceFetcher -t
```

## Removing the Deployment

To remove all deployed resources:

```bash
serverless remove
# Or
npm run remove
```

## Scheduled Execution

The Lambda functions are scheduled to run:

- **Price Fetcher**: Every hour at 30 minutes past the hour (`cron(30 * * * ? *)`)
- **Price Analyzer**: Every hour on the hour (`cron(0 * * * ? *)`)

## Troubleshooting

Common issues:

1. **Missing dependencies**: Make sure you've installed the serverless-python-requirements plugin

2. **Missing AWS credentials**: Make sure you have AWS credentials configured. Run `aws configure` to set them up.

3. **Permissions issues**: Verify your AWS credentials have appropriate IAM permissions

4. **Region issues**: If you need to deploy to a specific region, use `--region`:
   ```bash
   serverless deploy --region eu-west-1
   ```

5. **Python version**: Ensure you're using Python 3.9 or later. Check with `python --version`.

6. **Environment variables**: Check that all required environment variables are set. If they aren't being loaded, try setting them directly:
   ```bash
   FUSIONSOLAR_USERNAME=your_username serverless deploy
   ```

7. **Package size**: If your deployment package is too large, try enabling `dockerizePip: true` in the serverless.yml configuration 

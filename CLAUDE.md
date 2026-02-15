# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FusionSolar Power Adjustment system that automatically adjusts Huawei FusionSolar inverter power limits based on Bulgarian electricity prices from IBEX. Runs as AWS Lambda functions deployed via Serverless Framework.

## Common Commands

```bash
# Run tests
pytest
pytest -v                                    # verbose
pytest tests/test_daylight.py               # single file
pytest tests/test_daylight.py::TestClass::test_method  # single test

# Deploy to AWS
npm install                                  # install serverless deps
serverless deploy                            # full deploy (builds Docker image)
serverless deploy function -f priceFetcher  # deploy single function
serverless deploy function -f priceAnalyzer

# Test deployed functions
serverless invoke -f priceFetcher
serverless invoke -f priceAnalyzer

# View logs
serverless logs -f priceFetcher
serverless logs -f priceAnalyzer -t         # stream logs

# Local development
python scheduler.py                          # run scheduler locally (continuous)
python price_analyzer.py                     # one-time price analysis
```

## Architecture

**Two Lambda Functions:**
- `priceFetcher` - Fetches next-day electricity prices from IBEX (runs hourly at :30)
- `priceAnalyzer` - Analyzes prices and adjusts inverter power via browser automation (runs every 15 min)

**Core Flow:**
1. `PriceRepository` fetches prices from `ibex.bg` API, stores as JSON
2. `price_analyzer` determines if current price exceeds threshold
3. `SetPower` uses Playwright to log into FusionSolar web UI and adjust power limits
4. `TelegramNotifier` sends status updates

**Key Components:**
- `config.py` - Centralized config; pulls from env vars → AWS Secrets Manager → defaults
- `storage_interface.py` - Abstract storage with `LocalFileStorage` and `S3Storage` implementations
- `price_repository.py` - Price data fetching/caching from IBEX API
- `set_power.py` - Playwright browser automation for FusionSolar UI
- `scheduler.py` - Local scheduler using `schedule` library; also used by Lambda handlers

**Storage:**
- Prices stored at `prices/parsed/ibex.bg-{date}.json` and `prices/raw/ibex.bg-{date}.raw.json`
- Screenshots stored at `screenshots/session_{timestamp}/`
- Uses S3 in Lambda, local filesystem for development

## Deployment

Uses container-based Lambda deployment (not zip packages) because Playwright requires specific system dependencies.

**How it works:**
- `Dockerfile.lambda` builds Ubuntu 22.04 image with Python, Playwright, and Chromium
- `serverless.yml` configures ECR image build and Lambda functions
- `serverless deploy` builds the Docker image, pushes to ECR, and updates Lambda

**Key files:**
- `serverless.yml` - Lambda config, IAM permissions, scheduled triggers, env vars
- `Dockerfile.lambda` - Container image definition

**Secrets:** Stored in AWS Secrets Manager under `FusionSolarSecrets` (JSON with multiple keys). Lambda has IAM permissions to read secrets.

## Configuration

Environment variables (see `config.py` for full list):
- `FUSIONSOLAR_USERNAME/PASSWORD` - FusionSolar credentials
- `TELEGRAM_BOT_TOKEN/CHAT_ID` - Notification settings
- `PRICE_THRESHOLD` - EUR/MWh threshold (default: 15.04)
- `LOW_POWER_SETTING` / `HIGH_POWER_SETTING` - Power limits
- `FUSIONSOLAR_STORAGE_TYPE` - `local` or `s3`
- `USE_SECRETS_MANAGER` - Enable AWS Secrets Manager integration

## Testing

Tests use fixtures in `tests/conftest.py` that mock required environment variables. No AWS credentials needed for local tests.

Testing the FusionSolar browser automation (`set_power.py`) requires running against the real FusionSolar portal - there's no staging environment.

## Notes

- **Power settings naming**: LOW = low price = low output (limited kW). HIGH = high price = no limit (full output). The system limits power when electricity is cheap (to sell less at low prices).
- **Telegram notifications**: Write in Bulgarian, following the existing message patterns in `scheduler.py` and `telegram_notifier.py`.

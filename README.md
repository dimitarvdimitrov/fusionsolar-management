# FusionSolar Power Adjustment

This repository contains tools for managing FusionSolar power systems based on electricity price data.

## TODO

- Only post when the power actually changes; do not change the power if the current value is the same (change in the set_power.py)
- Do not overwrite the price list if it is already stored. Check if what we fetched is something we already have on disk.
- Set up alerts to fire when a job hasn't ran in the past X hours (we need prices 6h before end of day).
- Fix the docker-compose ansible setup so it builds the container and starts it.

## Building a Docker Image

```bash
docker build -t fusionsolar_fusionsolar:latest .
```

## Running the Application

You can run the application in two different modes:

### One-time Execution

To run the price analyzer once and exit:

```bash
python price_analyzer.py
```

This will:
1. Fetch current electricity prices
2. Analyze the price data
3. Adjust FusionSolar power settings based on price thresholds
4. Exit after completion

### Continuous Operation

To run the application continuously with scheduled tasks:

```bash
python scheduler.py
```

This mode:
1. Keeps the application running in the background
2. Automatically fetches price data at scheduled intervals
3. Applies power adjustments based on the configuration settings
4. Continues running until manually stopped

The scheduler ensures that price data is fetched regularly and power adjustments are made according to your configured price thresholds.

## Configuration

All configuration settings and secrets are centralized in the `config.py` file. You can modify the following settings:

- FusionSolar credentials
- Telegram notification settings
- Price thresholds and power limits
- File storage paths
- Timezone settings

### Environment Variables

The application also supports configuration via environment variables:

- `FUSIONSOLAR_SCREENSHOT_DIR`: Directory for storing screenshots (default: `/tmp/fusionsolar_management/screenshots`)
- `FUSIONSOLAR_PRICE_STORAGE_DIR`: Directory for storing price history (default: `/tmp/fusionsolar_management/prices`)

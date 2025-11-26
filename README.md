# SweMPer Data Dashboard

A web-based dashboard for visualizing and analyzing the SweMPer dataset.

## Features
- **Timeline Visualization:** View data distribution over time.
- **Journal Analysis:** Detailed breakdown of image and text coverage per journal.
- **OCR Candidate Reporting:** Identify missing text coverage and generate reports.

## Setup

1.  **Install Dependencies:**
    ```bash
    pip install flask markdown
    ```

2.  **Configuration:**
    The application uses a `config.json` file for settings. A default file will be created if it doesn't exist, but you can create one manually:
    ```json
    {
      "server": {
        "host": "0.0.0.0",
        "port": 9093,
        "debug": false
      },
      "paths": {
        "temp_dir": "./tmp"
      }
    }
    ```

3.  **Run the Application:**
    ```bash
    # Scan a directory
    python dataset_webapp.py --root-dir /path/to/dataset

    # Load from a saved state
    python dataset_webapp.py --load-state data.json
    ```

## Usage
- **Dashboard:** Overview of all journals and timeline.
- **Reports:** Generate CSV reports for missing years and pages.

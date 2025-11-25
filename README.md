# SweMPer Dataset Dashboard

The **SweMPer Dataset Dashboard** is a Flask-based consistency auditing tool developed for the **[Communicating Medicine: Digitalisation of Swedish Medical Periodicals 1781–2011 (SweMPer)](https://www.rj.se/en/grants/2022/communicating-medicine-digitalisation-of-swedish-medical-periodicals-17812011-swemper/)** project.

This application scans large-scale digitized journal archives to cross-reference source images against derivative files (OCR text, XML, AltoXML, and Metadata). It provides a visual interface to identify missing data, generate consistency metrics, and create "to-do" lists for the OCR and metadata pipelines.

## ✨ Key Features

- **Consistency Auditing:** Recursively checks journal directories to ensure every source image (JPG) has corresponding derivative files (AVIF, Text, XML, Metadata).
- **Visual Dashboard:**
    - **Activity Rings:** Visualizes data completeness for specific profiles (e.g., Tesseract vs. RA-OCR).
    - **Dataset Timeline:** A heat-map style visualization of the entire dataset.
        - **Multi-Year View:** See coverage across all journals and years simultaneously.
        - **Drag-to-Calculate:** Click and drag across the timeline header to calculate total page counts for specific periods (e.g., "How many pages between 1850-1900?").
        - **Gap Analysis:** Color-coded stripes within year cells reveal specific missing file types.
    - **Growth Charts:** Displays dataset size and image counts per journal and year.
    - **Profile Filtering:** Toggle specific file types to isolate issues (e.g., hide "AVIF" to focus solely on "XML" gaps).
- **Drill-Down Navigation:**
    - **Journal View:** Detailed breakdown of coverage by year.
    - **Year View:** Exact lists of missing files for granular debugging.
- **OCR Reporting:** Automatically generates downloadable CSV reports identifying years with zero text coverage or specific pages missing OCR.
- **State Management:** Save and load scan results to JSON to avoid re-scanning the multi-terabyte dataset on every restart.
- **Changelog Integration:** Renders the project's `CHANGELOG.md` directly in the UI.

## 🛠 Prerequisites

- **Python 3.8+**
- **Internet Connection:** The dashboard uses CDN links for Tailwind CSS and Chart.js.

## 📦 Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    The application requires `flask` and `markdown`.

    ```bash
    pip install flask markdown
    ```
## Deploying

```bash
git clone https://github.com/CDHUppsala/swemper-data-dashboard.git
cd swemper-data-dashboard
docker compose up -d
```

Make sure that the `data.json` exists inside the folder `data` as well, and is named exactly as `data.json`.
The default port for the container is 3000. Edit the `docker-compose.yml`, and change the port mapping if you want a differnt port.
## 📂 Expected Data Structure

The application is configured to scan the specific SweMPer directory structure defined in `dataset_webapp.py`. It expects a **Root Directory** containing **Journal folders**, which then contain specific sub-directories for each file profile.

**Structure Layout:**

```text
Root_Directory/
├── Journal_Name/
│   ├── images/
│   │   ├── jpg/           <-- Source of Truth (e.g., 1890/page1.jpg)
│   │   └── avif/          <-- Compressed images
│   ├── texts/
│   │   ├── tesseract-v1/  <-- OCR output (Tesseract)
│   │   └── ra-ocr/        <-- OCR output (Recogito/Other)
│   ├── xml/               <-- Standard XML
│   ├── altoxml/           <-- ALTO XML
│   └── metadata/
│       ├── v1/            <-- Schema V1
│       └── v2/            <-- Schema V2
└── ...
```

_Note: The scanner expects Year folders (e.g., `1890`, `1891-1892`) inside the specific profile folders (e.g., inside `images/jpg/`)_.

## 🚀 Usage

The application is run via the command line. You must provide either a directory to scan or a saved state file.

### 1\\. Perform a New Scan

Scan the raw dataset directory. This may take time depending on the archive size.

```bash
python dataset_webapp.py --root-dir /path/to/swemper/data
```

### 2\\. Scan and Save State (Recommended)

Scan the directory and save the results to a JSON file. This allows you to reload the dashboard instantly later without re-scanning.

```bash
python dataset_webapp.py --root-dir /path/to/swemper/data --save-state swemper_scan_2024.json
```

### 3\\. Load from Saved State

Load a previously generated scan file.

```bash
python dataset_webapp.py --load-state swemper_scan_2024.json
```

### Accessing the Dashboard

Once the server is running, open your web browser and navigate to:
**`http://localhost:9092`**

## ⚙️ Configuration

The file profiles are defined in the `PROFILES` dictionary within `dataset_webapp.py`. You can modify this dictionary to match your specific folder structure or file extensions.

### Modifying `PROFILES`

Locate the `PROFILES` dictionary in the source code:

```python
# dataset_webapp.py

PROFILES = {
    'images': {'path_parts': ('images', 'jpg'), 'extension': '.jpg'},
    'avif': {'path_parts': ('images', 'avif'), 'extension': '.avif'},
    'texts-tesseract-v1': {'path_parts': ('texts', 'tesseract-v1',), 'extension': '.txt'},
    # ...
}
```

To add a new data type (e.g., a new OCR version), add a new key-value pair:

1.  **Key Name:** The internal name for the profile (e.g., `'texts-new-ocr'`).
2.  **`path_parts`:** A tuple representing the folder path relative to the **Journal** folder.
    - _Example:_ If your files are in `Journal/ocr/v3/`, the tuple is `('ocr', 'v3')`.
3.  **`extension`:** The file suffix to look for (e.g., `.xml`, `.txt`, `.json`).

**Important Note:** The scanner uses the `'images'` profile as the "Source of Truth." It finds all `.jpg` files in the `images/jpg` folder first, and then checks if corresponding files exist in all other defined profiles.

## 📊 Generating Reports

The tool includes a reporting engine to assist with workflow management:

1.  Go to the **Reports** tab.
2.  Click **"Generate OCR Candidate Report"**.
3.  The system calculates gaps and offers two CSV downloads:
    - **Missing Years CSV:** Lists journal years that have zero text coverage.
    - **Missing Pages CSV:** Lists specific pages that are missing text files within otherwise complete years.

## 📄 License

This project is part of the SweMPer research initiative funded by Riksbankens Jubileumsfond (Grant 17812011).

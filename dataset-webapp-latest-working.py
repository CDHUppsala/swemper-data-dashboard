import os
import re
import json
import argparse
import io
import csv
import uuid
from pathlib import Path
from typing import Set, Optional
from datetime import datetime

from flask import Flask, render_template, url_for, g, redirect, session, make_response
from markdown import markdown

# --- Configuration for Different Data Types ---
PROFILES = {
    'images': {'path_parts': ('images', 'jpg'), 'extension': '.jpg'},
    'texts-tesseract-v1': {'path_parts': ('texts', 'tesseract-v1',), 'extension': '.txt'},
    'texts-ra-ocr': {'path_parts': ('texts', 'ra-ocr',), 'extension': '.txt'},
    'xml': {'path_parts': ('xml',), 'extension': '.xml'},
    'altoxml': {'path_parts': ('altoxml',), 'extension': '.alto.xml'},
    'metadata-v1': {'path_parts': ('metadata', 'v1'), 'extension': '.yaml'}
}

# --- Flask App Initialization ---
app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for session management
# Global variables to manage state
SCAN_RESULTS = None
ROOT_DIR = None
SAVE_STATE_PATH = None
TEMP_DIR = Path('./tmp')  # For temporary report files

# --- Helper Functions ---


def parse_year_string(year_str: str) -> bool:
    match = re.match(r'^(\d{4})(?:-(\d{4}))?$', year_str)
    if not match:
        return False
    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else start
    return start <= end

# --- Core Scanning Logic (Rewritten) ---


def scan_all_journals(root_dir: Path):
    print("--- Starting Full Scan ---")
    results = {}

    source_profile = PROFILES['images']
    text_profiles = {name: conf for name,
                     conf in PROFILES.items() if conf['path_parts'][0] == 'texts'}
    standard_profiles = {name: conf for name, conf in PROFILES.items(
    ) if name != 'images' and name not in text_profiles}

    for journal_dir in sorted(root_dir.iterdir()):
        if not journal_dir.is_dir():
            continue

        images_root_dir = journal_dir / Path(*source_profile['path_parts'])
        if not images_root_dir.is_dir():
            continue

        print(f"Scanning Journal: {journal_dir.name}...")
        journal_name = journal_dir.name
        journal_data = {
            "summary": {"total_images": 0},
            "years": {}
        }
        # Initialize summaries dynamically
        journal_data["summary"]["profile_counts"] = {
            name: 0 for name in standard_profiles.keys()}
        journal_data["summary"]["profile_counts"]["texts_group"] = {
            "missing_coverage": 0, "edition_counts": {name: 0 for name in text_profiles.keys()}
        }

        for year_dir in sorted(images_root_dir.iterdir()):
            if not year_dir.is_dir() or not parse_year_string(year_dir.name):
                continue

            year_str = year_dir.name

            image_files = [f for f in year_dir.iterdir() if f.is_file(
            ) and f.name.lower().endswith(source_profile['extension'])]
            if not image_files:
                continue

            num_images = len(image_files)
            year_data = {"summary": {"images": num_images}}
            year_data["summary"]["profile_counts"] = {
                name: 0 for name in standard_profiles.keys()}
            year_data["summary"]["profile_counts"]["texts_group"] = {
                "missing_coverage": 0, "edition_counts": {name: 0 for name in text_profiles.keys()}
            }

            for image_path in image_files:
                basename = image_path.name.split('.', 1)[0]

                # Check standard profiles
                for name, config in standard_profiles.items():
                    target_file = journal_dir.joinpath(
                        *config['path_parts'], year_str, f"{basename}{config['extension']}")
                    if not target_file.exists():
                        year_data["summary"]["profile_counts"][name] += 1

                # Check text profiles for coverage
                has_text_coverage = False
                for name, config in text_profiles.items():
                    target_file = journal_dir.joinpath(
                        *config['path_parts'], year_str, f"{basename}{config['extension']}")
                    if target_file.exists():
                        has_text_coverage = True
                        year_data["summary"]["profile_counts"]["texts_group"]["edition_counts"][name] += 1

                if not has_text_coverage:
                    year_data["summary"]["profile_counts"]["texts_group"]["missing_coverage"] += 1

            # Aggregate year data into journal summary
            journal_data["summary"]["total_images"] += num_images
            for name in standard_profiles.keys():
                journal_data["summary"]["profile_counts"][name] += year_data["summary"]["profile_counts"][name]

            journal_data["summary"]["profile_counts"]["texts_group"]["missing_coverage"] += year_data["summary"]["profile_counts"]["texts_group"]["missing_coverage"]
            for name in text_profiles.keys():
                journal_data["summary"]["profile_counts"]["texts_group"]["edition_counts"][
                    name] += year_data["summary"]["profile_counts"]["texts_group"]["edition_counts"][name]

            journal_data["years"][year_str] = year_data

        results[journal_name] = journal_data

    print("--- Scan Complete ---")
    return {
        "metadata": {"root_dir": str(root_dir), "scan_time": datetime.utcnow().isoformat()},
        "results": results
    }

# --- Flask Routes ---


@app.route('/')
def index():
    if SCAN_RESULTS:
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.route('/scan')
def scan():
    global SCAN_RESULTS
    if ROOT_DIR:
        SCAN_RESULTS = scan_all_journals(ROOT_DIR)
        if SAVE_STATE_PATH:
            try:
                with open(SAVE_STATE_PATH, 'w', encoding='utf-8') as f:
                    json.dump(SCAN_RESULTS, f, indent=2)
                print(f"✅ State successfully saved to {SAVE_STATE_PATH}")
            except Exception as e:
                print(f"❌ ERROR: Could not save state file. Reason: {e}")
    return redirect(url_for('dashboard'))


@app.route('/dashboard')
def dashboard():
    if SCAN_RESULTS is None:
        return redirect(url_for('index'))

    standard_profiles = {name for name, conf in PROFILES.items(
    ) if name != 'images' and conf['path_parts'][0] != 'texts'}
    has_texts = any(conf['path_parts'][0] == 'texts' for conf in PROFILES.values())

    filter_profiles = sorted(list(standard_profiles))
    if has_texts:
        filter_profiles.insert(0, "Texts")

    return render_template('dashboard.html', data=SCAN_RESULTS, filter_profiles=filter_profiles)


@app.route('/journal/<journal_name>')
def journal_detail(journal_name):
    if SCAN_RESULTS is None or journal_name not in SCAN_RESULTS.get('results', {}):
        return "Journal not found or scan not performed.", 404

    journal_data = SCAN_RESULTS['results'][journal_name]
    standard_profiles = {name for name, conf in PROFILES.items(
    ) if name != 'images' and conf['path_parts'][0] != 'texts'}
    has_texts = any(conf['path_parts'][0] == 'texts' for conf in PROFILES.values())
    filter_profiles = sorted(list(standard_profiles))
    if has_texts:
        filter_profiles.insert(0, "Texts")

    return render_template('journal.html', journal_name=journal_name, data=journal_data, filter_profiles=filter_profiles)


@app.route('/journal/<journal_name>/<year_str>')
def year_detail(journal_name, year_str):
    if SCAN_RESULTS is None or journal_name not in SCAN_RESULTS.get('results', {}) or year_str not in SCAN_RESULTS['results'][journal_name]['years']:
        return "Year not found or scan not performed.", 404

    current_root_dir = Path(SCAN_RESULTS['metadata']['root_dir'])
    journal_dir = current_root_dir / journal_name
    source_profile = PROFILES['images']

    image_dir = journal_dir / Path(*source_profile['path_parts']) / year_str
    image_files = [f for f in image_dir.iterdir() if f.is_file(
    ) and f.name.lower().endswith(source_profile['extension'])]

    missing_files_by_profile = {}
    for name, config in PROFILES.items():
        if name == 'images':
            continue
        missing_files = []
        for image_path in image_files:
            basename = image_path.name.split('.', 1)[0]
            target_file = journal_dir.joinpath(
                *config['path_parts'], year_str, f"{basename}{config['extension']}")
            if not target_file.exists():
                missing_files.append(target_file.name)

        if missing_files:
            missing_files_by_profile[name] = sorted(missing_files)

    return render_template('year.html', journal_name=journal_name, year_str=year_str, missing_files=missing_files_by_profile)


@app.route('/changelog')
def changelog():
    changelog_content = "<h2>Changelog Not Found</h2><p>Could not find CHANGELOG.md.</p>"
    current_root_dir = Path(SCAN_RESULTS.get('metadata', {}).get(
        'root_dir')) if SCAN_RESULTS else ROOT_DIR
    if current_root_dir:
        changelog_path = current_root_dir / "CHANGELOG.md"
        if changelog_path.is_file():
            try:
                with open(changelog_path, 'r', encoding='utf-8') as f:
                    markdown_text = f.read()
                markdown_text = re.sub(r'==(.+?)==', r'<mark>\1</mark>', markdown_text)
                markdown_text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', markdown_text)
                changelog_content = markdown(markdown_text, extensions=['extra'])
            except Exception as e:
                changelog_content = f"<h2>Error Reading Changelog</h2><p>An error occurred: {e}</p>"
    return render_template('changelog.html', changelog_content=changelog_content)

# --- Routes for OCR Candidate Reporting ---


@app.route('/reports')
def reports():
    if SCAN_RESULTS is None:
        return redirect(url_for('index'))
    return render_template('reports.html')


@app.route('/reports/generate-ocr-candidates')
def generate_ocr_candidates():
    if SCAN_RESULTS is None:
        return redirect(url_for('index'))

    print("--- Generating OCR Candidate Report ---")
    missing_years, incomplete_years = [], []
    text_profiles = {name: conf for name,
                     conf in PROFILES.items() if conf['path_parts'][0] == 'texts'}

    for journal_name, journal_data in SCAN_RESULTS['results'].items():
        for year_str, year_data in journal_data['years'].items():
            text_group = year_data['summary']['profile_counts'].get('texts_group', {})
            edition_counts = text_group.get('edition_counts', {})
            total_texts_in_year = sum(edition_counts.values())

            if total_texts_in_year == 0 and year_data['summary']['images'] > 0:
                missing_years.append(
                    {'journal_name': journal_name, 'year_dir': year_str})
            elif text_group.get('missing_coverage', 0) > 0:
                incomplete_years.append(
                    {'journal_name': journal_name, 'year_dir': year_str})

    missing_pages = []
    current_root_dir = Path(SCAN_RESULTS['metadata']['root_dir'])
    for item in incomplete_years:
        journal_name, year_str = item['journal_name'], item['year_dir']
        journal_dir = current_root_dir / journal_name

        image_dir = journal_dir / Path(*PROFILES['images']['path_parts']) / year_str
        image_files = [f for f in image_dir.iterdir() if f.is_file(
        ) and f.name.lower().endswith(PROFILES['images']['extension'])]

        for image_path in image_files:
            basename = image_path.name.split('.', 1)[0]
            is_covered = False
            for name, config in text_profiles.items():
                target_file = journal_dir.joinpath(
                    *config['path_parts'], year_str, f"{basename}{config['extension']}")
                if target_file.exists():
                    is_covered = True
                    break
            if not is_covered:
                missing_pages.append({
                    'journal_name': journal_name,
                    'year_dir': year_str,
                    'missing_text_for_image_file': image_path.name
                })

    report_id = str(uuid.uuid4())
    TEMP_DIR.mkdir(exist_ok=True)
    with open(TEMP_DIR / f"{report_id}_years.json", 'w') as f:
        json.dump(missing_years, f)
    with open(TEMP_DIR / f"{report_id}_pages.json", 'w') as f:
        json.dump(missing_pages, f)
    session['report_id'] = report_id

    return render_template('ocr_candidates_report.html', missing_years=missing_years, missing_pages=missing_pages)


@app.route('/download/missing_years_csv')
def download_missing_years_csv():
    report_id = session.get('report_id')
    if not report_id:
        return "No report ID found in session.", 404
    try:
        with open(TEMP_DIR / f"{report_id}_years.json", 'r') as f:
            report_data = json.load(f)
    except FileNotFoundError:
        return "Report data not found on server.", 404
    if not report_data:
        return "No data to export.", 200

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=report_data[0].keys())
    writer.writeheader()
    writer.writerows(report_data)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=ocr_candidates_missing_years.csv"
    response.headers["Content-type"] = "text/csv"
    return response

###

@app.route('/download/missing_pages_csv')
def download_missing_pages_csv():
    report_id = session.get('report_id')
    if not report_id:
        return "No report ID found in session.", 404
    try:
        with open(TEMP_DIR / f"{report_id}_pages.json", 'r') as f:
            report_data = json.load(f)
    except FileNotFoundError:
        return "Report data not found on server.", 404
    if not report_data:
        return "No data to export.", 200

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=report_data[0].keys())
    writer.writeheader()
    writer.writerows(report_data)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=ocr_candidates_missing_pages.csv"
    response.headers["Content-type"] = "text/csv"
    return response


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Web app to check for dataset consistency.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--root-dir", help="The root directory containing all journal folders to scan.")
    group.add_argument(
        "--load-state", help="Load a previously saved scan state from a JSON file.")
    parser.add_argument(
        "--save-state", help="[Scan Mode] After scanning, save the results to this JSON file.")
    args = parser.parse_args()

    if args.load_state:
        try:
            with open(args.load_state, 'r', encoding='utf-8') as f:
                SCAN_RESULTS = json.load(f)
            ROOT_DIR = Path(SCAN_RESULTS['metadata']['root_dir'])
            print(
                f"✅ State successfully loaded from '{args.load_state}'. View at http://127.0.0.1:9092")
        except Exception as e:
            print(f"❌ ERROR: Could not load or parse state file. Reason: {e}")
            exit(1)
    else:
        ROOT_DIR = Path(args.root_dir)
        if not ROOT_DIR.is_dir():
            print(f"❌ ERROR: Directory not found at '{ROOT_DIR}'")
            exit(1)
        if args.save_state:
            SAVE_STATE_PATH = args.save_state
        print(
            f"✅ Server started. Open http://127.0.0.1:9092 to begin scanning '{ROOT_DIR.name}'.")

    TEMP_DIR.mkdir(exist_ok=True)
    app.run(host='0.0.0.0', port=9092, debug=False)

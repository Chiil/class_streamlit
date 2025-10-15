import tomllib
import urllib.parse
import webbrowser
import base64
import json
import gzip


# Settings what and where to send.
base_url = "http://localhost:8501" # Server-side (default)
# base_url = "http://localhost:8000/class_streamlit.html" # Client-side (pyiodide)
# base_url = "https://chiil.github.io/class_streamlit/index.html" # Client-side (pyiodide)


# Load settings from .toml files.
run_list = [
    ("Martorell (simplified)", "martorell_simplified"),
]

runs = []
for name, file_name in run_list:
    with open(f"{file_name}.toml", "rb") as f:
        run = tomllib.load(f)
    run["name"] = name
    run["starttime"] = str(run["starttime"])
    run["startdate"] = str(run["startdate"])

    runs.append(run)


# Merge data into JSON
all_data = {
    "settings": runs,
}

all_data_json = json.dumps(all_data, separators=(',', ':'))
all_data_compressed = gzip.compress(all_data_json.encode('utf-8'))


# Encode the URL and launch the browser.
case_url_params = base64.urlsafe_b64encode(all_data_compressed).decode('ascii')
case_url = f"{base_url}?c={case_url_params}"

print(f"Opening URL (length = {len(case_url)}): {case_url}")
webbrowser.open(case_url)

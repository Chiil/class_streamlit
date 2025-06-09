import tomllib
import urllib.parse
import webbrowser
import base64
import json
import gzip
import pandas as pd


# Settings what and where to send.
case_name = "Cabauw"
base_url = "http://localhost:8501" # Server-side (default)
# base_url = "http://localhost:8000/class_streamlit.html" # Client-side (pyiodide)
# base_url = "https://chiil.github.io/class_streamlit/index.html" # Client-side (pyiodide)


# Load settings
with open(f"{case_name.lower()}_settings.toml", "rb") as f:
    case_settings = tomllib.load(f)
case_settings["name"] = case_name
case_settings["starttime"] = str(case_settings["starttime"])
case_settings["startdate"] = str(case_settings["startdate"])


# Load sounding
case_sounding_1 = pd.read_csv("cabauw_sounding_1.csv").to_dict(orient="list") # use the list to remove the index.
for key, series in case_sounding_1.items():
    case_sounding_1[key] = [ round(value, 3) for value in series ]

case_sounding_1["name"] = "Cabauw [13.08.21 07h]"

case_sounding_2 = pd.read_csv("cabauw_sounding_2.csv").to_dict(orient="list") # use the list to remove the index.
for key, series in case_sounding_2.items():
    case_sounding_2[key] = [ round(value, 3) for value in series ]

case_sounding_2["name"] = "Cabauw [13.08.21 10h]"


# Merge data into JSON
all_data = {
    "settings": case_settings,
    "soundings": [ case_sounding_1, case_sounding_2 ],
}

all_data_json = json.dumps(all_data, separators=(',', ':'))
all_data_compressed = gzip.compress(all_data_json.encode('utf-8'))


# Encode the URL and launch the browser.
case_url_params = base64.urlsafe_b64encode(all_data_compressed).decode('ascii')
case_url = f"{base_url}?c={case_url_params}"

print(f"Opening URL (length = {len(case_url)}): {case_url}")
webbrowser.open(case_url)

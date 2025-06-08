import tomllib
import urllib.parse
import webbrowser
import base64
import json
import zlib
import pandas as pd


# Settings what and where to send.
case_name = "Cabauw"
sounding_name = "cabauw_sounding"
base_url = "http://localhost:8501"
use_compression = False


# Load settings
with open(f"{case_name.lower()}_settings.toml", "rb") as f:
    case_settings = tomllib.load(f)
case_settings["name"] = case_name


# Load sounding
case_sounding = pd.read_csv("cabauw_sounding.csv").to_dict(orient="list") # use the list to remove the index.
case_sounding["name"] = sounding_name


# Merge data into JSON
all_data = {
    "settings": case_settings,
    "sounding": case_sounding,
}

if use_compression:
    all_data_json = json.dumps(all_data)
    compressed_params = base64.urlsafe_b64encode(all_data_json.encode()).decode()
    case_url = f"{base_url}?c={compressed_params}"
else:
    case_url_params = urllib.parse.urlencode(all_data)
    case_url = f"{base_url}?{case_url_params}"

print(f"Opening URL: {case_url}")
webbrowser.open(case_url)

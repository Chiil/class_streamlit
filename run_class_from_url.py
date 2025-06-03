import tomllib
import urllib.parse
import webbrowser


case_name = "Cabauw"
base_url = "http://localhost:8501"


# Load the default settings from disk and override with URL settings.
with open(f"{case_name.lower()}_settings.toml", "rb") as f:
    case_settings = tomllib.load(f)

case_settings["run_name"] = case_name

case_url_params = urllib.parse.urlencode(case_settings)
case_url = f"{base_url}?{case_url_params}"

print(f"Opening URL: {case_url}")
webbrowser.open(case_url)

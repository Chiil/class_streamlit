This code runs server-side (default) with:

`python -m streamlit run class_streamlit.py`

or if you prefer to test the (experimental) Stlite Pyodide client-side version:

`python -m http.server 8000`

Once the code is running and the Streamlit server is active, you can send a case via URL.

First, example input data needs to be generated:

`python make_example_sounding.py`

Then, the case can be launched using:

`python run_class_from_url.py`

Make sure to set the address to the correct destination depending on whether you
use the server-side or client-side version.

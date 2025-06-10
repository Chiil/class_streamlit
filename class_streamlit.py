import streamlit as st
from streamlit import session_state as ss
from class_streamlit_defs import *
import tomllib
import datetime
import plotly.express as px
import plotly.graph_objects as go
import plotly.io
import base64
import json
import gzip


# Ensure that plots fill the whole page, must be first call to streamlit.
st.set_page_config(
    layout="wide",
    page_title="CLASS",
    page_icon=":material/partly_cloudy_day:",
)


# Set the variables to handle the plotting properly.
streamlit_template = plotly.io.templates["streamlit"]
color_cycle = streamlit_template.layout.colorway
plot_font_size = st.get_option("theme.baseFontSize")
n_maxruns = 128


# Define all callback functions.
def process_selected_run():
    ss.all_runs_key = ss.selected_run


def process_clone_run():
    cloned_run = ss.all_runs_key + " (clone)"
    if cloned_run in ss.all_runs:
        st.warning(f"Run name {cloned_run} already exists, aborting clone")
        return

    if len(ss.all_runs) >= n_maxruns:
        st.warning(f"Maximum number of {n_maxruns} runs reached, aborting clone")
        return

    color_index = ss.available_colors.pop(0)
    ss.all_runs[cloned_run] = MixedLayerModel(ss.all_runs[ss.all_runs_key].settings, color_index)
    ss.all_runs_key = cloned_run


def process_edit_run():
    ss.main_mode = MainMode.EDIT


def process_delete_run():
    # Delete the run name from all plot items.
    for i, plot in ss.all_plots.items():
        if ss.all_runs_key in ss[f"plot_{i}_runs"]:
            ss[f"plot_{i}_runs"].remove(ss.all_runs_key)

    # Return the color to the available color list.
    ss.available_colors.append(ss.all_runs[ss.all_runs_key].color_index)
    ss.available_colors.sort()

    del(ss.all_runs[ss.all_runs_key])
    if not ss.all_runs:
        color_index = ss.available_colors.pop(0)
        ss.all_runs = {ss.default_name: MixedLayerModel(ss.default_settings, color_index)}
        ss.all_runs_key = ss.default_name
    else:
        ss.all_runs_key = list(ss.all_runs.keys())[0]


def process_new_line_plot():
    ss.n_plots += 1
    ss.all_plots[ss.n_plots] = LinePlot()


def process_new_profile_plot():
    ss.n_plots += 1
    ss.all_plots[ss.n_plots] = ProfilePlot()


def process_new_plume_plot():
    ss.n_plots += 1
    ss.all_plots[ss.n_plots] = PlumePlot()


def process_delete_plot(i):
    del(ss.all_plots[i])


def process_edit_save():
    ss.run_name_input = ss.run_name_input.strip()

    if ss.run_name_input != ss.all_runs_key:
        if ss.run_name_input in ss.all_runs:
            st.warning(f"Run name {ss.run_name_input} already exists, skipping name change")
        else:
            # Change the run name in the run dictionary.
            ss.all_runs[ss.run_name_input] = ss.all_runs.pop(ss.all_runs_key)

            # Change the run name in all plot items.
            for i, plot in ss.all_plots.items():
                for j, run_name in enumerate(plot.selected_runs):
                    if run_name == ss.all_runs_key:
                        ss[f"plot_{i}_runs"][j] = ss.run_name_input

            # Overwrite the previous key now the info is no longer needed.
            ss.all_runs_key = ss.run_name_input

    color = ss.all_runs[ss.all_runs_key].color_index
    del(ss.all_runs[ss.all_runs_key])
    settings = {}
    settings["runtime"] = ss.settings_general_runtime
    settings["starttime"] = ss.settings_general_starttime
    settings["startdate"] = ss.settings_general_startdate
    settings["dt"] = ss.settings_general_dt
    settings["dt_output"] = ss.settings_general_dt_output

    settings["h"] = ss.settings_mixedlayer_h
    settings["beta"] = ss.settings_mixedlayer_beta
    settings["div"] = ss.settings_mixedlayer_div

    settings["theta"] = ss.settings_temperature_theta
    settings["dtheta"] = ss.settings_temperature_dtheta
    settings["wtheta"] = ss.settings_temperature_wtheta
    settings["gammatheta"] = ss.settings_temperature_gammatheta

    # Convert back from kg kg-1 to kkg kg-1
    settings["q"] = ss.settings_moisture_q * 1e-3
    settings["dq"] = ss.settings_moisture_dq * 1e-3
    settings["wq"] = ss.settings_moisture_wq * 1e-3
    settings["gammaq"] = ss.settings_moisture_gammaq * 1e-3

    settings["dtheta_plume"] = ss.settings_fire_atmosphere_dtheta_plume
    settings["dq_plume"] = ss.settings_fire_atmosphere_dq_plume * 1e-3

    ss.all_runs[ss.all_runs_key] = MixedLayerModel(settings, color)
    ss.main_mode = MainMode.PLOT


def process_edit_cancel():
    ss.main_mode = MainMode.PLOT


def process_add_sounding():
    ss.main_mode = MainMode.SOUNDING


def process_edit_sounding():
    pass


def process_delete_sounding():
    # Delete the run name from all plot items.
    for i, plot in ss.all_plots.items():
        if isinstance(plot, ProfilePlot):
            if ss.all_soundings_key in ss[f"plot_{i}_soundings"]:
                ss[f"plot_{i}_soundings"].remove(ss.all_soundings_key)

    del(ss.all_soundings[ss.all_soundings_key])

    if not ss.all_soundings:
        ss.all_soundings_key = None
    else:
        ss.all_soundings_key = list(ss.all_soundings.keys())[0]


def process_sounding_uploaded():
    if ss.sounding_name_input == "":
        st.warning("Sounding name cannot be empty")
        return

    if ss.sounding_uploaded is not None:
        df = pd.read_csv(ss.sounding_uploaded)
        ss.all_soundings[ss.sounding_name_input] = df
        ss.all_soundings_key = ss.sounding_name_input
        ss.selected_sounding = ss.all_soundings_key

    ss.main_mode = MainMode.PLOT


def process_sounding_close():
    ss.main_mode = MainMode.PLOT


# Load the default settings from disk.
if "default_name" not in ss:
    with open(f"default_settings.toml", "rb") as f:
        ss.default_settings = tomllib.load(f)
        ss.default_name = "Default"
        if "startdate" not in ss.default_settings:
            ss.default_settings["startdate"] = datetime.datetime.now().date()


# Get runs and soundings from query params and if none given initialize defaults.
if "all_runs" not in ss:
    ss.all_runs = {}
if "all_runs_key" not in ss:
    ss.all_runs_key = None
if "all_soundings" not in ss:
    ss.all_soundings = {}
if "all_soundings_key" not in ss:
    ss.all_soundings_key = None
if "available_colors" not in ss:
    ss.available_colors = [i for i in range(n_maxruns)]

if "c" in st.query_params:
    compressed = base64.urlsafe_b64decode(st.query_params["c"].encode('ascii'))
    json_str = gzip.decompress(compressed).decode('utf-8')
    url_data = json.loads(json_str)

    # Get the run settings.
    if "settings" in url_data:
        try:
            url_settings = {}

            ds = url_data["settings"]

            for d in ds:
                run_name = d["name"]

                url_settings["runtime"] = float(d["runtime"])
                url_settings["starttime"] = datetime.time.fromisoformat(d["starttime"])
                url_settings["startdate"] = datetime.date.fromisoformat(d["startdate"])
                url_settings["dt"] = float(d["dt"])
                url_settings["dt_output"] = float(d["dt_output"])

                url_settings["h"] = float(d["h"])
                url_settings["beta"] = float(d["beta"])
                url_settings["div"] = float(d["div"])

                url_settings["theta"] = float(d["theta"])
                url_settings["dtheta"] = float(d["dtheta"])
                url_settings["wtheta"] = float(d["wtheta"])
                url_settings["gammatheta"] = float(d["gammatheta"])

                url_settings["q"] = float(d["q"])
                url_settings["dq"] = float(d["dq"])
                url_settings["wq"] = float(d["wq"])
                url_settings["gammaq"] = float(d["gammaq"])

                url_settings["dtheta_plume"] = float(d["dtheta_plume"])
                url_settings["dq_plume"] = float(d["dq_plume"])

                # Input is valid, overwrite the defaults.
                color_index = ss.available_colors.pop(0)
                ss.all_runs[run_name] = MixedLayerModel(url_settings, color_index)

                if ss.all_runs_key == None:
                    ss.all_runs_key = run_name

        except KeyError:
            st.warning("The provided settings via the URL are incomplete or corrupt, reverting to default settings")

    # Get the provided sounding.
    if "soundings" in url_data:
        try:
            ds = url_data["soundings"]

            for d in ds:
                sounding_name = d["name"]

                df = pd.DataFrame.from_dict(d)
                ss.all_soundings[sounding_name] = df

                if ss.all_soundings_key == None:
                    ss.all_soundings_key = sounding_name
                    ss.selected_sounding = ss.all_soundings_key

        except KeyError:
            st.warning("The provided sounding via the URL is incomplete or corrupt, not loaded")
            ss.all_soundings = {}
            ss.all_soundings_key = None

st.query_params.clear()

if not ss.all_runs:
    color_index = ss.available_colors.pop(0)
    ss.all_runs = {ss.default_name: MixedLayerModel(ss.default_settings, color_index)}
    ss.all_runs_key = ss.default_name


# Deal with the state.
if "main_mode" not in ss:
    ss.main_mode = MainMode.PLOT
if "n_plots" not in ss:
    ss.n_plots = 0
if "all_plots" not in ss:
    ss.all_plots = {0: LinePlot()} # Start with one line plot.
else:
    # This code is need to prevent auto-cleanup by streamlit
    for i, plot in ss.all_plots.items():
        if f"plot_{i}_runs" in ss:
            ss[f"plot_{i}_runs"] = ss[f"plot_{i}_runs"]
        if f"plot_{i}_soundings" in ss:
            ss[f"plot_{i}_soundings"] = ss[f"plot_{i}_soundings"]


# Check the range of plot_times.
ss.time_max = 0
for _, run in ss.all_runs.items():
    ss.time_max = max(ss.time_max, run.output.time.values[-1])


# Side bar.
with st.sidebar:
    st.title("CLASS web")
    st.header("Experiments")

    # handle selectbox selection first
    st.selectbox(
        "Name",
        ss.all_runs.keys(),
        index=list(ss.all_runs.keys()).index(ss.all_runs_key),
        key="selected_run",
        on_change=process_selected_run
    )

    clone_run, edit_run, delete_run = st.columns(3)
    clone_run.button("", icon=":material/content_copy:", use_container_width=True, on_click=process_clone_run)
    edit_run.button("", icon=":material/edit:", use_container_width=True, on_click=process_edit_run)
    delete_run.button("", icon=":material/delete:", use_container_width=True, on_click=process_delete_run)

    st.divider()

    st.header("Plots")
    new_line_plot, new_profile_plot, new_fire_plot = st.columns(3)
    new_line_plot.button(
        "",
        help="New timeseries plot",
        icon=":material/line_axis:",
        use_container_width=True,
        on_click=process_new_line_plot)
    new_profile_plot.button(
        "",
        help="New profile plot",
        icon=":material/expand:",
        use_container_width=True,
        on_click=process_new_profile_plot)
    new_fire_plot.button(
        "",
        help="New fire plume plot",
        icon=":material/local_fire_department:",
        use_container_width=True,
        on_click=process_new_plume_plot)

    for i, plot in ss.all_plots.items():
        if isinstance(plot, LinePlot):
            if f"plot_{i}_runs" not in ss:
                ss[f"plot_{i}_runs"] = list(ss.all_runs.keys())

            # Update plot state BEFORE rendering selectboxes
            if f"plot_{i}_xaxis" in ss:
                plot.xaxis_key = ss[f"plot_{i}_xaxis"]
                plot.xaxis_index = plot.xaxis_options.index(plot.xaxis_key)

            if f"plot_{i}_yaxis" in ss:
                plot.yaxis_key = ss[f"plot_{i}_yaxis"]
                plot.yaxis_index = plot.yaxis_options.index(plot.yaxis_key)

            plot.selected_runs = ss[f"plot_{i}_runs"]

            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                col1.header(f":material/line_axis: Plot {i}")
                col2.button(
                        "",
                        icon=":material/delete:",
                        use_container_width=True,
                        key=f"plot_{i}_delete",
                        on_click=process_delete_plot,
                        args=(i,)
                )

                x_axis, y_axis = st.columns(2)
                x_axis.selectbox("X-axis", plot.xaxis_options, index=plot.xaxis_index, key=f"plot_{i}_xaxis")
                y_axis.selectbox("Y-axis", plot.yaxis_options, index=plot.yaxis_index, key=f"plot_{i}_yaxis")

                st.multiselect(
                    "Runs to plot",
                    options=list(ss.all_runs.keys()),
                    key=f"plot_{i}_runs",
                )

        elif isinstance(plot, ProfilePlot):
            if f"plot_{i}_runs" not in ss:
                ss[f"plot_{i}_runs"] = list(ss.all_runs.keys())
            if f"plot_{i}_soundings" not in ss:
                ss[f"plot_{i}_soundings"] = []

            # Update plot state BEFORE rendering selectboxes
            if f"plot_{i}_xaxis" in ss:
                plot.xaxis_key = ss[f"plot_{i}_xaxis"]
                plot.xaxis_index = plot.xaxis_options.index(plot.xaxis_key)

            if f"plot_{i}_time" in ss:
                plot.time_plot = ss[f"plot_{i}_time"]

            plot.selected_runs = ss[f"plot_{i}_runs"]

            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                col1.header(f":material/expand: Plot {i}")
                col2.button(
                    "",
                    icon=":material/delete:",
                    use_container_width=True,
                    key=f"plot_{i}_delete",
                    on_click=process_delete_plot,
                    args=(i,)
                )

                x_axis, time_slider = st.columns(2)
                x_axis.selectbox("X-axis", plot.xaxis_options, index=plot.xaxis_index, key=f"plot_{i}_xaxis")

                time_slider.slider("Time", 0.0, ss.time_max, plot.time_plot, 0.25, key=f"plot_{i}_time")

                st.multiselect(
                    "Runs to plot",
                    options=list(ss.all_runs.keys()),
                    key=f"plot_{i}_runs",
                )

                st.multiselect(
                    "Soundings to plot",
                    options=list(ss.all_soundings.keys()),
                    key=f"plot_{i}_soundings",
                )


        elif isinstance(plot, PlumePlot):
            if f"plot_{i}_runs" not in ss:
                ss[f"plot_{i}_runs"] = [ss.all_runs_key]
            if f"plot_{i}_soundings" not in ss:
                ss[f"plot_{i}_soundings"] = []

            # Update plot state BEFORE rendering selectboxes
            if f"plot_{i}_xaxis" in ss:
                plot.xaxis_key = ss[f"plot_{i}_xaxis"]
                plot.xaxis_index = plot.xaxis_options.index(plot.xaxis_key)

            if f"plot_{i}_time" in ss:
                plot.time_plot = ss[f"plot_{i}_time"]

            plot.selected_runs = ss[f"plot_{i}_runs"]

            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                col1.header(f":material/local_fire_department: Plot {i}")
                col2.button(
                    "",
                    icon=":material/delete:",
                    use_container_width=True,
                    key=f"plot_{i}_delete",
                    on_click=process_delete_plot,
                    args=(i,)
                )

                x_axis, time_slider = st.columns(2)
                x_axis.selectbox("X-axis", plot.xaxis_options, index=plot.xaxis_index, key=f"plot_{i}_xaxis")

                # Prevent the slider to select a value that does not exist.
                if not ss[f"plot_{i}_runs"]:
                    time_max = 1.0
                    time_plot = (0.0, 1.0)
                else:
                    time_max = ss.all_runs[ss[f"plot_{i}_runs"][0]].output.time.values[-1]
                    time_plot = (0.0 if plot.time_plot[0] > time_max else plot.time_plot[0], min(time_max, plot.time_plot[1]))

                time_slider.slider("Time", 0.0, time_max, time_plot, 0.25, key=f"plot_{i}_time")

                st.multiselect(
                    "Runs to plot",
                    options=list(ss.all_runs.keys()),
                    key=f"plot_{i}_runs",
                )

                if f"plot_{i}_fire" not in ss:
                    ss[f"plot_{i}_fire"] = ["1 x"]

                st.pills(
                    "🔥 Fire multiplier",
                    ["0.25 x", "0.5 x", "1 x", "2 x", "4 x"],
                    selection_mode="multi",
                    key=f"plot_{i}_fire")

                st.multiselect(
                    "Soundings to plot",
                    options=list(ss.all_soundings.keys()),
                    key=f"plot_{i}_soundings",
                )


    st.divider()

    st.header("Soundings")

    soundings_index = None

    # handle selectbox selection first
    st.selectbox(
        "Name",
        ss.all_soundings.keys(),
        index=soundings_index,
        key="selected_sounding",
    )

    add_sounding, edit_sounding, delete_sounding = st.columns(3)
    add_sounding.button("", icon=":material/add:", use_container_width=True, on_click=process_add_sounding, key="add_sounding_button")
    # edit_sounding.button("", icon=":material/edit:", use_container_width=True, on_click=process_edit_sounding, key="edit_sounding_button")
    delete_sounding.button("", icon=":material/delete:", use_container_width=True, on_click=process_delete_sounding, key="delete_sounding_button")


if ss.main_mode == MainMode.PLOT:
    ncols = st.radio("Number of columns", [1, 2, 3, 4], horizontal=True)
    n = 0

    cols = st.columns(ncols)
    for i, plot in ss.all_plots.items():
        col = cols[n % ncols]
        n += 1
        with col.container(border=True):

            if isinstance(plot, LinePlot):
                st.subheader(f":material/line_axis: Plot {i}")
                fig = go.Figure()
                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]
                    fig.add_trace(
                        go.Scatter(
                            x=run.output[plot.xaxis_key],
                            y=run.output[plot.yaxis_key],
                            mode="lines+markers", name=run_name,
                            line=dict(color=color_cycle[run.color_index % len(color_cycle)])
                        )
                    )

                fig.update_traces(showlegend=True)
                fig.update_layout(
                    margin={"t": 50, "l": 0, "b": 0, "r": 0},
                    xaxis_title=plot.xaxis_key,
                    yaxis_title=plot.yaxis_key,
                    xaxis_title_font_size=plot_font_size,
                    xaxis_tickfont_size=plot_font_size,
                    yaxis_title_font_size=plot_font_size,
                    yaxis_tickfont_size=plot_font_size,
                    legend_font_size=plot_font_size,
                )
                st.plotly_chart(fig, key=f"plot_{i}_plotly")

            elif isinstance(plot, ProfilePlot):
                st.subheader(f":material/expand: Plot {i}")
                fig = go.Figure()

                # Get the plot ranges
                theta_min = 1e9
                theta_max = -1e9
                h_max = -1e9

                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]
                    h_max = max(h_max, run.output.h.max())
                    theta_min = min(theta_min, run.output.theta.min())

                h_max *= 1.35

                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]
                    theta_max_run = (run.output.theta + run.output.dtheta + run.gammatheta*(h_max-run.output.h)).max()
                    theta_max = max(theta_max, theta_max_run)

                # Plot the profiles.
                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]

                    # Plot the reference state
                    time_plot = plot.time_plot[0] * 3600
                    if time_plot <= run.runtime:
                        idx = round(time_plot / run.dt_output)

                        h = run.output.h.values[idx]

                        if plot.xaxis_key == "theta":
                            theta = run.output.theta.values[idx]
                            dtheta = run.output.dtheta.values[idx]
                            gammatheta = run.gammatheta
                            x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(h_max-h)]

                        elif plot.xaxis_key == "q":
                            q = run.output.q.values[idx]
                            dq = run.output.dq.values[idx]
                            gammaq = run.gammaq * 1e3
                            x_plot = [q, q, q + dq, q + dq + gammaq*(h_max-h)]

                        elif plot.xaxis_key == "thetav":
                            theta = run.output.theta.values[idx]
                            dtheta = run.output.dtheta.values[idx]
                            gammatheta = run.gammatheta

                            q = run.output.q.values[idx] * 1e-3
                            dq = run.output.dq.values[idx] * 1e-3
                            gammaq = run.gammaq

                            x_plot = [
                                virtual_temperature(theta, q, 0.0),
                                virtual_temperature(theta, q, 0.0),
                                virtual_temperature(theta + dtheta, q + dq, 0.0),
                                virtual_temperature(theta + dtheta + gammatheta*(h_max-h), q + dq + gammaq*(h_max-h), 0.0)
                            ]

                        z_plot = [0, h, h, h_max]

                        fig.add_trace(
                            go.Scatter(
                                x=x_plot,
                                y=z_plot,
                                mode="lines+markers",
                                showlegend=False,
                                name=None,
                                line=dict(color=color_cycle[run.color_index % len(color_cycle)], dash="dot"),
                            )
                        )

                    # Plot the actual state if available.
                    time_plot = plot.time_plot[1] * 3600
                    if time_plot <= run.runtime:
                        idx = round(time_plot / run.dt_output)

                        h = run.output.h.values[idx]

                        if plot.xaxis_key == "theta":
                            theta = run.output.theta.values[idx]
                            dtheta = run.output.dtheta.values[idx]
                            gammatheta = run.gammatheta
                            x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(h_max-h)]

                        elif plot.xaxis_key == "q":
                            q = run.output.q.values[idx]
                            dq = run.output.dq.values[idx]
                            gammaq = run.gammaq * 1e3
                            x_plot = [q, q, q + dq, q + dq + gammaq*(h_max-h)]

                        elif plot.xaxis_key == "thetav":
                            theta = run.output.theta.values[idx]
                            dtheta = run.output.dtheta.values[idx]
                            gammatheta = run.gammatheta

                            q = run.output.q.values[idx] * 1e-3
                            dq = run.output.dq.values[idx] * 1e-3
                            gammaq = run.gammaq

                            x_plot = [
                                virtual_temperature(theta, q, 0.0),
                                virtual_temperature(theta, q, 0.0),
                                virtual_temperature(theta + dtheta, q + dq, 0.0),
                                virtual_temperature(theta + dtheta + gammatheta*(h_max-h), q + dq + gammaq*(h_max-h), 0.0)
                            ]

                        z_plot = [0, h, h, h_max]

                        fig.add_trace(
                            go.Scatter(
                                x=x_plot,
                                y=z_plot,
                                mode="lines+markers",
                                showlegend=True,
                                name=run_name,
                                line=dict(color=color_cycle[run.color_index % len(color_cycle)])
                            )
                        )

                for sounding_name in ss[f"plot_{i}_soundings"]:
                    sounding_df = ss.all_soundings[sounding_name]

                    if plot.xaxis_key not in sounding_df.columns:
                        st.toast(f"Requested variable \"{plot.xaxis_key}\" is not in sounding \"{sounding_name}\"")

                    else:
                        fig.add_trace(
                            go.Scatter(
                                x=sounding_df[plot.xaxis_key],
                                y=sounding_df["z"],
                                mode="markers",
                                showlegend=True,
                                name=sounding_name,
                                marker=dict(
                                    color="black",
                                    symbol="cross",
                                    size=3,
                                    )
                            )
                        )

                fig.update_layout(
                    margin={"t": 50, "l": 0, "b": 0, "r": 0},
                    xaxis_title=plot.xaxis_key,
                    yaxis_title="z",
                    xaxis_title_font_size=plot_font_size,
                    xaxis_tickfont_size=plot_font_size,
                    yaxis_title_font_size=plot_font_size,
                    yaxis_tickfont_size=plot_font_size,
                    legend_font_size=plot_font_size,
                )
                st.plotly_chart(fig, key=f"plot_{i}_plotly")

            elif isinstance(plot, PlumePlot):
                st.subheader(f":material/local_fire_department: Plot {i}")
                fig = go.Figure()

                # Get the plot ranges
                h_max = -1e9

                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]
                    h_max = max(h_max, run.output.h.max())

                h_max *= 2.0

                # Plot the profiles.
                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]

                    # If they are the same, double plotting is not necessary.
                    if plot.time_plot[0] != plot.time_plot[1]:

                        # Plot the reference state
                        time_plot = plot.time_plot[0] * 3600
                        if time_plot <= run.runtime:
                            idx = round(time_plot / run.dt_output)

                            h = run.output.h.values[idx]

                            if plot.xaxis_key == "theta":
                                theta = run.output.theta.values[idx]
                                dtheta = run.output.dtheta.values[idx]
                                gammatheta = run.gammatheta
                                x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(h_max-h)]

                            elif plot.xaxis_key == "q":
                                q = run.output.q.values[idx]
                                dq = run.output.dq.values[idx]
                                gammaq = run.gammaq * 1e3
                                x_plot = [q, q, q + dq, q + dq + gammaq*(h_max-h)]

                            elif plot.xaxis_key == "thetav":
                                theta = run.output.theta.values[idx]
                                dtheta = run.output.dtheta.values[idx]
                                gammatheta = run.gammatheta

                                q = run.output.q.values[idx] * 1e-3
                                dq = run.output.dq.values[idx] * 1e-3
                                gammaq = run.gammaq

                                x_plot = [
                                    virtual_temperature(theta, q, 0.0),
                                    virtual_temperature(theta, q, 0.0),
                                    virtual_temperature(theta + dtheta, q + dq, 0.0),
                                    virtual_temperature(theta + dtheta + gammatheta*(h_max-h), q + dq + gammaq*(h_max-h), 0.0)
                                ]

                            z_plot = [0, h, h, h_max]

                            fig.add_trace(
                                go.Scatter(
                                    x=x_plot,
                                    y=z_plot,
                                    mode="lines+markers",
                                    showlegend=False,
                                    name=None,
                                    line=dict(color=color_cycle[run.color_index % len(color_cycle)], dash="dot"),
                                )
                            )

                            ss[f"plot_{i}_fire"].sort()

                            for fire_label in ss[f"plot_{i}_fire"]:
                                if fire_label == "0.25 x":
                                    fac_fire = 0.25
                                    color = "#781c6d"
                                elif fire_label == "0.5 x":
                                    fac_fire = 0.5
                                    color = "#bc3754"
                                elif fire_label == "1 x":
                                    fac_fire = 1.0
                                    color = "#dd513a"
                                elif fire_label == "2 x":
                                    fac_fire = 2.0
                                    color = "#f37819"
                                elif fire_label == "4 x":
                                    fac_fire = 4.0
                                    color = "#fca50a"

                                if plot.xaxis_key == "theta":
                                    x_plot, _, _, type_plume, z_plot = run.launch_entraining_plume(time_plot, fac_fire)
                                elif plot.xaxis_key == "q":
                                    _, x_plot, _, type_plume, z_plot = run.launch_entraining_plume(time_plot, fac_fire)
                                elif plot.xaxis_key == "thetav":
                                    _, _, x_plot, type_plume, z_plot = run.launch_entraining_plume(time_plot, fac_fire)

                                marker_sizes = np.zeros_like(z_plot)
                                marker_sizes[::5] = np.where(type_plume[::5] > 0, 5, marker_sizes[::5])
                                marker_sizes[0], marker_sizes[-1] = 5, 5

                                fig.add_trace(
                                    go.Scatter(
                                        x=x_plot,
                                        y=z_plot,
                                        mode="lines+markers",
                                        showlegend=False,
                                        line=dict(
                                            color=color,
                                            dash="dot",
                                            width=1.5,
                                            ),
                                        marker=dict(
                                            color=color,
                                            # symbol="cross",
                                            size=marker_sizes,
                                            )
                                    )
                                )

                    # Plot the actual state if available.
                    time_plot = plot.time_plot[1] * 3600
                    if time_plot <= run.runtime:
                        idx = round(time_plot / run.dt_output)

                        h = run.output.h.values[idx]

                        if plot.xaxis_key == "theta":
                            theta = run.output.theta.values[idx]
                            dtheta = run.output.dtheta.values[idx]
                            gammatheta = run.gammatheta
                            x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(h_max-h)]

                        elif plot.xaxis_key == "q":
                            q = run.output.q.values[idx]
                            dq = run.output.dq.values[idx]
                            gammaq = run.gammaq * 1e3
                            x_plot = [q, q, q + dq, q + dq + gammaq*(h_max-h)]

                        elif plot.xaxis_key == "thetav":
                            theta = run.output.theta.values[idx]
                            dtheta = run.output.dtheta.values[idx]
                            gammatheta = run.gammatheta

                            # Convert back to kg/kg
                            q = run.output.q.values[idx] * 1e-3
                            dq = run.output.dq.values[idx] * 1e-3
                            gammaq = run.gammaq

                            x_plot = [
                                virtual_temperature(theta, q, 0.0),
                                virtual_temperature(theta, q, 0.0),
                                virtual_temperature(theta + dtheta, q + dq, 0.0),
                                virtual_temperature(theta + dtheta + gammatheta*(h_max-h), q + dq + gammaq*(h_max-h), 0.0)
                            ]

                        z_plot = [0, h, h, h_max]

                        fig.add_trace(
                            go.Scatter(
                                x=x_plot,
                                y=z_plot,
                                mode="lines+markers",
                                showlegend=True,
                                name=run_name,
                                line=dict(color=color_cycle[run.color_index % len(color_cycle)])
                            )
                        )

                        ss[f"plot_{i}_fire"].sort()

                        for fire_label in ss[f"plot_{i}_fire"]:
                            if fire_label == "0.25 x":
                                fac_fire = 0.25
                                color = "#781c6d"
                            elif fire_label == "0.5 x":
                                fac_fire = 0.5
                                color = "#bc3754"
                            elif fire_label == "1 x":
                                fac_fire = 1.0
                                color = "#dd513a"
                            elif fire_label == "2 x":
                                fac_fire = 2.0
                                color = "#f37819"
                            elif fire_label == "4 x":
                                fac_fire = 4.0
                                color = "#fca50a"

                            if plot.xaxis_key == "theta":
                                x_plot, _, _, type_plume, z_plot = run.launch_entraining_plume(time_plot, fac_fire)
                            elif plot.xaxis_key == "q":
                                _, x_plot, _, type_plume, z_plot = run.launch_entraining_plume(time_plot, fac_fire)
                            elif plot.xaxis_key == "thetav":
                                _, _, x_plot, type_plume, z_plot = run.launch_entraining_plume(time_plot, fac_fire)

                            marker_sizes = np.zeros_like(z_plot)
                            marker_sizes[::5] = np.where(type_plume[::5] > 0, 5, marker_sizes[::5])
                            marker_sizes[0], marker_sizes[-1] = 5, 5

                            fig.add_trace(
                                go.Scatter(
                                    x=x_plot,
                                    y=z_plot,
                                    mode="lines+markers",
                                    showlegend=True,
                                    name=f"🔥 {fire_label}",
                                    line=dict(
                                        color=color,
                                        width=1.5,
                                        ),
                                    marker=dict(
                                        color=color,
                                        # symbol="cross",
                                        size=marker_sizes,
                                        )
                                )
                            )

                for sounding_name in ss[f"plot_{i}_soundings"]:
                    sounding_df = ss.all_soundings[sounding_name]

                    if plot.xaxis_key not in sounding_df.columns:
                        st.toast(f"Requested variable \"{plot.xaxis_key}\" is not in sounding \"{sounding_name}\"")

                    else:
                        fig.add_trace(
                            go.Scatter(
                                x=sounding_df[plot.xaxis_key],
                                y=sounding_df["z"],
                                mode="markers",
                                showlegend=True,
                                name=sounding_name,
                                marker=dict(
                                    color="black",
                                    symbol="cross",
                                    size=3,
                                    )
                            )
                        )

                fig.update_layout(
                    margin={"t": 50, "l": 0, "b": 0, "r": 0},
                    xaxis_title=plot.xaxis_key,
                    yaxis_title="z",
                    xaxis_title_font_size=plot_font_size,
                    xaxis_tickfont_size=plot_font_size,
                    yaxis_title_font_size=plot_font_size,
                    yaxis_tickfont_size=plot_font_size,
                    legend_font_size=plot_font_size,
                )
                st.plotly_chart(fig, key=f"plot_{i}_plotly")


elif ss.main_mode == MainMode.EDIT:

    st.header("Edit run")

    active_run = ss.all_runs[ss.all_runs_key]

    if "settings_general_runtime" not in ss:
        ss.settings_general_runtime = active_run.settings["runtime"]
    if "settings_general_starttime" not in ss:
        ss.settings_general_starttime = active_run.settings["starttime"]
    if "settings_general_startdate" not in ss:
        ss.settings_general_startdate = active_run.settings["startdate"]
    if "settings_general_dt" not in ss:
        ss.settings_general_dt = active_run.settings["dt"]
    if "settings_general_dt_output" not in ss:
        ss.settings_general_dt_output = active_run.settings["dt_output"]

    if "settings_mixedlayer_h" not in ss:
        ss.settings_mixedlayer_h = active_run.settings["h"]
    if "settings_mixedlayer_beta" not in ss:
        ss.settings_mixedlayer_beta = active_run.settings["beta"]
    if "settings_mixedlayer_div" not in ss:
        ss.settings_mixedlayer_div = active_run.settings["div"]

    if "settings_temperature_theta" not in ss:
        ss.settings_temperature_theta = active_run.settings["theta"]
    if "settings_temperature_dtheta" not in ss:
        ss.settings_temperature_dtheta = active_run.settings["dtheta"]
    if "settings_temperature_wtheta" not in ss:
        ss.settings_temperature_wtheta = active_run.settings["wtheta"]
    if "settings_temperature_gammatheta" not in ss:
        ss.settings_temperature_gammatheta = active_run.settings["gammatheta"]

    if "settings_moisture_q" not in ss:
        ss.settings_moisture_q = active_run.settings["q"] * 1e3
    if "settings_moisture_dq" not in ss:
        ss.settings_moisture_dq = active_run.settings["dq"] * 1e3
    if "settings_temperature_wq" not in ss:
        ss.settings_moisture_wq = active_run.settings["wq"] * 1e3
    if "settings_temperature_gammaq" not in ss:
        ss.settings_moisture_gammaq = active_run.settings["gammaq"] * 1e3

    if "settings_fire_atmosphere_dtheta_plume" not in ss:
        ss.settings_fire_atmosphere_dtheta_plume = active_run.settings["dtheta_plume"]
    if "settings_fire_atmosphere_dq_plume" not in ss:
        ss.settings_fire_atmosphere_dq_plume = active_run.settings["dq_plume"] * 1e3

    # Always set the edit key to the selected run.
    ss.run_name_input = ss.all_runs_key

    with st.form("edit_form", border=False):
        col1, col2, col3 = st.columns(3, vertical_alignment="bottom")

        # text input for editing the current run name
        col1.text_input("Edit current run name", key="run_name_input")
        col2.form_submit_button("Save", on_click=process_edit_save)
        col3.form_submit_button("Cancel", on_click=process_edit_cancel)

        tab_default, tab_fire = st.tabs(["Basic", "Fire plume"])

        with tab_default:
            col1, col2 = st.columns(2)
            with col1:
                with st.expander("General", expanded=True):
                    st.number_input(
                        r"runtime (s)",
                        help="total runtime (s)",
                        step=1.0,
                        format="%0.0f",
                        key="settings_general_runtime"
                    )

                    st.time_input(
                        r"start time (hh:mm)",
                        help="start time (hh:mm)",
                        key="settings_general_starttime"
                    )

                    st.date_input(
                        r"start date (YYYY/MM/DD)",
                        help="start date (YYYY/MM/DD)",
                        key="settings_general_startdate"
                    )

                    st.number_input(
                        r"$\Delta t$ (s)",
                        help="time step (s)",
                        step=1.0,
                        format="%0.1f",
                        key="settings_general_dt"
                    )

                    st.number_input(
                        r"output $\Delta t$ (s)",
                        help="output time step (s)",
                        step=1.0,
                        format="%0.1f",
                        key="settings_general_dt_output"
                    )

                with st.expander("Mixed layer", expanded=True):
                    st.number_input(
                        r"$h$ (m)",
                        help="boundary-layer depth (m)",
                        step=1.0,
                        format="%0.0f",
                        key="settings_mixedlayer_h"
                    )

                    st.number_input(
                        r"$\beta$ (-)",
                        help="entrainment coefficient (-)",
                        step=0.01,
                        format="%0.2f",
                        key="settings_mixedlayer_beta"
                    )

                    st.number_input(
                        r"$div$ (s-1)",
                        help="large-scale divergence (s-1)",
                        step=0.000001,
                        format="%0.3e",
                        key="settings_mixedlayer_div"
                    )

            with col2:
                with st.expander("Temperature", expanded=True):
                    st.number_input(
                        r"$\theta$ (K)",
                        help="mixed-layer potential temperature (K)",
                        step=0.5,
                        format="%0.1f",
                        key="settings_temperature_theta"
                    )

                    st.number_input(
                        r"$\Delta \theta$ (K)",
                        help="potential temperature jump (K)",
                        step=0.5,
                        format="%0.2f",
                        key="settings_temperature_dtheta"
                    )

                    st.number_input(
                        r"$\overline{w^\prime \theta^\prime}_s$ (K m s-1)",
                        help="potential temperature surface flux (K m s-1)",
                        step=0.01,
                        format="%0.2f",
                        key="settings_temperature_wtheta"
                    )

                    st.number_input(
                        r"$\gamma_\theta$ (K m-1)",
                        help="potential temperature lapse rate (K m-1)",
                        step=0.0005,
                        format="%0.4f",
                        key="settings_temperature_gammatheta"
                    )

                with st.expander("Moisture", expanded=True):
                    st.number_input(
                        r"$q$ (g kg-1)",
                        help="specific humidity (g kg-1)",
                        step=0.5,
                        format="%0.1f",
                        key="settings_moisture_q"
                    )

                    st.number_input(
                        r"$\Delta q$ (g kg-1)",
                        help="specific humidity jump (g kg-1)",
                        step=0.5,
                        format="%0.1f",
                        key="settings_moisture_dq"
                    )

                    st.number_input(
                        r"$\overline{w^\prime q^\prime}_s$ (g kg-1 m s-1)",
                        help="specific humidity surface flux (g kg-1 m s-1)",
                        step=0.01,
                        format="%0.3f",
                        key="settings_moisture_wq"
                    )

                    st.number_input(
                        r"$\gamma_\theta$ (g kg-1  m-1)",
                        help="specific humidity lapse rate (g kg-1 m-1)",
                        step=0.0005,
                        format="%0.4f",
                        key="settings_moisture_gammaq"
                    )


        with tab_fire:
            col1, col2 = st.columns(2)
            # with col1:
            #     with st.expander("Fire surface", expanded=True):
            #         pass

            with col1:
                with st.expander("Atmosphere", expanded=True):
                    st.number_input(
                        r"$\Delta \theta_\textrm{plume}$ (K)",
                        help="Plume excess temperature (K)",
                        step=0.2,
                        format="%0.01f",
                        key="settings_fire_atmosphere_dtheta_plume"
                    )

                    st.number_input(
                        r"$\Delta q_\textrm{plume}$ (g kg-1)",
                        help="Plume excess specific humidity (g kg-1)",
                        step=0.5,
                        format="%0.1f",
                        key="settings_fire_atmosphere_dq_plume"
                    )


elif ss.main_mode == MainMode.SOUNDING:

    st.header("Edit sounding")

    with st.form("sounding_form", border=False):
        col_add, col_cancel = st.columns(2)
        col_add.form_submit_button("Add", on_click=process_sounding_uploaded)
        col_cancel.form_submit_button("Close", on_click=process_sounding_close)

        st.text_input("Sounding name", key="sounding_name_input")
        st.file_uploader("Upload a sounding .csv file", key="sounding_uploaded")

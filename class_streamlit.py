import streamlit as st
from streamlit import session_state as ss
from class_streamlit_defs import *
import tomllib
import plotly.express as px
import plotly.graph_objects as go
import plotly.io


# Ensure that plots fill the whole page, must be first call to streamlit.
st.set_page_config(layout="wide")


# Load the default settings from disk and override with URL settings.
if "default_name" not in ss:
    with open(f"default_settings.toml", "rb") as f:
        ss.default_settings = tomllib.load(f)
        ss.default_name = "Default"

    if "run_name" in st.query_params:
        url_settings = {}
        try:
            url_settings["runtime"] = float(st.query_params["runtime"])
            url_settings["dt"] = float(st.query_params["dt"])
            url_settings["dt_output"] = float(st.query_params["dt_output"])
            url_settings["h"] = float(st.query_params["h"])
            url_settings["beta"] = float(st.query_params["beta"])
            url_settings["div"] = float(st.query_params["div"])
            url_settings["theta"] = float(st.query_params["theta"])
            url_settings["dtheta"] = float(st.query_params["dtheta"])
            url_settings["wtheta"] = float(st.query_params["wtheta"])
            url_settings["gammatheta"] = float(st.query_params["gammatheta"])

            # Input is valid, overwrite the defaults.
            ss.default_name = str(st.query_params["run_name"])
            ss.default_settings = url_settings

        except KeyError:
            st.warning("The provided input via the URL is incomplete or corrupt, reverting to default settings")

        st.query_params.clear()


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


def process_new_skewt_plot():
    pass


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
    settings["dt"] = ss.settings_general_dt
    settings["dt_output"] = ss.settings_general_dt_output
    settings["h"] = ss.settings_mixedlayer_h
    settings["beta"] = ss.settings_mixedlayer_beta
    settings["div"] = ss.settings_mixedlayer_div
    settings["theta"] = ss.settings_temperature_theta
    settings["dtheta"] = ss.settings_temperature_dtheta
    settings["wtheta"] = ss.settings_temperature_wtheta
    settings["gammatheta"] = ss.settings_temperature_gammatheta
    ss.all_runs[ss.all_runs_key] = MixedLayerModel(settings, color)
    ss.main_mode = MainMode.PLOT


def process_edit_cancel():
    ss.main_mode = MainMode.PLOT


# Deal with the state.
if "available_colors" not in ss:
    ss.available_colors = [i for i in range(n_maxruns)]
if "all_runs" not in ss:
    color_index = ss.available_colors.pop(0)
    ss.all_runs = {ss.default_name: MixedLayerModel(ss.default_settings, color_index)} # Start the code with a fully run default case.
if "all_runs_key" not in ss:
    ss.all_runs_key = ss.default_name
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
    new_line_plot, new_profile_plot, new_skewt_plot = st.columns(3)
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
    new_skewt_plot.button(
        "",
        help="New Skew-T plot",
        icon=":material/partly_cloudy_day:",
        use_container_width=True,
        on_click=process_new_skewt_plot)

    for i, plot in ss.all_plots.items():
        if f"plot_{i}_runs" not in ss:
            ss[f"plot_{i}_runs"] = list(ss.all_runs.keys())

        if isinstance(plot, LinePlot):
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
                col1.header(f"Plot {i}")
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
            # Update plot state BEFORE rendering selectboxes
            if f"plot_{i}_xaxis" in ss:
                plot.xaxis_key = ss[f"plot_{i}_xaxis"]
                plot.xaxis_index = plot.xaxis_options.index(plot.xaxis_key)

            if f"plot_{i}_time" in ss:
                plot.time_plot = ss[f"plot_{i}_time"]

            plot.selected_runs = ss[f"plot_{i}_runs"]

            with st.container(border=True):
                col1, col2 = st.columns([2, 1])
                col1.header(f"Plot {i}")
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


if ss.main_mode == MainMode.PLOT:
    ncols = st.radio("Number of columns", [1, 2, 3, 4], horizontal=True)
    n = 0

    cols = st.columns(ncols)
    for i, plot in ss.all_plots.items():
        col = cols[n % ncols]
        n += 1
        with col.container(border=True):
            if isinstance(plot, LinePlot):
                st.subheader(f"Plot {i}")
                fig = go.Figure()
                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]
                    fig.add_trace(go.Scatter(x=run.output[plot.xaxis_key], y=run.output[plot.yaxis_key], mode="lines+markers", name=run_name, line=dict(color=color_cycle[run.color_index % len(color_cycle)])))
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
                st.subheader(f"Plot {i}")
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

                    # Plot the initial state
                    h = run.output.h.values[0]
                    theta = run.output.theta.values[0]
                    dtheta = run.output.dtheta.values[0]
                    gammatheta = run.gammatheta

                    x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(h_max-h)]
                    z_plot = [0, h, h, h_max]

                    fig.add_trace(
                        go.Scatter(
                            x=x_plot,
                            y=z_plot,
                            mode="lines",
                            showlegend=False,
                            name=None,
                            line=dict(color=color_cycle[run.color_index % len(color_cycle)], dash="dot"),
                        )
                    )

                    # Plot the actual state if available.
                    time_plot = plot.time_plot * 3600
                    if time_plot <= run.runtime:
                        idx = round(time_plot / run.dt_output)

                        h = run.output.h.values[idx]
                        theta = run.output.theta.values[idx]
                        dtheta = run.output.dtheta.values[idx]
                        gammatheta = run.gammatheta

                        x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(h_max-h)]
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

                        # x_fire_plot = [theta + 3, theta + 3]
                        # z_fire_plot = [0, h_max]

                        # fig.add_trace(
                        #     go.Scatter(
                        #         x=x_fire_plot,
                        #         y=z_fire_plot,
                        #         mode="lines",
                        #         showlegend=True,
                        #         name="Fire plume",
                        #         line=dict(color="#000000", dash="dot")
                        #     )
                        # )


                fig.update_layout(
                    margin={"t": 50, "l": 0, "b": 0, "r": 0},
                    xaxis_range=(theta_min-0.25, theta_max+0.25),
                    yaxis_range=(-25, h_max+50),
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

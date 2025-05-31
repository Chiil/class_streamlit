import streamlit as st
from streamlit import session_state as ss
from class_streamlit_defs import *
import tomllib
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(layout="wide")


with open(f"default_settings.toml", "rb") as f:
    default_settings = tomllib.load(f)


def process_name_change():
    for i, plot in enumerate(ss.line_plots):
        for j, run_name in enumerate(plot.selected_runs):
            if run_name == ss.all_runs_key:
                plot.selected_runs[j] = ss.run_name_input


# state to save
if "all_runs" not in ss:
    ss.all_runs = {"Default": MixedLayerModel(default_settings)}
if "all_runs_key" not in ss:
    ss.all_runs_key = "Default"
if "main_mode" not in ss:
    ss.main_mode = 0
if "line_plots" not in ss:
    ss.line_plots = [LinePlot()]


# sidebar
with st.sidebar:
    st.title("CLASS web")
    st.header("Experiments")

    # handle selectbox selection first
    selected_run = st.selectbox(
        "Name",
        ss.all_runs.keys(),
        index=list(ss.all_runs.keys()).index(ss.all_runs_key)
    )

    # update index if changed
    if selected_run != ss.all_runs_key:
        ss.all_runs_key = selected_run
        st.rerun()

    clone_run, edit_run, delete_run = st.columns(3)
    if clone_run.button("", icon=":material/content_copy:", use_container_width=True):
        cloned_run = ss.all_runs_key + " (clone)"
        ss.all_runs[cloned_run] = MixedLayerModel(ss.all_runs[ss.all_runs_key].settings)
        ss.all_runs_key = cloned_run
        st.rerun()
    if edit_run.button("", icon=":material/edit:", use_container_width=True):
        ss.main_mode = 1
        st.rerun()
    if delete_run.button("", icon=":material/delete:", use_container_width=True):
        del(ss.all_runs[ss.all_runs_key])
        if not ss.all_runs:
            ss.all_runs = {"Default": MixedLayerModel(default_settings)}
            ss.all_runs_key = "Default"
        else:
            ss.all_runs_key = list(ss.all_runs.keys())[0]
        st.rerun()

    st.divider()

    st.header("Plots")
    new_line_plot, new_profile, new_skewt = st.columns(3)
    if new_line_plot.button("", help="New timeseries plot", icon=":material/line_axis:", use_container_width=True):
        ss.line_plots.append(LinePlot())
    if new_profile.button("", help="New profile plot", icon=":material/vertical_align_top:", use_container_width=True):
        ss.line_plots.append(ProfilePlot())
    if new_skewt.button("", help="New Skew-T plot", icon=":material/partly_cloudy_day:", use_container_width=True):
        pass

    for i, plot in enumerate(ss.line_plots):
        if isinstance(plot, LinePlot):
            if f"plot_{i}_runs" not in ss:
                ss[f"plot_{i}_runs"] = list(ss.all_runs.keys())
            else:
                ss[f"plot_{i}_runs"] = plot.selected_runs

            # Update plot state BEFORE rendering selectboxes
            if f"plot_{i}_xaxis" in ss:
                plot.xaxis_key = ss[f"plot_{i}_xaxis"]
                plot.xaxis_index = plot.xaxis_options.index(plot.xaxis_key)

            if f"plot_{i}_yaxis" in ss:
                plot.yaxis_key = ss[f"plot_{i}_yaxis"]
                plot.yaxis_index = plot.yaxis_options.index(plot.yaxis_key)

            with st.container(border=True):
                st.header(f"Plot {i}")
                x_axis, y_axis = st.columns(2)
                x_axis.selectbox("X-axis", plot.xaxis_options, index=plot.xaxis_index, key=f"plot_{i}_xaxis")
                y_axis.selectbox("Y-axis", plot.yaxis_options, index=plot.yaxis_index, key=f"plot_{i}_yaxis")

                plot.selected_runs = st.multiselect(
                    "Runs to plot",
                    options=list(ss.all_runs.keys()),
                    key=f"plot_{i}_runs",
                )

        elif isinstance(plot, ProfilePlot):
            if f"plot_{i}_runs" not in ss:
                ss[f"plot_{i}_runs"] = list(ss.all_runs.keys())
            else:
                ss[f"plot_{i}_runs"] = plot.selected_runs

            # Update plot state BEFORE rendering selectboxes
            if f"plot_{i}_xaxis" in ss:
                plot.xaxis_key = ss[f"plot_{i}_xaxis"]
                plot.xaxis_index = plot.xaxis_options.index(plot.xaxis_key)

            if f"plot_{i}_time" in ss:
                plot.time_plot = ss[f"plot_{i}_time"]

            with st.container(border=True):
                st.header(f"Plot {i}")
                x_axis, time_slider = st.columns(2)
                x_axis.selectbox("X-axis", plot.xaxis_options, index=plot.xaxis_index, key=f"plot_{i}_xaxis")

                plot.time_plot = time_slider.slider("Time", 0.0, 3.0, plot.time_plot, 0.25, key=f"plot_{i}_time")

                plot.selected_runs = st.multiselect(
                    "Runs to plot",
                    options=list(ss.all_runs.keys()),
                    key=f"plot_{i}_runs",
                )



if ss.main_mode == 0:
    for i, plot in enumerate(ss.line_plots):
        if isinstance(plot, LinePlot):
            with st.container(border=True):
                st.subheader(f"Plot {i}")
                fig = go.Figure()
                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]
                    fig.add_trace(go.Scatter(x=run.output[plot.xaxis_key], y=run.output[plot.yaxis_key], mode="lines+markers", name=run_name))
                fig.update_traces(showlegend=True)
                fig.update_layout(margin={'t': 50, 'l': 0, 'b': 0, 'r': 0}, xaxis_title=plot.xaxis_key, yaxis_title=plot.yaxis_key)
                st.plotly_chart(fig, key=f"plot_{i}_plotly")

        elif isinstance(plot, ProfilePlot):
            with st.container(border=True):
                st.subheader(f"Plot {i}")
                fig = go.Figure()
                for run_name in plot.selected_runs:
                    run = ss.all_runs[run_name]

                    time_plot = plot.time_plot * 3600
                    if time_plot <= run.runtime:
                        idx = round(time_plot / run.dt_output)

                        h = run.output.h.values[idx]
                        theta = run.output.theta.values[idx]
                        dtheta = run.output.dtheta.values[idx]
                        gammatheta = run.gammatheta

                        x_plot = [theta, theta, theta + dtheta, theta + dtheta + gammatheta*(2000.0-h)]
                        z_plot = [0, h, h, 2000.0]

                        fig.add_trace(go.Scatter(x=x_plot, y=z_plot, mode="lines+markers", name=run_name))

                fig.update_traces(showlegend=True)
                fig.update_layout(margin={'t': 50, 'l': 0, 'b': 0, 'r': 0}, xaxis_title=plot.xaxis_key, yaxis_title="z")
                st.plotly_chart(fig, key=f"plot_{i}_plotly")


elif ss.main_mode == 1:
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

    col1, col2, col3, col4, col5 = st.columns(5, vertical_alignment="bottom")

    # text input for editing the current run name
    new_name = col1.text_input(
        "Edit current run name", value=ss.all_runs_key, key="run_name_input", on_change=process_name_change
    )

    # update the name if it changed
    new_name = new_name.strip()
    if new_name != ss.all_runs_key:
        ss.all_runs[new_name] = ss.all_runs.pop(ss.all_runs_key)
        ss.all_runs_key = new_name
        st.rerun()

    if col2.button("Save"):
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
        ss.all_runs[ss.all_runs_key] = MixedLayerModel(settings)
        st.rerun()

    if col3.button("Save & close"):
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
        ss.all_runs[ss.all_runs_key] = MixedLayerModel(settings)
        ss.main_mode = 0
        st.rerun()

    if col4.button("Reset"):
        st.rerun()

    if col5.button("Close"):
        ss.main_mode = 0
        st.rerun()

    tab_default, tab_fire = st.tabs(["Default", "Fire plume"])

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

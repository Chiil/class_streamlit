import streamlit as st
import copy
import numpy as np
import pandas as pd
import tomllib
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(layout="wide")


with open(f"default_settings.toml", "rb") as f:
    default_settings = tomllib.load(f)


class MixedLayerModel:
    class Output:
        pass


    class Input:
        pass


    def __init__(self, settings):
        self.settings = settings

        self.runtime = settings["runtime"]
        self.dt = settings["dt"]
        self.dt_output = settings["dt_output"]

        self.h = settings["h"]
        self.beta = settings["beta"]
        self.div = settings["div"]

        self.theta = settings["theta"]
        self.dtheta = settings["dtheta"]
        self.wtheta = settings["wtheta"]
        self.gammatheta = settings["gammatheta"]

        self.run()


    def step(self):
        # First, compute the growth.
        # CvH, improve later, no moisture now
        wthetav = self.wtheta
        thetav = self.theta
        dthetav = self.dtheta
        we = self.beta * wthetav / dthetav
        ws = - self.h * self.div

        # Compute the tendencies.
        dhdt = we + ws
        dthetadt = (self.wtheta + we * self.dtheta) / self.h
        ddthetadt = we * self.gammatheta - dthetadt

        # Integrate the variables.
        self.time += self.dt
        self.h += self.dt * dhdt
        self.theta += self.dt * dthetadt
        self.dtheta += self.dt * ddthetadt


    def run(self):
        self.time = 0

        nt = round(self.runtime / self.dt)
        nt_output = round(nt * self.dt / self.dt_output)
        nt_ratio = round(self.dt_output / self.dt)

        # Output
        output = self.Output()
        output.time = np.nan * np.zeros(nt_output)
        output.h = np.nan * np.zeros(nt_output)
        output.theta = np.nan * np.zeros(nt_output)
        output.dtheta = np.nan * np.zeros(nt_output)

        output.time[0] = self.time
        output.h[0] = self.h
        output.theta[0] = self.theta
        output.dtheta[0] = self.dtheta

        for i in range(nt):
            self.step()

            if (i % nt_ratio) == 0:
                ii = i // nt_ratio
                output.time[ii] = self.time
                output.h[ii] = self.h
                output.theta[ii] = self.theta
                output.dtheta[ii] = self.dtheta
        
        self.output = pd.DataFrame(data = {
            "time": output.time,
            "h": output.h,
            "theta": output.theta,
            "dtheta": output.dtheta}).set_index("time")


default = MixedLayerModel(default_settings)
default.run()


# state to save
if "all_runs" not in st.session_state:
    st.session_state.all_runs = {"Default": MixedLayerModel(default_settings)}
if "all_runs_key" not in st.session_state:
    st.session_state.all_runs_key = "Default"
if "main_mode" not in st.session_state:
    st.session_state.main_mode = 0


# sidebar
with st.sidebar:
    # handle selectbox selection first
    selected_key = st.selectbox(
        "Name",
        st.session_state.all_runs.keys(),
        key="run_selector",
        index=list(st.session_state.all_runs.keys()).index(st.session_state.all_runs_key)
    )

    # update index if changed
    if selected_key != st.session_state.all_runs_key:
        st.session_state.all_runs_key = selected_key
        st.rerun()

    clone_run, edit_run, delete_run = st.columns(3)
    if clone_run.button("", icon=":material/content_copy:", use_container_width=True):
        cloned_run = st.session_state.all_runs_key + " (clone)"
        st.session_state.all_runs[cloned_run] = MixedLayerModel(st.session_state.all_runs[st.session_state.all_runs_key].settings)
        st.session_state.all_runs_key = cloned_run
        st.rerun()
    if edit_run.button("", icon=":material/edit:", use_container_width=True):
        st.session_state.main_mode = 1
        st.rerun()
    if delete_run.button("", icon=":material/delete:", use_container_width=True):
        del(st.session_state.all_runs[st.session_state.all_runs_key])
        if not st.session_state.all_runs:
            st.session_state.all_runs = {"Default": MixedLayerModel(default_settings)}
            st.session_state.all_runs_key = "Default"
        else:
            st.session_state.all_runs_key = list(st.session_state.all_runs.keys())[0]
        st.rerun()

    st.divider()


if st.session_state.main_mode == 0:
    col_plot1, col_plot2 = st.columns(2)

    with col_plot1.container(border=True):
        fig = go.Figure()

        for name, run in st.session_state.all_runs.items():
            h = run.output["h"].values[-1]
            theta = run.output["theta"].values[-1]
            dtheta = run.output["dtheta"].values[-1]
            gammatheta = run.gammatheta

            z_plot = np.array([ 0, h, h, 2000.0 ])
            theta_plot = np.array([ theta, theta, theta + dtheta, theta + dtheta + gammatheta*(2000.0-h) ])

            df = pd.DataFrame({"theta": theta_plot, "z": z_plot })

            fig.add_trace(go.Scatter(x=df["theta"], y=df["z"], mode="lines+markers", name=name))

        fig.update_layout(margin={'t': 50, 'l': 0, 'b': 0, 'r': 0}, xaxis_title="theta (K)", yaxis_title="z (m)")
        st.plotly_chart(fig)


    with col_plot2.container(border=True):
        fig = go.Figure()
        for name, run in st.session_state.all_runs.items():
            fig.add_trace(go.Scatter(x=run.output.index / 3600, y=run.output["h"], mode="lines+markers", name=name))
        fig.update_layout(margin={'t': 50, 'l': 0, 'b': 0, 'r': 0}, xaxis_title="time (h)", yaxis_title="h (m)")
        st.plotly_chart(fig)


elif st.session_state.main_mode == 1:
    st.header("Edit run")

    active_run = st.session_state.all_runs[st.session_state.all_runs_key]
    if "edit_settings" not in st.session_state:
        st.session_state.edit_settings = copy.deepcopy(active_run.settings)

    settings = st.session_state.edit_settings

    col1, col2, col3, col4, col5 = st.columns(5, vertical_alignment="bottom")

    # text input for editing the current run name
    new_name = col1.text_input(
        "Edit current run name", value=st.session_state.all_runs_key, key="run_name_input"
    )

    # update the name if it changed
    new_name = new_name.strip()
    if new_name != st.session_state.all_runs_key:
        st.session_state.all_runs[new_name] = st.session_state.all_runs.pop(st.session_state.all_runs_key)
        st.session_state.all_runs_key = new_name
        st.rerun()
    
    if col2.button("Save"):
        del(st.session_state.all_runs[st.session_state.all_runs_key])
        st.session_state.all_runs[st.session_state.all_runs_key] = MixedLayerModel(st.session_state.edit_settings)
        st.rerun()

    if col3.button("Save & close"):
        del(st.session_state.all_runs[st.session_state.all_runs_key])
        st.session_state.all_runs[st.session_state.all_runs_key] = MixedLayerModel(st.session_state.edit_settings)
        st.session_state.main_mode = 0
        st.rerun()

    if col4.button("Reset"):
        active_run = st.session_state.all_runs[st.session_state.all_runs_key]
        st.rerun()

    if col5.button("Close"):
        st.session_state.main_mode = 0
        st.rerun()
    
    tab_default, tab_fire = st.tabs(["Default", "Fire plume"])
    
    with tab_default:
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("General", expanded=True):
                settings["runtime"] = st.number_input(
                    r"runtime (s)",
                    help="total runtime (s)",
                    value=active_run.settings["runtime"],
                    step=1.0,
                    format="%0.0f",
                )
    
                settings["dt"] = st.number_input(
                    r"$\Delta t$ (s)",
                    help="time step (s)",
                    value=active_run.settings["dt"],
                    step=0.1,
                    format="%0.1f",
                )
    
                settings["dt_output"] = st.number_input(
                    r"output $\Delta t$ (s)",
                    help="output time step (s)",
                    value=active_run.settings["dt_output"],
                    step=0.1,
                    format="%0.1f",
                )
    
            with st.expander("Mixed layer", expanded=True):
                settings["h"] = st.number_input(
                    r"$h$ (m)",
                    help="boundary-layer depth (m)",
                    value=active_run.settings["h"],
                    step=1.0,
                    format="%0.0f",
                )
    
                settings["beta"] = st.number_input(
                    r"$\beta$ (-)",
                    help="entrainment coefficient (-)",
                    value=active_run.settings["beta"],
                    step=0.01,
                    format="%0.2f",
                )
    
                settings["div"] = st.number_input(
                    r"$div$ (s-1)",
                    help="large-scale divergence (s-1)",
                    value=active_run.settings["div"],
                    step=0.000001,
                    format="%0.3e",
                )
    
        with col2:
            with st.expander("Temperature", expanded=True):
                settings["theta"] = st.number_input(
                    r"$\theta$ (K)",
                    help="mixed-layer potential temperature (K)",
                    value=active_run.settings["theta"],
                    step=0.1,
                    format="%0.1f",
                )
    
                settings["dtheta"] = st.number_input(
                    r"$\Delta \theta$ (K)",
                    help="potential temperature jump (K)",
                    value=active_run.settings["dtheta"],
                    step=0.01,
                    format="%0.2f",
                )
    
                settings["wtheta"] = st.number_input(
                    r"$\overline{w^\prime \theta^\prime}_s$ (K m s-1)",
                    help="potential temperature surface flux (K m s-1)",
                    value=active_run.settings["wtheta"],
                    step=0.01,
                    format="%0.2f",
                )
    
                settings["gamma_theta"] = st.number_input(
                    r"$\gamma_\theta$ (K m-1)",
                    help="potential temperature lapse rate (K m-1)",
                    value=active_run.settings["gammatheta"],
                    step=0.0001,
                    format="%0.4f",
                )


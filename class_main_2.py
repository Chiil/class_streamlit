import streamlit as st
import numpy as np
import pandas as pd
import tomllib


with open(f"default_settings.toml", "rb") as f:
    default_settings = tomllib.load(f)


st.set_page_config(layout="wide")


# state to save
if "all_runs" not in st.session_state:
    st.session_state.all_runs = ["Default"]
if "all_runs_index" not in st.session_state:
    st.session_state.all_runs_index = 0
if "main_mode" not in st.session_state:
    st.session_state.main_mode = 0


# sidebar
with st.sidebar:
    # handle selectbox selection first
    selected_index = st.selectbox(
        "Name",
        range(len(st.session_state.all_runs)),
        format_func=lambda x: st.session_state.all_runs[x],
        index=st.session_state.all_runs_index,
        key="run_selector",
    )

    # update index if changed
    if selected_index != st.session_state.all_runs_index:
        st.session_state.all_runs_index = selected_index
        st.rerun()

    # get the active run name
    if len(st.session_state.all_runs) > 0:
        active_run = st.session_state.all_runs[st.session_state.all_runs_index]


    clone_run, clear_runs = st.columns(2)
    if clone_run.button("Clone", use_container_width=True):
        cloned_run = active_run + " (clone)"
        st.session_state.all_runs.append(cloned_run)
        st.session_state.all_runs_index = len(st.session_state.all_runs) - 1
        st.rerun()
    if clear_runs.button("Clear", use_container_width=True):
        st.session_state.all_runs.clear()
        st.session_state.all_runs = ["Default"]
        st.session_state.all_runs_index = 0
        st.rerun()

    edit_run, delete_run = st.columns(2)
    if clone_run.button("Edit", use_container_width=True):
        st.session_state.main_mode = 1
        st.rerun()
    if clear_runs.button("Delete", use_container_width=True):
        del(st.session_state.all_runs[st.session_state.all_runs_index])
        st.session_state.all_runs_index -= 1

        if st.session_state.all_runs_index < 0:
            st.session_state.all_runs = ["Default"]
            st.session_state.all_runs_index = 0
        st.rerun()

    st.divider()


if st.session_state.main_mode == 0:
    st.header("Plots")

elif st.session_state.main_mode == 1:
    st.header("Edit run")

    col1, col2 = st.columns(2, vertical_alignment="bottom")

    # text input for editing the current run name
    new_name = col1.text_input(
        "Edit current run name", value=active_run, key="run_name_input"
    )

    # update the name if it changed
    if new_name != active_run and new_name.strip():
        st.session_state.all_runs[st.session_state.all_runs_index] = new_name
        st.rerun()
    
    if col2.button("Close"):
        st.session_state.main_mode = 0
        st.rerun()
    
    tab_default, tab_fire = st.tabs(["Default", "Fire plume"])
    
    with tab_default:
        col1, col2 = st.columns(2)
        with col1:
            with st.expander("General", expanded=True):
                runtime = st.number_input(
                    r"runtime (s)",
                    help="total runtime (s)",
                    value=default_settings["runtime"],
                    step=1.0,
                    format="%0.0f",
                )
    
                dt = st.number_input(
                    r"$\Delta t$ (s)",
                    help="time step (s)",
                    value=default_settings["dt"],
                    step=0.1,
                    format="%0.1f",
                )
    
            with st.expander("Mixed layer", expanded=True):
                h = st.number_input(
                    r"$h$ (m)",
                    help="boundary-layer depth (m)",
                    value=default_settings["h"],
                    step=1.0,
                    format="%0.0f",
                )
    
                beta = st.number_input(
                    r"$\beta$ (-)",
                    help="entrainment coefficient (-)",
                    value=default_settings["beta"],
                    step=0.01,
                    format="%0.2f",
                )
    
                ws = st.number_input(
                    r"$w_s$ (-)",
                    help="large-scale vertical velocity (m s-1)",
                    value=default_settings["ws"],
                    step=0.001,
                    format="%0.3f",
                )
    
        with col2:
            with st.expander("Temperature", expanded=True):
                theta = st.number_input(
                    r"$\theta$ (K)",
                    help="mixed-layer potential temperature (K)",
                    value=default_settings["theta"],
                    step=0.1,
                    format="%0.1f",
                )
    
                dtheta = st.number_input(
                    r"$\Delta \theta$ (K)",
                    help="potential temperature jump (K)",
                    value=default_settings["dtheta"],
                    step=0.01,
                    format="%0.2f",
                )
    
                wtheta = st.number_input(
                    r"$\overline{w^\prime \theta^\prime}_s$ (K m s-1)",
                    help="potential temperature surface flux (K m s-1)",
                    value=default_settings["wtheta"],
                    step=0.01,
                    format="%0.2f",
                )
    
                gamma_theta = st.number_input(
                    r"$\gamma_\theta$ (K m-1)",
                    help="potential temperature lapse rate (K m-1)",
                    value=default_settings["gammatheta"],
                    step=0.0001,
                    format="%0.4f",
                )

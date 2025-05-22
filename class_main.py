import streamlit as st
import numpy as np
import pandas as pd


# state to save
if "all_runs" not in st.session_state:
    st.session_state.all_runs = ["default"]
if "all_runs_index" not in st.session_state:
    st.session_state.all_runs_index = 0


# sidebar
with st.sidebar:
    # handle selectbox selection first
    selected_index = st.selectbox(
        "name",
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
    active_run = st.session_state.all_runs[st.session_state.all_runs_index]

    clone_run, clear_runs = st.columns(2)
    if clone_run.button("clone", use_container_width=True):
        cloned_run = active_run + " (clone)"
        st.session_state.all_runs.append(cloned_run)
        st.session_state.all_runs_index = len(st.session_state.all_runs) - 1
        st.rerun()
    if clear_runs.button("clear", use_container_width=True):
        st.session_state.all_runs.clear()
        st.session_state.all_runs = ["default"]
        st.session_state.all_runs_index = 0
        st.rerun()

    st.divider()

    # text input for editing the current run name
    new_name = st.text_input(
        "Edit current run name", value=active_run, key="run_name_input"
    )

    # update the name if it changed
    if new_name != active_run and new_name.strip():
        st.session_state.all_runs[st.session_state.all_runs_index] = new_name
        st.rerun()

    tab_default, tab_fire = st.tabs(["Default", "Fire plume"])

    with tab_default:
        with st.expander("General", expanded=True):
            runtime = st.number_input(
                r"runtime (s)",
                help="total runtime (m)",
            )

            dt = st.number_input(
                r"$\Delta t$ (s)",
                help="time step (s)",
            )

        with st.expander("Mixed layer", expanded=True):
            h = st.number_input(
                r"$h$ (m)",
                help="boundary-layer depth (m)",
            )

            beta = st.number_input(
                r"$\beta$ (-)",
                help="entrainment coefficient (-)",
            )

        with st.expander("Temperature", expanded=True):
            theta = st.number_input(
                r"$\theta$ (K)",
                help="mixed-layer potential temperature (K)",
            )

            dtheta = st.number_input(
                r"$\Delta \theta$ (K)",
                help="potential temperature jump (K)",
            )

            wtheta = st.number_input(
                r"$\overline{w^\prime \theta^\prime}_s$ (K m s-1)",
                help="potential temperature surface flux (K m s-1)",
            )

            gamma_theta = st.number_input(
                r"$\gamma_\theta$ (K m-1)",
                help="potential temperature lapse rate (K m-1)",
            )


# Now active_run will reflect the current name
st.write(f"Active run: {st.session_state.all_runs[st.session_state.all_runs_index]}")

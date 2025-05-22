import streamlit as st
import numpy as np
import pandas as pd


# State to save.
if "all_runs" not in st.session_state:
    st.session_state.all_runs = []


# Sidebar
with st.sidebar:
    active_run = st.selectbox(
        "Name",
        st.session_state.all_runs,
    )

    clone_run, clear_runs = st.columns(2)
    if clone_run.button("Clone", use_container_width=True):
        cloned_run = active_run + " (clone)"
        st.session_state.all_runs.append(cloned_run)
        st.rerun()
    if clear_runs.button("Clear", use_container_width=True):
        all_runs.clear()

    st.divider()

    run_name = st.text_input("Run name")
    start_run, delete_run = st.columns(2)

    if start_run.button("Run", use_container_width=True):
        st.session_state.all_runs.append(run_name)
        st.rerun()
    if delete_run.button("Delete", use_container_width=True):
        all_runs.remove(run_name)

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


# Main window
x = np.arange(0, 10, 0.01)
y = np.sin(x)
y2 = 2 * np.sin(3 * x)

run1 = pd.DataFrame({"x": x, "y": y, "y2": y2})

if "plots" not in st.session_state:
    st.session_state.plots = []

new_plot_clicked = st.button("New plot")
if new_plot_clicked:
    st.session_state.plots.append("Oioi")

for plot in st.session_state.plots:
    with st.container(border=True):
        st.subheader(plot)
        st.line_chart(run1, x="x", y=["y", "y2"])

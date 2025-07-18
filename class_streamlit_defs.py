from enum import Enum, auto
import numpy as np
import pandas as pd
import datetime


# IMPORTANT!
# All implementations here are in a separate file, because otherwise Streamlit keeps
# defining them, and then Enum ==  and isinstance do not work properly.


# Some constants.
cp = 1005.0
Lv = 2.5e6
Rd = 287.04
Rv = 461.5
p0 = 1e5
g = 9.81
ep = 0.622


class MainMode(Enum):
    PLOT = auto()
    EDIT = auto()
    SOUNDING = auto()


def virtual_temperature(t, qt, ql):
    tv = t * (1.0 - (1.0 - Rv/Rd) * qt - Rv/Rd * ql)
    return tv


def esat_liq(t):
    Tc = t - 273.15
    Tc = min(Tc, 50) # Avoid excess values
    esat = 611.21 * np.exp(17.502 * Tc / (240.97 + Tc))
    return esat


def qsat_liq(p, t):
    qsat = ep * esat_liq(t) / (p - (1.0 - ep) * esat_liq(t))
    return qsat


def dqsatdT_liq(p, t):
    den = p - esat_liq(t)*(1.0 - ep)
    dqsatdT = (ep/den + (1.0 - ep)*ep*esat_liq(t)/den**2) * Lv*esat_liq(t) / (Rv*t**2)
    return dqsatdT


# Define a function to compute thetav (do saturation adjustment)
def calc_thetav(thl, qt, p, exner):
    # Define the starting values of the adjustment.
    tl = exner * thl
    qsat = qsat_liq(p, tl)
    ql = 0.0

    if qt - qsat <= 0.0:
        return virtual_temperature(thl, qt, 0.0), ql

    # Solve the adjustment problem.
    niter = 0
    nitermax = 100
    tnr = tl
    tnr_old = 1e9

    while (np.abs(tnr - tnr_old) / tnr_old > 1e-5) and (niter < nitermax):
        niter +=1
        tnr_old = tnr
        qsat = qsat_liq(p, tnr)
        f = tnr - tl - Lv/cp*(qt - qsat)
        f_prime = 1 + Lv/cp*dqsatdT_liq(p, tnr)

        tnr -= f / f_prime

    ql = qt - qsat
    return virtual_temperature(tnr/exner, qt, ql), ql


class MixedLayerModel:
    class Output:
        pass


    class Input:
        pass


    def __init__(self, settings, color_index):
        self.settings = settings
        self.color_index = color_index

        self.runtime = settings["runtime"]
        self.starttime = settings["starttime"]
        self.startdate = settings["startdate"]
        self.dt = settings["dt"]
        self.dt_output = settings["dt_output"]

        self.h = settings["h"]
        self.beta = settings["beta"]
        self.div = settings["div"]

        self.theta = settings["theta"]
        self.dtheta = settings["dtheta"]
        self.wtheta = settings["wtheta"]
        self.gammatheta = settings["gammatheta"]

        self.q = settings["q"]
        self.dq = settings["dq"]
        self.wq = settings["wq"]
        self.gammaq = settings["gammaq"]

        # CvH: this should go elsewhere, is separate model.
        # Save also the fire plume settings in here.
        self.dtheta_plume = settings["dtheta_plume"]
        self.dq_plume = settings["dq_plume"]

        self.run()


    def step(self):
        # First, compute the growth, assume no condensation in virtual temp calculations.
        wthetav = self.wtheta * (1.0 + (Rv/Rd - 1.0) * self.q) + (Rv/Rd - 1.0) * self.theta * self.wq
        thetav = virtual_temperature(self.theta, self.q, 0.0)
        dthetav = virtual_temperature(self.theta + self.dtheta, self.q + self.dq, 0.0) - thetav

        we = self.beta * wthetav / dthetav
        ws = - self.h * self.div

        # Compute the tendencies.
        dhdt = we + ws

        dthetadt = (self.wtheta + we * self.dtheta) / self.h
        ddthetadt = we * self.gammatheta - dthetadt

        dqdt = (self.wq + we * self.dq) / self.h
        ddqdt = we * self.gammaq - dqdt

        # Integrate the variables.
        self.time += self.dt
        self.h += self.dt * dhdt
        self.theta += self.dt * dthetadt
        self.dtheta += self.dt * ddthetadt
        self.q += self.dt * dqdt
        self.dq += self.dt * ddqdt


    def run(self):
        self.time = 0

        nt = round(self.runtime / self.dt)
        nt_output = round(nt * self.dt / self.dt_output) + 1
        nt_ratio = round(self.dt_output / self.dt)

        # Output
        output = self.Output()
        output.time = np.nan * np.zeros(nt_output)
        output.h = np.nan * np.zeros(nt_output)
        output.theta = np.nan * np.zeros(nt_output)
        output.dtheta = np.nan * np.zeros(nt_output)
        output.q = np.nan * np.zeros(nt_output)
        output.dq = np.nan * np.zeros(nt_output)
        output.thetav = np.nan * np.zeros(nt_output)
        output.dthetav = np.nan * np.zeros(nt_output)

        output.time[0] = self.time
        output.h[0] = self.h
        output.theta[0] = self.theta
        output.dtheta[0] = self.dtheta
        output.q[0] = self.q
        output.dq[0] = self.dq
        output.thetav[0] = virtual_temperature(self.theta, self.q, 0.0)
        output.dthetav[0] = virtual_temperature(self.theta + self.dtheta, self.q + self.dq, 0.0) - output.thetav[0]

        for i in range(1, nt+1):
            self.step()

            if (i % nt_ratio) == 0:
                ii = i // nt_ratio
                output.time[ii] = self.time / 3600 # convert to hours.
                output.h[ii] = self.h
                output.theta[ii] = self.theta
                output.dtheta[ii] = self.dtheta
                output.q[ii] = self.q
                output.dq[ii] = self.dq
                output.thetav[ii] = virtual_temperature(self.theta, self.q, 0.0)
                output.dthetav[ii] = virtual_temperature(self.theta + self.dtheta, self.q + self.dq, 0.0) - output.thetav[ii]

        full_datetime = datetime.datetime.combine(self.startdate, self.starttime)
        output.datetime_utc = [ (full_datetime + datetime.timedelta(hours=time)) for time in output.time ]

        self.output = pd.DataFrame(data = {
            "time": output.time,
            "time UTC": output.datetime_utc,
            "h": output.h,
            "theta": output.theta,
            "dtheta": output.dtheta,
            "q": output.q * 1e3,
            "dq": output.dq * 1e3,
            "thetav": output.thetav,
            "dthetav": output.dthetav,
            },
        )


    def launch_entraining_plume(self, time, fire_multiplier, skewt=False):
        idx = round(time / self.dt_output)

        theta = self.output.theta[idx]
        dtheta = self.output.dtheta[idx]

        q = self.output.q[idx] * 1e-3
        dq = self.output.dq[idx] * 1e-3

        h = self.output.h[idx]

        # Create the grid.
        dz = 10
        z = np.arange(0, 2.0*self.output.h.values[-1] + dz/2, dz) # Extend the grid to twice the max ABL height.

        # Create the environmental profiles
        theta_env = np.where(z < h, theta, theta + dtheta + (z - h)*self.gammatheta)
        q_env = np.where(z < h, q, q + dq + (z - h)*self.gammaq)

        thetav_env = np.zeros_like(z)
        p_env = np.zeros_like(z)
        exner_env = np.zeros_like(z)

        # Compute the pressure profile.
        p_Rdcp = np.zeros_like(z)
        p_Rdcp[0] = p0**(Rd/cp)
        p_env[0] = p_Rdcp[0]**(cp/Rd)
        exner_env[0] = (p_env[0]/p0)**(Rd/cp)

        thetav_env[0], ql = calc_thetav(theta_env[0], q_env[0], p_env[0], exner_env[0])

        for i in range(1, len(z)):
            p_Rdcp[i] = p_Rdcp[i-1] - g/cp * p0**(Rd/cp) / thetav_env[i-1] * dz
            p_env[i] = p_Rdcp[i]**(cp/Rd)
            exner_env[i] = (p_env[i]/p0)**(Rd/cp)
            thetav_env[i], ql = calc_thetav(theta_env[i], q_env[i], p_env[i], exner_env[i])
            if ql > 0:
                print(f"Warning, environmental profile is saturated at z = {z[i]} m")

        rho_env = p_env / (Rd * exner_env * thetav_env)

        # Compute the entraining plume ascent.
        theta_plume = np.zeros_like(z)
        q_plume = np.zeros_like(z)
        thetav_plume = np.zeros_like(z)
        area_plume = np.zeros_like(z)
        w_plume = np.zeros_like(z)
        mass_flux_plume = np.zeros_like(z)
        entrainment_plume = np.zeros_like(z)
        detrainment_plume = np.zeros_like(z)
        type_plume = np.zeros_like(z, dtype=np.int8)

        # Initial plume conditions.
        theta_plume[0] = theta_env[0] + fire_multiplier*self.dtheta_plume
        q_plume[0] = q_env[0] + fire_multiplier*self.dq_plume
        thetav_plume[0], _ = calc_thetav(theta_plume[0], q_plume[0], p_env[0], exner_env[0])
        area_plume[0] = 300_000 # 1,000 * 300 from Martin's script for Martorell.
        w_plume[0] = 0.1

        mass_flux_plume[0] = rho_env[0] * area_plume[0] * w_plume[0]

        fac_ent = 0.0025
        beta = 0.75
        epsi = fac_ent*beta
        delt = epsi/beta

        a_w = 1.0
        b_w = 0.1

        entrainment_plume[0] = epsi*mass_flux_plume[0]
        detrainment_plume[0] = 0.0

        for i in range(1, len(z)):
            mass_flux_plume[i] = mass_flux_plume[i-1] + (entrainment_plume[i-1] - detrainment_plume[i-1])*dz
            theta_plume[i] = theta_plume[i-1] - entrainment_plume[i-1]*(theta_plume[i-1] - theta_env[i-1]) / mass_flux_plume[i-1] * dz
            q_plume[i] = q_plume[i-1] - entrainment_plume[i-1]*(q_plume[i-1] - q_env[i-1]) / mass_flux_plume[i-1] * dz

            thetav_plume[i], ql = calc_thetav(theta_plume[i], q_plume[i], p_env[i], exner_env[i])

            if ql > 0:
                type_plume[i] = 1

            buoy_m = g/thetav_env[i-1] * (thetav_plume[i-1] - thetav_env[i-1])

            w_plume[i] = (max(0, w_plume[i-1]**2 + 2*(a_w*buoy_m - b_w*epsi*w_plume[i-1]**2) * dz))**.5

            entrainment_plume[i] = epsi * mass_flux_plume[i]
            detrainment_plume[i] = delt * mass_flux_plume[i]

            w_eps = 1e-6
            area_plume[i] = mass_flux_plume[i] / (rho_env[i] * (w_plume[i] + w_eps))

            if (area_plume[i] <= 0) or (w_plume[i] < w_eps):
                break

        if skewt:
            return exner_env[:i] * theta_plume[:i] - 273.15, type_plume[:i], p_env[:i] / 100.0
        else:
            return theta_plume[:i], q_plume[:i] * 1e3, thetav_plume[:i], type_plume[:i], z[:i]


class LinePlot:
    def __init__(self):
        self.xaxis_options = ["time", "time UTC"]
        self.yaxis_options = ["h", "theta", "dtheta", "q", "dq", "thetav", "dthetav"]
        self.xaxis_index = 0
        self.yaxis_index = 0
        self.xaxis_key = self.xaxis_options[0]
        self.yaxis_key = self.yaxis_options[0]
        self.selected_runs = []


class ProfilePlot:
    def __init__(self):
        self.xaxis_options = ["theta", "q", "thetav"]
        self.xaxis_index = 0
        self.xaxis_key = self.xaxis_options[0]
        self.time_plot = (0.0, 1.0)
        self.selected_runs = []


class PlumePlot:
    def __init__(self):
        self.xaxis_options = ["theta", "q", "thetav"]
        self.xaxis_index = 0
        self.xaxis_key = self.xaxis_options[0]
        self.time_plot = (0.0, 1.0)
        self.selected_runs = []


class SkewPlot:
    def __init__(self):
        self.time_plot = 0.0
        self.selected_runs = []


# Transform function for skewing
def skew_transform(temp_c, pressure_hpa):
    # Skewing factor - adjust this to change the skew angle
    skew_factor = 30  # degrees
    log_p = np.log(pressure_hpa)
    skewed_temp = temp_c + skew_factor * (np.log(1000) - log_p)
    return skewed_temp


def calc_skew_lines(h, theta, dtheta, gammatheta, q, dq, gammaq, p0):
    # Create the grid.
    dz = 10
    z_max = 5_000

    z = np.arange(0, z_max + dz/2, dz) # Extend the grid to twice the max ABL height.

    # Create the environmental profiles
    theta_env = np.where(z < h, theta, theta + dtheta + (z - h)*gammatheta)
    q_env = np.where(z < h, q, q + dq + (z - h)*gammaq)

    thetav_env = np.zeros_like(z)
    p_env = np.zeros_like(z)
    exner_env = np.zeros_like(z)

    # Compute the pressure profile.
    p_Rdcp = np.zeros_like(z)
    p_Rdcp[0] = p0**(Rd/cp)
    p_env[0] = p_Rdcp[0]**(cp/Rd)
    exner_env[0] = (p_env[0]/p0)**(Rd/cp)

    thetav_env[0], ql = calc_thetav(theta_env[0], q_env[0], p_env[0], exner_env[0])

    for i in range(1, len(z)):
        p_Rdcp[i] = p_Rdcp[i-1] - g/cp * p0**(Rd/cp) / thetav_env[i-1] * dz
        p_env[i] = p_Rdcp[i]**(cp/Rd)
        exner_env[i] = (p_env[i]/p0)**(Rd/cp)
        thetav_env[i], ql = calc_thetav(theta_env[i], q_env[i], p_env[i], exner_env[i])
        if ql > 0:
            print(f"Warning, environmental profile is saturated at z = {z[i]} m")

    rho_env = p_env / (Rd * exner_env * thetav_env)

    T_env = exner_env * theta_env - 273.15 # In Celcius
    w_env = q_env / (1.0 - q_env)
    e_env = (w_env * p_env) / (0.622 + w_env)
    Td_env = (243.12 * np.log(e_env/611.2)) / (17.62 - np.log(e_env/611.2))

    return p_env / 100, T_env, Td_env


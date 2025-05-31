import copy
import numpy as np
import pandas as pd


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
        nt_output = round(nt * self.dt / self.dt_output) + 1
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

        for i in range(1, nt+1):
            self.step()

            if (i % nt_ratio) == 0:
                ii = i // nt_ratio
                output.time[ii] = self.time / 3600 # convert to hours.
                output.h[ii] = self.h
                output.theta[ii] = self.theta
                output.dtheta[ii] = self.dtheta

        self.output = pd.DataFrame(data = {
            "time": output.time,
            "h": output.h,
            "theta": output.theta,
            "dtheta": output.dtheta}) #.set_index("time") do not set index, so time can be queried


class LinePlot:
    def __init__(self):
        self.xaxis_options = ["time", "time UTC"]
        self.yaxis_options = ["h", "theta", "dtheta"]
        self.xaxis_index = 0
        self.yaxis_index = 0
        self.xaxis_key = self.xaxis_options[0]
        self.yaxis_key = self.yaxis_options[0]
        self.selected_runs = []


class ProfilePlot:
    def __init__(self):
        self.xaxis_options = ["theta"]
        self.xaxis_index = 0
        self.xaxis_key = self.xaxis_options[0]
        self.time_plot = 0.0
        self.selected_runs = []

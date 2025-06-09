import numpy as np
import pandas as pd


# Sounding 1
h = 200

theta = 285.0
dtheta = 4.0
gammatheta = 0.006

q = 0.006
dq = -0.001
gammaq = 0.0

dz = 25.0
z = np.arange(dz/2, 1200.0, dz)

theta_plot = np.where(z < h, theta, theta + dtheta + gammatheta*(z - h)) + (np.random.rand(len(z)) - 0.5)
q_plot = np.where(z < h, q, q + dq + gammaq*(z - h)) + 0.0005*(np.random.rand(len(z)) - 0.5)

df = pd.DataFrame(data={
    "z": z,
    "theta": theta_plot,
    "q": q_plot*1e3,
})

df.to_csv("cabauw_sounding_1.csv", index=False)


# Sounding 2
h = 765.0

theta = 291.3
dtheta = 1.05
gammatheta = 0.006

q = 0.00667
dq = -0.00167
gammaq = 0.0

dz = 25.0
z = np.arange(dz/2, 1200.0, dz)

theta_plot = np.where(z < h, theta, theta + dtheta + gammatheta*(z - h)) + (np.random.rand(len(z)) - 0.5)
q_plot = np.where(z < h, q, q + dq + gammaq*(z - h)) + 0.0005*(np.random.rand(len(z)) - 0.5)

df = pd.DataFrame(data={
    "z": z,
    "theta": theta_plot,
    "q": q_plot*1e3,
})

df.to_csv("cabauw_sounding_2.csv", index=False)

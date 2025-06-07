import numpy as np
import pandas as pd

h = 200

theta = 285.0
dtheta = 4.0
wtheta = 0.15
gammatheta = 0.006

q = 0.006
dq = -0.001
wq = 1e-4
gammaq = 0.0

dz = 25.0
z = np.arange(dz/2, 1.5*h, dz)

theta_plot = np.where(z < h, theta, theta + dtheta + gammatheta*(z - h)) + np.random.rand(len(z))
q_plot = np.where(z < h, q, q + dq + gammaq*(z - h)) + 0.001*np.random.rand(len(z))


df = pd.DataFrame(data={
    "z": z,
    "theta": theta_plot,
    "q": q_plot,
})

df.to_csv("cabauw_sounding.csv")

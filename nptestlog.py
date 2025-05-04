import numpy as np
import pandas as pd
from Calculation import Calculations as calc
import matplotlib.pyplot as plt

log_ffi = {'x_pos': [1, 2, 3, 4.1, 10, 50, 150, 200],
           'y_pos': [0, 0, 0, 0, 0, 0, 0, 0],
           'time': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]}

mode = 'X'

a = calc.testFFI(log_ffi, mode)
plt.show()
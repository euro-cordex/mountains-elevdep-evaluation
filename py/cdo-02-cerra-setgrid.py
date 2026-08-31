# calc monthly means using CDO
import os
import glob
from cdo import Cdo
import re

cdo = Cdo()

grid_file = "/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/mon/tas/tas_CERRA_mon_1984.nc"

variable = "tasmax"

path_in = os.path.join("/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/mon/", variable+"2")
path_out = os.path.join("/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/mon/", variable)

if not os.path.exists(path_out):
    os.makedirs(path_out)


all_files = os.listdir(path_in)
all_files.sort()

for file in all_files:
    if file.endswith(".nc"):
        # year = re.search(r'\d{4}', file).group()
        # file_out = f"{variable}_CERRA_mon_{year}.nc"
        input_file = os.path.join(path_in, file)
        output_file = os.path.join(path_out, file)
        cdo.setgrid(grid_file, input=input_file, output=output_file)



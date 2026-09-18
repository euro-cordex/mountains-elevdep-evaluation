# calc precsep with CDO
import os
import glob
from cdo import Cdo
import re

cdo = Cdo()

path_out = os.path.join("/mnt/CORDEX_CMIP6_tmp/user_tmp/mmatiu/cerra-precsep/")
if not os.path.exists(path_out):
    os.makedirs(path_out)

path_temp = os.path.join(path_out, "tmp")
if not os.path.exists(path_temp):
    os.makedirs(path_temp)

all_files_tasmax = os.listdir("/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmax/")
all_files_tasmax.sort()
all_files_tasmin = os.listdir("/mnt/CORDEX_CMIP6_tmp/aux_data/cerra/day/tasmin/")
all_files_tasmin.sort()
all_files_pr = os.listdir("/mnt/CORDEX_CMIP6_tmp/aux_data/cerra-land/day/pr/")
all_files_pr.sort()


for year in range(1991, 2021):

    file_tas = os.path.join(path_temp, "tas_" + str(year) + ".nc")
    cdo.

file_out = os.path.join(i_path_out, "HN.nc")
# file_in_chain = (" -ifthen -ltc,2 " + file_in_tasmin +
#                  " -mul " + file_in_pr + 
#                  " -div -subc,2 " + file_in_tasmin + 
#                  " -sub " + file_in_tasmin + " " + file_in_tasmax)
file_in_chain = ("-setmisstoc,0 -ifthen -ltc,2 " + file_in_tas + " " + file_in_pr)
file_tmp = os.path.join(path_temp, "beforemask.nc")
if not os.path.exists(file_out):
    cdo.yearsum(input=file_in_chain, output=file_tmp)
    cdo.div(input=file_tmp+" -gtc,-1 -timmin "+file_in_pr,output=file_out) # for masking



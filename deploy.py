#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2021/9/3 22:32


"""部署BioPlot至集群"""


import os
import subprocess

path = os.path.realpath(os.path.dirname(__file__))

# 1. uwsgi部署值c1b01，c2b01,c3b01
host_map = {
    "c15b02": "10.1.2.78:50002",
    "c16b01": "10.1.2.81:50003",
    "c17b01": "10.1.2.85:50004",
}


for name, host in host_map.items():
    print(f"deploy to {host}")
    cmd = f"uwsgi " \
          f"--ini uwsgi.ini " \
          f"--http {host} " \
          f"--processes=20 " \
          f"--threads=5 " \
          f"--chdir={path} >> {path}/log/uwsgi.{name}.log"
    print(cmd)
    cmd = f'bsub -J BioPlotServer -q high -n 20 -R "span[hosts=1]" -m {name} "{cmd}"'
    subprocess.check_call(cmd, shell=True)

print(f"run 'nginx -c /dssg/home/sheny/MyProject/BioPlot/destiny.conf'")
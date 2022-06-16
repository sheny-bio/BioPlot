#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2021/9/3 22:32


"""部署BioPlot至阿里云"""


import os
import subprocess

path = os.path.realpath(os.path.dirname(__file__))

# 1. uwsgi部署值c1b01，c2b01,c3b01
host_map = {
    "c15b02": "0.0.0.0:50002",
    "c16b01": "0.0.0.0:50003",
    "c17b01": "0.0.0.0:50004",
}


for name, host in host_map.items():
    print(f"deploy to {host}")
    cmd = f"uwsgi " \
          f"--ini uwsgi.ini " \
          f"--http {host} " \
          f"--processes=20 " \
          f"--threads=20 " \
          f"--chdir={path} >> {path}/log/uwsgi.{name}.log"
    print(cmd)
    cmd = f'nohup {cmd} &'
    subprocess.Popen(cmd, shell=True)

print(f"run 'nginx -c /root/MyProject/BioPlot/destiny_aliyun.conf'")
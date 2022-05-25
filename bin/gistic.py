#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2021/6/7 16:43


"""合并seg文件，并做gistic分析"""

from glob import glob
import os
import subprocess

import click
import pandas as pd


def analyze_gistic(d_segs, d_output, id, ta, td, rx, cap, qvt, broad, brlen, genegistic, path_gistic, path_mat):

    # 生成combine.seg文件
    files = glob(f"{d_segs}/*.seg")
    f_combine = f"{d_output}/combine.seg"
    d_rslt = f"{d_output}/Results"
    if not os.path.exists(d_rslt):
        os.makedirs(d_rslt)

    rslt = []
    for file in files:
        name = os.path.basename(file).replace(".seg", "")
        df_t = pd.read_csv(file)
        df_t.chrom = df_t.chrom.astype(str)
        df_t = df_t[df_t.chrom != "23"]
        df_t["sampleid"] = name
        df_t = df_t[["sampleid", "chrom", "start", "end", "num.mark", "cnlr.median"]]
        rslt.append(df_t)
    df_combine = pd.concat(rslt, ignore_index=True, sort=False)
    df_combine.to_csv(f_combine, sep="\t", index=False, header=None)

    cmd = f"{path_gistic} -b {d_rslt} -seg {f_combine} -refgene {path_mat} " \
          f"-ta {ta} -td {td} -fname {id} -rx {rx} -cap {cap} -qvt {qvt} -broad {broad} -brlen {brlen} -genegistic {genegistic}"
    subprocess.check_call(cmd, shell=True)
    # subprocess.check_call(f"zip -j -r {d_output}/{id}.gistic.zip {d_rslt}/*", shell=True)


@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option(f"--d_segs")
@click.option(f"--d_output")
@click.option(f"--id")
@click.option(f"--ta")
@click.option(f"--td")
@click.option(f"--rx")
@click.option(f"--cap")
@click.option(f"--qvt")
@click.option(f"--broad")
@click.option(f"--brlen")
@click.option(f"--genegistic")
@click.option(f"--path_gistic", default="/dssg/home/sheny/software/GISTIC2/gistic2", show_default=True)
@click.option(f"--path_mat", default="/dssg/home/sheny/database/soft/GISTIC/hg19.mat", show_default=True)
def cli(**kwargs):
    analyze_gistic(**kwargs)


if __name__ == '__main__':
    cli()

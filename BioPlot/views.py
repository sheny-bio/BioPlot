#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2020-11-23 11:12

import os
import time
import uuid
import subprocess
import shutil


from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from BioPlot.form import *
from BioPlot.form import KeggForm
from glob import glob
from django.http import FileResponse
from django.views import View


def navigation(request):
    """进入导航页"""
    host = request.get_host()
    ip = host.split(":")[0]
    return render(request, 'navigation.html', context={"ip": ip})


def home(request):
    return render(request, 'home.html')


def home_pipeline(request):
    return render(request, 'home_pipeline.html')


def home_plot(request):
    return render(request, 'home_plot.html')


def home_rd(request):
    return render(request, 'home_rd.html')


def plot_mut_cnv(request):
    """mut_cnv作图"""

    if request.method == "GET":
        return render(request, 'plot/plot_mut_cnv.html')


def plot_mut_cnv_doc(request):
    return render(request, 'document/plot_mut_cnv_doc.html')


def plot_heatmap(request):
    """热图绘制"""

    return render(request, 'plot/plot_heatmap.html')


def plot_heatmap_doc(request):

    return render(request, 'document/plot_heatmap_doc.html')


def plot_dot(request):
    """散点图"""

    rslt = {
        "family": ["serif", "sans", "Times"],
        "face": ["plain", "italic", "bold", "bold.italic"],
        "linetype": ["blank", "solid", "dashed", "dotted", "dotdash", "logndash", "twodash"],
        "position": ["none", "left", "right", "top", "botton", "XY"],
        "direction": ["vertical", "horizontal"],
        "color_seq": ["YIOrRd", "YIOrBr", "YIGnBu", "YIGn", "Reds", "RdPu", "Purples", "PuRd", "PuBuGn", "PuBu", "OrRd",
                      "Oranges", "Greys", "Greens", "GnBu", "BuPu", "BuGn", "Blues"],
        "color_qual": ["Sepectral", "RdYIGn", "RdYIBu", "RdGy", "RdBu", "PuOr", "PRGn", "PiYG", "BrBG", "Set3",
                       "Set2", "Set1", "Pastel2", "Pastel1", "Paired", "Dark2", "Accent"],

        "plot_themes": ["gray", "bw", "linedraw", "light", "dark", "minimal", "classic", "void"]
    }

    return render(request, 'plot/plot_dot.html', rslt)


def plot_dot_doc(request):
    """散点图说明文档"""

    return HttpResponse("散点图说明文档")


def plot_boxplot(request):
    """散点图"""

    rslt = {
        "family": ["serif", "sans", "Times"],
        "face": ["plain", "italic", "bold", "bold.italic"],
        "linetype": ["blank", "solid", "dashed", "dotted", "dotdash", "logndash", "twodash"],
        "position": ["none", "left", "right", "top", "botton", "XY"],
        "direction": ["vertical", "horizontal"],
        "color_seq": ["YIOrRd", "YIOrBr", "YIGnBu", "YIGn", "Reds", "RdPu", "Purples", "PuRd", "PuBuGn", "PuBu", "OrRd",
                      "Oranges", "Greys", "Greens", "GnBu", "BuPu", "BuGn", "Blues"],
        "color_qual": ["Sepectral", "RdYIGn", "RdYIBu", "RdGy", "RdBu", "PuOr", "PRGn", "PiYG", "BrBG", "Set3",
                       "Set2", "Set1", "Pastel2", "Pastel1", "Paired", "Dark2", "Accent"]

    }

    return render(request, 'plot/plot_boxplot.html', rslt)


def plot_boxplot_doc(request):
    """散点图说明文档"""

    return HttpResponse("箱线图图说明文档")


def plot_line(request):
    """散点图"""

    rslt = {
        "family": ["serif", "sans", "Times"],
        "face": ["plain", "italic", "bold", "bold.italic"],
        "linetype": ["blank", "solid", "dashed", "dotted", "dotdash", "logndash", "twodash"],
        "position": ["none", "left", "right", "top", "botton", "XY"],
        "direction": ["vertical", "horizontal"],
        "color_seq": ["YIOrRd", "YIOrBr", "YIGnBu", "YIGn", "Reds", "RdPu", "Purples", "PuRd", "PuBuGn", "PuBu", "OrRd",
                      "Oranges", "Greys", "Greens", "GnBu", "BuPu", "BuGn", "Blues"],
        "color_qual": ["Sepectral", "RdYIGn", "RdYIBu", "RdGy", "RdBu", "PuOr", "PRGn", "PiYG", "BrBG", "Set3",
                       "Set2", "Set1", "Pastel2", "Pastel1", "Paired", "Dark2", "Accent"]

    }

    return render(request, 'plot/plot_line.html', rslt)


def plot_line_doc(request):
    """折线图图说明文档"""

    return HttpResponse("折线图说明文档")


def plot_bar(request):
    """柱形图图"""

    rslt = {
        "family": ["serif", "sans", "Times"],
        "face": ["plain", "italic", "bold", "bold.italic"],
        "linetype": ["blank", "solid", "dashed", "dotted", "dotdash", "logndash", "twodash"],
        "position": ["none", "left", "right", "top", "botton", "XY"],
        "direction": ["vertical", "horizontal"],
        "color_seq": ["YIOrRd", "YIOrBr", "YIGnBu", "YIGn", "Reds", "RdPu", "Purples", "PuRd", "PuBuGn", "PuBu", "OrRd",
                      "Oranges", "Greys", "Greens", "GnBu", "BuPu", "BuGn", "Blues"],
        "color_qual": ["Sepectral", "RdYIGn", "RdYIBu", "RdGy", "RdBu", "PuOr", "PRGn", "PiYG", "BrBG", "Set3",
                       "Set2", "Set1", "Pastel2", "Pastel1", "Paired", "Dark2", "Accent"]

    }

    return render(request, 'plot/plot_bar.html', rslt)


def plot_bar_doc(request):
    """柱形图说明文档"""

    return HttpResponse("柱形图说明文档")


def plot_oncoprint(request):
    """oncoprint图分析"""

    return render(request, 'plot/plot_oncoprint.html')


def plot_oncoprint_doc(request):
    """oncoprint说明文档"""

    return render(request, 'document/plot_oncoprint_doc.html')


def plot_hrd_density(request):

    return render(request, 'plot/plot_hrd_density.html')


def plot_hrd_density_doc(request):

    return render(request, "document/plot_hrd_density_doc.html")


def plot_swimmer(request):
    """泳图"""

    return render(request, 'plot/plot_swimmer.html')


def plot_swimmer_doc(request):
    """泳图文档"""

    return HttpResponse("泳图文档")


def pipeline_gistic(request):
    """gistic分析页面"""

    return render(request, 'pipeline/pipeline_gistic.html')


def pipeline_gistic_rslt(request):
    """gistic结果展示页面"""

    return render(request, 'rslt_home/pipeline_gistic_rslt.html')


def pipeline_gistic_doc(request):

    file_path = f"{os.path.dirname(__file__)}/../templates/document/pipeline_gistic_doc.pdf"
    data = open(file_path, "rb").read()
    response = HttpResponse(data, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{os.path.basename(file_path)}"'
    return response


def pipeline_kegg(request):

    return render(request, 'pipeline/pipeline_kegg.html')


def pipeline_kegg_rslt(request):

    return render(request, 'rslt_home/pipeline_kegg_rslt.html')


def pipeline_kegg_doc(request):

    return render(request, 'document/pipeline_kegg_doc.html')


def others_layui_index(request):
    """layui说明文档 -- 主页"""

    url = request.GET.get("url")

    return render(request, f'others/layui/{url}')


###################################################  研发部门相关工具 ###########################################

def plot_rd_qc_boxplot(request):
    """研发质控箱线图"""

    rslt = {
        "family": ["serif", "sans", "Times"],
        "face": ["plain", "italic", "bold", "bold.italic"],
        "linetype": ["blank", "solid", "dashed", "dotted", "dotdash", "logndash", "twodash"],
        "position": ["none", "left", "right", "top", "botton", "XY"],
        "direction": ["vertical", "horizontal"],
        "color_seq": ["YIOrRd", "YIOrBr", "YIGnBu", "YIGn", "Reds", "RdPu", "Purples", "PuRd", "PuBuGn", "PuBu", "OrRd",
                      "Oranges", "Greys", "Greens", "GnBu", "BuPu", "BuGn", "Blues"],
        "color_qual": ["Sepectral", "RdYIGn", "RdYIBu", "RdGy", "RdBu", "PuOr", "PRGn", "PiYG", "BrBG", "Set3",
                       "Set2", "Set1", "Pastel2", "Pastel1", "Paired", "Dark2", "Accent"],
        "classic": ["gray", "bw", "linedraw", "light", "dark", "minimal", "classic", "void"]

    }

    return render(request, 'plot/plot_rd_qc_boxplot.html', rslt)


def plot_rd_qc_lineplot(request):
    """研发质控折线图"""

    rslt = {
        "family": ["serif", "sans", "Times"],
        "face": ["plain", "italic", "bold", "bold.italic"],
        "linetype": ["blank", "solid", "dashed", "dotted", "dotdash", "logndash", "twodash"],
        "position": ["none", "left", "right", "top", "botton", "XY"],
        "direction": ["vertical", "horizontal"],
        "color_seq": ["YIOrRd", "YIOrBr", "YIGnBu", "YIGn", "Reds", "RdPu", "Purples", "PuRd", "PuBuGn", "PuBu", "OrRd",
                      "Oranges", "Greys", "Greens", "GnBu", "BuPu", "BuGn", "Blues"],
        "color_qual": ["Sepectral", "RdYIGn", "RdYIBu", "RdGy", "RdBu", "PuOr", "PRGn", "PiYG", "BrBG", "Set3",
                       "Set2", "Set1", "Pastel2", "Pastel1", "Paired", "Dark2", "Accent"]

    }

    return render(request, 'plot/plot_rd_qc_line.html', rslt)
#################################################################################################################














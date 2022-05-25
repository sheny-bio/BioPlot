"""BioPlot URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from . import views

urlpatterns = [
    path('get_file/', views.get_file, name="get_file"),
    path('file_columns/', views.file_columns, name="file_columns"),
    path('upload_file/', views.upload_file, name="upload_file"),
    path('check_job_status/', views.check_job_status, name="check_job_status"),
    path('give_me_directory/', views.give_me_directory, name="give_me_directory"),
    path('download/', views.download, name="download"),
    path('group_by_file/', views.group_by_file, name="group_by_file"),

    path('plot/heatmap/', views.plot_heatmap, name="plot_heatmap"),
    path('plot/dot/', views.plot_dot, name="plot_dot"),
    path('plot/boxplot/', views.plot_boxplot, name="plot_boxplot"),
    path('plot/line/', views.plot_line, name="plot_line"),
    path('plot/bar/', views.plot_bar, name="plot_bar"),

    path('plot/mut_cnv/', views.plot_mut_cnv, name="plot_mut_cnv"),
    path('plot/hrd_density/', views.plot_hrd_density, name="plot_hrd_density"),
    path('plot/hrd_oncoprint/', views.plot_oncoprint, name="plot_oncoprint"),
    path('plot/swimmer/', views.plot_swimmer, name="plot_swimmer"),

    path('pipeline/kegg/', views.pipeline_kegg, name="pipeline_kegg"),
    path('pipeline/kegg/rslt', views.pipeline_kegg_rslt, name="pipeline_kegg_rslt"),

    path('pipeline/gistic/', views.pipeline_gistic, name="pipeline_gistic"),
    path('pipeline/gistic/rslt', views.pipeline_gistic_rslt, name="pipeline_gistic_rslt"),

    # 研发部相关工具
    path('plot/rd_qc_boxplot/', views.plot_rd_qc_boxplot, name="plot_rd_qc_boxplot"),
    path('plot/rd_qc_line/', views.plot_rd_qc_line, name="plot_rd_qc_line"),
]

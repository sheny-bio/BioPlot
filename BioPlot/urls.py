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
from django.conf.urls.static import static
from django.conf import settings

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.navigation, name="navigation"),
    path('backstage/', include(('backstage.urls', 'backstage'), namespace='backstage')),

    path('home/', views.home, name="home"),
    path('home/pipeline/', views.home_pipeline, name="home_pipeline"),
    path('home/plot/', views.home_plot, name="home_plot"),
    path('home/rd/', views.home_rd, name="home_rd"),

    path('plot/mut_cnv/', views.plot_mut_cnv, name='plot_mut_cnv'),
    path('plot/mut_cnv/doc', views.plot_mut_cnv_doc, name='plot_mut_cnv_doc'),

    path('plot/heatmap/', views.plot_heatmap, name='plot_heatmap'),
    path('plot/heatmap/doc/', views.plot_heatmap_doc, name='plot_heatmap_doc'),

    path('plot/dot/', views.plot_dot, name='plot_dot'),
    path('plot/dot/doc', views.plot_dot_doc, name='plot_dot_doc'),

    path('plot/boxplot/', views.plot_boxplot, name='plot_boxplot'),
    path('plot/boxplot/doc', views.plot_boxplot_doc, name='plot_boxplot_doc'),

    path('plot/line/', views.plot_line, name='plot_line'),
    path('plot/line/doc', views.plot_line_doc, name='plot_line_doc'),

    path('plot/bar/', views.plot_bar, name='plot_bar'),
    path('plot/bar/doc', views.plot_bar_doc, name='plot_bar_doc'),

    path('plot/oncoprint/', views.plot_oncoprint, name='plot_oncoprint'),
    path('plot/oncoprint/doc', views.plot_oncoprint_doc, name='plot_oncoprint_doc'),

    path('plot/hrd_density/', views.plot_hrd_density, name='plot_hrd_density'),
    path('plot/hrd_density/doc/', views.plot_hrd_density_doc, name='plot_hrd_density_doc'),

    path('plot/swimmer/', views.plot_swimmer, name='plot_swimmer'),
    path('plot/swimmer/doc', views.plot_swimmer_doc, name='plot_swimmer_doc'),

    path('pipeline/kegg/', views.pipeline_kegg, name='pipeline_kegg'),
    path('pipeline/kegg/rslt/', views.pipeline_kegg_rslt, name='pipeline_kegg_rslt'),
    path('pipeline/kegg/doc/', views.pipeline_kegg_doc, name='pipeline_kegg_doc'),

    path('pipeline/gistic/', views.pipeline_gistic, name='pipeline_gistic'),
    path('pipeline/gistic/rslt/', views.pipeline_gistic_rslt, name='pipeline_gistic_rslt'),
    path('pipeline/gistic/doc/', views.pipeline_gistic_doc, name='pipeline_gistic_doc'),

    path('others/layui/', views.others_layui_index, name='others_layui'),

    # 研发部相关工具
    path('plot/rd_qc_boxplot/', views.plot_rd_qc_boxplot, name='plot_rd_qc_boxplot'),  # 研发质控箱线图
    path('plot/rd_qc_lineplot/', views.plot_rd_qc_lineplot, name='plot_rd_qc_lineplot'),  # 研发质控箱线图

















]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

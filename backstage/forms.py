#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2021/9/1 16:04

"""表单验证"""

import os
from django import forms


class GgplotForm(forms.Form):
    """ggplot2画图相关表单验证"""

    input_file = forms.Field(required=True)
    x = forms.Field(required=True)
    y = forms.Field(required=True)
    # 图片输出参数
    output_name = forms.Field(required=False)
    output_height = forms.IntegerField(required=False)
    output_width = forms.IntegerField(required=False)
    output_units = forms.Field(required=False)
    # 主题
    plot_themes = forms.Field(required=False)
    # 全局颜色
    color_qual_theme = forms.Field(required=False)
    color_seq_theme = forms.Field(required=False)
    color_qual_self = forms.Field(required=False)
    color_seq_self = forms.Field(required=False)
    color_seq_value = forms.Field(required=False)

    fill_qual_theme = forms.Field(required=False)
    fill_seq_theme = forms.Field(required=False)
    fill_seq_self = forms.Field(required=False)
    fill_qual_self = forms.Field(required=False)
    fill_seq_value = forms.Field(required=False)

    # 分面
    col_facets = forms.Field(required=False)
    row_facets = forms.Field(required=False)
    facets_nrow = forms.Field(required=False)
    facets_ncol = forms.Field(required=False)
    facets_scales = forms.Field(required=False)


    facets_text_x_family = forms.Field(required=False)
    facets_text_x_size = forms.Field(required=False)
    facets_text_x_face = forms.Field(required=False)
    facets_text_x_color = forms.Field(required=False)
    facets_text_x_vjust = forms.Field(required=False)
    facets_text_x_angle = forms.Field(required=False)
    facets_x_background_fill = forms.Field(required=False)
    facets_x_background_color = forms.Field(required=False)
    facets_x_background_size = forms.Field(required=False)
    facets_text_y_family = forms.Field(required=False)
    facets_text_y_size = forms.Field(required=False)
    facets_text_y_face = forms.Field(required=False)
    facets_text_y_color = forms.Field(required=False)
    facets_text_y_hjust = forms.Field(required=False)
    facets_text_y_angle = forms.Field(required=False)
    facets_y_background_fill = forms.Field(required=False)
    facets_y_background_color = forms.Field(required=False)
    facets_y_background_size = forms.Field(required=False)
    facets_y_background_linetype = forms.Field(required=False)

    # 网格线和背景
    # 整体背景
    plot_background_fill = forms.Field(required=False)
    plot_background_color = forms.Field(required=False)
    plot_background_size = forms.IntegerField(required=False)
    plot_background_linetype = forms.Field(required=False)
    # 绘图区背景
    panel_background_fill = forms.Field(required=False)
    panel_background_color = forms.Field(required=False)
    panel_background_size = forms.IntegerField(required=False)
    panel_background_linetype = forms.Field(required=False)
    # 主要网格线
    panel_grid_major_color = forms.Field(required=False)
    panel_grid_major_size = forms.FloatField(required=False)
    panel_grid_major_linetype = forms.Field(required=False)
    # 次要网格线
    panel_grid_minor_color = forms.Field(required=False)
    panel_grid_minor_size = forms.FloatField(required=False)
    panel_grid_minor_linetype = forms.Field(required=False)
    # 坐标系
    # 全局字体
    text_family = forms.Field(required=False)
    text_size = forms.IntegerField(required=False)
    text_face = forms.Field(required=False)
    text_color = forms.Field(required=False)
    text_vjust = forms.FloatField(required=False)
    text_angle = forms.IntegerField(required=False)
    # x轴字体
    text_x_family = forms.Field(required=False)
    text_x_size = forms.IntegerField(required=False)
    text_x_face = forms.Field(required=False)
    text_x_color = forms.Field(required=False)
    text_x_vjust = forms.FloatField(required=False)
    text_x_hjust = forms.FloatField(required=False)
    text_x_angle = forms.IntegerField(required=False)
    # y轴字体
    text_y_family = forms.Field(required=False)
    text_y_size = forms.IntegerField(required=False)
    text_y_face = forms.Field(required=False)
    text_y_color = forms.Field(required=False)
    text_y_vjust = forms.FloatField(required=False)
    text_y_hjust = forms.FloatField(required=False)
    text_y_angle = forms.IntegerField(required=False)
    # 坐标轴线
    axis_line_color = forms.Field(required=False)
    axis_line_size = forms.IntegerField(required=False)
    axis_line_linetype = forms.Field(required=False)
    # 坐标刻度
    axis_ticks_color = forms.Field(required=False)
    axis_ticks_size = forms.IntegerField(required=False)
    axis_ticks_linetype = forms.Field(required=False)
    # 标题
    # 标题内容
    labs_title = forms.Field(required=False)
    labs_x = forms.Field(required=False)
    labs_y = forms.Field(required=False)
    labs_color = forms.Field(required=False)
    labs_fill = forms.Field(required=False)
    labs_size = forms.Field(required=False)
    labs_linetype = forms.Field(required=False)
    labs_shape = forms.Field(required=False)
    labs_alpha = forms.Field(required=False)
    # title格式
    plot_title_family = forms.Field(required=False)
    plot_title_size = forms.IntegerField(required=False)
    plot_title_face = forms.Field(required=False)
    plot_title_color = forms.Field(required=False)
    plot_title_vjust = forms.FloatField(required=False)
    plot_title_hjust = forms.FloatField(required=False)
    plot_title_angle = forms.IntegerField(required=False)
    # X轴标题格式
    text_x_blank = forms.Field(required=False)
    aixs_title_x_family = forms.Field(required=False)
    aixs_title_x_size = forms.IntegerField(required=False)
    aixs_title_x_face = forms.Field(required=False)
    aixs_title_x_color = forms.Field(required=False)
    aixs_title_x_vjust = forms.FloatField(required=False)
    aixs_title_x_hjust = forms.FloatField(required=False)
    aixs_title_x_angle = forms.IntegerField(required=False)
    # Y轴标题格式
    text_y_blank = forms.Field(required=False)
    aixs_title_y_family = forms.Field(required=False)
    aixs_title_y_size = forms.IntegerField(required=False)
    aixs_title_y_face = forms.Field(required=False)
    aixs_title_y_color = forms.Field(required=False)
    aixs_title_y_vjust = forms.FloatField(required=False)
    aixs_title_y_hjust = forms.FloatField(required=False)
    aixs_title_y_angle = forms.IntegerField(required=False)
    # 图例
    # 图例位置
    legend_direction = forms.Field(required=False)
    legend_position = forms.Field(required=False)
    legend_position_x = forms.FloatField(required=False)
    legend_position_y = forms.FloatField(required=False)
    # 图例标题文字格式
    legend_title_family = forms.Field(required=False)
    legend_title_size = forms.IntegerField(required=False)
    legend_title_face = forms.Field(required=False)
    legend_title_color = forms.Field(required=False)
    # 图例内容文字格式
    legend_text_family = forms.Field(required=False)
    legend_text_size = forms.IntegerField(required=False)
    legend_text_face = forms.Field(required=False)
    legend_text_color = forms.Field(required=False)
    # 图例背景
    legend_background_fill = forms.Field(required=False)
    legend_background_color = forms.Field(required=False)
    legend_background_size = forms.IntegerField(required=False)
    legend_background_linetype = forms.Field(required=False)
    # lengend keys
    legend_keys_fill = forms.Field(required=False)
    legend_keys_color = forms.Field(required=False)
    legend_keys_size = forms.IntegerField(required=False)
    legend_keys_linetype = forms.Field(required=False)
    # 副标题
    subtitle_content = forms.Field(required=False)
    subtitle_family = forms.Field(required=False)
    subtitle_size = forms.IntegerField(required=False)
    subtitle_face = forms.Field(required=False)
    subtitle_color = forms.Field(required=False)
    subtitle_hjust = forms.FloatField(required=False)
    # 脚注
    caption_content = forms.Field(required=False)
    caption_family = forms.Field(required=False)
    caption_size = forms.IntegerField(required=False)
    caption_face = forms.Field(required=False)
    caption_color = forms.Field(required=False)
    caption_hjust = forms.FloatField(required=False)

    def clean_input_file(self):
        value = self.cleaned_data['input_file']
        if not os.path.exists(value):
            raise forms.ValidationError('can not find input file')
        return value


class DotPlotForm(GgplotForm):

    # 散点独有配置
    group = forms.Field(required=False)
    group_group = forms.Field(required=False)
    group_fill = forms.Field(required=False)
    group_color = forms.Field(required=False)
    group_shape = forms.Field(required=False)
    point_size = forms.IntegerField(required=False)
    point_shape = forms.IntegerField(required=False)
    point_color = forms.Field(required=False)
    point_fill = forms.Field(required=False)
    point_alpha = forms.FloatField(required=False)


class BoxPlotForm(GgplotForm):
    group = forms.Field(required=False)
    group_fill = forms.Field(required=False)
    group_color = forms.Field(required=False)
    group_shape = forms.Field(required=False)
    point_size = forms.IntegerField(required=False)
    point_shape = forms.IntegerField(required=False)
    point_color = forms.Field(required=False)
    point_fill = forms.Field(required=False)
    point_alpha = forms.FloatField(required=False)

    box_color = forms.Field(required=False)
    box_fill = forms.Field(required=False)
    outlier_fill = forms.Field(required=False)
    outlier_color = forms.Field(required=False)
    outlier_shape = forms.Field(required=False)
    outlier_size = forms.Field(required=False)
    outlier_alpha = forms.Field(required=False)


class LinePlotForm(GgplotForm):
    group = forms.Field(required=False)
    point_color = forms.Field(required=False)
    group_group = forms.Field(required=False)



class PlotSwimmerForm(forms.Form):

    # 泳图表单
    # 输入文件
    input_for_plotting_bars = forms.Field()
    input_for_plotting_dots = forms.Field()
    input_for_adding_lines = forms.Field(required=False)
    # 输出设置
    out_fig_name = forms.Field()
    set_fig_width = forms.IntegerField()
    set_fig_height = forms.IntegerField()
    # 设置点的大小
    set_dot_size = forms.FloatField(required=False)
    # 柱状图数据及图形外观参数2
    set_bar_order = forms.Field(required=False)
    set_bar_stroke_color = forms.Field()
    set_bar_width = forms.FloatField(required=False)
    set_bar_transparency = forms.FloatField()
    set_bar_color = forms.Field(required=False)
    # 箭头外观参数
    add_arrows = forms.Field(required=False)
    set_arrows_length = forms.FloatField()
    set_arrows_style = forms.Field(required=False)
    set_arrows_size = forms.FloatField(required=False)
    set_arrows_angle = forms.IntegerField(required=False)
    # 点图外观参数
    set_dot_color = forms.Field(required=False)
    set_line_size = forms.IntegerField(required=False)


#
# class HeatmapForm(forms.Field):
#
#     exprTable = forms.CharField(required=True)
#     set_pic_width = forms.IntegerField()
#     set_pic_height
#     set_filename
#
#     whether_cluster_column
#     whether_cluster_row
#     whether_original_order_column
#     whether_original_order_row
#
#     set_clustering_method
#     set_clustering_distance_rows
#     set_clustering_distance_cols
#     set_treeheight_col
#     set_treeheight_row
#
#     whether_show_legend
#     whether_scale
#
#     whether_show_rownames
#     whether_show_colnames
#     set_font_size_row
#     set_font_size_col
#     set_angle_col
#
#     set_cellwidth
#     set_cellheight
#     set_color_gradient
#     set_color_gradient_number
#     set_border_color
#     whether_display_number
#     set_font_size_num
#     set_number_color
#
#     set_cutree_cols
#     set_cutree_rows

#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2022/1/15 1:40


import pandas as pd
from plotnine import *


class BoxPlot(object):

    def __init__(self, f_input, f_output, x_col, y_col):
        self.f_input = f_input
        self.f_output = f_output
        self.x_col = x_col
        self.y_col = y_col

    def plot(self):

        if self.f_input.endswith(".csv"):
            df_data = pd.read_csv(self.f_input)
        elif self.f_input.endswith(".xls") or self.f_input.endswith(".xlsx"):
            df_data = pd.read_excel(self.f_input)
        else:
            df_data = pd.read_csv(self.f_input, sep="\t")

        cmd = f"box_plot=(ggplot(df,aes(x='class',y="value",fill="class"))
+geom_boxplot(show_legend=False)
+scale_fill_hue(s = 0.90, l = 0.65, h=0.0417,color_space='husl')
+theme_matplotlib()
+theme(
    dpi=100,
    figure_size=(8,6))
         )"

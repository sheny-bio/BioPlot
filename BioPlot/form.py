#!/usr/bin/env python
# coding: utf-8
# Author：Shen Yi
# Date ：2021-04-14 13:50

from django import forms
import re


class MutCnvForm(forms.Form):
    name = forms.CharField(required=False, error_messages={'required': "结果文件名不能为空"})
    tmp_dir = forms.CharField(required=True, error_messages={'required':  "临时目录不能为空"})
    mut_data = forms.CharField(required=True, error_messages={'required':  "结果数据不能为空"})

    def clean_mut_data(self):
        mut_data = self.cleaned_data['mut_data']
        if not mut_data.startswith("sample\t1\t2\n"):
            raise forms.ValidationError("待分析数据必须包含表头。")
        return mut_data


class HrdDensityForm(forms.Form):
    name = forms.CharField(required=False, error_messages={'required': "结果文件名不能为空"})
    tmp_dir = forms.CharField(required=True, error_messages={'required':  "临时目录不能为空"})
    hrd_data = forms.CharField(required=True, error_messages={'required':  "结果数据不能为空"})

    def clean_hrd_data(self):
        hrd_data = self.cleaned_data['hrd_data']
        hrd_data = re.sub(" +", "\t", hrd_data)

        if not hrd_data.startswith("Sample"):
            raise forms.ValidationError("待分析数据必须包含表头。")
        return hrd_data


class KeggForm(forms.Form):
    name = forms.CharField(required=False)
    cutoff_field = forms.CharField(required=False, error_messages={'required': "cutoff_field must supply"})
    min_cutoff = forms.FloatField(required=False, min_value=0, max_value=1, error_messages={'required': "min cutoff must supply"})
    width = forms.FloatField(required=False, error_messages={'required': "width must supply"})
    height = forms.FloatField(required=False, error_messages={'required': "height must supply"})
    gene_list = forms.CharField(required=False, error_messages={'required': "gene list must supply"})
    tmp_dir = forms.CharField(required=True, error_messages={'required': "临时目录不能为空"})

    def clean_cutoff_field(self):
        cutoff_field = self.cleaned_data["cutoff_field"]
        if str(cutoff_field) not in ["1", "0"]:
            raise forms.ValidationError("cutoff_field muts in [padjust, pvalue]")
        return cutoff_field

    def clean_gene_list(self):
        gene_list = self.cleaned_data["gene_list"]
        gene_list = re.sub(" +", "\t", gene_list)
        if not gene_list.startswith("sample"):
            raise forms.ValidationError("待分析数据必须包含表头。[sample  gene]")
        return gene_list

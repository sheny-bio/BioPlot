from glob import glob
import os
import re
import subprocess
import time
import uuid

from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponse
import pandas as pd

from .forms import *


def _is_post(func):
    """ 判断前端是否为post请求，
    :param request: 前端请求
    :return: 若不是post请求，则返回403
    """

    def wrapper(request, *args, **kwargs):
        if request.method != "POST":
            return JsonResponse({}, status=403, reason="Get requests are not supported")
        else:
            return func(request, *args, **kwargs)
    return wrapper


def get_file(request):
    """访问一个后端文件，并在前端展示"""

    file_path = request.GET.get("path")
    file_path = os.path.abspath(file_path)

    if file_path.endswith("png") or file_path.endswith("jpg"):
        data = open(file_path, "rb").read()
        response = HttpResponse(data, content_type='image/png')
        response['Content-Disposition'] = f'filename="{os.path.basename(file_path)}"'
    elif file_path.endswith("pdf"):
        data = open(file_path, "rb").read()
        response = HttpResponse(data, content_type='application/pdf')
        response['Content-Disposition'] = f'filename="{os.path.basename(file_path)}"'
    else:
        data = open(file_path, "r").read()
        response = HttpResponse(data)
        response['Content-Disposition'] = f'filename="{os.path.basename(file_path)}"'
    return response


def file_columns(request):
    """获得样本的列名"""

    file = request.GET.get("file")
    file = os.path.abspath(file)
    if not os.path.exists(file):
        return JsonResponse({}, status=412)

    if file.endswith("xlsx") or file.endswith("xls"):
        df_t = pd.read_excel(file)
    elif file.endswith("csv"):
        df_t = pd.read_csv(file)
    else:
        df_t = pd.read_csv(file, sep="\t")
    columns = list(df_t.columns)
    return JsonResponse({"columns": columns})


@_is_post
def upload_file(request):
    """将文件上传至指定目录"""

    tmp_dir = request.POST.get("TmpDir", "") or _give_me_directory(f"{settings.DIR_TMP}/Upload")
    tmp_dir = os.path.abspath(tmp_dir)
    if not os.path.exists(tmp_dir):
        try:
            os.makedirs(tmp_dir)
        except Exception as _:
            pass

    try:
        file_obj = request.FILES.get('file')
        if file_obj.name.endswith("xls") or file_obj.name.endswith("xlsx"):
            with open(f"{tmp_dir}/{file_obj.name}", "wb") as fw:
                fw.write(file_obj.read())
        else:
            with open(f"{tmp_dir}/{file_obj.name}", "w") as fw:
                fw.write(file_obj.read().decode("utf-8"))
    except Exception as error:
        print(error)
        return JsonResponse({"code": 1, "msg": error, "data": ""})
    else:
        return JsonResponse({"code": 0, "msg": "", "data": "", "file": f"{tmp_dir}/{file_obj.name}"})


@_is_post
def group_by_file(request):
    """获取某个文件，某一列的所有分组结果"""

    file = request.POST.get("file")
    col_index = request.POST.get("col_index", 0)

    df_f = pd.read_excel(file)
    col_name = list(df_f.columns)[int(col_index)]
    data_group = list(set(df_f[col_name]))
    return JsonResponse({"data": data_group})


@_is_post
def check_job_status(request):
    """ 检查任务状态

    code表示任务的当前状态： run-分析中；done-完成无报错；error-分析失败
    """

    job_id = request.POST.get("job_id")
    f_error = request.POST.get("f_error")
    f_success = request.POST.get("f_success")
    if not job_id:
        return JsonResponse({}, status=412, reason="job id is required")

    output = subprocess.check_output(f"bjobs {job_id}", shell=True)
    output = output.decode("utf-8")
    flag = output.split("\n")[1].split()[2]

    if flag in ["PEND", "RUN"]:
        rslt = {"code": "run", "jobid": job_id, "flag": flag, "time": time.strftime("%H:%M:%S", time.localtime())}
        return JsonResponse(rslt, status=200)
    else:
        rslt = {"code": "done", "jobid": job_id, "flag": flag, "time": time.strftime("%H:%M:%S", time.localtime())}
        if not os.path.exists(f_success):
            rslt["code"] = "error"
            if os.path.exists(f_error):
                rslt["error"] = f"{f_error}\n" + open(f_error).read()
        return JsonResponse(rslt, status=200)


@_is_post
def give_me_directory(request):
    """创建一个目录"""

    tmp_dir = request.POST.get("tmp_dir")
    tmp_dir = _give_me_directory(f"{settings.DIR_TMP}/{tmp_dir}")
    return JsonResponse({"tmp_dir": tmp_dir})


@_is_post
def plot_mut_cnv(request):

    job_name = request.POST.get("id")
    mut_data = request.POST.get("mut_data")
    if not job_name:
        return JsonResponse({}, status=412, reason="job id is required")
    elif not mut_data:
        return JsonResponse({}, status=412, reason="mut data is required")

    d_output = _give_me_directory(f"{settings.DIR_TMP}/MutCnv/{job_name}")
    d_output = os.path.abspath(d_output)
    f_output = f"{d_output}/{job_name}.png"
    f_input = f"{d_output}/mut_cnv.tsv"
    f_error = f"{d_output}/mut_cnv.error"

    with open(f_input, "w") as fw:
        if not mut_data.endswith("\n"):
            mut_data = mut_data + "\n"
        fw.write(mut_data.replace("\t", ","))

    cmd = f"Rscript {settings.DIR_SCRIPT}/MUT_CNV_curve.R {f_input} {f_output} 2> {f_error}"
    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as _:
        error = open(f_error).read()
        return JsonResponse({}, status=412, reason=error.encode("utf-8"), charset="utf-8")
    else:
        return JsonResponse({"f_output": f_output})


@_is_post
def plot_hrd_density(request):
    """hrd 得分分布图绘制"""

    job_name = request.POST.get("id")
    hrd_data = request.POST.get("hrd_data")
    if not job_name:
        return JsonResponse({}, status=412, reason="job id is required")
    if not hrd_data:
        return JsonResponse({}, status=412, reason="hrd data is required")

    d_output = _give_me_directory(f"{settings.DIR_TMP}/HRD/{job_name}")
    d_output = os.path.abspath(d_output)

    f_hrd = f"{d_output}/{job_name}.hrd.tsv"
    f_fig = f"{d_output}/{job_name}.hrd.jpg"
    f_pdf = f"{d_output}/{job_name}.hrd.pdf"
    f_error = f"{d_output}/{job_name}.hrd.error"

    with open(f_hrd, "w") as fw:
        if not hrd_data.endswith("\n"):
            hrd_data = hrd_data + "\n"
        fw.write(hrd_data)

    cmd = f"Rscript {settings.DIR_SCRIPT}/HrdCutoffPlot.R " \
          f"{settings.DIR_DB}/Y190_pair_model_cutoff_plot.txt " \
          f"{f_hrd} " \
          f"{f_fig} " \
          f"{settings.DIR_DB}/fzltxh_gbk.TTF 2> {f_error}"

    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as _:
        error = open(f_error).read()
        return JsonResponse({}, status=412, reason=error.encode("utf-8"), charset="utf-8")
    else:
        return JsonResponse({"f_output": f_pdf})


@_is_post
def plot_oncoprint(request):
    """oncoprint图分析"""

    all_args = request.POST.dict()
    base_args = ['output', 'column_split', 'width', 'height', 'file', 'clinic', 'gene', 'color']
    list_types = [key for key in all_args.keys() if key not in base_args]
    list_files = [all_args[f] for f in list_types]

    job_name = request.POST.get("output")
    d_output = _give_me_directory(f"{settings.DIR_TMP}/OncoPrint/{job_name}")
    f_png = f"{d_output}/{job_name}.png"
    f_pdf = f"{d_output}/{job_name}.pdf"
    f_error = f"{d_output}/{job_name}.error"

    # 检查输入文件是否合规
    if not all_args.get("output"):
        return JsonResponse({}, status=412, reason="output is required", charset="utf-8")
    if not all_args.get("clinic"):
        return JsonResponse({}, status=412, reason="clinic file is required", charset="utf-8")
    if not all_args.get("gene"):
        return JsonResponse({}, status=412, reason="gene file is required", charset="utf-8")

    cmd = f"{settings.RSCRIPT_ONCO} {settings.DIR_SCRIPT}/OncoPrint.r " \
          f"--clinfile={all_args['clinic']} " \
          f"--types='{','.join(list_types)}' " \
          f"--files={','.join(list_files)} " \
          f"--gene={all_args['gene']} " \
          f"--outfile={d_output}/{job_name} "
    if all_args.get('column_split'):
        cmd += f"column_split={all_args['column_split']} "
    if all_args.get("color"):
        cmd += f"--color={all_args['color']} "
    if all_args.get('height'):
        cmd += f"--height={all_args['height']} "
    if all_args.get('width'):
        cmd += f"--width={all_args['width']} "

    cmd += f"2> {f_error}"

    print(cmd)
    try:
        subprocess.check_output(cmd, shell=True)
    except Exception as _:
        error = open(f_error).read()
        return JsonResponse({}, status=412, reason=error.encode("utf-8"), charset="utf-8")
    else:
        return JsonResponse({"f_png": f_png, "f_pdf": f_pdf})


@_is_post
def pipeline_kegg(request):
    """kegg分析"""

    job_name = request.POST.get("id")
    gene_list = request.POST.get("gene_list")
    cutoff_field = request.POST.get("cutoff_field")
    min_cutoff = request.POST.get("min_cutoff")
    width = request.POST.get("width")
    height = request.POST.get("height")
    if not job_name:
        return JsonResponse({}, status=412, reason="job id is required")
    if not gene_list:
        return JsonResponse({}, status=412, reason="gene_list is required")

    d_output = _give_me_directory(f"{settings.DIR_TMP}/KEGG/")
    d_output = os.path.abspath(d_output)
    d_analyze = f"{d_output}/Result"
    os.makedirs(d_analyze)
    f_gene = f"{d_output}/{job_name}.gene.list"
    f_zip = f"{d_output}/{job_name}.zip"
    f_cmd = f"{d_output}/run.sh"

    with open(f_gene, "w") as fw:
        if not gene_list.endswith("\n"):
            gene_list = gene_list + "\n"
        fw.write(gene_list)

    with open(f_cmd, "w") as fw:
        cmd = f"{settings.RSCRIPT_KEGG} {settings.DIR_SCRIPT}/plot_go_kegg_enrich_plot.R " \
              f"{f_gene} " \
              f"{d_analyze} " \
              f"{cutoff_field} " \
              f"{min_cutoff} " \
              f"{width} " \
              f"{height} " \
              f"&& zip -j -r {f_zip} {d_analyze}/*"
        fw.write(cmd)

    try:
        rslt = _submit_job(job_id=job_name, command=cmd, d_output=d_output)
    except Exception as error:
        print(error)
        return JsonResponse({}, status=412, reason="submit error")
    else:
        # rslt["rslt"] = os.path.abspath(d_output).split("temp", 2)[-1]
        rslt["rslt"] = os.path.abspath(d_output)
        print(rslt)
        return JsonResponse(rslt)


@_is_post
def pipeline_kegg_rslt(request):
    """获得样本所有kegg结果"""

    path = request.POST.get("path")
    # print(path)
    # # path = os.path.abspath(path)
    path = os.path.abspath(path)
    path_rslt = f"{path}/Result"

    all_files = glob(f"{path_rslt}/*")
    print(path)
    print(glob(f"{path}/*.zip")[0])
    rslt = {
        "f_zip": glob(f"{path}/*.zip")[0], "KEGG_ALL": "none", "KEGG_TOP20": "none", "GO_BP_ALL": "none",
        "GO_BP_TOP20": "none", "GO_CC_ALL": "none", "GO_CC_TOP20": "none", "GO_MF_ALL": "none", "GO_MF_TOP20": "none",
    }
    for file in all_files:
        if "_kegg.filter" in file and ".all.pdf" in file:
            rslt["KEGG_ALL"] = file.split("temp", 2)[-1]
        if "_kegg.filter" in file and ".top20.pdf" in file:
            rslt["KEGG_TOP20"] = file.split("temp", 2)[-1]
        if "_go_bp.filter" in file and ".all.pdf" in file:
            rslt["GO_BP_ALL"] = file.split("temp", 2)[-1]
        if "_go_bp.filter" in file and ".top20.pdf" in file:
            rslt["GO_BP_TOP20"] = file.split("temp", 2)[-1]
        if "_go_cc.filter" in file and ".all.pdf" in file:
            rslt["GO_CC_ALL"] = file.split("temp", 2)[-1]
        if "_go_cc.filter" in file and ".top20.pdf" in file:
            rslt["GO_CC_TOP20"] = file.split("temp", 2)[-1]
        if "_go_mf.filter" in file and ".all.pdf" in file:
            rslt["GO_MF_ALL"] = file.split("temp", 2)[-1]
        if "_go_mf.filter" in file and ".top20.pdf" in file:
            rslt["GO_MF_TOP20"] = file.split("temp", 2)[-1]
    return JsonResponse(rslt)


@_is_post
def pipeline_gistic(request):
    """gistic分析"""

    args = request.POST.dict()
    d_output = args['TmpDir']
    d_analyze = f"{d_output}/Results"
    f_cmd = f"{d_output}/run.sh"
    f_zip = f"{d_output}/{args['id']}.gistic.zip"
    if not os.path.exists(d_analyze):
        os.makedirs(d_analyze)

    with open(f_cmd, "w") as fw:
        cmd = f"python {settings.DIR_SCRIPT}/gistic.py " \
              f"--d_segs {d_output}/segs " \
              f"--d_output {d_analyze} " \
              f"--ta {args['ta']} " \
              f"--td {args['td']} " \
              f"--id {args['id']} " \
              f"--rx {args['rx']} " \
              f"--cap {args['cap']} " \
              f"--qvt {args['qvt']} " \
              f"--broad {args['broad']} " \
              f"--brlen {args['brlen']} " \
              f"--genegistic {args['genegistic']} && " \
              f"zip -j -r {f_zip} {d_analyze}/*"
        fw.write(cmd)

    try:
        job_name = f"Gistic.{args['id']}"
        rslt = _submit_job(job_id=job_name, command=cmd, d_output=d_output)
    except Exception as error:
        print(error)
        return JsonResponse({}, status=412, reason="submit error")
    else:
        rslt["path"] = os.path.basename(d_output)
        print(rslt)
        return JsonResponse(rslt)


def pipeline_gistic_rslt(request):
    """获得gistic结果文件"""

    path = request.GET.get("path")
    file = request.GET.get("file")

    if file == "AMP_qplot":
        file = glob(f"{settings.DIR_TMP}/Gistic/{path}/Results/Results/*.amp_qplot.pdf")[0]
    elif file == "DEL_qplot":
        file = glob(f"{settings.DIR_TMP}/Gistic/{path}/Results/Results/*.del_qplot.pdf")[0]
    elif file == "freqarms_vs_ngenes":
        file = glob(f"{settings.DIR_TMP}/Gistic/{path}/Results/Results/*.freqarms_vs_ngenes.pdf")[0]
    elif file == "copy_number":
        file = glob(f"{settings.DIR_TMP}/Gistic/{path}/Results/Results/*.raw_copy_number.pdf")[0]

    data = open(file, "rb").read()
    response = HttpResponse(data, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="{os.path.basename(file)}"'
    return response


def download(request):
    """下载文件"""

    name = os.path.basename(request.GET.get("file"))
    file = open(request.GET.get("file"), 'rb')
    response = FileResponse(file)
    response['Content-Type'] = 'application/octet-stream'
    response['Content-Disposition'] = f'attachment;filename="{name}"'
    return response


@_is_post
def plot_heatmap(request):
    """绘制热图"""

    args = request.POST.dict()
    d_output = _give_me_directory(f"{settings.DIR_TMP}/Heatmap/")
    d_output = os.path.abspath(d_output)
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{args['set_filename']}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:
        cmd = f"library(pheatmap)\n" \
              f"library(openxlsx)\n" \
              f"setwd('{d_output}')\n" \
              f"mydat <- read.xlsx('{args['exprTable']}',colNames = T,rowNames =T, sheet = 1)\n" \
              f"print(mydat)\n" \
              f"pheatmap(plot_args)\n"

        plot_args = []
        if args["whether_original_order_column"] == "TRUE":
            file = "mydat[,order(colnames(mydat))]"
        elif args["whether_original_order_row"] == "TRUE":
            file = "mydat[order(rownames(mydat)),]"
        else:
            file = "mydat"
        plot_args.append(file)

        # 是否按列聚类
        plot_args.append(f"cluster_cols = {args['whether_cluster_column']}")
        plot_args.append(f"cluster_rows = {args['whether_cluster_row']}")
        plot_args.append(f"show_colnames = {args['whether_show_colnames']}")
        plot_args.append(f"show_rownames = {args['whether_show_rownames']}")
        # 颜色梯度
        set_color_gradient = ','.join([f'"{i}"' for i in args['set_color_gradient'].split(",")])
        plot_args.append(f"color = colorRampPalette(c({set_color_gradient}))({args['set_color_gradient_number']})")
        # 标准化
        if args["whether_scale"] == "TRUE":
            plot_args.append(f"scale = TRUE")
        # 边框颜色
        plot_args.append(f"border_color = '{args['set_border_color']}'")
        # 图例显示
        if args['whether_show_legend'] == "TRUE":
            plot_args.append(f"legend = TRUE")
        # 标签大小
        if args['set_font_size_row']:
            plot_args.append(f"fontsize_row = {args['set_font_size_row']}")
        if args["set_font_size_col"]:
            plot_args.append(f"fontsize_col = {args['set_font_size_col']}")
        # 标签角度
        plot_args.append(f"angle_col = {args['set_angle_col']}")
        # 分区
        if args['set_cutree_cols']:
            plot_args.append(f"cutree_cols = {args['set_cutree_cols']}")
        if args['set_cutree_rows']:
            plot_args.append(f"cutree_rows = {args['set_cutree_rows']}")
        # 树的高度
        if args['set_treeheight_col']:
            plot_args.append(f"treeheight_col = {args['set_treeheight_col']}")
        if args['set_treeheight_row']:
            plot_args.append(f"treeheight_row = {args['set_treeheight_row']}")
        # 聚类方式
        plot_args.append(f"clustering_method = '{args['set_clustering_method']}'")
        if args["set_clustering_distance_rows"]:
            plot_args.append(f"clustering_distance_rows = '{args['set_clustering_distance_rows']}'")
        if args['set_clustering_distance_cols']:
            plot_args.append(f"clustering_distance_cols = '{args['set_clustering_distance_cols']}'")
        # 其他
        if args['whether_display_number']:
            plot_args.append(f"display_numbers = TRUE")
        if args['set_font_size_num']:
            plot_args.append(f"fontsize_number = {args['set_font_size_num']}")
        if args['set_number_color']:
            plot_args.append(f"number_color = '{args['set_number_color']}'")
        if args['set_cellwidth']:
            plot_args.append(f"cellwidth = {args['set_cellwidth']}")
        if args['set_cellheight']:
            plot_args.append(f"cellheight = {args['set_cellheight']}")
        # 图片输出
        plot_args.append(f"filename = '{f_output}'")
        plot_args.append(f"width = {args['set_pic_width']}")
        plot_args.append(f"height = {args['set_pic_height']}")

        cmd = cmd.replace("plot_args", ', '.join(plot_args))
        fw.write(cmd)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "file": f_output})








    # args["file_path"] = d_output
    # f_script = f"{d_output}/plot.r"
    # # 生成分析脚本
    # with open(f_script, "w") as fw:
    #     for line in open(f"{settings.DIR_SCRIPT}/heatmap.R"):
    #         for arg, value in args.items():
    #             line = line.replace("{{" + arg + "}}", value)
    #         fw.write(line)
    #
    # cmd = f"{settings.RSCRIPT_BASE} {f_script}"
    # try:
    #     subprocess.check_call(cmd, shell=True)
    # except Exception as error:
    #     return JsonResponse({}, status=412, reason="plot error")
    # else:
    #     rslt = {"file": f"{d_output}/{args['set_filename']}.jpg"}
    #     return JsonResponse(rslt)


@_is_post
def plot_swimmer(request):
    """泳图"""

    dict_post = request.POST.dict()
    data = PlotSwimmerForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        print(data.errors)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotSwimmer")
    f_script = f"{d_output}/run.R"
    f_jpg = f"{d_output}/{data.get('out_fig_name', 'PlotSwimmer')}.jpg"
    f_pdf = f"{d_output}/{data.get('out_fig_name', 'PlotSwimmer')}.pdf"
    f_error = f"{d_output}/error.log"

    # 参数调整： 获得各文件的列名
    df_bar = pd.read_excel(data['input_for_plotting_bars'])
    set_id_for_bar_graph, set_entity_of_bars, set_endpoint_of_bars = list(df_bar.columns)[0: 3]
    df_dot = pd.read_excel(data['input_for_plotting_dots'])
    set_id_for_dot_graph, set_entity_of_dots, set_condition_of_dots, set_location_of_dots = list(df_dot.columns)[0: 4]

    # 参数调整：柱形图顺序
    _order_col = ','.join([f"'{i}'" for i in df_bar.drop_duplicates(subset=set_id_for_bar_graph)[set_id_for_bar_graph]])
    _order_col = f"c({_order_col})"
    set_bar_order = _order_col if data.get('set_bar_order') == "excel" else ""

    # 参数调整：柱形图颜色自定义
    _color_list = [f'"{key.replace("bar-fn-", "")}"="{value}"' for key, value in dict_post.items() if "bar-fn-" in key and value]
    print(_color_list)
    color_bar = f'c({",".join(_color_list)})' if _color_list else ""

    # # 参数调整：点图颜色自定义
    # _color_list = [f'"{key.replace("dot-fn-", "")}"="{value}"' for key, value in dict_post.items() if "dot-fn-" in key]
    # color_dot = f'c({",".join(_color_list)})' if _color_list else ""

    with open(f_script, "w") as fw:
        script = f"library(openxlsx)\n" \
                 f"library(swimplot)\n" \
                 f"library(ggplot2)\n" \
                 f"library(ggpubr)\n"
        # 读取文件
        script += f"plotting_bars <- read.xlsx(\"{data['input_for_plotting_bars']}\",colNames = T)\n"
        script += f"plotting_dots <- read.xlsx(\"{data['input_for_plotting_dots']}\",colNames = T)\n"
        # 画柱形图
        script += f"bar_plot <- swimmer_plot(df = plotting_bars,\n"
        script += f"id = '{set_id_for_bar_graph}',\n"
        script += f"end = '{set_endpoint_of_bars}',\n"
        script += f"name_fill = '{set_entity_of_bars}',\n"
        script += f"col = '{data.get('set_bar_stroke_color')}',\n"
        script += f"alpha = {data.get('set_bar_transparency')},\n"
        if set_bar_order:
            script += f"id_order = {set_bar_order},\n"
        script += f")\n"
        if color_bar:
            script += f"bar_plot <- bar_plot + ggplot2::scale_fill_manual(name = '{set_entity_of_bars}', values = {color_bar})\n"
        # 画点图
        script += f"bar_plot <- bar_plot + swimmer_points(df_points = plotting_dots,\n"
        script += f"id = '{set_id_for_dot_graph}',\n"
        script += f"time = '{set_location_of_dots}',\n"
        script += f"name_shape = '{set_entity_of_dots}',\n"
        script += f"fill = 'white',\n"
        script += f"name_col = '{set_condition_of_dots}',\n"
        if data.get("set_dot_size"):
            script += f"size = {set_dot_size},\n"
        script += f")\n"
        # 画箭头
        if data.get("add_arrows"):
            script += f"bar_plot <- bar_plot + swimmer_arrows(df_arrows = plotting_bars,\n"
            script += f"id = '{set_id_for_bar_graph}',\n"
            script += f"arrow_start = '{set_endpoint_of_bars}',\n"
            script += f"cont = '{data.get('add_arrows')}',\n"
            script += f"length = {data.get('set_arrows_length')},\n"
            if data.get('set_arrows_angle'):
                script += f"angle = {data.get('set_arrows_angle')},\n"
            if data.get('set_arrows_size'):
                script += f"cex = {data.get('set_arrows_size')},\n"
            if data.get('set_arrows_style'):
                script += f"type = '{data.get('set_arrows_style')}',\n"
            script += f")\n"

        # 画线图
        if data.get("input_for_adding_lines"):
            df_line = pd.read_excel(data['input_for_adding_lines'])
            set_id_for_adding_lines, set_entity_of_lines, set_startpoint_of_lines, set_endpoint_of_lines = list(df_line.columns)[0: 4]

            script += f"plotting_lines <- read.xlsx(\"{data['input_for_adding_lines']}\",colNames = T)\n"
            script += f"bar_plot <- bar_plot + swimmer_lines(df = plotting_lines,\n"
            script += f"id = '{set_id_for_adding_lines}',\n"
            script += f"start = '{set_startpoint_of_lines}',\n"
            script += f"end = '{set_endpoint_of_lines}',\n"
            script += f"name_col = '{set_entity_of_lines}',\n"
            if data.get("set_line_size"):
                script += f"size = '{set_line_size}',\n"
            script += ")\n"
        # 保存图片
        script += f"ggexport(bar_plot, width = {data.get('set_fig_width')}, height = {data.get('set_fig_width')}, filename = '{f_pdf}', device = 'pdf')\n"
        script += f"ggexport(bar_plot, res=100, filename = '{f_jpg}')\n"
        fw.write(script)

    cmd = f"{settings.RSCRIPT_SWIMMER} {f_script} 2> {f_error}"
    print(cmd)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": open(f_error).read()})
    else:
        return JsonResponse({"code": 0, "f_pdf": f_pdf, "f_jpg": f_jpg})


@_is_post
def plot_dot(request):
    """绘制散点图"""

    # 表单验证
    data = DotPlotForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotDot")
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{data.get('output_name', 'DotPlot')}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:

        # 基本框架
        script = """
            library('ggplot2')
            library('openxlsx')
            library('RColorBrewer')
            
            df_data <- {{read_table}}
            
            p <- ggplot(df_data, aes({{x}}, {{y}})) + 
                 geom_point({{geom_point}}) +
                 <<{{plot_theme}} +>>   # 主题
                 <<{{scale_qual_color}} +>>   #  离散型颜色
                 <<{{scale_qual_fill}} +>>   #  离散型颜色
                 <<{{scale_seq_color}} +>>  # 连续型颜色
                 <<{{scale_seq_fill}} +>>  # 连续型颜色
                 <<{{facets}} +>>  # 分面
                 <<{{labs}} +>>
                 
                 theme(
                     <<{{plot_background}},>>
                     <<{{panel_background}},>>
                     <<{{panel_grid_major}},>>
                     <<{{panel_grid_minor}},>>
                     <<{{axis_text}},>>
                     <<{{axis_text_x}},>>
                     <<{{axis_text_y}},>>
                     <<{{axis_line}},>>
                     <<{{axis_ticks}},>>
                     <<{{axis_title_x}},>>
                     <<{{axis_title_y}},>>
                     <<{{plot_title}},>>
                     <<{{legend_background}},>>
                     <<{{legend_keys}},>>
                     <<{{legend_position}},>>
                     <<{{legend_direction}},>>
                     <<{{plot_subtitle}},>>
                     <<{{plot_caption}},>>
                 )
            
            ggsave(p, filename="{{f_output}}", {{pig_size}})
        """
        script = script.replace("{{x}}", data.get("x"))
        script = script.replace("{{y}}", data.get("y"))
        script = script.replace("{{f_output}}", f_output)

        # 读取文件
        input_file = data.get("input_file")
        if input_file.endswith("xlsx") or input_file.endswith("xls"):
            s_read_table = f"read.xlsx('{input_file}',sheet = 1)"
        elif input_file.endswith("csv"):
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F)"
        else:
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F, sep='\\t')"
        script = script.replace("{{read_table}}", s_read_table)

        # 散点独有配置
        group = data.get("group", "")
        group_fill = data.get("group_fill", "")
        group_color = data.get("group_color", "")
        group_shape = data.get("group_shape", "")
        point_size = data.get("point_size", "")
        point_shape = data.get("point_shape", "")
        point_color = data.get("point_color", "")
        point_fill = data.get("point_fill", "")
        point_alpha = data.get("point_alpha", "")

        s_geom_point = ""
        if group or group_fill or group_color or group_shape:
            s_aes = f"aes("
            s_aes += f"group={group}," if group else ""
            s_aes += f"fill={group_fill}," if group_fill else ""
            s_aes += f"color={group_color}," if group_color else ""
            s_aes += f"shape={group_shape}," if group_shape else ""
            s_aes += "), "
            s_geom_point += s_aes
        s_geom_point += f"size={point_size}," if point_size else ""
        s_geom_point += f"shape={point_shape}," if point_shape else ""
        s_geom_point += f"color='{point_color}'," if point_color else ""
        s_geom_point += f"fill='{point_fill}'," if point_fill else ""
        s_geom_point += f"alpha='{point_alpha}'," if point_alpha else ""
        script = script.replace("{{geom_point}}", s_geom_point)

        # 主题
        themes = data.get("plot_themes")
        if themes:
            script = script.replace("{{plot_theme}}", f"theme_{themes}()")
        else:
            script = script.replace("{{plot_theme}}", f"")

        # 配置离散型颜色 -- 边框色
        color_qual = data.get("color_qual_theme", "")
        color_qual_self = data.get("color_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_color_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_color_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_color}}", s_scale_color)

        # 配置离散型颜色 -- 填充色
        color_qual = data.get("fill_qual_theme", "")
        color_qual_self = data.get("fill_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_fill_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_fill_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_fill}}", s_scale_color)

        # 配置连续型颜色 -- 边框色
        color_seq = data.get("color_seq_theme", "")
        color_seq_self = data.get("color_seq_self", "")
        color_seq_self_value = data.get("color_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_color_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_color_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_color}}", s_scale_fill)

        # 配置连续型颜色 -- 填充
        color_seq = data.get("fill_seq_theme", "")
        color_seq_self = data.get("fill_seq_self", "")
        color_seq_self_value = data.get("fill_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_fill_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_fill_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_fill}}", s_scale_fill)

        # 分面参数
        col_facets = data.get("col_facets", "")
        row_facets = data.get("row_facets", "")
        facets_nrow = data.get("facets_nrow")
        facets_ncol = data.get("facets_ncol")
        facets_scales = data.get("facets_scales")
        if col_facets and row_facets:
            s_facets = f"facet_grid('{row_facets} ~ {col_facets}'"
        elif col_facets:
            s_facets = f"facet_grid('. ~ {col_facets}'"
        elif row_facets:
            s_facets = f"facet_grid('{row_facets} ~ .'"
        else:
            s_facets = ""

        if s_facets:
            if facets_nrow:
                s_facets += f" ,nrow={facets_nrow}"
            if facets_ncol:
                s_facets += f" ,ncol={facets_ncol}"
            if facets_scales:
                s_facets += f" ,scales='{facets_scales}'"
            s_facets += ")"
        script = script.replace("{{facets}}", s_facets)

        # 整体背景
        plot_background_fill = data.get("plot_background_fill", "")
        plot_background_color = data.get("plot_background_color", "")
        plot_background_size = data.get("plot_background_size", "")
        plot_background_linetype = data.get("plot_background_linetype", "")
        if plot_background_fill or plot_background_color or plot_background_size or plot_background_linetype:
            s_plot_background = f"plot.background = element_rect("
            s_plot_background += f'fill = "{plot_background_fill}",' if plot_background_fill else ""
            s_plot_background += f'colour = "{plot_background_color}",' if plot_background_color else ""
            s_plot_background += f'size = {plot_background_size},' if plot_background_size else ""
            s_plot_background += f'linetype = "{plot_background_linetype}",' if plot_background_linetype else ""
            s_plot_background += ")"
        else:
            s_plot_background = ""
        script = script.replace("{{plot_background}}", s_plot_background)

        # 绘图区背景
        panel_background_fill = data.get("panel_background_fill", "")
        panel_background_color = data.get("panel_background_color", "")
        panel_background_size = data.get("panel_background_size", "")
        panel_background_linetype = data.get("panel_background_linetype", "")
        if panel_background_fill or panel_background_color or panel_background_size or panel_background_linetype:
            s_panel_background = f"panel.background = element_rect("
            s_panel_background += f'fill = "{panel_background_fill}",' if panel_background_fill else ""
            s_panel_background += f'colour = "{panel_background_color}",' if panel_background_color else ""
            s_panel_background += f'size = {panel_background_size},' if panel_background_size else ""
            s_panel_background += f'linetype = "{panel_background_linetype}",' if panel_background_linetype else ""
            s_panel_background += ")"
        else:
            s_panel_background = ""
        script = script.replace("{{panel_background}}", s_panel_background)

        # 主要网格线
        panel_grid_major_color = data.get("panel_grid_major_color", "")
        panel_grid_major_size = data.get("panel_grid_major_size", "")
        panel_grid_major_linetype = data.get("panel_grid_major_linetype", "")
        if panel_grid_major_color or panel_grid_major_size or panel_grid_major_linetype:
            s_panel_grid_major = f"panel.grid.major = element_line("
            s_panel_grid_major += f'colour = "{panel_grid_major_color}",' if panel_grid_major_color else ""
            s_panel_grid_major += f'size = {panel_grid_major_size},' if panel_grid_major_size else ""
            s_panel_grid_major += f'linetype = "{panel_grid_major_linetype}",' if panel_grid_major_linetype else ""
            s_panel_grid_major += ")"
        else:
            s_panel_grid_major = ""
        script = script.replace("{{panel_grid_major}}", s_panel_grid_major)

        # 次要网格线
        panel_grid_minor_color = data.get("panel_grid_minor_color", "")
        panel_grid_minor_size = data.get("panel_grid_minor_size", "")
        panel_grid_minor_linetype = data.get("panel_grid_minor_linetype", "")
        if panel_grid_minor_color or panel_grid_minor_size or panel_grid_minor_linetype:
            s_panel_grid_minor = f"panel.grid.minor = element_line("
            s_panel_grid_minor += f'colour = "{panel_grid_minor_color}",' if panel_grid_minor_color else ""
            s_panel_grid_minor += f'size = {panel_grid_minor_size},' if panel_grid_minor_size else ""
            s_panel_grid_minor += f'linetype = "{panel_grid_minor_linetype}",' if panel_grid_minor_linetype else ""
            s_panel_grid_minor += ")"
        else:
            s_panel_grid_minor = ""
        script = script.replace("{{panel_grid_minor}}", s_panel_grid_minor)

        # 全局字体
        text_family = data.get("text_family", "")
        text_size = data.get("text_size", "")
        text_face = data.get("text_face", "")
        text_color = data.get("text_color", "")
        text_vjust = data.get("text_vjust", "")
        text_angle = data.get("text_angle", "")
        if text_family or text_size or text_face or text_color or text_vjust or text_angle:
            s_text = f"axis.text = element_text("
            s_text += f'family = "{text_family}",' if text_family else ""
            s_text += f'size = {text_size},' if text_size else ""
            s_text += f'face = "{text_face}",' if text_face else ""
            s_text += f'colour = "{text_color}",' if text_color else ""
            s_text += f'vjust = {text_vjust},' if text_vjust else ""
            s_text += f'angle = {text_angle},' if text_angle else ""
            s_text += ")"
        else:
            s_text = ""
        script = script.replace("{{axis_text}}", s_text)

        # x轴字体
        if data.get("text_x_blank") == "true":
            s_text_x = "axis.text.x = element_blank() "
        else:
            text_x_family = data.get("text_x_family", "")
            text_x_size = data.get("text_x_size", "")
            text_x_face = data.get("text_x_face", "")
            text_x_color = data.get("text_x_color", "")
            text_x_vjust = data.get("text_x_vjust", "")
            text_x_hjust = data.get("text_x_hjust", "")
            text_x_angle = data.get("text_x_angle", "")
            if text_x_family or text_x_size or text_x_face or text_x_color or text_x_vjust or text_x_hjust or text_x_angle:
                s_text_x = f"axis.text.x = element_text("
                s_text_x += f'family = "{text_x_family}",' if text_x_family else ""
                s_text_x += f'size = {text_x_size},' if text_x_size else ""
                s_text_x += f'face = "{text_x_face}",' if text_x_face else ""
                s_text_x += f'colour = "{text_x_color}",' if text_x_color else ""
                s_text_x += f'vjust = {text_x_vjust},' if text_x_vjust else ""
                s_text_x += f'hjust = {text_x_hjust},' if text_x_hjust else ""
                s_text_x += f'angle = {text_x_angle},' if text_x_angle else ""
                s_text_x += ")"
            else:
                s_text_x = ""
        script = script.replace("{{axis_text_x}}", s_text_x)

        # y轴字体
        if data.get("text_y_blank") == "true":
            s_text_y = "axis.text.y = element_blank() "
        else:
            text_y_family = data.get("text_y_family", "")
            text_y_size = data.get("text_y_size", "")
            text_y_face = data.get("text_y_face", "")
            text_y_color = data.get("text_y_color", "")
            text_y_vjust = data.get("text_y_vjust", "")
            text_y_hjust = data.get("text_y_hjust", "")
            text_y_angle = data.get("text_y_angle", "")
            if text_y_family or text_y_size or text_y_face or text_y_color or text_y_vjust or text_y_hjust or text_y_angle:
                s_text_y = f"axis.text.y = element_text("
                s_text_y += f'family = "{text_y_family}",' if text_y_family else ""
                s_text_y += f'size = {text_y_size},' if text_y_size else ""
                s_text_y += f'face = "{text_y_face}",' if text_y_face else ""
                s_text_y += f'colour = "{text_y_color}",' if text_y_color else ""
                s_text_y += f'vjust = {text_y_vjust},' if text_y_vjust else ""
                s_text_y += f'hjust = {text_y_hjust},' if text_y_hjust else ""
                s_text_y += f'angle = {text_y_angle},' if text_y_angle else ""
                s_text_y += ")"
            else:
                s_text_y = ""
        script = script.replace("{{axis_text_y}}", s_text_y)

        # 坐标轴线
        axis_line_color = data.get("axis_line_color", "")
        axis_line_size = data.get("axis_line_size", "")
        axis_line_linetype = data.get("axis_line_linetype", "")
        if axis_line_color or axis_line_size or axis_line_linetype:
            s_axis_line = "axis.line = element_line("
            s_axis_line += f'colour = "{axis_line_color}",' if axis_line_color else ""
            s_axis_line += f'size = {axis_line_size},' if axis_line_size else ""
            s_axis_line += f'linetype = "{axis_line_linetype}",' if axis_line_linetype else ""
            s_axis_line += ")"
        else:
            s_axis_line = ""
        script = script.replace("{{axis_line}}", s_axis_line)

        # 坐标刻度
        axis_ticks_color = data.get("axis_ticks_color", "")
        axis_ticks_size = data.get("axis_ticks_size", "")
        axis_ticks_linetype = data.get("axis_ticks_linetype", "")
        if axis_ticks_color or axis_ticks_size or axis_ticks_linetype:
            s_axis_ticks = "axis.ticks = element_line("
            s_axis_ticks += f'colour = "{axis_ticks_color}",' if axis_ticks_color else ""
            s_axis_ticks += f'size = {axis_ticks_size},' if axis_ticks_size else ""
            s_axis_ticks += f'linetype = "{axis_ticks_linetype}",' if axis_ticks_linetype else ""
            s_axis_ticks += ")"
        else:
            s_axis_ticks = ""
        script = script.replace("{{axis_ticks}}", s_axis_ticks)

        # 标题内容
        labs_title = data.get("labs_title", "")
        labs_x = data.get("labs_x", "")
        labs_y = data.get("labs_y", "")
        labs_color = data.get("labs_color", "")
        labs_fill = data.get("labs_fill", "")
        labs_size = data.get("labs_size", "")
        labs_linetype = data.get("labs_linetype", "")
        labs_shape = data.get("labs_shape", "")
        labs_alpha = data.get("labs_alpha", "")
        subtitle_content = data.get("subtitle_content", "")
        caption_content = data.get("caption_content", "")
        if labs_title or labs_x or labs_y or labs_color or labs_fill or labs_size or labs_linetype or labs_shape or \
                labs_alpha or subtitle_content or caption_content:
            s_labs = "labs("
            s_labs += f'title = "{labs_title}",' if labs_title else ""
            s_labs += f'x = "{labs_x}",' if labs_x else ""
            s_labs += f'y = "{labs_y}",' if labs_y else ""
            s_labs += f'colour = "{labs_color}",' if labs_color else ""
            s_labs += f'fill = "{labs_fill}",' if labs_fill else ""
            s_labs += f'size = "{labs_size}",' if labs_size else ""
            s_labs += f'linetype = "{labs_linetype}",' if labs_linetype else ""
            s_labs += f'shape = "{labs_shape}",' if labs_shape else ""
            s_labs += f'alpha = "{labs_alpha}",' if labs_alpha else ""
            s_labs += f'subtitle = "{subtitle_content}",' if subtitle_content else ""
            s_labs += f'caption = "{caption_content}",' if caption_content else ""
            s_labs = s_labs.strip(",")
            s_labs += ")"
        else:
            s_labs = ""
        script = script.replace("{{labs}}", s_labs)

        # title 格式
        plot_title_family = data.get("plot_title_family", "")
        plot_title_size = data.get("plot_title_size", "")
        plot_title_face = data.get("plot_title_face", "")
        plot_title_color = data.get("plot_title_color", "")
        plot_title_vjust = data.get("plot_title_vjust", "")
        plot_title_hjust = data.get("plot_title_hjust", "")
        plot_title_angle = data.get("plot_title_angle", "")
        if plot_title_family or plot_title_size or plot_title_face or plot_title_color or plot_title_vjust or plot_title_hjust or plot_title_angle:
            s_plot_title = "plot.title = element_text("
            s_plot_title += f'family = "{plot_title_family}",' if plot_title_family else ""
            s_plot_title += f'size = {plot_title_size},' if plot_title_size else ""
            s_plot_title += f'face = "{plot_title_face}",' if plot_title_face else ""
            s_plot_title += f'colour = "{plot_title_color}",' if plot_title_color else ""
            s_plot_title += f'vjust = {plot_title_vjust},' if plot_title_vjust else ""
            s_plot_title += f'hjust = {plot_title_hjust},' if plot_title_hjust else ""
            s_plot_title += f'angle = {plot_title_angle},' if plot_title_angle else ""
            s_plot_title = s_plot_title.strip(",") + ")"
        else:
            s_plot_title = ""
        script = script.replace("{{plot_title}}", s_plot_title)

        # X轴标题格式
        aixs_title_x_family = data.get("aixs_title_x_family", "")
        aixs_title_x_size = data.get("aixs_title_x_size", "")
        aixs_title_x_face = data.get("aixs_title_x_face", "")
        aixs_title_x_color = data.get("aixs_title_x_color", "")
        aixs_title_x_vjust = data.get("aixs_title_x_vjust", "")
        aixs_title_x_hjust = data.get("aixs_title_x_hjust", "")
        aixs_title_x_angle = data.get("aixs_title_x_angle", "")
        if aixs_title_x_family or aixs_title_x_size or aixs_title_x_face or aixs_title_x_color or aixs_title_x_vjust or \
                aixs_title_x_hjust or aixs_title_x_angle:
            s_axis_x_title = "axis.title.x = element_text("
            s_axis_x_title += f'family = "{aixs_title_x_family}",' if aixs_title_x_family else ""
            s_axis_x_title += f'size = {aixs_title_x_size},' if aixs_title_x_size else ""
            s_axis_x_title += f'face = "{aixs_title_x_face}",' if aixs_title_x_face else ""
            s_axis_x_title += f'colour = "{aixs_title_x_color}",' if aixs_title_x_color else ""
            s_axis_x_title += f'vjust = {aixs_title_x_vjust},' if aixs_title_x_vjust else ""
            s_axis_x_title += f'hjust = {aixs_title_x_hjust},' if aixs_title_x_hjust else ""
            s_axis_x_title += f'angle = {aixs_title_x_angle},' if aixs_title_x_angle else ""
            s_axis_x_title = s_axis_x_title.strip(",") + ")"
        else:
            s_axis_x_title = ""
        script = script.replace("{{axis_title_x}}", s_axis_x_title)

        # Y轴标题格式
        aixs_title_y_family = data.get("aixs_title_y_family", "")
        aixs_title_y_size = data.get("aixs_title_y_size", "")
        aixs_title_y_face = data.get("aixs_title_y_face", "")
        aixs_title_y_color = data.get("aixs_title_y_color", "")
        aixs_title_y_vjust = data.get("aixs_title_y_vjust", "")
        aixs_title_y_hjust = data.get("aixs_title_y_hjust", "")
        aixs_title_y_angle = data.get("aixs_title_y_angle", "")
        if aixs_title_y_family or aixs_title_y_size or aixs_title_y_face or aixs_title_y_color or aixs_title_y_vjust or \
                aixs_title_y_hjust or aixs_title_y_angle:
            s_axis_y_title = "axis.title.y = element_text("
            s_axis_y_title += f'family = "{aixs_title_y_family}",' if aixs_title_y_family else ""
            s_axis_y_title += f'size = {aixs_title_y_size},' if aixs_title_y_size else ""
            s_axis_y_title += f'face = "{aixs_title_y_face}",' if aixs_title_y_face else ""
            s_axis_y_title += f'colour = "{aixs_title_y_color}",' if aixs_title_y_color else ""
            s_axis_y_title += f'vjust = {aixs_title_y_vjust},' if aixs_title_y_vjust else ""
            s_axis_y_title += f'hjust = {aixs_title_y_hjust},' if aixs_title_y_hjust else ""
            s_axis_y_title += f'angle = {aixs_title_y_angle},' if aixs_title_y_angle else ""
            s_axis_y_title = s_axis_y_title.strip(",") + ")"
        else:
            s_axis_y_title = ""
        script = script.replace("{{axis_title_y}}", s_axis_y_title)

        # 图例位置
        legend_position = data.get("legend_position", "")
        position_x = data.get("legend_position_x", "")
        position_y = data.get("legend_position_y", "")
        if legend_position or (position_x and position_y):
            if legend_position:
                s_legend_position = f'legend.position = "{legend_position}"'
            else:
                s_legend_position = f'legend.position = c("{position_x}", "{position_y}")'
        else:
            s_legend_position = ""
        script = script.replace("{{legend_position}}", s_legend_position)

        # 图例方向
        legend_direction = data.get("legend_direction", "")
        s_legend_direction = f'legend.direction = "{legend_direction}"' if legend_direction else ""
        script = script.replace("{{legend_direction}}", s_legend_direction)

        # 图例背景
        legend_background_fill = data.get("legend_background_fill", "")
        legend_background_color = data.get("legend_background_color", "")
        legend_background_size = data.get("legend_background_size", "")
        legend_background_linetype = data.get("legend_background_linetype", "")
        if legend_background_fill or legend_background_color or legend_background_size or legend_background_linetype:
            s_legend_background = "legend.background = element_rect("
            s_legend_background += f'fill = "{legend_background_fill}",' if legend_background_fill else ""
            s_legend_background += f'colour = "{legend_background_color}",' if legend_background_color else ""
            s_legend_background += f'size = {legend_background_size},' if legend_background_size else ""
            s_legend_background += f'linetype = "{legend_background_linetype}",' if legend_background_linetype else ""
            s_legend_background = s_legend_background.strip(",") + ")"
        else:
            s_legend_background = ""
        script = script.replace("{{legend_background}}", s_legend_background)

        # legend keys
        legend_keys_fill = data.get("legend_keys_fill", "")
        legend_keys_color = data.get("legend_keys_color", "")
        legend_keys_size = data.get("legend_keys_size", "")
        legend_keys_linetype = data.get("legend_keys_linetype", "")
        if legend_keys_fill or legend_keys_color or legend_keys_size or legend_keys_linetype:
            s_legend_keys = "legend.key = element_rect("
            s_legend_keys += f'fill = "{legend_keys_fill}",' if legend_keys_fill else ""
            s_legend_keys += f'colour = "{legend_keys_color}",' if legend_keys_color else ""
            s_legend_keys += f'size = {legend_keys_size},' if legend_keys_size else ""
            s_legend_keys += f'linetype = "{legend_keys_linetype}",' if legend_keys_linetype else ""
            s_legend_keys = s_legend_keys.strip(",") + ")"
        else:
            s_legend_keys = ""
        script = script.replace("{{legend_keys}}", s_legend_keys)

        # 副标题
        subtitle_family = data.get("subtitle_family", "")
        subtitle_size = data.get("subtitle_size", "")
        subtitle_face = data.get("subtitle_face", "")
        subtitle_color = data.get("subtitle_color", "")
        subtitle_hjust = data.get("subtitle_hjust", "")
        if subtitle_family or subtitle_size or subtitle_face or subtitle_color or subtitle_hjust:
            s_subtitle = f"plot.subtitle = element_text("
            s_subtitle += f'family = "{subtitle_family}",' if subtitle_family else ""
            s_subtitle += f'size = {subtitle_size},' if subtitle_size else ""
            s_subtitle += f'face = "{subtitle_face}",' if subtitle_face else ""
            s_subtitle += f'colour = "{subtitle_color}",' if subtitle_color else ""
            s_subtitle += f'hjust = {subtitle_hjust},' if subtitle_hjust else ""
            s_subtitle = s_subtitle.strip(",") + ")"
        else:
            s_subtitle = ""
        script = script.replace("{{plot_subtitle}}", s_subtitle)

        # 脚注
        caption_family = data.get("caption_family", "")
        caption_size = data.get("caption_size", "")
        caption_face = data.get("caption_face", "")
        caption_color = data.get("caption_color", "")
        caption_hjust = data.get("caption_hjust", "")
        if caption_family or caption_size or caption_face or caption_hjust or caption_color:
            s_caption = f"plot.caption = element_text("
            s_caption += f'family = "{caption_family}",' if caption_family else ""
            s_caption += f'size = {caption_size},' if caption_size else ""
            s_caption += f'face = "{caption_face}",' if caption_face else ""
            s_caption += f'colour = "{caption_color}",' if caption_color else ""
            s_caption += f'hjust = {caption_hjust},' if caption_hjust else ""
            s_caption = s_caption.strip(",") + ")"
        else:
            s_caption = ""
        script = script.replace("{{plot_caption}}", s_caption)

        # 图形大小
        fig_height = data.get("output_height", 6)
        fig_width = data.get("output_width", 8)
        fig_units = data.get("output_units", "in")
        fig_dpi = data.get("output_dpi", "")
        s_fig_size = f"width={fig_width}, height={fig_height}, units='{fig_units}' "
        s_fig_size = s_fig_size + f",dpi={fig_dpi} " if fig_dpi else s_fig_size
        script = script.replace("{{pig_size}}", s_fig_size)

        #最后处理
        script = script.replace("<< +>>", "")
        script = script.replace("<<,>>", "")
        script = script.replace("<<", "")
        script = script.replace(">>", "")
        script = script.replace(">>", "")
        fw.write(script)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    print(script)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "f_output": f_output})


@_is_post
def plot_boxplot(request):
    """绘制箱线图图"""

    # 表单验证
    data = BoxPlotForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotDot")
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{data.get('output_name', 'DotPlot')}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:

        # 基本框架
        script = """
            library('ggplot2')
            library('openxlsx')
            library('RColorBrewer')

            df_data <- {{read_table}}

            p <- ggplot(df_data, aes({{x}}, {{y}})) + 
                 geom_boxplot({{geom_boxplot}}) +
                 <<{{plot_point}} +>>   # 散点
                 <<{{plot_theme}} +>>   # 主题
                 <<{{scale_qual_color}} +>>   #  离散型颜色
                 <<{{scale_qual_fill}} +>>   #  离散型颜色
                 <<{{scale_seq_color}} +>>  # 连续型颜色
                 <<{{scale_seq_fill}} +>>  # 连续型颜色
                 <<{{facets}} +>>  # 分面
                 <<{{scale_y_continuous}} +>>  # y轴刻度范围
                 <<{{labs}} +>>

                 theme(
                     <<{{plot_background}},>>
                     <<{{panel_background}},>>
                     <<{{panel_grid_major}},>>
                     <<{{panel_grid_minor}},>>
                     <<{{axis_text}},>>
                     <<{{axis_text_x}},>>
                     <<{{axis_text_y}},>>
                     <<{{axis_line}},>>
                     <<{{axis_ticks}},>>
                     <<{{axis_title_x}},>>
                     <<{{axis_title_y}},>>
                     <<{{plot_title}},>>
                     <<{{legend_background}},>>
                     <<{{legend_keys}},>>
                     <<{{legend_position}},>>
                     <<{{legend_direction}},>>
                     <<{{plot_subtitle}},>>
                     <<{{plot_caption}},>>
                 )

            ggsave(p, filename="{{f_output}}", {{pig_size}})
        """
        script = script.replace("{{x}}", data.get("x"))
        script = script.replace("{{y}}", data.get("y"))
        script = script.replace("{{f_output}}", f_output)

        # 读取文件
        input_file = data.get("input_file")
        if input_file.endswith("xlsx") or input_file.endswith("xls"):
            s_read_table = f"read.xlsx('{input_file}',sheet = 1)"
        elif input_file.endswith("csv"):
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F)"
        else:
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F, sep='\\t')"
        script = script.replace("{{read_table}}", s_read_table)

        # box独有配置
        box_color = data.get("box_color", "")
        box_fill = data.get("box_fill", "")
        outlier_fill = data.get("outlier_fill", "")
        outlier_color = data.get("outlier_color", "")
        outlier_shape = data.get("outlier_shape", "")
        outlier_size = data.get("outlier_size", "")
        outlier_alpha = data.get("outlier_alpha", "")

        group = data.get("group", "")
        group_fill = data.get("group_fill", "")
        group_color = data.get("group_color", "")
        group_shape = data.get("group_shape", "")

        s_geom_box = ""
        if group or group_fill or group_color or group_shape:
            s_aes = f"aes("
            s_aes += f"group={group}," if group else ""
            s_aes += f"fill={group_fill}," if group_fill else ""
            s_aes += f"color={group_color}," if group_color else ""
            s_aes += "), "
            s_geom_box += s_aes

        s_geom_box += f"outlier.size={outlier_size}," if outlier_size else ""
        s_geom_box += f"outlier.shape={outlier_shape}," if outlier_shape else ""
        s_geom_box += f"outlier.alpha={outlier_alpha}," if outlier_alpha else ""
        s_geom_box += f"outlier.fill='{outlier_fill}'," if outlier_fill else ""
        s_geom_box += f"outlier.color='{outlier_color}'," if outlier_color else ""
        script = script.replace("{{geom_boxplot}}", s_geom_box)

        # 散点配置
        point_size = data.get("point_size", "")
        point_shape = data.get("point_shape", "")
        point_color = data.get("point_color", "")
        point_fill = data.get("point_fill", "")
        point_alpha = data.get("point_alpha", "")

        if point_size or point_shape or point_color or point_fill or point_alpha:
            s_geom_point = f"geom_point(aes(),"
            s_geom_point += f"size={point_size}," if point_size else ""
            s_geom_point += f"shape={point_shape}," if point_shape else ""
            s_geom_point += f"color='{point_color}'," if point_color else ""
            s_geom_point += f"fill='{point_fill}'," if point_fill else ""
            s_geom_point += f"alpha='{point_alpha}'," if point_alpha else ""
            s_geom_point += ", position = position_jitter())"
        else:
            s_geom_point = ""
        script = script.replace("{{plot_point}}", s_geom_point)

        # 主题
        themes = data.get("plot_themes")
        if themes:
            script = script.replace("{{plot_theme}}", f"theme_{themes}()")
        else:
            script = script.replace("{{plot_theme}}", f"")

        # y轴刻度范围
        y_minu = data.get("y_min")
        y_max = data.get("y_max")
        y_step = data.get("y_step")
        if y_minu or y_max or y_step:
            script = script.replace("{{scale_y_continuous}}", f"scale_x_continuous(breaks=seq({y_minu}，{y_max}，{y_step}))")
        else:
            script = script.replace("{{scale_y_continuous}}", f"")

        # 配置离散型颜色 -- 边框色
        color_qual = data.get("color_qual_theme", "")
        color_qual_self = data.get("color_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_color_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_color_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_color}}", s_scale_color)

        # 配置离散型颜色 -- 填充色
        color_qual = data.get("fill_qual_theme", "")
        color_qual_self = data.get("fill_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_fill_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_fill_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_fill}}", s_scale_color)

        # 配置连续型颜色 -- 边框色
        color_seq = data.get("color_seq_theme", "")
        color_seq_self = data.get("color_seq_self", "")
        color_seq_self_value = data.get("color_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_color_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_color_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_color}}", s_scale_fill)

        # 配置连续型颜色 -- 填充
        color_seq = data.get("fill_seq_theme", "")
        color_seq_self = data.get("fill_seq_self", "")
        color_seq_self_value = data.get("fill_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_fill_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_fill_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_fill}}", s_scale_fill)

        # 分面参数
        col_facets = data.get("col_facets", "")
        row_facets = data.get("row_facets", "")
        facets_nrow = data.get("facets_nrow")
        facets_ncol = data.get("facets_ncol")
        facets_scales = data.get("facets_scales")
        if col_facets and row_facets:
            s_facets = f"facet_grid('{row_facets} ~ {col_facets}'"
        elif col_facets:
            s_facets = f"facet_grid('. ~ {col_facets}'"
        elif row_facets:
            s_facets = f"facet_grid('{row_facets} ~ .'"
        else:
            s_facets = ""

        if s_facets:
            if facets_nrow:
                s_facets += f" ,nrow={facets_nrow}"
            if facets_ncol:
                s_facets += f" ,ncol={facets_ncol}"
            if facets_scales:
                s_facets += f" ,scales='{facets_scales}'"
            s_facets += ")"
        script = script.replace("{{facets}}", s_facets)

        # 整体背景
        plot_background_fill = data.get("plot_background_fill", "")
        plot_background_color = data.get("plot_background_color", "")
        plot_background_size = data.get("plot_background_size", "")
        plot_background_linetype = data.get("plot_background_linetype", "")
        if plot_background_fill or plot_background_color or plot_background_size or plot_background_linetype:
            s_plot_background = f"plot.background = element_rect("
            s_plot_background += f'fill = "{plot_background_fill}",' if plot_background_fill else ""
            s_plot_background += f'colour = "{plot_background_color}",' if plot_background_color else ""
            s_plot_background += f'size = {plot_background_size},' if plot_background_size else ""
            s_plot_background += f'linetype = "{plot_background_linetype}",' if plot_background_linetype else ""
            s_plot_background += ")"
        else:
            s_plot_background = ""
        script = script.replace("{{plot_background}}", s_plot_background)

        # 绘图区背景
        panel_background_fill = data.get("panel_background_fill", "")
        panel_background_color = data.get("panel_background_color", "")
        panel_background_size = data.get("panel_background_size", "")
        panel_background_linetype = data.get("panel_background_linetype", "")
        if panel_background_fill or panel_background_color or panel_background_size or panel_background_linetype:
            s_panel_background = f"panel.background = element_rect("
            s_panel_background += f'fill = "{panel_background_fill}",' if panel_background_fill else ""
            s_panel_background += f'colour = "{panel_background_color}",' if panel_background_color else ""
            s_panel_background += f'size = {panel_background_size},' if panel_background_size else ""
            s_panel_background += f'linetype = "{panel_background_linetype}",' if panel_background_linetype else ""
            s_panel_background += ")"
        else:
            s_panel_background = ""
        script = script.replace("{{panel_background}}", s_panel_background)

        # 主要网格线
        panel_grid_major_color = data.get("panel_grid_major_color", "")
        panel_grid_major_size = data.get("panel_grid_major_size", "")
        panel_grid_major_linetype = data.get("panel_grid_major_linetype", "")
        if panel_grid_major_color or panel_grid_major_size or panel_grid_major_linetype:
            s_panel_grid_major = f"panel.grid.major = element_line("
            s_panel_grid_major += f'colour = "{panel_grid_major_color}",' if panel_grid_major_color else ""
            s_panel_grid_major += f'size = {panel_grid_major_size},' if panel_grid_major_size else ""
            s_panel_grid_major += f'linetype = "{panel_grid_major_linetype}",' if panel_grid_major_linetype else ""
            s_panel_grid_major += ")"
        else:
            s_panel_grid_major = ""
        script = script.replace("{{panel_grid_major}}", s_panel_grid_major)

        # 次要网格线
        panel_grid_minor_color = data.get("panel_grid_minor_color", "")
        panel_grid_minor_size = data.get("panel_grid_minor_size", "")
        panel_grid_minor_linetype = data.get("panel_grid_minor_linetype", "")
        if panel_grid_minor_color or panel_grid_minor_size or panel_grid_minor_linetype:
            s_panel_grid_minor = f"panel.grid.minor = element_line("
            s_panel_grid_minor += f'colour = "{panel_grid_minor_color}",' if panel_grid_minor_color else ""
            s_panel_grid_minor += f'size = {panel_grid_minor_size},' if panel_grid_minor_size else ""
            s_panel_grid_minor += f'linetype = "{panel_grid_minor_linetype}",' if panel_grid_minor_linetype else ""
            s_panel_grid_minor += ")"
        else:
            s_panel_grid_minor = ""
        script = script.replace("{{panel_grid_minor}}", s_panel_grid_minor)

        # 全局字体
        text_family = data.get("text_family", "")
        text_size = data.get("text_size", "")
        text_face = data.get("text_face", "")
        text_color = data.get("text_color", "")
        text_vjust = data.get("text_vjust", "")
        text_angle = data.get("text_angle", "")
        if text_family or text_size or text_face or text_color or text_vjust or text_angle:
            s_text = f"axis.text = element_text("
            s_text += f'family = "{text_family}",' if text_family else ""
            s_text += f'size = {text_size},' if text_size else ""
            s_text += f'face = "{text_face}",' if text_face else ""
            s_text += f'colour = "{text_color}",' if text_color else ""
            s_text += f'vjust = {text_vjust},' if text_vjust else ""
            s_text += f'angle = {text_angle},' if text_angle else ""
            s_text += ")"
        else:
            s_text = ""
        script = script.replace("{{axis_text}}", s_text)

        # x轴字体
        if data.get("text_x_blank") == "true":
            s_text_x = "axis.text.x = element_blank() "
        else:
            text_x_family = data.get("text_x_family", "")
            text_x_size = data.get("text_x_size", "")
            text_x_face = data.get("text_x_face", "")
            text_x_color = data.get("text_x_color", "")
            text_x_vjust = data.get("text_x_vjust", "")
            text_x_hjust = data.get("text_x_hjust", "")
            text_x_angle = data.get("text_x_angle", "")
            if text_x_family or text_x_size or text_x_face or text_x_color or text_x_vjust or text_x_hjust or text_x_angle:
                s_text_x = f"axis.text.x = element_text("
                s_text_x += f'family = "{text_x_family}",' if text_x_family else ""
                s_text_x += f'size = {text_x_size},' if text_x_size else ""
                s_text_x += f'face = "{text_x_face}",' if text_x_face else ""
                s_text_x += f'colour = "{text_x_color}",' if text_x_color else ""
                s_text_x += f'vjust = {text_x_vjust},' if text_x_vjust else ""
                s_text_x += f'hjust = {text_x_hjust},' if text_x_hjust else ""
                s_text_x += f'angle = {text_x_angle},' if text_x_angle else ""
                s_text_x += ")"
            else:
                s_text_x = ""
        script = script.replace("{{axis_text_x}}", s_text_x)

        # y轴字体
        if data.get("text_y_blank") == "true":
            s_text_y = "axis.text.y = element_blank() "
        else:
            text_y_family = data.get("text_y_family", "")
            text_y_size = data.get("text_y_size", "")
            text_y_face = data.get("text_y_face", "")
            text_y_color = data.get("text_y_color", "")
            text_y_vjust = data.get("text_y_vjust", "")
            text_y_hjust = data.get("text_y_hjust", "")
            text_y_angle = data.get("text_y_angle", "")
            if text_y_family or text_y_size or text_y_face or text_y_color or text_y_vjust or text_y_hjust or text_y_angle:
                s_text_y = f"axis.text.y = element_text("
                s_text_y += f'family = "{text_y_family}",' if text_y_family else ""
                s_text_y += f'size = {text_y_size},' if text_y_size else ""
                s_text_y += f'face = "{text_y_face}",' if text_y_face else ""
                s_text_y += f'colour = "{text_y_color}",' if text_y_color else ""
                s_text_y += f'vjust = {text_y_vjust},' if text_y_vjust else ""
                s_text_y += f'hjust = {text_y_hjust},' if text_y_hjust else ""
                s_text_y += f'angle = {text_y_angle},' if text_y_angle else ""
                s_text_y += ")"
            else:
                s_text_y = ""
        script = script.replace("{{axis_text_y}}", s_text_y)

        # 坐标轴线
        axis_line_color = data.get("axis_line_color", "")
        axis_line_size = data.get("axis_line_size", "")
        axis_line_linetype = data.get("axis_line_linetype", "")
        if axis_line_color or axis_line_size or axis_line_linetype:
            s_axis_line = "axis.line = element_line("
            s_axis_line += f'colour = "{axis_line_color}",' if axis_line_color else ""
            s_axis_line += f'size = {axis_line_size},' if axis_line_size else ""
            s_axis_line += f'linetype = "{axis_line_linetype}",' if axis_line_linetype else ""
            s_axis_line += ")"
        else:
            s_axis_line = ""
        script = script.replace("{{axis_line}}", s_axis_line)

        # 坐标刻度
        axis_ticks_color = data.get("axis_ticks_color", "")
        axis_ticks_size = data.get("axis_ticks_size", "")
        axis_ticks_linetype = data.get("axis_ticks_linetype", "")
        if axis_ticks_color or axis_ticks_size or axis_ticks_linetype:
            s_axis_ticks = "axis.ticks = element_line("
            s_axis_ticks += f'colour = "{axis_ticks_color}",' if axis_ticks_color else ""
            s_axis_ticks += f'size = {axis_ticks_size},' if axis_ticks_size else ""
            s_axis_ticks += f'linetype = "{axis_ticks_linetype}",' if axis_ticks_linetype else ""
            s_axis_ticks += ")"
        else:
            s_axis_ticks = ""
        script = script.replace("{{axis_ticks}}", s_axis_ticks)

        # 标题内容
        labs_title = data.get("labs_title", "")
        labs_x = data.get("labs_x", "")
        labs_y = data.get("labs_y", "")
        labs_color = data.get("labs_color", "")
        labs_fill = data.get("labs_fill", "")
        labs_size = data.get("labs_size", "")
        labs_linetype = data.get("labs_linetype", "")
        labs_shape = data.get("labs_shape", "")
        labs_alpha = data.get("labs_alpha", "")
        subtitle_content = data.get("subtitle_content", "")
        caption_content = data.get("caption_content", "")
        if labs_title or labs_x or labs_y or labs_color or labs_fill or labs_size or labs_linetype or labs_shape or \
                labs_alpha or subtitle_content or caption_content:
            s_labs = "labs("
            s_labs += f'title = "{labs_title}",' if labs_title else ""
            s_labs += f'x = "{labs_x}",' if labs_x else ""
            s_labs += f'y = "{labs_y}",' if labs_y else ""
            s_labs += f'colour = "{labs_color}",' if labs_color else ""
            s_labs += f'fill = "{labs_fill}",' if labs_fill else ""
            s_labs += f'size = "{labs_size}",' if labs_size else ""
            s_labs += f'linetype = "{labs_linetype}",' if labs_linetype else ""
            s_labs += f'shape = "{labs_shape}",' if labs_shape else ""
            s_labs += f'alpha = "{labs_alpha}",' if labs_alpha else ""
            s_labs += f'subtitle = "{subtitle_content}",' if subtitle_content else ""
            s_labs += f'caption = "{caption_content}",' if caption_content else ""
            s_labs = s_labs.strip(",")
            s_labs += ")"
        else:
            s_labs = ""
        script = script.replace("{{labs}}", s_labs)

        # title 格式
        plot_title_family = data.get("plot_title_family", "")
        plot_title_size = data.get("plot_title_size", "")
        plot_title_face = data.get("plot_title_face", "")
        plot_title_color = data.get("plot_title_color", "")
        plot_title_vjust = data.get("plot_title_vjust", "")
        plot_title_hjust = data.get("plot_title_hjust", "")
        plot_title_angle = data.get("plot_title_angle", "")
        if plot_title_family or plot_title_size or plot_title_face or plot_title_color or plot_title_vjust or plot_title_hjust or plot_title_angle:
            s_plot_title = "plot.title = element_text("
            s_plot_title += f'family = "{plot_title_family}",' if plot_title_family else ""
            s_plot_title += f'size = {plot_title_size},' if plot_title_size else ""
            s_plot_title += f'face = "{plot_title_face}",' if plot_title_face else ""
            s_plot_title += f'colour = "{plot_title_color}",' if plot_title_color else ""
            s_plot_title += f'vjust = {plot_title_vjust},' if plot_title_vjust else ""
            s_plot_title += f'hjust = {plot_title_hjust},' if plot_title_hjust else ""
            s_plot_title += f'angle = {plot_title_angle},' if plot_title_angle else ""
            s_plot_title = s_plot_title.strip(",") + ")"
        else:
            s_plot_title = ""
        script = script.replace("{{plot_title}}", s_plot_title)

        # X轴标题格式
        aixs_title_x_family = data.get("aixs_title_x_family", "")
        aixs_title_x_size = data.get("aixs_title_x_size", "")
        aixs_title_x_face = data.get("aixs_title_x_face", "")
        aixs_title_x_color = data.get("aixs_title_x_color", "")
        aixs_title_x_vjust = data.get("aixs_title_x_vjust", "")
        aixs_title_x_hjust = data.get("aixs_title_x_hjust", "")
        aixs_title_x_angle = data.get("aixs_title_x_angle", "")
        if aixs_title_x_family or aixs_title_x_size or aixs_title_x_face or aixs_title_x_color or aixs_title_x_vjust or \
                aixs_title_x_hjust or aixs_title_x_angle:
            s_axis_x_title = "axis.title.x = element_text("
            s_axis_x_title += f'family = "{aixs_title_x_family}",' if aixs_title_x_family else ""
            s_axis_x_title += f'size = {aixs_title_x_size},' if aixs_title_x_size else ""
            s_axis_x_title += f'face = "{aixs_title_x_face}",' if aixs_title_x_face else ""
            s_axis_x_title += f'colour = "{aixs_title_x_color}",' if aixs_title_x_color else ""
            s_axis_x_title += f'vjust = {aixs_title_x_vjust},' if aixs_title_x_vjust else ""
            s_axis_x_title += f'hjust = {aixs_title_x_hjust},' if aixs_title_x_hjust else ""
            s_axis_x_title += f'angle = {aixs_title_x_angle},' if aixs_title_x_angle else ""
            s_axis_x_title = s_axis_x_title.strip(",") + ")"
        else:
            s_axis_x_title = ""
        script = script.replace("{{axis_title_x}}", s_axis_x_title)

        # Y轴标题格式
        aixs_title_y_family = data.get("aixs_title_y_family", "")
        aixs_title_y_size = data.get("aixs_title_y_size", "")
        aixs_title_y_face = data.get("aixs_title_y_face", "")
        aixs_title_y_color = data.get("aixs_title_y_color", "")
        aixs_title_y_vjust = data.get("aixs_title_y_vjust", "")
        aixs_title_y_hjust = data.get("aixs_title_y_hjust", "")
        aixs_title_y_angle = data.get("aixs_title_y_angle", "")
        if aixs_title_y_family or aixs_title_y_size or aixs_title_y_face or aixs_title_y_color or aixs_title_y_vjust or \
                aixs_title_y_hjust or aixs_title_y_angle:
            s_axis_y_title = "axis.title.y = element_text("
            s_axis_y_title += f'family = "{aixs_title_y_family}",' if aixs_title_y_family else ""
            s_axis_y_title += f'size = {aixs_title_y_size},' if aixs_title_y_size else ""
            s_axis_y_title += f'face = "{aixs_title_y_face}",' if aixs_title_y_face else ""
            s_axis_y_title += f'colour = "{aixs_title_y_color}",' if aixs_title_y_color else ""
            s_axis_y_title += f'vjust = {aixs_title_y_vjust},' if aixs_title_y_vjust else ""
            s_axis_y_title += f'hjust = {aixs_title_y_hjust},' if aixs_title_y_hjust else ""
            s_axis_y_title += f'angle = {aixs_title_y_angle},' if aixs_title_y_angle else ""
            s_axis_y_title = s_axis_y_title.strip(",") + ")"
        else:
            s_axis_y_title = ""
        script = script.replace("{{axis_title_y}}", s_axis_y_title)

        # 图例位置
        legend_position = data.get("legend_position", "")
        position_x = data.get("legend_position_x", "")
        position_y = data.get("legend_position_y", "")
        if legend_position or (position_x and position_y):
            if legend_position:
                s_legend_position = f'legend.position = "{legend_position}"'
            else:
                s_legend_position = f'legend.position = c("{position_x}", "{position_y}")'
        else:
            s_legend_position = ""
        script = script.replace("{{legend_position}}", s_legend_position)

        # 图例方向
        legend_direction = data.get("legend_direction", "")
        s_legend_direction = f'legend.direction = "{legend_direction}"' if legend_direction else ""
        script = script.replace("{{legend_direction}}", s_legend_direction)

        # 图例背景
        legend_background_fill = data.get("legend_background_fill", "")
        legend_background_color = data.get("legend_background_color", "")
        legend_background_size = data.get("legend_background_size", "")
        legend_background_linetype = data.get("legend_background_linetype", "")
        if legend_background_fill or legend_background_color or legend_background_size or legend_background_linetype:
            s_legend_background = "legend.background = element_rect("
            s_legend_background += f'fill = "{legend_background_fill}",' if legend_background_fill else ""
            s_legend_background += f'colour = "{legend_background_color}",' if legend_background_color else ""
            s_legend_background += f'size = {legend_background_size},' if legend_background_size else ""
            s_legend_background += f'linetype = "{legend_background_linetype}",' if legend_background_linetype else ""
            s_legend_background = s_legend_background.strip(",") + ")"
        else:
            s_legend_background = ""
        script = script.replace("{{legend_background}}", s_legend_background)

        # legend keys
        legend_keys_fill = data.get("legend_keys_fill", "")
        legend_keys_color = data.get("legend_keys_color", "")
        legend_keys_size = data.get("legend_keys_size", "")
        legend_keys_linetype = data.get("legend_keys_linetype", "")
        if legend_keys_fill or legend_keys_color or legend_keys_size or legend_keys_linetype:
            s_legend_keys = "legend.key = element_rect("
            s_legend_keys += f'fill = "{legend_keys_fill}",' if legend_keys_fill else ""
            s_legend_keys += f'colour = "{legend_keys_color}",' if legend_keys_color else ""
            s_legend_keys += f'size = {legend_keys_size},' if legend_keys_size else ""
            s_legend_keys += f'linetype = "{legend_keys_linetype}",' if legend_keys_linetype else ""
            s_legend_keys = s_legend_keys.strip(",") + ")"
        else:
            s_legend_keys = ""
        script = script.replace("{{legend_keys}}", s_legend_keys)

        # 副标题
        subtitle_family = data.get("subtitle_family", "")
        subtitle_size = data.get("subtitle_size", "")
        subtitle_face = data.get("subtitle_face", "")
        subtitle_color = data.get("subtitle_color", "")
        subtitle_hjust = data.get("subtitle_hjust", "")
        if subtitle_family or subtitle_size or subtitle_face or subtitle_color or subtitle_hjust:
            s_subtitle = f"plot.subtitle = element_text("
            s_subtitle += f'family = "{subtitle_family}",' if subtitle_family else ""
            s_subtitle += f'size = {subtitle_size},' if subtitle_size else ""
            s_subtitle += f'face = "{subtitle_face}",' if subtitle_face else ""
            s_subtitle += f'colour = "{subtitle_color}",' if subtitle_color else ""
            s_subtitle += f'hjust = {subtitle_hjust},' if subtitle_hjust else ""
            s_subtitle = s_subtitle.strip(",") + ")"
        else:
            s_subtitle = ""
        script = script.replace("{{plot_subtitle}}", s_subtitle)

        # 脚注
        caption_family = data.get("caption_family", "")
        caption_size = data.get("caption_size", "")
        caption_face = data.get("caption_face", "")
        caption_color = data.get("caption_color", "")
        caption_hjust = data.get("caption_hjust", "")
        if caption_family or caption_size or caption_face or caption_hjust or caption_color:
            s_caption = f"plot.caption = element_text("
            s_caption += f'family = "{caption_family}",' if caption_family else ""
            s_caption += f'size = {caption_size},' if caption_size else ""
            s_caption += f'face = "{caption_face}",' if caption_face else ""
            s_caption += f'colour = "{caption_color}",' if caption_color else ""
            s_caption += f'hjust = {caption_hjust},' if caption_hjust else ""
            s_caption = s_caption.strip(",") + ")"
        else:
            s_caption = ""
        script = script.replace("{{plot_caption}}", s_caption)

        # 图形大小
        fig_height = data.get("output_height", 6)
        fig_width = data.get("output_width", 8)
        fig_units = data.get("output_units", "in")
        fig_dpi = data.get("output_dpi", "")
        s_fig_size = f"width={fig_width}, height={fig_height}, units='{fig_units}' "
        s_fig_size = s_fig_size + f",dpi={fig_dpi} " if fig_dpi else s_fig_size
        script = script.replace("{{pig_size}}", s_fig_size)

        # 最后处理
        script = script.replace("<< +>>", "")
        script = script.replace("<<,>>", "")
        script = script.replace("<<", "")
        script = script.replace(">>", "")
        script = script.replace(">>", "")
        fw.write(script)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    print(script)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "f_output": f_output})


@_is_post
def plot_line(request):
    """绘制散点图"""

    # 表单验证
    data = DotPlotForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotDot")
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{data.get('output_name', 'DotPlot')}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:

        # 基本框架
        script = """
            library('ggplot2')
            library('openxlsx')
            library('RColorBrewer')

            df_data <- {{read_table}}

            p <- ggplot(df_data, aes({{x}}, {{y}}, group = 1)) + 
                 geom_line({{geom_line}}) +
                 <<{{plot_theme}} +>>   # 主题
                 <<{{scale_qual_color}} +>>   #  离散型颜色
                 <<{{scale_qual_fill}} +>>   #  离散型颜色
                 <<{{scale_seq_color}} +>>  # 连续型颜色
                 <<{{scale_seq_fill}} +>>  # 连续型颜色
                 <<{{facets}} +>>  # 分面
                 <<{{labs}} +>>

                 theme(
                     <<{{plot_background}},>>
                     <<{{panel_background}},>>
                     <<{{panel_grid_major}},>>
                     <<{{panel_grid_minor}},>>
                     <<{{axis_text}},>>
                     <<{{axis_text_x}},>>
                     <<{{axis_text_y}},>>
                     <<{{axis_line}},>>
                     <<{{axis_ticks}},>>
                     <<{{axis_title_x}},>>
                     <<{{axis_title_y}},>>
                     <<{{plot_title}},>>
                     <<{{legend_background}},>>
                     <<{{legend_keys}},>>
                     <<{{legend_position}},>>
                     <<{{legend_direction}},>>
                     <<{{plot_subtitle}},>>
                     <<{{plot_caption}},>>
                 )

            ggsave(p, filename="{{f_output}}", {{pig_size}})
        """
        script = script.replace("{{x}}", "x=" + data.get("x"))
        script = script.replace("{{y}}", "y=" + data.get("y"))
        script = script.replace("{{f_output}}", f_output)

        # 读取文件
        input_file = data.get("input_file")
        if input_file.endswith("xlsx") or input_file.endswith("xls"):
            s_read_table = f"read.xlsx('{input_file}',sheet = 1)"
        elif input_file.endswith("csv"):
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F)"
        else:
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F, sep='\\t')"
        script = script.replace("{{read_table}}", s_read_table)

        # 独有配置
        group = data.get("group", "")
        group_color = data.get("group_color", "")

        s_geom_point = ""
        if group or group_color:
            s_aes = f"aes("
            s_aes += f"group={group}," if group else ""
            s_aes += f"color={group_color}," if group_color else ""
            s_aes += "), "
            s_geom_point += s_aes
        script = script.replace("{{geom_line}}", s_geom_point)

        # 主题
        themes = data.get("plot_themes")
        if themes:
            script = script.replace("{{plot_theme}}", f"theme_{themes}()")
        else:
            script = script.replace("{{plot_theme}}", f"")

        # 配置离散型颜色 -- 边框色
        color_qual = data.get("color_qual_theme", "")
        color_qual_self = data.get("color_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_color_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_color_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_color}}", s_scale_color)

        # 配置离散型颜色 -- 填充色
        color_qual = data.get("fill_qual_theme", "")
        color_qual_self = data.get("fill_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_fill_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_fill_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_fill}}", s_scale_color)

        # 配置连续型颜色 -- 边框色
        color_seq = data.get("color_seq_theme", "")
        color_seq_self = data.get("color_seq_self", "")
        color_seq_self_value = data.get("color_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_color_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_color_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_color}}", s_scale_fill)

        # 配置连续型颜色 -- 填充
        color_seq = data.get("fill_seq_theme", "")
        color_seq_self = data.get("fill_seq_self", "")
        color_seq_self_value = data.get("fill_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_fill_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_fill_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_fill}}", s_scale_fill)

        # 分面参数
        col_facets = data.get("col_facets", "")
        row_facets = data.get("row_facets", "")
        facets_nrow = data.get("facets_nrow")
        facets_ncol = data.get("facets_ncol")
        facets_scales = data.get("facets_scales")
        if col_facets and row_facets:
            s_facets = f"facet_grid('{row_facets} ~ {col_facets}'"
        elif col_facets:
            s_facets = f"facet_grid('. ~ {col_facets}'"
        elif row_facets:
            s_facets = f"facet_grid('{row_facets} ~ .'"
        else:
            s_facets = ""

        if s_facets:
            if facets_nrow:
                s_facets += f" ,nrow={facets_nrow}"
            if facets_ncol:
                s_facets += f" ,ncol={facets_ncol}"
            if facets_scales:
                s_facets += f" ,scales='{facets_scales}'"
            s_facets += ")"
        script = script.replace("{{facets}}", s_facets)

        # 整体背景
        plot_background_fill = data.get("plot_background_fill", "")
        plot_background_color = data.get("plot_background_color", "")
        plot_background_size = data.get("plot_background_size", "")
        plot_background_linetype = data.get("plot_background_linetype", "")
        if plot_background_fill or plot_background_color or plot_background_size or plot_background_linetype:
            s_plot_background = f"plot.background = element_rect("
            s_plot_background += f'fill = "{plot_background_fill}",' if plot_background_fill else ""
            s_plot_background += f'colour = "{plot_background_color}",' if plot_background_color else ""
            s_plot_background += f'size = {plot_background_size},' if plot_background_size else ""
            s_plot_background += f'linetype = "{plot_background_linetype}",' if plot_background_linetype else ""
            s_plot_background += ")"
        else:
            s_plot_background = ""
        script = script.replace("{{plot_background}}", s_plot_background)

        # 绘图区背景
        panel_background_fill = data.get("panel_background_fill", "")
        panel_background_color = data.get("panel_background_color", "")
        panel_background_size = data.get("panel_background_size", "")
        panel_background_linetype = data.get("panel_background_linetype", "")
        if panel_background_fill or panel_background_color or panel_background_size or panel_background_linetype:
            s_panel_background = f"panel.background = element_rect("
            s_panel_background += f'fill = "{panel_background_fill}",' if panel_background_fill else ""
            s_panel_background += f'colour = "{panel_background_color}",' if panel_background_color else ""
            s_panel_background += f'size = {panel_background_size},' if panel_background_size else ""
            s_panel_background += f'linetype = "{panel_background_linetype}",' if panel_background_linetype else ""
            s_panel_background += ")"
        else:
            s_panel_background = ""
        script = script.replace("{{panel_background}}", s_panel_background)

        # 主要网格线
        panel_grid_major_color = data.get("panel_grid_major_color", "")
        panel_grid_major_size = data.get("panel_grid_major_size", "")
        panel_grid_major_linetype = data.get("panel_grid_major_linetype", "")
        if panel_grid_major_color or panel_grid_major_size or panel_grid_major_linetype:
            s_panel_grid_major = f"panel.grid.major = element_line("
            s_panel_grid_major += f'colour = "{panel_grid_major_color}",' if panel_grid_major_color else ""
            s_panel_grid_major += f'size = {panel_grid_major_size},' if panel_grid_major_size else ""
            s_panel_grid_major += f'linetype = "{panel_grid_major_linetype}",' if panel_grid_major_linetype else ""
            s_panel_grid_major += ")"
        else:
            s_panel_grid_major = ""
        script = script.replace("{{panel_grid_major}}", s_panel_grid_major)

        # 次要网格线
        panel_grid_minor_color = data.get("panel_grid_minor_color", "")
        panel_grid_minor_size = data.get("panel_grid_minor_size", "")
        panel_grid_minor_linetype = data.get("panel_grid_minor_linetype", "")
        if panel_grid_minor_color or panel_grid_minor_size or panel_grid_minor_linetype:
            s_panel_grid_minor = f"panel.grid.minor = element_line("
            s_panel_grid_minor += f'colour = "{panel_grid_minor_color}",' if panel_grid_minor_color else ""
            s_panel_grid_minor += f'size = {panel_grid_minor_size},' if panel_grid_minor_size else ""
            s_panel_grid_minor += f'linetype = "{panel_grid_minor_linetype}",' if panel_grid_minor_linetype else ""
            s_panel_grid_minor += ")"
        else:
            s_panel_grid_minor = ""
        script = script.replace("{{panel_grid_minor}}", s_panel_grid_minor)

        # 全局字体
        text_family = data.get("text_family", "")
        text_size = data.get("text_size", "")
        text_face = data.get("text_face", "")
        text_color = data.get("text_color", "")
        text_vjust = data.get("text_vjust", "")
        text_angle = data.get("text_angle", "")
        if text_family or text_size or text_face or text_color or text_vjust or text_angle:
            s_text = f"axis.text = element_text("
            s_text += f'family = "{text_family}",' if text_family else ""
            s_text += f'size = {text_size},' if text_size else ""
            s_text += f'face = "{text_face}",' if text_face else ""
            s_text += f'colour = "{text_color}",' if text_color else ""
            s_text += f'vjust = {text_vjust},' if text_vjust else ""
            s_text += f'angle = {text_angle},' if text_angle else ""
            s_text += ")"
        else:
            s_text = ""
        script = script.replace("{{axis_text}}", s_text)

        # x轴字体
        if data.get("text_x_blank") == "true":
            s_text_x = "axis.text.x = element_blank() "
        else:
            text_x_family = data.get("text_x_family", "")
            text_x_size = data.get("text_x_size", "")
            text_x_face = data.get("text_x_face", "")
            text_x_color = data.get("text_x_color", "")
            text_x_vjust = data.get("text_x_vjust", "")
            text_x_hjust = data.get("text_x_hjust", "")
            text_x_angle = data.get("text_x_angle", "")
            if text_x_family or text_x_size or text_x_face or text_x_color or text_x_vjust or text_x_hjust or text_x_angle:
                s_text_x = f"axis.text.x = element_text("
                s_text_x += f'family = "{text_x_family}",' if text_x_family else ""
                s_text_x += f'size = {text_x_size},' if text_x_size else ""
                s_text_x += f'face = "{text_x_face}",' if text_x_face else ""
                s_text_x += f'colour = "{text_x_color}",' if text_x_color else ""
                s_text_x += f'vjust = {text_x_vjust},' if text_x_vjust else ""
                s_text_x += f'hjust = {text_x_hjust},' if text_x_hjust else ""
                s_text_x += f'angle = {text_x_angle},' if text_x_angle else ""
                s_text_x += ")"
            else:
                s_text_x = ""
        script = script.replace("{{axis_text_x}}", s_text_x)

        # y轴字体
        if data.get("text_y_blank") == "true":
            s_text_y = "axis.text.y = element_blank() "
        else:
            text_y_family = data.get("text_y_family", "")
            text_y_size = data.get("text_y_size", "")
            text_y_face = data.get("text_y_face", "")
            text_y_color = data.get("text_y_color", "")
            text_y_vjust = data.get("text_y_vjust", "")
            text_y_hjust = data.get("text_y_hjust", "")
            text_y_angle = data.get("text_y_angle", "")
            if text_y_family or text_y_size or text_y_face or text_y_color or text_y_vjust or text_y_hjust or text_y_angle:
                s_text_y = f"axis.text.y = element_text("
                s_text_y += f'family = "{text_y_family}",' if text_y_family else ""
                s_text_y += f'size = {text_y_size},' if text_y_size else ""
                s_text_y += f'face = "{text_y_face}",' if text_y_face else ""
                s_text_y += f'colour = "{text_y_color}",' if text_y_color else ""
                s_text_y += f'vjust = {text_y_vjust},' if text_y_vjust else ""
                s_text_y += f'hjust = {text_y_hjust},' if text_y_hjust else ""
                s_text_y += f'angle = {text_y_angle},' if text_y_angle else ""
                s_text_y += ")"
            else:
                s_text_y = ""
        script = script.replace("{{axis_text_y}}", s_text_y)

        # 坐标轴线
        axis_line_color = data.get("axis_line_color", "")
        axis_line_size = data.get("axis_line_size", "")
        axis_line_linetype = data.get("axis_line_linetype", "")
        if axis_line_color or axis_line_size or axis_line_linetype:
            s_axis_line = "axis.line = element_line("
            s_axis_line += f'colour = "{axis_line_color}",' if axis_line_color else ""
            s_axis_line += f'size = {axis_line_size},' if axis_line_size else ""
            s_axis_line += f'linetype = "{axis_line_linetype}",' if axis_line_linetype else ""
            s_axis_line += ")"
        else:
            s_axis_line = ""
        script = script.replace("{{axis_line}}", s_axis_line)

        # 坐标刻度
        axis_ticks_color = data.get("axis_ticks_color", "")
        axis_ticks_size = data.get("axis_ticks_size", "")
        axis_ticks_linetype = data.get("axis_ticks_linetype", "")
        if axis_ticks_color or axis_ticks_size or axis_ticks_linetype:
            s_axis_ticks = "axis.ticks = element_line("
            s_axis_ticks += f'colour = "{axis_ticks_color}",' if axis_ticks_color else ""
            s_axis_ticks += f'size = {axis_ticks_size},' if axis_ticks_size else ""
            s_axis_ticks += f'linetype = "{axis_ticks_linetype}",' if axis_ticks_linetype else ""
            s_axis_ticks += ")"
        else:
            s_axis_ticks = ""
        script = script.replace("{{axis_ticks}}", s_axis_ticks)

        # 标题内容
        labs_title = data.get("labs_title", "")
        labs_x = data.get("labs_x", "")
        labs_y = data.get("labs_y", "")
        labs_color = data.get("labs_color", "")
        labs_fill = data.get("labs_fill", "")
        labs_size = data.get("labs_size", "")
        labs_linetype = data.get("labs_linetype", "")
        labs_shape = data.get("labs_shape", "")
        labs_alpha = data.get("labs_alpha", "")
        subtitle_content = data.get("subtitle_content", "")
        caption_content = data.get("caption_content", "")
        if labs_title or labs_x or labs_y or labs_color or labs_fill or labs_size or labs_linetype or labs_shape or \
                labs_alpha or subtitle_content or caption_content:
            s_labs = "labs("
            s_labs += f'title = "{labs_title}",' if labs_title else ""
            s_labs += f'x = "{labs_x}",' if labs_x else ""
            s_labs += f'y = "{labs_y}",' if labs_y else ""
            s_labs += f'colour = "{labs_color}",' if labs_color else ""
            s_labs += f'fill = "{labs_fill}",' if labs_fill else ""
            s_labs += f'size = "{labs_size}",' if labs_size else ""
            s_labs += f'linetype = "{labs_linetype}",' if labs_linetype else ""
            s_labs += f'shape = "{labs_shape}",' if labs_shape else ""
            s_labs += f'alpha = "{labs_alpha}",' if labs_alpha else ""
            s_labs += f'subtitle = "{subtitle_content}",' if subtitle_content else ""
            s_labs += f'caption = "{caption_content}",' if caption_content else ""
            s_labs = s_labs.strip(",")
            s_labs += ")"
        else:
            s_labs = ""
        script = script.replace("{{labs}}", s_labs)

        # title 格式
        plot_title_family = data.get("plot_title_family", "")
        plot_title_size = data.get("plot_title_size", "")
        plot_title_face = data.get("plot_title_face", "")
        plot_title_color = data.get("plot_title_color", "")
        plot_title_vjust = data.get("plot_title_vjust", "")
        plot_title_hjust = data.get("plot_title_hjust", "")
        plot_title_angle = data.get("plot_title_angle", "")
        if plot_title_family or plot_title_size or plot_title_face or plot_title_color or plot_title_vjust or plot_title_hjust or plot_title_angle:
            s_plot_title = "plot.title = element_text("
            s_plot_title += f'family = "{plot_title_family}",' if plot_title_family else ""
            s_plot_title += f'size = {plot_title_size},' if plot_title_size else ""
            s_plot_title += f'face = "{plot_title_face}",' if plot_title_face else ""
            s_plot_title += f'colour = "{plot_title_color}",' if plot_title_color else ""
            s_plot_title += f'vjust = {plot_title_vjust},' if plot_title_vjust else ""
            s_plot_title += f'hjust = {plot_title_hjust},' if plot_title_hjust else ""
            s_plot_title += f'angle = {plot_title_angle},' if plot_title_angle else ""
            s_plot_title = s_plot_title.strip(",") + ")"
        else:
            s_plot_title = ""
        script = script.replace("{{plot_title}}", s_plot_title)

        # X轴标题格式
        aixs_title_x_family = data.get("aixs_title_x_family", "")
        aixs_title_x_size = data.get("aixs_title_x_size", "")
        aixs_title_x_face = data.get("aixs_title_x_face", "")
        aixs_title_x_color = data.get("aixs_title_x_color", "")
        aixs_title_x_vjust = data.get("aixs_title_x_vjust", "")
        aixs_title_x_hjust = data.get("aixs_title_x_hjust", "")
        aixs_title_x_angle = data.get("aixs_title_x_angle", "")
        if aixs_title_x_family or aixs_title_x_size or aixs_title_x_face or aixs_title_x_color or aixs_title_x_vjust or \
                aixs_title_x_hjust or aixs_title_x_angle:
            s_axis_x_title = "axis.title.x = element_text("
            s_axis_x_title += f'family = "{aixs_title_x_family}",' if aixs_title_x_family else ""
            s_axis_x_title += f'size = {aixs_title_x_size},' if aixs_title_x_size else ""
            s_axis_x_title += f'face = "{aixs_title_x_face}",' if aixs_title_x_face else ""
            s_axis_x_title += f'colour = "{aixs_title_x_color}",' if aixs_title_x_color else ""
            s_axis_x_title += f'vjust = {aixs_title_x_vjust},' if aixs_title_x_vjust else ""
            s_axis_x_title += f'hjust = {aixs_title_x_hjust},' if aixs_title_x_hjust else ""
            s_axis_x_title += f'angle = {aixs_title_x_angle},' if aixs_title_x_angle else ""
            s_axis_x_title = s_axis_x_title.strip(",") + ")"
        else:
            s_axis_x_title = ""
        script = script.replace("{{axis_title_x}}", s_axis_x_title)

        # Y轴标题格式
        aixs_title_y_family = data.get("aixs_title_y_family", "")
        aixs_title_y_size = data.get("aixs_title_y_size", "")
        aixs_title_y_face = data.get("aixs_title_y_face", "")
        aixs_title_y_color = data.get("aixs_title_y_color", "")
        aixs_title_y_vjust = data.get("aixs_title_y_vjust", "")
        aixs_title_y_hjust = data.get("aixs_title_y_hjust", "")
        aixs_title_y_angle = data.get("aixs_title_y_angle", "")
        if aixs_title_y_family or aixs_title_y_size or aixs_title_y_face or aixs_title_y_color or aixs_title_y_vjust or \
                aixs_title_y_hjust or aixs_title_y_angle:
            s_axis_y_title = "axis.title.y = element_text("
            s_axis_y_title += f'family = "{aixs_title_y_family}",' if aixs_title_y_family else ""
            s_axis_y_title += f'size = {aixs_title_y_size},' if aixs_title_y_size else ""
            s_axis_y_title += f'face = "{aixs_title_y_face}",' if aixs_title_y_face else ""
            s_axis_y_title += f'colour = "{aixs_title_y_color}",' if aixs_title_y_color else ""
            s_axis_y_title += f'vjust = {aixs_title_y_vjust},' if aixs_title_y_vjust else ""
            s_axis_y_title += f'hjust = {aixs_title_y_hjust},' if aixs_title_y_hjust else ""
            s_axis_y_title += f'angle = {aixs_title_y_angle},' if aixs_title_y_angle else ""
            s_axis_y_title = s_axis_y_title.strip(",") + ")"
        else:
            s_axis_y_title = ""
        script = script.replace("{{axis_title_y}}", s_axis_y_title)

        # 图例位置
        legend_position = data.get("legend_position", "")
        position_x = data.get("legend_position_x", "")
        position_y = data.get("legend_position_y", "")
        if legend_position or (position_x and position_y):
            if legend_position:
                s_legend_position = f'legend.position = "{legend_position}"'
            else:
                s_legend_position = f'legend.position = c("{position_x}", "{position_y}")'
        else:
            s_legend_position = ""
        script = script.replace("{{legend_position}}", s_legend_position)

        # 图例方向
        legend_direction = data.get("legend_direction", "")
        s_legend_direction = f'legend.direction = "{legend_direction}"' if legend_direction else ""
        script = script.replace("{{legend_direction}}", s_legend_direction)

        # 图例背景
        legend_background_fill = data.get("legend_background_fill", "")
        legend_background_color = data.get("legend_background_color", "")
        legend_background_size = data.get("legend_background_size", "")
        legend_background_linetype = data.get("legend_background_linetype", "")
        if legend_background_fill or legend_background_color or legend_background_size or legend_background_linetype:
            s_legend_background = "legend.background = element_rect("
            s_legend_background += f'fill = "{legend_background_fill}",' if legend_background_fill else ""
            s_legend_background += f'colour = "{legend_background_color}",' if legend_background_color else ""
            s_legend_background += f'size = {legend_background_size},' if legend_background_size else ""
            s_legend_background += f'linetype = "{legend_background_linetype}",' if legend_background_linetype else ""
            s_legend_background = s_legend_background.strip(",") + ")"
        else:
            s_legend_background = ""
        script = script.replace("{{legend_background}}", s_legend_background)

        # legend keys
        legend_keys_fill = data.get("legend_keys_fill", "")
        legend_keys_color = data.get("legend_keys_color", "")
        legend_keys_size = data.get("legend_keys_size", "")
        legend_keys_linetype = data.get("legend_keys_linetype", "")
        if legend_keys_fill or legend_keys_color or legend_keys_size or legend_keys_linetype:
            s_legend_keys = "legend.key = element_rect("
            s_legend_keys += f'fill = "{legend_keys_fill}",' if legend_keys_fill else ""
            s_legend_keys += f'colour = "{legend_keys_color}",' if legend_keys_color else ""
            s_legend_keys += f'size = {legend_keys_size},' if legend_keys_size else ""
            s_legend_keys += f'linetype = "{legend_keys_linetype}",' if legend_keys_linetype else ""
            s_legend_keys = s_legend_keys.strip(",") + ")"
        else:
            s_legend_keys = ""
        script = script.replace("{{legend_keys}}", s_legend_keys)

        # 副标题
        subtitle_family = data.get("subtitle_family", "")
        subtitle_size = data.get("subtitle_size", "")
        subtitle_face = data.get("subtitle_face", "")
        subtitle_color = data.get("subtitle_color", "")
        subtitle_hjust = data.get("subtitle_hjust", "")
        if subtitle_family or subtitle_size or subtitle_face or subtitle_color or subtitle_hjust:
            s_subtitle = f"plot.subtitle = element_text("
            s_subtitle += f'family = "{subtitle_family}",' if subtitle_family else ""
            s_subtitle += f'size = {subtitle_size},' if subtitle_size else ""
            s_subtitle += f'face = "{subtitle_face}",' if subtitle_face else ""
            s_subtitle += f'colour = "{subtitle_color}",' if subtitle_color else ""
            s_subtitle += f'hjust = {subtitle_hjust},' if subtitle_hjust else ""
            s_subtitle = s_subtitle.strip(",") + ")"
        else:
            s_subtitle = ""
        script = script.replace("{{plot_subtitle}}", s_subtitle)

        # 脚注
        caption_family = data.get("caption_family", "")
        caption_size = data.get("caption_size", "")
        caption_face = data.get("caption_face", "")
        caption_color = data.get("caption_color", "")
        caption_hjust = data.get("caption_hjust", "")
        if caption_family or caption_size or caption_face or caption_hjust or caption_color:
            s_caption = f"plot.caption = element_text("
            s_caption += f'family = "{caption_family}",' if caption_family else ""
            s_caption += f'size = {caption_size},' if caption_size else ""
            s_caption += f'face = "{caption_face}",' if caption_face else ""
            s_caption += f'colour = "{caption_color}",' if caption_color else ""
            s_caption += f'hjust = {caption_hjust},' if caption_hjust else ""
            s_caption = s_caption.strip(",") + ")"
        else:
            s_caption = ""
        script = script.replace("{{plot_caption}}", s_caption)

        # 图形大小
        fig_height = data.get("output_height", 6)
        fig_width = data.get("output_width", 8)
        fig_units = data.get("output_units", "in")
        fig_dpi = data.get("output_dpi", "")
        s_fig_size = f"width={fig_width}, height={fig_height}, units='{fig_units}' "
        s_fig_size = s_fig_size + f",dpi={fig_dpi} " if fig_dpi else s_fig_size
        script = script.replace("{{pig_size}}", s_fig_size)

        # 最后处理
        script = script.replace("<< +>>", "")
        script = script.replace("<<,>>", "")
        script = script.replace("<<", "")
        script = script.replace(">>", "")
        script = script.replace(">>", "")
        fw.write(script)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    print(script)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "f_output": f_output})


@_is_post
def plot_bar(request):
    """绘制散点图"""

    # 表单验证
    data = DotPlotForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotDot")
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{data.get('output_name', 'DotPlot')}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:

        # 基本框架
        script = """
            library('ggplot2')
            library('openxlsx')
            library('RColorBrewer')

            df_data <- {{read_table}}

            p <- ggplot(df_data, aes({{x}}, {{y}})) + 
                 geom_point({{geom_point}}) +
                 <<{{plot_theme}} +>>   # 主题
                 <<{{scale_qual_color}} +>>   #  离散型颜色
                 <<{{scale_qual_fill}} +>>   #  离散型颜色
                 <<{{scale_seq_color}} +>>  # 连续型颜色
                 <<{{scale_seq_fill}} +>>  # 连续型颜色
                 <<{{facets}} +>>  # 分面
                 <<{{labs}} +>>

                 theme(
                     <<{{plot_background}},>>
                     <<{{panel_background}},>>
                     <<{{panel_grid_major}},>>
                     <<{{panel_grid_minor}},>>
                     <<{{axis_text}},>>
                     <<{{axis_text_x}},>>
                     <<{{axis_text_y}},>>
                     <<{{axis_line}},>>
                     <<{{axis_ticks}},>>
                     <<{{axis_title_x}},>>
                     <<{{axis_title_y}},>>
                     <<{{plot_title}},>>
                     <<{{legend_background}},>>
                     <<{{legend_keys}},>>
                     <<{{legend_position}},>>
                     <<{{legend_direction}},>>
                     <<{{plot_subtitle}},>>
                     <<{{plot_caption}},>>
                 )

            ggsave(p, filename="{{f_output}}", {{pig_size}})
        """
        script = script.replace("{{x}}", data.get("x"))
        script = script.replace("{{y}}", data.get("y"))
        script = script.replace("{{f_output}}", f_output)

        # 读取文件
        input_file = data.get("input_file")
        if input_file.endswith("xlsx") or input_file.endswith("xls"):
            s_read_table = f"read.xlsx('{input_file}',sheet = 1)"
        elif input_file.endswith("csv"):
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F)"
        else:
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F, sep='\\t')"
        script = script.replace("{{read_table}}", s_read_table)

        # 散点独有配置
        group = data.get("group", "")
        group_fill = data.get("group_fill", "")
        group_color = data.get("group_color", "")
        group_shape = data.get("group_shape", "")
        point_size = data.get("point_size", "")
        point_shape = data.get("point_shape", "")
        point_color = data.get("point_color", "")
        point_fill = data.get("point_fill", "")
        point_alpha = data.get("point_alpha", "")

        s_geom_point = ""
        if group or group_fill or group_color or group_shape:
            s_aes = f"aes("
            s_aes += f"group={group}," if group else ""
            s_aes += f"fill={group_fill}," if group_fill else ""
            s_aes += f"color={group_color}," if group_color else ""
            s_aes += f"shape={group_shape}," if group_shape else ""
            s_aes += "), "
            s_geom_point += s_aes
        s_geom_point += f"size={point_size}," if point_size else ""
        s_geom_point += f"shape={point_shape}," if point_shape else ""
        s_geom_point += f"color='{point_color}'," if point_color else ""
        s_geom_point += f"fill='{point_fill}'," if point_fill else ""
        s_geom_point += f"alpha='{point_alpha}'," if point_alpha else ""
        script = script.replace("{{geom_point}}", s_geom_point)

        # 主题
        themes = data.get("plot_themes")
        if themes:
            script = script.replace("{{plot_theme}}", f"theme_{themes}()")
        else:
            script = script.replace("{{plot_theme}}", f"")

        # 配置离散型颜色 -- 边框色
        color_qual = data.get("color_qual_theme", "")
        color_qual_self = data.get("color_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_color_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_color_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_color}}", s_scale_color)

        # 配置离散型颜色 -- 填充色
        color_qual = data.get("fill_qual_theme", "")
        color_qual_self = data.get("fill_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_fill_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_fill_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_fill}}", s_scale_color)

        # 配置连续型颜色 -- 边框色
        color_seq = data.get("color_seq_theme", "")
        color_seq_self = data.get("color_seq_self", "")
        color_seq_self_value = data.get("color_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_color_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_color_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_color}}", s_scale_fill)

        # 配置连续型颜色 -- 填充
        color_seq = data.get("fill_seq_theme", "")
        color_seq_self = data.get("fill_seq_self", "")
        color_seq_self_value = data.get("fill_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_fill_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_fill_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_fill}}", s_scale_fill)

        # 分面参数
        col_facets = data.get("col_facets", "")
        row_facets = data.get("row_facets", "")
        facets_nrow = data.get("facets_nrow")
        facets_ncol = data.get("facets_ncol")
        facets_scales = data.get("facets_scales")
        if col_facets and row_facets:
            s_facets = f"facet_grid('{row_facets} ~ {col_facets}'"
        elif col_facets:
            s_facets = f"facet_grid('. ~ {col_facets}'"
        elif row_facets:
            s_facets = f"facet_grid('{row_facets} ~ .'"
        else:
            s_facets = ""

        if s_facets:
            if facets_nrow:
                s_facets += f" ,nrow={facets_nrow}"
            if facets_ncol:
                s_facets += f" ,ncol={facets_ncol}"
            if facets_scales:
                s_facets += f" ,scales='{facets_scales}'"
            s_facets += ")"
        script = script.replace("{{facets}}", s_facets)

        # 整体背景
        plot_background_fill = data.get("plot_background_fill", "")
        plot_background_color = data.get("plot_background_color", "")
        plot_background_size = data.get("plot_background_size", "")
        plot_background_linetype = data.get("plot_background_linetype", "")
        if plot_background_fill or plot_background_color or plot_background_size or plot_background_linetype:
            s_plot_background = f"plot.background = element_rect("
            s_plot_background += f'fill = "{plot_background_fill}",' if plot_background_fill else ""
            s_plot_background += f'colour = "{plot_background_color}",' if plot_background_color else ""
            s_plot_background += f'size = {plot_background_size},' if plot_background_size else ""
            s_plot_background += f'linetype = "{plot_background_linetype}",' if plot_background_linetype else ""
            s_plot_background += ")"
        else:
            s_plot_background = ""
        script = script.replace("{{plot_background}}", s_plot_background)

        # 绘图区背景
        panel_background_fill = data.get("panel_background_fill", "")
        panel_background_color = data.get("panel_background_color", "")
        panel_background_size = data.get("panel_background_size", "")
        panel_background_linetype = data.get("panel_background_linetype", "")
        if panel_background_fill or panel_background_color or panel_background_size or panel_background_linetype:
            s_panel_background = f"panel.background = element_rect("
            s_panel_background += f'fill = "{panel_background_fill}",' if panel_background_fill else ""
            s_panel_background += f'colour = "{panel_background_color}",' if panel_background_color else ""
            s_panel_background += f'size = {panel_background_size},' if panel_background_size else ""
            s_panel_background += f'linetype = "{panel_background_linetype}",' if panel_background_linetype else ""
            s_panel_background += ")"
        else:
            s_panel_background = ""
        script = script.replace("{{panel_background}}", s_panel_background)

        # 主要网格线
        panel_grid_major_color = data.get("panel_grid_major_color", "")
        panel_grid_major_size = data.get("panel_grid_major_size", "")
        panel_grid_major_linetype = data.get("panel_grid_major_linetype", "")
        if panel_grid_major_color or panel_grid_major_size or panel_grid_major_linetype:
            s_panel_grid_major = f"panel.grid.major = element_line("
            s_panel_grid_major += f'colour = "{panel_grid_major_color}",' if panel_grid_major_color else ""
            s_panel_grid_major += f'size = {panel_grid_major_size},' if panel_grid_major_size else ""
            s_panel_grid_major += f'linetype = "{panel_grid_major_linetype}",' if panel_grid_major_linetype else ""
            s_panel_grid_major += ")"
        else:
            s_panel_grid_major = ""
        script = script.replace("{{panel_grid_major}}", s_panel_grid_major)

        # 次要网格线
        panel_grid_minor_color = data.get("panel_grid_minor_color", "")
        panel_grid_minor_size = data.get("panel_grid_minor_size", "")
        panel_grid_minor_linetype = data.get("panel_grid_minor_linetype", "")
        if panel_grid_minor_color or panel_grid_minor_size or panel_grid_minor_linetype:
            s_panel_grid_minor = f"panel.grid.minor = element_line("
            s_panel_grid_minor += f'colour = "{panel_grid_minor_color}",' if panel_grid_minor_color else ""
            s_panel_grid_minor += f'size = {panel_grid_minor_size},' if panel_grid_minor_size else ""
            s_panel_grid_minor += f'linetype = "{panel_grid_minor_linetype}",' if panel_grid_minor_linetype else ""
            s_panel_grid_minor += ")"
        else:
            s_panel_grid_minor = ""
        script = script.replace("{{panel_grid_minor}}", s_panel_grid_minor)

        # 全局字体
        text_family = data.get("text_family", "")
        text_size = data.get("text_size", "")
        text_face = data.get("text_face", "")
        text_color = data.get("text_color", "")
        text_vjust = data.get("text_vjust", "")
        text_angle = data.get("text_angle", "")
        if text_family or text_size or text_face or text_color or text_vjust or text_angle:
            s_text = f"axis.text = element_text("
            s_text += f'family = "{text_family}",' if text_family else ""
            s_text += f'size = {text_size},' if text_size else ""
            s_text += f'face = "{text_face}",' if text_face else ""
            s_text += f'colour = "{text_color}",' if text_color else ""
            s_text += f'vjust = {text_vjust},' if text_vjust else ""
            s_text += f'angle = {text_angle},' if text_angle else ""
            s_text += ")"
        else:
            s_text = ""
        script = script.replace("{{axis_text}}", s_text)

        # x轴字体
        if data.get("text_x_blank") == "true":
            s_text_x = "axis.text.x = element_blank() "
        else:
            text_x_family = data.get("text_x_family", "")
            text_x_size = data.get("text_x_size", "")
            text_x_face = data.get("text_x_face", "")
            text_x_color = data.get("text_x_color", "")
            text_x_vjust = data.get("text_x_vjust", "")
            text_x_hjust = data.get("text_x_hjust", "")
            text_x_angle = data.get("text_x_angle", "")
            if text_x_family or text_x_size or text_x_face or text_x_color or text_x_vjust or text_x_hjust or text_x_angle:
                s_text_x = f"axis.text.x = element_text("
                s_text_x += f'family = "{text_x_family}",' if text_x_family else ""
                s_text_x += f'size = {text_x_size},' if text_x_size else ""
                s_text_x += f'face = "{text_x_face}",' if text_x_face else ""
                s_text_x += f'colour = "{text_x_color}",' if text_x_color else ""
                s_text_x += f'vjust = {text_x_vjust},' if text_x_vjust else ""
                s_text_x += f'hjust = {text_x_hjust},' if text_x_hjust else ""
                s_text_x += f'angle = {text_x_angle},' if text_x_angle else ""
                s_text_x += ")"
            else:
                s_text_x = ""
        script = script.replace("{{axis_text_x}}", s_text_x)

        # y轴字体
        if data.get("text_y_blank") == "true":
            s_text_y = "axis.text.y = element_blank() "
        else:
            text_y_family = data.get("text_y_family", "")
            text_y_size = data.get("text_y_size", "")
            text_y_face = data.get("text_y_face", "")
            text_y_color = data.get("text_y_color", "")
            text_y_vjust = data.get("text_y_vjust", "")
            text_y_hjust = data.get("text_y_hjust", "")
            text_y_angle = data.get("text_y_angle", "")
            if text_y_family or text_y_size or text_y_face or text_y_color or text_y_vjust or text_y_hjust or text_y_angle:
                s_text_y = f"axis.text.y = element_text("
                s_text_y += f'family = "{text_y_family}",' if text_y_family else ""
                s_text_y += f'size = {text_y_size},' if text_y_size else ""
                s_text_y += f'face = "{text_y_face}",' if text_y_face else ""
                s_text_y += f'colour = "{text_y_color}",' if text_y_color else ""
                s_text_y += f'vjust = {text_y_vjust},' if text_y_vjust else ""
                s_text_y += f'hjust = {text_y_hjust},' if text_y_hjust else ""
                s_text_y += f'angle = {text_y_angle},' if text_y_angle else ""
                s_text_y += ")"
            else:
                s_text_y = ""
        script = script.replace("{{axis_text_y}}", s_text_y)

        # 坐标轴线
        axis_line_color = data.get("axis_line_color", "")
        axis_line_size = data.get("axis_line_size", "")
        axis_line_linetype = data.get("axis_line_linetype", "")
        if axis_line_color or axis_line_size or axis_line_linetype:
            s_axis_line = "axis.line = element_line("
            s_axis_line += f'colour = "{axis_line_color}",' if axis_line_color else ""
            s_axis_line += f'size = {axis_line_size},' if axis_line_size else ""
            s_axis_line += f'linetype = "{axis_line_linetype}",' if axis_line_linetype else ""
            s_axis_line += ")"
        else:
            s_axis_line = ""
        script = script.replace("{{axis_line}}", s_axis_line)

        # 坐标刻度
        axis_ticks_color = data.get("axis_ticks_color", "")
        axis_ticks_size = data.get("axis_ticks_size", "")
        axis_ticks_linetype = data.get("axis_ticks_linetype", "")
        if axis_ticks_color or axis_ticks_size or axis_ticks_linetype:
            s_axis_ticks = "axis.ticks = element_line("
            s_axis_ticks += f'colour = "{axis_ticks_color}",' if axis_ticks_color else ""
            s_axis_ticks += f'size = {axis_ticks_size},' if axis_ticks_size else ""
            s_axis_ticks += f'linetype = "{axis_ticks_linetype}",' if axis_ticks_linetype else ""
            s_axis_ticks += ")"
        else:
            s_axis_ticks = ""
        script = script.replace("{{axis_ticks}}", s_axis_ticks)

        # 标题内容
        labs_title = data.get("labs_title", "")
        labs_x = data.get("labs_x", "")
        labs_y = data.get("labs_y", "")
        labs_color = data.get("labs_color", "")
        labs_fill = data.get("labs_fill", "")
        labs_size = data.get("labs_size", "")
        labs_linetype = data.get("labs_linetype", "")
        labs_shape = data.get("labs_shape", "")
        labs_alpha = data.get("labs_alpha", "")
        subtitle_content = data.get("subtitle_content", "")
        caption_content = data.get("caption_content", "")
        if labs_title or labs_x or labs_y or labs_color or labs_fill or labs_size or labs_linetype or labs_shape or \
                labs_alpha or subtitle_content or caption_content:
            s_labs = "labs("
            s_labs += f'title = "{labs_title}",' if labs_title else ""
            s_labs += f'x = "{labs_x}",' if labs_x else ""
            s_labs += f'y = "{labs_y}",' if labs_y else ""
            s_labs += f'colour = "{labs_color}",' if labs_color else ""
            s_labs += f'fill = "{labs_fill}",' if labs_fill else ""
            s_labs += f'size = "{labs_size}",' if labs_size else ""
            s_labs += f'linetype = "{labs_linetype}",' if labs_linetype else ""
            s_labs += f'shape = "{labs_shape}",' if labs_shape else ""
            s_labs += f'alpha = "{labs_alpha}",' if labs_alpha else ""
            s_labs += f'subtitle = "{subtitle_content}",' if subtitle_content else ""
            s_labs += f'caption = "{caption_content}",' if caption_content else ""
            s_labs = s_labs.strip(",")
            s_labs += ")"
        else:
            s_labs = ""
        script = script.replace("{{labs}}", s_labs)

        # title 格式
        plot_title_family = data.get("plot_title_family", "")
        plot_title_size = data.get("plot_title_size", "")
        plot_title_face = data.get("plot_title_face", "")
        plot_title_color = data.get("plot_title_color", "")
        plot_title_vjust = data.get("plot_title_vjust", "")
        plot_title_hjust = data.get("plot_title_hjust", "")
        plot_title_angle = data.get("plot_title_angle", "")
        if plot_title_family or plot_title_size or plot_title_face or plot_title_color or plot_title_vjust or plot_title_hjust or plot_title_angle:
            s_plot_title = "plot.title = element_text("
            s_plot_title += f'family = "{plot_title_family}",' if plot_title_family else ""
            s_plot_title += f'size = {plot_title_size},' if plot_title_size else ""
            s_plot_title += f'face = "{plot_title_face}",' if plot_title_face else ""
            s_plot_title += f'colour = "{plot_title_color}",' if plot_title_color else ""
            s_plot_title += f'vjust = {plot_title_vjust},' if plot_title_vjust else ""
            s_plot_title += f'hjust = {plot_title_hjust},' if plot_title_hjust else ""
            s_plot_title += f'angle = {plot_title_angle},' if plot_title_angle else ""
            s_plot_title = s_plot_title.strip(",") + ")"
        else:
            s_plot_title = ""
        script = script.replace("{{plot_title}}", s_plot_title)

        # X轴标题格式
        aixs_title_x_family = data.get("aixs_title_x_family", "")
        aixs_title_x_size = data.get("aixs_title_x_size", "")
        aixs_title_x_face = data.get("aixs_title_x_face", "")
        aixs_title_x_color = data.get("aixs_title_x_color", "")
        aixs_title_x_vjust = data.get("aixs_title_x_vjust", "")
        aixs_title_x_hjust = data.get("aixs_title_x_hjust", "")
        aixs_title_x_angle = data.get("aixs_title_x_angle", "")
        if aixs_title_x_family or aixs_title_x_size or aixs_title_x_face or aixs_title_x_color or aixs_title_x_vjust or \
                aixs_title_x_hjust or aixs_title_x_angle:
            s_axis_x_title = "axis.title.x = element_text("
            s_axis_x_title += f'family = "{aixs_title_x_family}",' if aixs_title_x_family else ""
            s_axis_x_title += f'size = {aixs_title_x_size},' if aixs_title_x_size else ""
            s_axis_x_title += f'face = "{aixs_title_x_face}",' if aixs_title_x_face else ""
            s_axis_x_title += f'colour = "{aixs_title_x_color}",' if aixs_title_x_color else ""
            s_axis_x_title += f'vjust = {aixs_title_x_vjust},' if aixs_title_x_vjust else ""
            s_axis_x_title += f'hjust = {aixs_title_x_hjust},' if aixs_title_x_hjust else ""
            s_axis_x_title += f'angle = {aixs_title_x_angle},' if aixs_title_x_angle else ""
            s_axis_x_title = s_axis_x_title.strip(",") + ")"
        else:
            s_axis_x_title = ""
        script = script.replace("{{axis_title_x}}", s_axis_x_title)

        # Y轴标题格式
        aixs_title_y_family = data.get("aixs_title_y_family", "")
        aixs_title_y_size = data.get("aixs_title_y_size", "")
        aixs_title_y_face = data.get("aixs_title_y_face", "")
        aixs_title_y_color = data.get("aixs_title_y_color", "")
        aixs_title_y_vjust = data.get("aixs_title_y_vjust", "")
        aixs_title_y_hjust = data.get("aixs_title_y_hjust", "")
        aixs_title_y_angle = data.get("aixs_title_y_angle", "")
        if aixs_title_y_family or aixs_title_y_size or aixs_title_y_face or aixs_title_y_color or aixs_title_y_vjust or \
                aixs_title_y_hjust or aixs_title_y_angle:
            s_axis_y_title = "axis.title.y = element_text("
            s_axis_y_title += f'family = "{aixs_title_y_family}",' if aixs_title_y_family else ""
            s_axis_y_title += f'size = {aixs_title_y_size},' if aixs_title_y_size else ""
            s_axis_y_title += f'face = "{aixs_title_y_face}",' if aixs_title_y_face else ""
            s_axis_y_title += f'colour = "{aixs_title_y_color}",' if aixs_title_y_color else ""
            s_axis_y_title += f'vjust = {aixs_title_y_vjust},' if aixs_title_y_vjust else ""
            s_axis_y_title += f'hjust = {aixs_title_y_hjust},' if aixs_title_y_hjust else ""
            s_axis_y_title += f'angle = {aixs_title_y_angle},' if aixs_title_y_angle else ""
            s_axis_y_title = s_axis_y_title.strip(",") + ")"
        else:
            s_axis_y_title = ""
        script = script.replace("{{axis_title_y}}", s_axis_y_title)

        # 图例位置
        legend_position = data.get("legend_position", "")
        position_x = data.get("legend_position_x", "")
        position_y = data.get("legend_position_y", "")
        if legend_position or (position_x and position_y):
            if legend_position:
                s_legend_position = f'legend.position = "{legend_position}"'
            else:
                s_legend_position = f'legend.position = c("{position_x}", "{position_y}")'
        else:
            s_legend_position = ""
        script = script.replace("{{legend_position}}", s_legend_position)

        # 图例方向
        legend_direction = data.get("legend_direction", "")
        s_legend_direction = f'legend.direction = "{legend_direction}"' if legend_direction else ""
        script = script.replace("{{legend_direction}}", s_legend_direction)

        # 图例背景
        legend_background_fill = data.get("legend_background_fill", "")
        legend_background_color = data.get("legend_background_color", "")
        legend_background_size = data.get("legend_background_size", "")
        legend_background_linetype = data.get("legend_background_linetype", "")
        if legend_background_fill or legend_background_color or legend_background_size or legend_background_linetype:
            s_legend_background = "legend.background = element_rect("
            s_legend_background += f'fill = "{legend_background_fill}",' if legend_background_fill else ""
            s_legend_background += f'colour = "{legend_background_color}",' if legend_background_color else ""
            s_legend_background += f'size = {legend_background_size},' if legend_background_size else ""
            s_legend_background += f'linetype = "{legend_background_linetype}",' if legend_background_linetype else ""
            s_legend_background = s_legend_background.strip(",") + ")"
        else:
            s_legend_background = ""
        script = script.replace("{{legend_background}}", s_legend_background)

        # legend keys
        legend_keys_fill = data.get("legend_keys_fill", "")
        legend_keys_color = data.get("legend_keys_color", "")
        legend_keys_size = data.get("legend_keys_size", "")
        legend_keys_linetype = data.get("legend_keys_linetype", "")
        if legend_keys_fill or legend_keys_color or legend_keys_size or legend_keys_linetype:
            s_legend_keys = "legend.key = element_rect("
            s_legend_keys += f'fill = "{legend_keys_fill}",' if legend_keys_fill else ""
            s_legend_keys += f'colour = "{legend_keys_color}",' if legend_keys_color else ""
            s_legend_keys += f'size = {legend_keys_size},' if legend_keys_size else ""
            s_legend_keys += f'linetype = "{legend_keys_linetype}",' if legend_keys_linetype else ""
            s_legend_keys = s_legend_keys.strip(",") + ")"
        else:
            s_legend_keys = ""
        script = script.replace("{{legend_keys}}", s_legend_keys)

        # 副标题
        subtitle_family = data.get("subtitle_family", "")
        subtitle_size = data.get("subtitle_size", "")
        subtitle_face = data.get("subtitle_face", "")
        subtitle_color = data.get("subtitle_color", "")
        subtitle_hjust = data.get("subtitle_hjust", "")
        if subtitle_family or subtitle_size or subtitle_face or subtitle_color or subtitle_hjust:
            s_subtitle = f"plot.subtitle = element_text("
            s_subtitle += f'family = "{subtitle_family}",' if subtitle_family else ""
            s_subtitle += f'size = {subtitle_size},' if subtitle_size else ""
            s_subtitle += f'face = "{subtitle_face}",' if subtitle_face else ""
            s_subtitle += f'colour = "{subtitle_color}",' if subtitle_color else ""
            s_subtitle += f'hjust = {subtitle_hjust},' if subtitle_hjust else ""
            s_subtitle = s_subtitle.strip(",") + ")"
        else:
            s_subtitle = ""
        script = script.replace("{{plot_subtitle}}", s_subtitle)

        # 脚注
        caption_family = data.get("caption_family", "")
        caption_size = data.get("caption_size", "")
        caption_face = data.get("caption_face", "")
        caption_color = data.get("caption_color", "")
        caption_hjust = data.get("caption_hjust", "")
        if caption_family or caption_size or caption_face or caption_hjust or caption_color:
            s_caption = f"plot.caption = element_text("
            s_caption += f'family = "{caption_family}",' if caption_family else ""
            s_caption += f'size = {caption_size},' if caption_size else ""
            s_caption += f'face = "{caption_face}",' if caption_face else ""
            s_caption += f'colour = "{caption_color}",' if caption_color else ""
            s_caption += f'hjust = {caption_hjust},' if caption_hjust else ""
            s_caption = s_caption.strip(",") + ")"
        else:
            s_caption = ""
        script = script.replace("{{plot_caption}}", s_caption)

        # 图形大小
        fig_height = data.get("output_height", 6)
        fig_width = data.get("output_width", 8)
        fig_units = data.get("output_units", "in")
        fig_dpi = data.get("output_dpi", "")
        s_fig_size = f"width={fig_width}, height={fig_height}, units='{fig_units}' "
        s_fig_size = s_fig_size + f",dpi={fig_dpi} " if fig_dpi else s_fig_size
        script = script.replace("{{pig_size}}", s_fig_size)

        # 最后处理
        script = script.replace("<< +>>", "")
        script = script.replace("<<,>>", "")
        script = script.replace("<<", "")
        script = script.replace(">>", "")
        script = script.replace(">>", "")
        fw.write(script)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    print(script)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "f_output": f_output})


def _give_me_directory(d_output):
    """创建一个唯一的新的目录"""

    uniq_dir = str(uuid.uuid1())
    d_output = f"{d_output}/{uniq_dir}"
    os.makedirs(d_output)
    return d_output


def _submit_job(job_id, command, d_output, threads=1):
    """ 将一条命令提交至服务器
    :param job_id: 任务id
    :param command: 脚本命令
    :param d_output: 结果输出目录
    :param threads: 分析允许的最大线程数
    :return:
    """

    f_log = f"{d_output}/{job_id}.log"
    f_error = f"{d_output}/{job_id}.error"
    f_success = f"{d_output}/{job_id}.success"
    f_failed = f"{d_output}/{job_id}.failed"

    cmd = f'bsub -n {threads} -J BioPlot.{job_id} -R "span[hosts=1]" -o {f_log} -e {f_error} ' \
          f'"{command} && touch {f_success} || touch {f_failed}"'

    output = subprocess.check_output(cmd, shell=True)
    jobid = re.findall("Job <(\d+)>", output.decode("utf-8"))[0]
    rslt = {"job_id": jobid, "f_log": f_log, "f_error": f_error, "f_success": f_success, "f_failed": f_failed}
    return rslt


@_is_post
def plot_rd_qc_boxplot(request):
    """绘制箱线图图"""

    # 表单验证
    data = BoxPlotForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotDot")
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{data.get('output_name', 'DotPlot')}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:

        # 基本框架
        script = """
            library('ggplot2')
            library('openxlsx')
            library('RColorBrewer')

            df_data <- {{read_table}}

            p <- ggplot(df_data, aes({{x}}, {{y}})) + 
                 geom_boxplot({{geom_boxplot}}) +
                 <<{{plot_point}} +>>   # 散点
                 <<{{plot_theme}} +>>   # 主题
                 <<{{scale_qual_color}} +>>   #  离散型颜色
                 <<{{scale_qual_fill}} +>>   #  离散型颜色
                 <<{{scale_seq_color}} +>>  # 连续型颜色
                 <<{{scale_seq_fill}} +>>  # 连续型颜色
                 <<{{facets}} +>>  # 分面
                 <<{{scale_y_continuous}} +>>  # y轴刻度范围
                 <<{{labs}} +>>

                 theme(
                     <<{{plot_background}},>>
                     <<{{panel_background}},>>
                     <<{{panel_grid_major}},>>
                     <<{{panel_grid_minor}},>>
                     <<{{axis_text}},>>
                     <<{{axis_text_x}},>>
                     <<{{axis_text_y}},>>
                     <<{{axis_line}},>>
                     <<{{axis_ticks}},>>
                     <<{{axis_title_x}},>>
                     <<{{axis_title_y}},>>
                     <<{{plot_title}},>>
                     <<{{legend_background}},>>
                     <<{{legend_keys}},>>
                     <<{{legend_position}},>>
                     <<{{legend_direction}},>>
                     <<{{plot_subtitle}},>>
                     <<{{plot_caption}},>>
                 )

            ggsave(p, filename="{{f_output}}", {{pig_size}})
        """
        script = script.replace("{{x}}", data.get("x"))
        script = script.replace("{{y}}", data.get("y"))
        script = script.replace("{{f_output}}", f_output)

        # 读取文件
        input_file = data.get("input_file")
        if input_file.endswith("xlsx") or input_file.endswith("xls"):
            s_read_table = f"read.xlsx('{input_file}',sheet = 1)"
        elif input_file.endswith("csv"):
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F)"
        else:
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F, sep='\\t')"
        script = script.replace("{{read_table}}", s_read_table)

        # box独有配置
        box_color = data.get("box_color", "")
        box_fill = data.get("box_fill", "")
        outlier_fill = data.get("outlier_fill", "")
        outlier_color = data.get("outlier_color", "")
        outlier_shape = data.get("outlier_shape", "")
        outlier_size = data.get("outlier_size", "")
        outlier_alpha = data.get("outlier_alpha", "")

        group = data.get("group", "")
        group_fill = data.get("group_fill", "")
        group_color = data.get("group_color", "")
        group_shape = data.get("group_shape", "")

        s_geom_box = ""
        if group or group_fill or group_color or group_shape:
            s_aes = f"aes("
            s_aes += f"group={group}," if group else ""
            s_aes += f"fill={group_fill}," if group_fill else ""
            s_aes += f"color={group_color}," if group_color else ""
            s_aes += "), "
            s_geom_box += s_aes

        s_geom_box += f"outlier.size={outlier_size}," if outlier_size else ""
        s_geom_box += f"outlier.shape={outlier_shape}," if outlier_shape else ""
        s_geom_box += f"outlier.alpha={outlier_alpha}," if outlier_alpha else ""
        s_geom_box += f"outlier.fill='{outlier_fill}'," if outlier_fill else ""
        s_geom_box += f"outlier.color='{outlier_color}'," if outlier_color else ""
        script = script.replace("{{geom_boxplot}}", s_geom_box)

        # 散点配置
        point_size = data.get("point_size", "")
        point_shape = data.get("point_shape", "")
        point_color = data.get("point_color", "")
        point_fill = data.get("point_fill", "")
        point_alpha = data.get("point_alpha", "")

        if point_size or point_shape or point_color or point_fill or point_alpha:
            s_geom_point = f"geom_point(aes(),"
            s_geom_point += f"size={point_size}," if point_size else ""
            s_geom_point += f"shape={point_shape}," if point_shape else ""
            s_geom_point += f"color='{point_color}'," if point_color else ""
            s_geom_point += f"fill='{point_fill}'," if point_fill else ""
            s_geom_point += f"alpha='{point_alpha}'," if point_alpha else ""
            s_geom_point += ", position = position_jitter())"
        else:
            s_geom_point = ""
        script = script.replace("{{plot_point}}", s_geom_point)

        # 主题
        themes = data.get("plot_themes")
        if themes:
            script = script.replace("{{plot_theme}}", f"theme_{themes}()")
        else:
            script = script.replace("{{plot_theme}}", f"")

        # y轴刻度范围
        y_minu = data.get("y_min")
        y_max = data.get("y_max")
        y_step = data.get("y_step")
        if y_minu or y_max or y_step:
            script = script.replace("{{scale_y_continuous}}", f"scale_x_continuous(breaks=seq({y_minu}，{y_max}，{y_step}))")
        else:
            script = script.replace("{{scale_y_continuous}}", f"")

        # 配置离散型颜色 -- 边框色
        color_qual = data.get("color_qual_theme", "")
        color_qual_self = data.get("color_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_color_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_color_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_color}}", s_scale_color)

        # 配置离散型颜色 -- 填充色
        color_qual = data.get("fill_qual_theme", "")
        color_qual_self = data.get("fill_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_fill_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_fill_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_fill}}", s_scale_color)

        # 配置连续型颜色 -- 边框色
        color_seq = data.get("color_seq_theme", "")
        color_seq_self = data.get("color_seq_self", "")
        color_seq_self_value = data.get("color_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_color_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_color_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_color}}", s_scale_fill)

        # 配置连续型颜色 -- 填充
        color_seq = data.get("fill_seq_theme", "")
        color_seq_self = data.get("fill_seq_self", "")
        color_seq_self_value = data.get("fill_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_fill_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_fill_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_fill}}", s_scale_fill)

        # 分面参数
        col_facets = data.get("col_facets", "")
        row_facets = data.get("row_facets", "")
        facets_nrow = data.get("facets_nrow")
        facets_ncol = data.get("facets_ncol")
        facets_scales = data.get("facets_scales")
        if col_facets and row_facets:
            s_facets = f"facet_grid('{row_facets} ~ {col_facets}'"
        elif col_facets:
            s_facets = f"facet_grid('. ~ {col_facets}'"
        elif row_facets:
            s_facets = f"facet_grid('{row_facets} ~ .'"
        else:
            s_facets = ""

        if s_facets:
            if facets_nrow:
                s_facets += f" ,nrow={facets_nrow}"
            if facets_ncol:
                s_facets += f" ,ncol={facets_ncol}"
            if facets_scales:
                s_facets += f" ,scales='{facets_scales}'"
            s_facets += ")"
        script = script.replace("{{facets}}", s_facets)

        # 整体背景
        plot_background_fill = data.get("plot_background_fill", "")
        plot_background_color = data.get("plot_background_color", "")
        plot_background_size = data.get("plot_background_size", "")
        plot_background_linetype = data.get("plot_background_linetype", "")
        if plot_background_fill or plot_background_color or plot_background_size or plot_background_linetype:
            s_plot_background = f"plot.background = element_rect("
            s_plot_background += f'fill = "{plot_background_fill}",' if plot_background_fill else ""
            s_plot_background += f'colour = "{plot_background_color}",' if plot_background_color else ""
            s_plot_background += f'size = {plot_background_size},' if plot_background_size else ""
            s_plot_background += f'linetype = "{plot_background_linetype}",' if plot_background_linetype else ""
            s_plot_background += ")"
        else:
            s_plot_background = ""
        script = script.replace("{{plot_background}}", s_plot_background)

        # 绘图区背景
        panel_background_fill = data.get("panel_background_fill", "")
        panel_background_color = data.get("panel_background_color", "")
        panel_background_size = data.get("panel_background_size", "")
        panel_background_linetype = data.get("panel_background_linetype", "")
        if panel_background_fill or panel_background_color or panel_background_size or panel_background_linetype:
            s_panel_background = f"panel.background = element_rect("
            s_panel_background += f'fill = "{panel_background_fill}",' if panel_background_fill else ""
            s_panel_background += f'colour = "{panel_background_color}",' if panel_background_color else ""
            s_panel_background += f'size = {panel_background_size},' if panel_background_size else ""
            s_panel_background += f'linetype = "{panel_background_linetype}",' if panel_background_linetype else ""
            s_panel_background += ")"
        else:
            s_panel_background = ""
        script = script.replace("{{panel_background}}", s_panel_background)

        # 主要网格线
        panel_grid_major_color = data.get("panel_grid_major_color", "")
        panel_grid_major_size = data.get("panel_grid_major_size", "")
        panel_grid_major_linetype = data.get("panel_grid_major_linetype", "")
        if panel_grid_major_color or panel_grid_major_size or panel_grid_major_linetype:
            s_panel_grid_major = f"panel.grid.major = element_line("
            s_panel_grid_major += f'colour = "{panel_grid_major_color}",' if panel_grid_major_color else ""
            s_panel_grid_major += f'size = {panel_grid_major_size},' if panel_grid_major_size else ""
            s_panel_grid_major += f'linetype = "{panel_grid_major_linetype}",' if panel_grid_major_linetype else ""
            s_panel_grid_major += ")"
        else:
            s_panel_grid_major = ""
        script = script.replace("{{panel_grid_major}}", s_panel_grid_major)

        # 次要网格线
        panel_grid_minor_color = data.get("panel_grid_minor_color", "")
        panel_grid_minor_size = data.get("panel_grid_minor_size", "")
        panel_grid_minor_linetype = data.get("panel_grid_minor_linetype", "")
        if panel_grid_minor_color or panel_grid_minor_size or panel_grid_minor_linetype:
            s_panel_grid_minor = f"panel.grid.minor = element_line("
            s_panel_grid_minor += f'colour = "{panel_grid_minor_color}",' if panel_grid_minor_color else ""
            s_panel_grid_minor += f'size = {panel_grid_minor_size},' if panel_grid_minor_size else ""
            s_panel_grid_minor += f'linetype = "{panel_grid_minor_linetype}",' if panel_grid_minor_linetype else ""
            s_panel_grid_minor += ")"
        else:
            s_panel_grid_minor = ""
        script = script.replace("{{panel_grid_minor}}", s_panel_grid_minor)

        # 全局字体
        text_family = data.get("text_family", "")
        text_size = data.get("text_size", "")
        text_face = data.get("text_face", "")
        text_color = data.get("text_color", "")
        text_vjust = data.get("text_vjust", "")
        text_angle = data.get("text_angle", "")
        if text_family or text_size or text_face or text_color or text_vjust or text_angle:
            s_text = f"axis.text = element_text("
            s_text += f'family = "{text_family}",' if text_family else ""
            s_text += f'size = {text_size},' if text_size else ""
            s_text += f'face = "{text_face}",' if text_face else ""
            s_text += f'colour = "{text_color}",' if text_color else ""
            s_text += f'vjust = {text_vjust},' if text_vjust else ""
            s_text += f'angle = {text_angle},' if text_angle else ""
            s_text += ")"
        else:
            s_text = ""
        script = script.replace("{{axis_text}}", s_text)

        # x轴字体
        if data.get("text_x_blank") == "true":
            s_text_x = "axis.text.x = element_blank() "
        else:
            text_x_family = data.get("text_x_family", "")
            text_x_size = data.get("text_x_size", "")
            text_x_face = data.get("text_x_face", "")
            text_x_color = data.get("text_x_color", "")
            text_x_vjust = data.get("text_x_vjust", "")
            text_x_hjust = data.get("text_x_hjust", "")
            text_x_angle = data.get("text_x_angle", "")
            if text_x_family or text_x_size or text_x_face or text_x_color or text_x_vjust or text_x_hjust or text_x_angle:
                s_text_x = f"axis.text.x = element_text("
                s_text_x += f'family = "{text_x_family}",' if text_x_family else ""
                s_text_x += f'size = {text_x_size},' if text_x_size else ""
                s_text_x += f'face = "{text_x_face}",' if text_x_face else ""
                s_text_x += f'colour = "{text_x_color}",' if text_x_color else ""
                s_text_x += f'vjust = {text_x_vjust},' if text_x_vjust else ""
                s_text_x += f'hjust = {text_x_hjust},' if text_x_hjust else ""
                s_text_x += f'angle = {text_x_angle},' if text_x_angle else ""
                s_text_x += ")"
            else:
                s_text_x = ""
        script = script.replace("{{axis_text_x}}", s_text_x)

        # y轴字体
        if data.get("text_y_blank") == "true":
            s_text_y = "axis.text.y = element_blank() "
        else:
            text_y_family = data.get("text_y_family", "")
            text_y_size = data.get("text_y_size", "")
            text_y_face = data.get("text_y_face", "")
            text_y_color = data.get("text_y_color", "")
            text_y_vjust = data.get("text_y_vjust", "")
            text_y_hjust = data.get("text_y_hjust", "")
            text_y_angle = data.get("text_y_angle", "")
            if text_y_family or text_y_size or text_y_face or text_y_color or text_y_vjust or text_y_hjust or text_y_angle:
                s_text_y = f"axis.text.y = element_text("
                s_text_y += f'family = "{text_y_family}",' if text_y_family else ""
                s_text_y += f'size = {text_y_size},' if text_y_size else ""
                s_text_y += f'face = "{text_y_face}",' if text_y_face else ""
                s_text_y += f'colour = "{text_y_color}",' if text_y_color else ""
                s_text_y += f'vjust = {text_y_vjust},' if text_y_vjust else ""
                s_text_y += f'hjust = {text_y_hjust},' if text_y_hjust else ""
                s_text_y += f'angle = {text_y_angle},' if text_y_angle else ""
                s_text_y += ")"
            else:
                s_text_y = ""
        script = script.replace("{{axis_text_y}}", s_text_y)

        # 坐标轴线
        axis_line_color = data.get("axis_line_color", "")
        axis_line_size = data.get("axis_line_size", "")
        axis_line_linetype = data.get("axis_line_linetype", "")
        if axis_line_color or axis_line_size or axis_line_linetype:
            s_axis_line = "axis.line = element_line("
            s_axis_line += f'colour = "{axis_line_color}",' if axis_line_color else ""
            s_axis_line += f'size = {axis_line_size},' if axis_line_size else ""
            s_axis_line += f'linetype = "{axis_line_linetype}",' if axis_line_linetype else ""
            s_axis_line += ")"
        else:
            s_axis_line = ""
        script = script.replace("{{axis_line}}", s_axis_line)

        # 坐标刻度
        axis_ticks_color = data.get("axis_ticks_color", "")
        axis_ticks_size = data.get("axis_ticks_size", "")
        axis_ticks_linetype = data.get("axis_ticks_linetype", "")
        if axis_ticks_color or axis_ticks_size or axis_ticks_linetype:
            s_axis_ticks = "axis.ticks = element_line("
            s_axis_ticks += f'colour = "{axis_ticks_color}",' if axis_ticks_color else ""
            s_axis_ticks += f'size = {axis_ticks_size},' if axis_ticks_size else ""
            s_axis_ticks += f'linetype = "{axis_ticks_linetype}",' if axis_ticks_linetype else ""
            s_axis_ticks += ")"
        else:
            s_axis_ticks = ""
        script = script.replace("{{axis_ticks}}", s_axis_ticks)

        # 标题内容
        labs_title = data.get("labs_title", "")
        labs_x = data.get("labs_x", "")
        labs_y = data.get("labs_y", "")
        labs_color = data.get("labs_color", "")
        labs_fill = data.get("labs_fill", "")
        labs_size = data.get("labs_size", "")
        labs_linetype = data.get("labs_linetype", "")
        labs_shape = data.get("labs_shape", "")
        labs_alpha = data.get("labs_alpha", "")
        subtitle_content = data.get("subtitle_content", "")
        caption_content = data.get("caption_content", "")
        if labs_title or labs_x or labs_y or labs_color or labs_fill or labs_size or labs_linetype or labs_shape or \
                labs_alpha or subtitle_content or caption_content:
            s_labs = "labs("
            s_labs += f'title = "{labs_title}",' if labs_title else ""
            s_labs += f'x = "{labs_x}",' if labs_x else ""
            s_labs += f'y = "{labs_y}",' if labs_y else ""
            s_labs += f'colour = "{labs_color}",' if labs_color else ""
            s_labs += f'fill = "{labs_fill}",' if labs_fill else ""
            s_labs += f'size = {labs_size},' if labs_size else ""
            s_labs += f'linetype = "{labs_linetype}",' if labs_linetype else ""
            s_labs += f'shape = "{labs_shape}",' if labs_shape else ""
            s_labs += f'alpha = "{labs_alpha}",' if labs_alpha else ""
            s_labs += f'subtitle = "{subtitle_content}",' if subtitle_content else ""
            s_labs += f'caption = "{caption_content}",' if caption_content else ""
            s_labs = s_labs.strip(",")
            s_labs += ")"
        else:
            s_labs = ""
        script = script.replace("{{labs}}", s_labs)

        # title 格式
        plot_title_family = data.get("plot_title_family", "")
        plot_title_size = data.get("plot_title_size", "")
        plot_title_face = data.get("plot_title_face", "")
        plot_title_color = data.get("plot_title_color", "")
        plot_title_vjust = data.get("plot_title_vjust", "")
        plot_title_hjust = data.get("plot_title_hjust", "")
        plot_title_angle = data.get("plot_title_angle", "")
        if plot_title_family or plot_title_size or plot_title_face or plot_title_color or plot_title_vjust or plot_title_hjust or plot_title_angle:
            s_plot_title = "plot.title = element_text("
            s_plot_title += f'family = "{plot_title_family}",' if plot_title_family else ""
            s_plot_title += f'size = {plot_title_size},' if plot_title_size else ""
            s_plot_title += f'face = "{plot_title_face}",' if plot_title_face else ""
            s_plot_title += f'colour = "{plot_title_color}",' if plot_title_color else ""
            s_plot_title += f'vjust = {plot_title_vjust},' if plot_title_vjust else ""
            s_plot_title += f'hjust = {plot_title_hjust},' if plot_title_hjust else ""
            s_plot_title += f'angle = {plot_title_angle},' if plot_title_angle else ""
            s_plot_title = s_plot_title.strip(",") + ")"
        else:
            s_plot_title = ""
        script = script.replace("{{plot_title}}", s_plot_title)

        # X轴标题格式
        aixs_title_x_family = data.get("aixs_title_x_family", "")
        aixs_title_x_size = data.get("aixs_title_x_size", "")
        aixs_title_x_face = data.get("aixs_title_x_face", "")
        aixs_title_x_color = data.get("aixs_title_x_color", "")
        aixs_title_x_vjust = data.get("aixs_title_x_vjust", "")
        aixs_title_x_hjust = data.get("aixs_title_x_hjust", "")
        aixs_title_x_angle = data.get("aixs_title_x_angle", "")
        if aixs_title_x_family or aixs_title_x_size or aixs_title_x_face or aixs_title_x_color or aixs_title_x_vjust or \
                aixs_title_x_hjust or aixs_title_x_angle:
            s_axis_x_title = "axis.title.x = element_text("
            s_axis_x_title += f'family = "{aixs_title_x_family}",' if aixs_title_x_family else ""
            s_axis_x_title += f'size = {aixs_title_x_size},' if aixs_title_x_size else ""
            s_axis_x_title += f'face = "{aixs_title_x_face}",' if aixs_title_x_face else ""
            s_axis_x_title += f'colour = "{aixs_title_x_color}",' if aixs_title_x_color else ""
            s_axis_x_title += f'vjust = {aixs_title_x_vjust},' if aixs_title_x_vjust else ""
            s_axis_x_title += f'hjust = {aixs_title_x_hjust},' if aixs_title_x_hjust else ""
            s_axis_x_title += f'angle = {aixs_title_x_angle},' if aixs_title_x_angle else ""
            s_axis_x_title = s_axis_x_title.strip(",") + ")"
        else:
            s_axis_x_title = ""
        script = script.replace("{{axis_title_x}}", s_axis_x_title)

        # Y轴标题格式
        aixs_title_y_family = data.get("aixs_title_y_family", "")
        aixs_title_y_size = data.get("aixs_title_y_size", "")
        aixs_title_y_face = data.get("aixs_title_y_face", "")
        aixs_title_y_color = data.get("aixs_title_y_color", "")
        aixs_title_y_vjust = data.get("aixs_title_y_vjust", "")
        aixs_title_y_hjust = data.get("aixs_title_y_hjust", "")
        aixs_title_y_angle = data.get("aixs_title_y_angle", "")
        if aixs_title_y_family or aixs_title_y_size or aixs_title_y_face or aixs_title_y_color or aixs_title_y_vjust or \
                aixs_title_y_hjust or aixs_title_y_angle:
            s_axis_y_title = "axis.title.y = element_text("
            s_axis_y_title += f'family = "{aixs_title_y_family}",' if aixs_title_y_family else ""
            s_axis_y_title += f'size = {aixs_title_y_size},' if aixs_title_y_size else ""
            s_axis_y_title += f'face = "{aixs_title_y_face}",' if aixs_title_y_face else ""
            s_axis_y_title += f'colour = "{aixs_title_y_color}",' if aixs_title_y_color else ""
            s_axis_y_title += f'vjust = {aixs_title_y_vjust},' if aixs_title_y_vjust else ""
            s_axis_y_title += f'hjust = {aixs_title_y_hjust},' if aixs_title_y_hjust else ""
            s_axis_y_title += f'angle = {aixs_title_y_angle},' if aixs_title_y_angle else ""
            s_axis_y_title = s_axis_y_title.strip(",") + ")"
        else:
            s_axis_y_title = ""
        script = script.replace("{{axis_title_y}}", s_axis_y_title)

        # 图例位置
        legend_position = data.get("legend_position", "")
        position_x = data.get("legend_position_x", "")
        position_y = data.get("legend_position_y", "")
        if legend_position or (position_x and position_y):
            if legend_position:
                s_legend_position = f'legend.position = "{legend_position}"'
            else:
                s_legend_position = f'legend.position = c("{position_x}", "{position_y}")'
        else:
            s_legend_position = ""
        script = script.replace("{{legend_position}}", s_legend_position)

        # 图例方向
        legend_direction = data.get("legend_direction", "")
        s_legend_direction = f'legend.direction = "{legend_direction}"' if legend_direction else ""
        script = script.replace("{{legend_direction}}", s_legend_direction)

        # 图例背景
        legend_background_fill = data.get("legend_background_fill", "")
        legend_background_color = data.get("legend_background_color", "")
        legend_background_size = data.get("legend_background_size", "")
        legend_background_linetype = data.get("legend_background_linetype", "")
        if legend_background_fill or legend_background_color or legend_background_size or legend_background_linetype:
            s_legend_background = "legend.background = element_rect("
            s_legend_background += f'fill = "{legend_background_fill}",' if legend_background_fill else ""
            s_legend_background += f'colour = "{legend_background_color}",' if legend_background_color else ""
            s_legend_background += f'size = {legend_background_size},' if legend_background_size else ""
            s_legend_background += f'linetype = "{legend_background_linetype}",' if legend_background_linetype else ""
            s_legend_background = s_legend_background.strip(",") + ")"
        else:
            s_legend_background = ""
        script = script.replace("{{legend_background}}", s_legend_background)

        # legend keys
        legend_keys_fill = data.get("legend_keys_fill", "")
        legend_keys_color = data.get("legend_keys_color", "")
        legend_keys_size = data.get("legend_keys_size", "")
        legend_keys_linetype = data.get("legend_keys_linetype", "")
        if legend_keys_fill or legend_keys_color or legend_keys_size or legend_keys_linetype:
            s_legend_keys = "legend.key = element_rect("
            s_legend_keys += f'fill = "{legend_keys_fill}",' if legend_keys_fill else ""
            s_legend_keys += f'colour = "{legend_keys_color}",' if legend_keys_color else ""
            s_legend_keys += f'size = {legend_keys_size},' if legend_keys_size else ""
            s_legend_keys += f'linetype = "{legend_keys_linetype}",' if legend_keys_linetype else ""
            s_legend_keys = s_legend_keys.strip(",") + ")"
        else:
            s_legend_keys = ""
        script = script.replace("{{legend_keys}}", s_legend_keys)

        # 副标题
        subtitle_family = data.get("subtitle_family", "")
        subtitle_size = data.get("subtitle_size", "")
        subtitle_face = data.get("subtitle_face", "")
        subtitle_color = data.get("subtitle_color", "")
        subtitle_hjust = data.get("subtitle_hjust", "")
        if subtitle_family or subtitle_size or subtitle_face or subtitle_color or subtitle_hjust:
            s_subtitle = f"plot.subtitle = element_text("
            s_subtitle += f'family = "{subtitle_family}",' if subtitle_family else ""
            s_subtitle += f'size = {subtitle_size},' if subtitle_size else ""
            s_subtitle += f'face = "{subtitle_face}",' if subtitle_face else ""
            s_subtitle += f'colour = "{subtitle_color}",' if subtitle_color else ""
            s_subtitle += f'hjust = {subtitle_hjust},' if subtitle_hjust else ""
            s_subtitle = s_subtitle.strip(",") + ")"
        else:
            s_subtitle = ""
        script = script.replace("{{plot_subtitle}}", s_subtitle)

        # 脚注
        caption_family = data.get("caption_family", "")
        caption_size = data.get("caption_size", "")
        caption_face = data.get("caption_face", "")
        caption_color = data.get("caption_color", "")
        caption_hjust = data.get("caption_hjust", "")
        if caption_family or caption_size or caption_face or caption_hjust or caption_color:
            s_caption = f"plot.caption = element_text("
            s_caption += f'family = "{caption_family}",' if caption_family else ""
            s_caption += f'size = {caption_size},' if caption_size else ""
            s_caption += f'face = "{caption_face}",' if caption_face else ""
            s_caption += f'colour = "{caption_color}",' if caption_color else ""
            s_caption += f'hjust = {caption_hjust},' if caption_hjust else ""
            s_caption = s_caption.strip(",") + ")"
        else:
            s_caption = ""
        script = script.replace("{{plot_caption}}", s_caption)

        # 图形大小
        fig_height = data.get("output_height", 6)
        fig_width = data.get("output_width", 8)
        fig_units = data.get("output_units", "in")
        fig_dpi = data.get("output_dpi", "")
        s_fig_size = f"width={fig_width}, height={fig_height}, units='{fig_units}' "
        s_fig_size = s_fig_size + f",dpi={fig_dpi} " if fig_dpi else s_fig_size
        script = script.replace("{{pig_size}}", s_fig_size)

        # 最后处理
        script = script.replace("<< +>>", "")
        script = script.replace("<<,>>", "")
        script = script.replace("<<", "")
        script = script.replace(">>", "")
        script = script.replace(">>", "")
        fw.write(script)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    print(script)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "f_output": f_output})


@_is_post
def plot_rd_qc_line(request):
    """绘制研发部质控折线图"""

    # 表单验证
    data = LinePlotForm(request.POST)
    if data.is_valid():
        data = data.cleaned_data
        print(data)
    else:
        error = [value[0]["message"] for key, value in data.errors.get_json_data().items()]
        error = "\n".join(error)
        return JsonResponse({"code": 1, "msg": error})

    # 生成命令
    d_output = _give_me_directory(f"{settings.DIR_TMP}/PlotDot")
    f_script = f"{d_output}/run.R"
    f_output = f"{d_output}/{data.get('output_name', 'DotPlot')}.jpg"
    f_error = f"{d_output}/error.log"

    with open(f_script, "w") as fw:

        # 基本框架
        script = """
            library('ggplot2')
            library('openxlsx')
            library('RColorBrewer')

            df_data <- {{read_table}}

            p <- ggplot(df_data, aes({{x}}, {{y}}, {{group}})) + 
                 geom_line({{geom_line}}) +
                 <<{{plot_theme}} +>>   # 主题
                 <<{{scale_qual_color}} +>>   #  离散型颜色
                 <<{{scale_qual_fill}} +>>   #  离散型颜色
                 <<{{scale_seq_color}} +>>  # 连续型颜色
                 <<{{scale_seq_fill}} +>>  # 连续型颜色
                 <<{{facets}} +>>  # 分面
                 <<{{labs}} +>>

                 theme(
                     <<{{plot_background}},>>
                     <<{{panel_background}},>>
                     <<{{panel_grid_major}},>>
                     <<{{panel_grid_minor}},>>
                     <<{{axis_text}},>>
                     <<{{axis_text_x}},>>
                     <<{{axis_text_y}},>>
                     <<{{axis_line}},>>
                     <<{{axis_ticks}},>>
                     <<{{axis_title_x}},>>
                     <<{{axis_title_y}},>>
                     <<{{plot_title}},>>
                     <<{{legend_background}},>>
                     <<{{legend_keys}},>>
                     <<{{legend_position}},>>
                     <<{{legend_direction}},>>
                     <<{{plot_subtitle}},>>
                     <<{{plot_caption}},>>
                 )

            ggsave(p, filename="{{f_output}}", {{pig_size}})
        """
        script = script.replace("{{x}}", "x=" + data.get("x"))
        script = script.replace("{{y}}", "y=" + data.get("y"))
        group = data.get("group", "")
        if group:
            script = script.replace("{{group}}", f"color={group}, shape={group}, group={group}")
        else:
            script = script.replace("{{group}}", f"")
        script = script.replace("{{f_output}}", f_output)

        # 读取文件
        input_file = data.get("input_file")
        if input_file.endswith("xlsx") or input_file.endswith("xls"):
            s_read_table = f"read.xlsx('{input_file}',sheet = 1)"
        elif input_file.endswith("csv"):
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F)"
        else:
            s_read_table = f"read.csv('{input_file}', stringsAsFactors = F, sep='\\t')"
        script = script.replace("{{read_table}}", s_read_table)

        # 独有配置
        group = ""
        group_color = ""

        s_geom_point = ""
        if group or group_color:
            s_aes = f"aes("
            s_aes += f"group={group}," if group else ""
            s_aes += f"color={group_color}," if group_color else ""
            s_aes += "), "
            s_geom_point += s_aes
        script = script.replace("{{geom_line}}", s_geom_point)

        # 主题
        themes = data.get("plot_themes")
        if themes:
            script = script.replace("{{plot_theme}}", f"theme_{themes}()")
        else:
            script = script.replace("{{plot_theme}}", f"")

        # 配置离散型颜色 -- 边框色
        color_qual = data.get("color_qual_theme", "")
        color_qual_self = data.get("color_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_color_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_color_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_color}}", s_scale_color)

        # 配置离散型颜色 -- 填充色
        color_qual = data.get("fill_qual_theme", "")
        color_qual_self = data.get("fill_qual_self", "")
        s_scale_color = ""
        if color_qual_self:
            color_qual_self = ', '.join([f'"{s}"' for s in color_qual_self.split(',')])
            s_scale_color = f'scale_fill_manual(values=c({color_qual_self}))'
        elif color_qual:
            s_scale_color = f'scale_fill_brewer(palette="{color_qual}")'
        script = script.replace("{{scale_qual_fill}}", s_scale_color)

        # 配置连续型颜色 -- 边框色
        color_seq = data.get("color_seq_theme", "")
        color_seq_self = data.get("color_seq_self", "")
        color_seq_self_value = data.get("color_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_color_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_color_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_color}}", s_scale_fill)

        # 配置连续型颜色 -- 填充
        color_seq = data.get("fill_seq_theme", "")
        color_seq_self = data.get("fill_seq_self", "")
        color_seq_self_value = data.get("fill_seq_value", 0)
        s_scale_fill = ""
        if color_seq_self:
            low, mid, high = color_seq_self.split(',')
            s_scale_fill = f'scale_fill_gradient2(low="{low}", mid="{mid}", high="{high}", midpoint={color_seq_self_value})'
        elif color_seq:
            s_scale_fill = f'scale_fill_distiller(palette = "{color_seq}")'
        script = script.replace("{{scale_seq_fill}}", s_scale_fill)

        # 分面参数
        col_facets = data.get("col_facets", "")
        row_facets = data.get("row_facets", "")
        facets_nrow = data.get("facets_nrow")
        facets_ncol = data.get("facets_ncol")
        facets_scales = data.get("facets_scales")
        if col_facets and row_facets:
            s_facets = f"facet_grid('{row_facets} ~ {col_facets}'"
        elif col_facets:
            s_facets = f"facet_grid('. ~ {col_facets}'"
        elif row_facets:
            s_facets = f"facet_grid('{row_facets} ~ .'"
        else:
            s_facets = ""

        if s_facets:
            if facets_nrow:
                s_facets += f" ,nrow={facets_nrow}"
            if facets_ncol:
                s_facets += f" ,ncol={facets_ncol}"
            if facets_scales:
                s_facets += f" ,scales='{facets_scales}'"
            s_facets += ")"
        script = script.replace("{{facets}}", s_facets)

        # 整体背景
        plot_background_fill = data.get("plot_background_fill", "")
        plot_background_color = data.get("plot_background_color", "")
        plot_background_size = data.get("plot_background_size", "")
        plot_background_linetype = data.get("plot_background_linetype", "")
        if plot_background_fill or plot_background_color or plot_background_size or plot_background_linetype:
            s_plot_background = f"plot.background = element_rect("
            s_plot_background += f'fill = "{plot_background_fill}",' if plot_background_fill else ""
            s_plot_background += f'colour = "{plot_background_color}",' if plot_background_color else ""
            s_plot_background += f'size = {plot_background_size},' if plot_background_size else ""
            s_plot_background += f'linetype = "{plot_background_linetype}",' if plot_background_linetype else ""
            s_plot_background += ")"
        else:
            s_plot_background = ""
        script = script.replace("{{plot_background}}", s_plot_background)

        # 绘图区背景
        panel_background_fill = data.get("panel_background_fill", "")
        panel_background_color = data.get("panel_background_color", "")
        panel_background_size = data.get("panel_background_size", "")
        panel_background_linetype = data.get("panel_background_linetype", "")
        if panel_background_fill or panel_background_color or panel_background_size or panel_background_linetype:
            s_panel_background = f"panel.background = element_rect("
            s_panel_background += f'fill = "{panel_background_fill}",' if panel_background_fill else ""
            s_panel_background += f'colour = "{panel_background_color}",' if panel_background_color else ""
            s_panel_background += f'size = {panel_background_size},' if panel_background_size else ""
            s_panel_background += f'linetype = "{panel_background_linetype}",' if panel_background_linetype else ""
            s_panel_background += ")"
        else:
            s_panel_background = ""
        script = script.replace("{{panel_background}}", s_panel_background)

        # 主要网格线
        panel_grid_major_color = data.get("panel_grid_major_color", "")
        panel_grid_major_size = data.get("panel_grid_major_size", "")
        panel_grid_major_linetype = data.get("panel_grid_major_linetype", "")
        if panel_grid_major_color or panel_grid_major_size or panel_grid_major_linetype:
            s_panel_grid_major = f"panel.grid.major = element_line("
            s_panel_grid_major += f'colour = "{panel_grid_major_color}",' if panel_grid_major_color else ""
            s_panel_grid_major += f'size = {panel_grid_major_size},' if panel_grid_major_size else ""
            s_panel_grid_major += f'linetype = "{panel_grid_major_linetype}",' if panel_grid_major_linetype else ""
            s_panel_grid_major += ")"
        else:
            s_panel_grid_major = ""
        script = script.replace("{{panel_grid_major}}", s_panel_grid_major)

        # 次要网格线
        panel_grid_minor_color = data.get("panel_grid_minor_color", "")
        panel_grid_minor_size = data.get("panel_grid_minor_size", "")
        panel_grid_minor_linetype = data.get("panel_grid_minor_linetype", "")
        if panel_grid_minor_color or panel_grid_minor_size or panel_grid_minor_linetype:
            s_panel_grid_minor = f"panel.grid.minor = element_line("
            s_panel_grid_minor += f'colour = "{panel_grid_minor_color}",' if panel_grid_minor_color else ""
            s_panel_grid_minor += f'size = {panel_grid_minor_size},' if panel_grid_minor_size else ""
            s_panel_grid_minor += f'linetype = "{panel_grid_minor_linetype}",' if panel_grid_minor_linetype else ""
            s_panel_grid_minor += ")"
        else:
            s_panel_grid_minor = ""
        script = script.replace("{{panel_grid_minor}}", s_panel_grid_minor)

        # 全局字体
        text_family = data.get("text_family", "")
        text_size = data.get("text_size", "")
        text_face = data.get("text_face", "")
        text_color = data.get("text_color", "")
        text_vjust = data.get("text_vjust", "")
        text_angle = data.get("text_angle", "")
        if text_family or text_size or text_face or text_color or text_vjust or text_angle:
            s_text = f"axis.text = element_text("
            s_text += f'family = "{text_family}",' if text_family else ""
            s_text += f'size = {text_size},' if text_size else ""
            s_text += f'face = "{text_face}",' if text_face else ""
            s_text += f'colour = "{text_color}",' if text_color else ""
            s_text += f'vjust = {text_vjust},' if text_vjust else ""
            s_text += f'angle = {text_angle},' if text_angle else ""
            s_text += ")"
        else:
            s_text = ""
        script = script.replace("{{axis_text}}", s_text)

        # x轴字体
        if data.get("text_x_blank") == "true":
            s_text_x = "axis.text.x = element_blank() "
        else:
            text_x_family = data.get("text_x_family", "")
            text_x_size = data.get("text_x_size", "")
            text_x_face = data.get("text_x_face", "")
            text_x_color = data.get("text_x_color", "")
            text_x_vjust = data.get("text_x_vjust", "")
            text_x_hjust = data.get("text_x_hjust", "")
            text_x_angle = data.get("text_x_angle", "")
            if text_x_family or text_x_size or text_x_face or text_x_color or text_x_vjust or text_x_hjust or text_x_angle:
                s_text_x = f"axis.text.x = element_text("
                s_text_x += f'family = "{text_x_family}",' if text_x_family else ""
                s_text_x += f'size = {text_x_size},' if text_x_size else ""
                s_text_x += f'face = "{text_x_face}",' if text_x_face else ""
                s_text_x += f'colour = "{text_x_color}",' if text_x_color else ""
                s_text_x += f'vjust = {text_x_vjust},' if text_x_vjust else ""
                s_text_x += f'hjust = {text_x_hjust},' if text_x_hjust else ""
                s_text_x += f'angle = {text_x_angle},' if text_x_angle else ""
                s_text_x += ")"
            else:
                s_text_x = ""
        script = script.replace("{{axis_text_x}}", s_text_x)

        # y轴字体
        if data.get("text_y_blank") == "true":
            s_text_y = "axis.text.y = element_blank() "
        else:
            text_y_family = data.get("text_y_family", "")
            text_y_size = data.get("text_y_size", "")
            text_y_face = data.get("text_y_face", "")
            text_y_color = data.get("text_y_color", "")
            text_y_vjust = data.get("text_y_vjust", "")
            text_y_hjust = data.get("text_y_hjust", "")
            text_y_angle = data.get("text_y_angle", "")
            if text_y_family or text_y_size or text_y_face or text_y_color or text_y_vjust or text_y_hjust or text_y_angle:
                s_text_y = f"axis.text.y = element_text("
                s_text_y += f'family = "{text_y_family}",' if text_y_family else ""
                s_text_y += f'size = {text_y_size},' if text_y_size else ""
                s_text_y += f'face = "{text_y_face}",' if text_y_face else ""
                s_text_y += f'colour = "{text_y_color}",' if text_y_color else ""
                s_text_y += f'vjust = {text_y_vjust},' if text_y_vjust else ""
                s_text_y += f'hjust = {text_y_hjust},' if text_y_hjust else ""
                s_text_y += f'angle = {text_y_angle},' if text_y_angle else ""
                s_text_y += ")"
            else:
                s_text_y = ""
        script = script.replace("{{axis_text_y}}", s_text_y)

        # 坐标轴线
        axis_line_color = data.get("axis_line_color", "")
        axis_line_size = data.get("axis_line_size", "")
        axis_line_linetype = data.get("axis_line_linetype", "")
        if axis_line_color or axis_line_size or axis_line_linetype:
            s_axis_line = "axis.line = element_line("
            s_axis_line += f'colour = "{axis_line_color}",' if axis_line_color else ""
            s_axis_line += f'size = {axis_line_size},' if axis_line_size else ""
            s_axis_line += f'linetype = "{axis_line_linetype}",' if axis_line_linetype else ""
            s_axis_line += ")"
        else:
            s_axis_line = ""
        script = script.replace("{{axis_line}}", s_axis_line)

        # 坐标刻度
        axis_ticks_color = data.get("axis_ticks_color", "")
        axis_ticks_size = data.get("axis_ticks_size", "")
        axis_ticks_linetype = data.get("axis_ticks_linetype", "")
        if axis_ticks_color or axis_ticks_size or axis_ticks_linetype:
            s_axis_ticks = "axis.ticks = element_line("
            s_axis_ticks += f'colour = "{axis_ticks_color}",' if axis_ticks_color else ""
            s_axis_ticks += f'size = {axis_ticks_size},' if axis_ticks_size else ""
            s_axis_ticks += f'linetype = "{axis_ticks_linetype}",' if axis_ticks_linetype else ""
            s_axis_ticks += ")"
        else:
            s_axis_ticks = ""
        script = script.replace("{{axis_ticks}}", s_axis_ticks)

        # 标题内容
        labs_title = data.get("labs_title", "")
        labs_x = data.get("labs_x", "")
        labs_y = data.get("labs_y", "")
        labs_color = data.get("labs_color", "")
        labs_fill = data.get("labs_fill", "")
        labs_size = data.get("labs_size", "")
        labs_linetype = data.get("labs_linetype", "")
        labs_shape = data.get("labs_shape", "")
        labs_alpha = data.get("labs_alpha", "")
        subtitle_content = data.get("subtitle_content", "")
        caption_content = data.get("caption_content", "")
        if labs_title or labs_x or labs_y or labs_color or labs_fill or labs_size or labs_linetype or labs_shape or \
                labs_alpha or subtitle_content or caption_content:
            s_labs = "labs("
            s_labs += f'title = "{labs_title}",' if labs_title else ""
            s_labs += f'x = "{labs_x}",' if labs_x else ""
            s_labs += f'y = "{labs_y}",' if labs_y else ""
            s_labs += f'colour = "{labs_color}",' if labs_color else ""
            s_labs += f'fill = "{labs_fill}",' if labs_fill else ""
            s_labs += f'size = "{labs_size}",' if labs_size else ""
            s_labs += f'linetype = "{labs_linetype}",' if labs_linetype else ""
            s_labs += f'shape = "{labs_shape}",' if labs_shape else ""
            s_labs += f'alpha = "{labs_alpha}",' if labs_alpha else ""
            s_labs += f'subtitle = "{subtitle_content}",' if subtitle_content else ""
            s_labs += f'caption = "{caption_content}",' if caption_content else ""
            s_labs = s_labs.strip(",")
            s_labs += ")"
        else:
            s_labs = ""
        script = script.replace("{{labs}}", s_labs)

        # title 格式
        plot_title_family = data.get("plot_title_family", "")
        plot_title_size = data.get("plot_title_size", "")
        plot_title_face = data.get("plot_title_face", "")
        plot_title_color = data.get("plot_title_color", "")
        plot_title_vjust = data.get("plot_title_vjust", "")
        plot_title_hjust = data.get("plot_title_hjust", "")
        plot_title_angle = data.get("plot_title_angle", "")
        if plot_title_family or plot_title_size or plot_title_face or plot_title_color or plot_title_vjust or plot_title_hjust or plot_title_angle:
            s_plot_title = "plot.title = element_text("
            s_plot_title += f'family = "{plot_title_family}",' if plot_title_family else ""
            s_plot_title += f'size = {plot_title_size},' if plot_title_size else ""
            s_plot_title += f'face = "{plot_title_face}",' if plot_title_face else ""
            s_plot_title += f'colour = "{plot_title_color}",' if plot_title_color else ""
            s_plot_title += f'vjust = {plot_title_vjust},' if plot_title_vjust else ""
            s_plot_title += f'hjust = {plot_title_hjust},' if plot_title_hjust else ""
            s_plot_title += f'angle = {plot_title_angle},' if plot_title_angle else ""
            s_plot_title = s_plot_title.strip(",") + ")"
        else:
            s_plot_title = ""
        script = script.replace("{{plot_title}}", s_plot_title)

        # X轴标题格式
        aixs_title_x_family = data.get("aixs_title_x_family", "")
        aixs_title_x_size = data.get("aixs_title_x_size", "")
        aixs_title_x_face = data.get("aixs_title_x_face", "")
        aixs_title_x_color = data.get("aixs_title_x_color", "")
        aixs_title_x_vjust = data.get("aixs_title_x_vjust", "")
        aixs_title_x_hjust = data.get("aixs_title_x_hjust", "")
        aixs_title_x_angle = data.get("aixs_title_x_angle", "")
        if aixs_title_x_family or aixs_title_x_size or aixs_title_x_face or aixs_title_x_color or aixs_title_x_vjust or \
                aixs_title_x_hjust or aixs_title_x_angle:
            s_axis_x_title = "axis.title.x = element_text("
            s_axis_x_title += f'family = "{aixs_title_x_family}",' if aixs_title_x_family else ""
            s_axis_x_title += f'size = {aixs_title_x_size},' if aixs_title_x_size else ""
            s_axis_x_title += f'face = "{aixs_title_x_face}",' if aixs_title_x_face else ""
            s_axis_x_title += f'colour = "{aixs_title_x_color}",' if aixs_title_x_color else ""
            s_axis_x_title += f'vjust = {aixs_title_x_vjust},' if aixs_title_x_vjust else ""
            s_axis_x_title += f'hjust = {aixs_title_x_hjust},' if aixs_title_x_hjust else ""
            s_axis_x_title += f'angle = {aixs_title_x_angle},' if aixs_title_x_angle else ""
            s_axis_x_title = s_axis_x_title.strip(",") + ")"
        else:
            s_axis_x_title = ""
        script = script.replace("{{axis_title_x}}", s_axis_x_title)

        # Y轴标题格式
        aixs_title_y_family = data.get("aixs_title_y_family", "")
        aixs_title_y_size = data.get("aixs_title_y_size", "")
        aixs_title_y_face = data.get("aixs_title_y_face", "")
        aixs_title_y_color = data.get("aixs_title_y_color", "")
        aixs_title_y_vjust = data.get("aixs_title_y_vjust", "")
        aixs_title_y_hjust = data.get("aixs_title_y_hjust", "")
        aixs_title_y_angle = data.get("aixs_title_y_angle", "")
        if aixs_title_y_family or aixs_title_y_size or aixs_title_y_face or aixs_title_y_color or aixs_title_y_vjust or \
                aixs_title_y_hjust or aixs_title_y_angle:
            s_axis_y_title = "axis.title.y = element_text("
            s_axis_y_title += f'family = "{aixs_title_y_family}",' if aixs_title_y_family else ""
            s_axis_y_title += f'size = {aixs_title_y_size},' if aixs_title_y_size else ""
            s_axis_y_title += f'face = "{aixs_title_y_face}",' if aixs_title_y_face else ""
            s_axis_y_title += f'colour = "{aixs_title_y_color}",' if aixs_title_y_color else ""
            s_axis_y_title += f'vjust = {aixs_title_y_vjust},' if aixs_title_y_vjust else ""
            s_axis_y_title += f'hjust = {aixs_title_y_hjust},' if aixs_title_y_hjust else ""
            s_axis_y_title += f'angle = {aixs_title_y_angle},' if aixs_title_y_angle else ""
            s_axis_y_title = s_axis_y_title.strip(",") + ")"
        else:
            s_axis_y_title = ""
        script = script.replace("{{axis_title_y}}", s_axis_y_title)

        # 图例位置
        legend_position = data.get("legend_position", "")
        position_x = data.get("legend_position_x", "")
        position_y = data.get("legend_position_y", "")
        if legend_position or (position_x and position_y):
            if legend_position:
                s_legend_position = f'legend.position = "{legend_position}"'
            else:
                s_legend_position = f'legend.position = c("{position_x}", "{position_y}")'
        else:
            s_legend_position = ""
        script = script.replace("{{legend_position}}", s_legend_position)

        # 图例方向
        legend_direction = data.get("legend_direction", "")
        s_legend_direction = f'legend.direction = "{legend_direction}"' if legend_direction else ""
        script = script.replace("{{legend_direction}}", s_legend_direction)

        # 图例背景
        legend_background_fill = data.get("legend_background_fill", "")
        legend_background_color = data.get("legend_background_color", "")
        legend_background_size = data.get("legend_background_size", "")
        legend_background_linetype = data.get("legend_background_linetype", "")
        if legend_background_fill or legend_background_color or legend_background_size or legend_background_linetype:
            s_legend_background = "legend.background = element_rect("
            s_legend_background += f'fill = "{legend_background_fill}",' if legend_background_fill else ""
            s_legend_background += f'colour = "{legend_background_color}",' if legend_background_color else ""
            s_legend_background += f'size = {legend_background_size},' if legend_background_size else ""
            s_legend_background += f'linetype = "{legend_background_linetype}",' if legend_background_linetype else ""
            s_legend_background = s_legend_background.strip(",") + ")"
        else:
            s_legend_background = ""
        script = script.replace("{{legend_background}}", s_legend_background)

        # legend keys
        legend_keys_fill = data.get("legend_keys_fill", "")
        legend_keys_color = data.get("legend_keys_color", "")
        legend_keys_size = data.get("legend_keys_size", "")
        legend_keys_linetype = data.get("legend_keys_linetype", "")
        if legend_keys_fill or legend_keys_color or legend_keys_size or legend_keys_linetype:
            s_legend_keys = "legend.key = element_rect("
            s_legend_keys += f'fill = "{legend_keys_fill}",' if legend_keys_fill else ""
            s_legend_keys += f'colour = "{legend_keys_color}",' if legend_keys_color else ""
            s_legend_keys += f'size = {legend_keys_size},' if legend_keys_size else ""
            s_legend_keys += f'linetype = "{legend_keys_linetype}",' if legend_keys_linetype else ""
            s_legend_keys = s_legend_keys.strip(",") + ")"
        else:
            s_legend_keys = ""
        script = script.replace("{{legend_keys}}", s_legend_keys)

        # 副标题
        subtitle_family = data.get("subtitle_family", "")
        subtitle_size = data.get("subtitle_size", "")
        subtitle_face = data.get("subtitle_face", "")
        subtitle_color = data.get("subtitle_color", "")
        subtitle_hjust = data.get("subtitle_hjust", "")
        if subtitle_family or subtitle_size or subtitle_face or subtitle_color or subtitle_hjust:
            s_subtitle = f"plot.subtitle = element_text("
            s_subtitle += f'family = "{subtitle_family}",' if subtitle_family else ""
            s_subtitle += f'size = {subtitle_size},' if subtitle_size else ""
            s_subtitle += f'face = "{subtitle_face}",' if subtitle_face else ""
            s_subtitle += f'colour = "{subtitle_color}",' if subtitle_color else ""
            s_subtitle += f'hjust = {subtitle_hjust},' if subtitle_hjust else ""
            s_subtitle = s_subtitle.strip(",") + ")"
        else:
            s_subtitle = ""
        script = script.replace("{{plot_subtitle}}", s_subtitle)

        # 脚注
        caption_family = data.get("caption_family", "")
        caption_size = data.get("caption_size", "")
        caption_face = data.get("caption_face", "")
        caption_color = data.get("caption_color", "")
        caption_hjust = data.get("caption_hjust", "")
        if caption_family or caption_size or caption_face or caption_hjust or caption_color:
            s_caption = f"plot.caption = element_text("
            s_caption += f'family = "{caption_family}",' if caption_family else ""
            s_caption += f'size = {caption_size},' if caption_size else ""
            s_caption += f'face = "{caption_face}",' if caption_face else ""
            s_caption += f'colour = "{caption_color}",' if caption_color else ""
            s_caption += f'hjust = {caption_hjust},' if caption_hjust else ""
            s_caption = s_caption.strip(",") + ")"
        else:
            s_caption = ""
        script = script.replace("{{plot_caption}}", s_caption)

        # 图形大小
        fig_height = data.get("output_height", 6)
        fig_width = data.get("output_width", 8)
        fig_units = data.get("output_units", "in")
        fig_dpi = data.get("output_dpi", "")
        s_fig_size = f"width={fig_width}, height={fig_height}, units='{fig_units}' "
        s_fig_size = s_fig_size + f",dpi={fig_dpi} " if fig_dpi else s_fig_size
        script = script.replace("{{pig_size}}", s_fig_size)

        # 最后处理
        script = script.replace("<< +>>", "")
        script = script.replace("<<,>>", "")
        script = script.replace("<<", "")
        script = script.replace(">>", "")
        script = script.replace(">>", "")
        fw.write(script)

    cmd = f"{settings.RSCRIPT_BASE} {f_script} >> {f_error}"
    print(script)
    try:
        subprocess.check_call(cmd, shell=True)
    except Exception as _:
        return JsonResponse({"code": 2, "msg": f_error})
    else:
        return JsonResponse({"code": 0, "f_output": f_output})
#####目前建议使用的R版本： 3.5.3 
rm(list=ls())

##############input file parameter#####################################
############需要修改：输入文件参数#####################################
##############input file name#####################################
############需要修改：输入文件名#####################################
exprTable <- "{{exprTable}}"
############set working directory#############
######需要修改：设置工作路径########
file_path <- "{{file_path}}"
##############ouput file parameter#####################################
#####################需要修改：输出文件设置############################
#需要修改：输出文件名，可选格式：pdf/jpeg/png，建议保存为pdf/jpeg，清晰度高。
set_filename = "{{set_filename}}.jpg"
#可以自定义：输出文件宽度
set_pic_width = {{set_pic_width}}
#可以自定义：输出文件长度
set_pic_height = {{set_pic_height}}

####################using manual order or clustering###################
#####################设定人为排序顺序或按照聚类顺序####################
#######################################################################
"注意！！！选择聚类的话，人为设定的行/列排列顺序就没有用了，
因此cluster_colum和whether_manual_order_columnd的TRUE和FALSE相反
cluster_row和whether_manual_order_row的TRUE和FALSE相反"
#######################################################################
#可以自定义：是否根据列聚类,聚类：TRUE；非聚类：FALSE,输出结果按照聚类排序
whether_cluster_column = "{{whether_cluster_column}}"
#可以自定义：是否根据行聚类,聚类：TRUE；非聚类：FALSE,输出结果按照聚类排序
whether_cluster_row = "{{whether_cluster_row}}"
#可以自定义：输出结果按照输入文件列排序，这样则不根据列聚类
whether_original_order_column = "{{whether_original_order_column}}"
#可以自定义：输出结果按照输入文件行排序，这样则不根据行聚类
whether_original_order_row = "{{whether_original_order_row}}"

#####################setting clustering parameters############################
#############################聚类方法及展示设置###############################
#可以自定义：设置聚类的方法，默认：可选：'ward.D', 'ward.D2', 'single', 'complete', 'average', 'mcquitty', 'median' or 'centroid'.
set_clustering_method = "{{set_clustering_method}}"
#可以自定义：设置行聚类的距离类型，默认：可选：correlation，euclidean，maximum，manhattan，canberra，binary，minkowski.
set_clustering_distance_rows = "{{set_clustering_distance_rows}}"
#可以自定义：设置列聚类的距离类型，默认：可选：correlation，euclidean，maximum，manhattan，canberra，binary，minkowski.
set_clustering_distance_cols = "{{set_clustering_distance_cols}}"
#可以自定义：设置列聚类树的显示高度
set_treeheight_col = {{set_treeheight_col}}
#可以自定义：设置行聚类树的显示高度
set_treeheight_row = {{set_treeheight_row}}


################setting legends##########################
#####################图例设置############################
#可以自定义：是否显示图例
whether_show_legend = "{{whether_show_legend}}"
#可以自定义：是否对行或列标准化,输出在图例中，通常可以对基因表达，CNV数值等做标准化处理。选填“none”，“row”,"column“
#注：如果数据中出现极大值或极小值，则建议选择将数据进行scale
whether_scale = "{{whether_scale}}"


####################setting axis parameter#######################
#####################横纵坐标参数设置############################
#可以自定义：是否显示横坐标ID
whether_show_rownames = "{{whether_show_rownames}}"
#可以自定义：是否显示纵坐标ID
whether_show_colnames = "{{whether_show_colnames}}"
#可以自定义：设置横坐标字体大小
set_font_size_row = {{set_font_size_row}}
#可以自定义：设置纵坐标字体大小
set_font_size_col = {{set_font_size_col}}
#可以自定义：设置横坐标数字的角度，可选："270","0","45","90","315"
set_angle_col = {{set_angle_col}}


##################setting colormap parameters####################
#####################热图方块参数设置############################
#可以自定义：设置热图方块的宽度，设置为NA表示自适应窗口
set_cellwidth = {{set_cellwidth}}
#可以自定义：设置热图方块的高度，设置为NA表示自适应窗口
set_cellheight = {{set_cellheight}}
#可以自定义：根据热图聚类对其进行区块儿划分，可以指定区域个数
#可以自定义：划分热图为几列
set_cutree_cols = {{set_cutree_cols}} 
#可以自定义：划分热图为几行
set_cutree_rows = {{set_cutree_rows}} 

#可以自定义：设置颜色梯度,可以设置多个颜色，建议2-3个
set_color_gradient <- unlist(strsplit("{{set_color_gradient}}",split = ","))
#可以自定义：设置颜色梯度数量，建议50个以上
set_color_gradient_number <- {{set_color_gradient_number}}
#可以自定义：格子边框是否有颜色，默认为“grey60”
set_border_color = "{{set_border_color}}"

#可以自定义：设置是否显示热图格子中的数字
whether_display_number = "{{whether_display_number}}"
###拓展，可以自定义：对热图方块儿进行标记；display_numbers，如果该值大于n，则为+，否则为-。
#whether_display_number = matrix(ifelse(data > 15, "+", "-"), nrow(data))
#可以自定义：设置热图格子中数字大小
set_font_size_num = {{set_font_size_num}}
#可以自定义：设置热图格子中数字颜色
set_number_color = "{{set_number_color}}"



############convert string to boolean###############
#################字符型转化回布尔型#################
if (whether_cluster_column == "TRUE"){
  whether_cluster_column <- TRUE
}else if (whether_cluster_column == "FALSE"){
  whether_cluster_column <- FALSE
}
if (whether_cluster_row == "TRUE"){
  whether_cluster_row <- TRUE
}else if (whether_cluster_row == "FALSE"){
  whether_cluster_row <- FALSE
}
if (whether_original_order_column == "TRUE"){
  whether_original_order_column <- TRUE
}else if (whether_original_order_column == "FALSE"){
  whether_original_order_column <- FALSE
}
if (whether_original_order_row == "TRUE"){
  whether_original_order_row <- TRUE
}else if (whether_original_order_row == "FALSE"){
  whether_original_order_row <- FALSE
}
if (whether_show_legend == "TRUE"){
  whether_show_legend <- TRUE
}else if (whether_show_legend == "FALSE"){
  whether_show_legend <- FALSE
}
if (whether_show_rownames == "TRUE"){
  whether_show_rownames <- TRUE
}else if (whether_show_rownames == "FALSE"){
  whether_show_rownames <- FALSE
}
if (whether_show_colnames == "TRUE"){
  whether_show_colnames <- TRUE
}else if (whether_show_colnames == "FALSE"){
  whether_show_colnames <- FALSE
}
if (whether_display_number == "TRUE"){
  whether_display_number <- TRUE
}else if (whether_display_number == "FALSE"){
  whether_display_number <- FALSE
}
class(whether_original_order_row)


############library R packages#############
######括号内填写载入需要的R包########
library(pheatmap)
library(openxlsx)

############set working directory#############
######设置工作路径，开始画图########
setwd(file_path)
#########可能修改：载入文件，输入文件所在excel表中第几个sheet，sheet=后的数字就改为几############
mydat <- read.xlsx(exprTable,colNames = T,rowNames =T, sheet = 1)
#mydat <- log2(mydat)
mydat

#order of columns and rows
#设置行和列的顺序
# if (whether_manual_order_column == TRUE & whether_manual_order_row == TRUE){
#   mydat <- mydat[manual_order_row, manual_order_column]
# }else if (whether_manual_order_column == TRUE){
#   mydat <- mydat[, manual_order_column]
# }else if (whether_manual_order_row == TRUE){
#   mydat <- mydat[manual_order_row, ]
# }else 
#   mydat <- mydat
# mydat
# 
# if (cluster_column == FALSE & whether_manual_order_column == TRUE){
#   manual_heatmap_order = mydat[order(colnames(mydat)),]
# }else if (cluster_row == FALSE & whether_manual_order_row == TRUE){
#   manual_heatmap_order = mydat[,order(rownames(mydat))]
# }else 
#   manual_heatmap_order = mydat
# manual_heatmap_order

#order of columns and rows
#设置行和列的顺序
if (whether_cluster_column == FALSE & whether_original_order_column == TRUE){
  heatmap_order = mydat[order(colnames(mydat)),]
}else if(whether_cluster_row == FALSE & whether_original_order_row == TRUE){
  heatmap_order = mydat[,order(rownames(mydat))]
}else{
  heatmap_order = mydat
}
heatmap_order

#作图
pheatmap(heatmap_order, 
         cluster_cols = whether_cluster_column, 
         cluster_rows = whether_cluster_row,
         show_colnames = whether_show_colnames,  
         show_rownames = whether_show_rownames,
         color = colorRampPalette(set_color_gradient)(set_color_gradient_number),
         scale = whether_scale,
         border_color = set_border_color,
         legend = whether_show_legend,
         fontsize_row = set_font_size_row,
         fontsize_col = set_font_size_col,
         angle_col = set_angle_col,
         cutree_cols = set_cutree_cols, 
         cutree_rows = set_cutree_rows,
         treeheight_col = set_treeheight_col, 
         treeheight_row = set_treeheight_row,
         clustering_method = set_clustering_method,
         clustering_distance_rows = set_clustering_distance_rows,
         clustering_distance_cols = set_clustering_distance_cols,
         display_numbers = whether_display_number,
         fontsize_number = set_font_size_num,
         number_color = set_number_color,
         #可以自定义：可选参数：设置图片标题
         #main = “name the title here”,
         cellwidth = set_cellwidth,
         cellheight = set_cellheight,
         #下面3行为输出图片为文件的参数
         filename = set_filename,
         width = set_pic_width,
         height = set_pic_height
)


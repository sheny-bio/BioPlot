args <- commandArgs(trailingOnly = TRUE)


file_name <- args[1]
output_name <- args[2]
# the main plot function
my_plot_fun <- function(file_name, out_file_name){
  # set working directory
  df <- read.csv(file_name, sep = ',', header = T, stringsAsFactors = F, strip.white = T, check.names = F)
  # setwd(dirname(file_name))
  # set figure file name
  # out_file_name <- paste0(basename(file_name), '.png')
  # print figure file name
  # print(out_file_name)

  library(reshape2)
  library(plyr)
  library(ggplot2)
  library(showtext)
  font_add('fzltxh',"/dssg/home/sheny/MyProject/BioPlot/static/db/fzltxh_gbk.TTF")
  showtext_auto()
  
  # create scale function to change y axis digits
  scaleFUN <- function(x) sprintf("%.2f", x)
  # read input file

  # calculate data dimension
  num_col <- ncol(df)
  num_row <- nrow(df)
  # get rows with percentage symbols
  pct_index <- grep('%', df[, 2])
  # png(filename = out_file_name, family='fzltxh',type='cairo', width = 1000, height = 500)
  # par(mar=c(10,10,10,10))
  if(length(pct_index) == 0){
    # CNV only
    # format df
    print('CNV only')
    remove_pct_df <- apply(df, 2, gsub, pattern = '%', replacement = '')
    if(is.null(dim(remove_pct_df))){
      remove_pct_df <- matrix(remove_pct_df, nrow = 1)
      colnames(remove_pct_df) <- names(df)
    }
    replace_space_df <- apply(remove_pct_df, 2, gsub, pattern = ' ', replacement = '_')
    if(is.null(dim(replace_space_df))){
      replace_space_df <- matrix(replace_space_df, nrow = 1)
      colnames(replace_space_df) <- names(df)
    }
    max_rounded_cn <- max(as.numeric(unlist(df[, 2:num_col])))
    rownames(replace_space_df) <- replace_space_df[, 1]
    replace_space_df <- replace_space_df[, 2:num_col, drop = F]
    # when we have Chinese characters in header, melt will not work for data frame, so use matrix instead
    final_df <- melt(replace_space_df, id.vars = colnames(replace_space_df))
    names(final_df) <- c('type', 'time', 'value')
    final_df$value <- as.numeric(as.character(final_df$value))
    # plot

    legend_col=ceiling(dim(replace_space_df)[1]/13)

    ggplot(final_df, aes(x = as.factor(time), y = value, color = type, shape = type, group = type)) +
      geom_point(size = 5) +
      geom_line(size = 1.5) +
      theme(text=element_text(family="fzltxh",size=22,colour = "#404040")) +
      xlab('') +
      scale_y_continuous(name = '扩增倍数',
                         labels = scaleFUN,
                         limits = c(1, max_rounded_cn)) +
      theme(plot.margin=unit(c(2,2,2,2),'cm'),
            legend.box.spacing = unit(1, 'cm'),
            legend.title = element_blank(),
            legend.text = element_text(size = 35),
            legend.key.height = unit(2, 'line'),
            legend.key.width = unit(3, 'line'),
            axis.title.y = element_text(margin = margin(t = 0, r = 20, b = 0, l = 0), angle = 90, vjust = 0.5),
            axis.title.x = element_text(margin = margin(t = 20, r = 0, b = 0, l = 0)),
            axis.text = element_text(size = 40),
            axis.title = element_text(size = 50, face = 'bold'),
            panel.background = element_rect(fill = 'white', colour = 'grey50'),
            panel.grid.major.y = element_line(color = 'black'),
            panel.grid.minor.y = element_line(color = 'black'),
            panel.grid.major.x = element_blank(),
            panel.grid.minor.x = element_blank())+
      guides(colour=guide_legend(ncol=legend_col))
    ggsave(filename = out_file_name, width = 12+(legend_col-1)*2, height = 6, limitsize = F)
  }else if(length(pct_index) == num_row){
    # mutation only
    # format df
    print('Mutations only')
    remove_pct_df <- apply(df, 2, gsub, pattern = '%', replacement = '')
    if(is.null(dim(remove_pct_df))){
      remove_pct_df <- matrix(remove_pct_df, nrow = 1)
      colnames(remove_pct_df) <- names(df)
    }
    replace_space_df <- apply(remove_pct_df, 2, gsub, pattern = ' ', replacement = '_')
    if(is.null(dim(replace_space_df))){
      replace_space_df <- matrix(replace_space_df, nrow = 1)
      colnames(replace_space_df) <- names(df)
    }
    replace_space_df[pct_index, 2:num_col] = as.numeric(replace_space_df[pct_index, 2:num_col])
    max_rounded_af <- max(as.numeric(unlist(replace_space_df[pct_index, 2:num_col])))
    rownames(replace_space_df) <- replace_space_df[, 1]
    replace_space_df <- replace_space_df[, 2:num_col, drop = F]
    final_df <- melt(replace_space_df, id.vars = colnames(replace_space_df))
    names(final_df) <- c('type', 'time', 'value')
    final_df$value <- as.numeric(as.character(final_df$value))
    # plot

    mut_count=length(pct_index) 
    legend_col=ceiling(mut_count/13)

    ggplot(final_df, aes(x = as.factor(time), y = value, color = type, shape = type, group = type)) +
      geom_point(size = 5) +
      geom_line(size = 1.5) +
      theme(text=element_text(family="fzltxh",size=22,colour = "#404040")) +
      xlab('') +
      scale_y_continuous(name = '突变丰度（%）',
                         labels = scaleFUN,
                         limits = c(0, max_rounded_af)) +
      theme(plot.margin=unit(c(2,2,2,2),'cm'),
            legend.box.spacing = unit(1, 'cm'),
            legend.title = element_blank(),
            legend.text = element_text(size = 35),
            legend.key.height = unit(2, 'line'),
            legend.key.width = unit(3, 'line'),
            axis.title.y = element_text(margin = margin(t = 0, r = 20, b = 0, l = 0), angle = 90, vjust = 0.5),
            axis.title.x = element_text(margin = margin(t = 20, r = 0, b = 0, l = 0)),
            axis.text = element_text(size = 40),
            axis.title = element_text(size = 50, face = 'bold'),
            panel.background = element_rect(fill = 'white', colour = 'grey50'),
            panel.grid.major.y = element_line(color = 'black'),
            panel.grid.minor.y = element_line(color = 'black'),
            panel.grid.major.x = element_blank(),
            panel.grid.minor.x = element_blank())+
      guides(colour=guide_legend(ncol=legend_col))
    ggsave(filename = out_file_name, width = 12+(legend_col-1)*2, height = 6, limitsize = F)
  }else{
    # both CNV and mutation
    # format df
    print('Both CNV and Mutations')
    remove_pct_df <- apply(df, 2, gsub, pattern = '%', replacement = '')
    replace_space_df <- apply(remove_pct_df, 2, gsub, pattern = ' ', replacement = '_')
    replace_space_df[pct_index, 2:num_col] = as.numeric(replace_space_df[pct_index, 2:num_col])
    max_rounded_cn <- round_any(max(as.numeric(unlist(df[-pct_index, 2:num_col]))), 5, f = ceiling)
    max_rounded_af <- round_any(max(as.numeric(unlist(replace_space_df[pct_index, 2:num_col]))), 5, f = ceiling)
    replace_space_df[-pct_index, 2:num_col] = (as.numeric(replace_space_df[-pct_index, 2:num_col]) - 1) * max_rounded_af / (max_rounded_cn-1)
    rownames(replace_space_df) <- replace_space_df[, 1]
    replace_space_df <- replace_space_df[, 2:num_col]
    final_df <- melt(replace_space_df, id.vars = colnames(replace_space_df))
    names(final_df) <- c('type', 'time', 'value')
    final_df$value <- as.numeric(as.character(final_df$value))
    # plot

    legend_col=ceiling(dim(replace_space_df)[1]/13)

    ggplot(final_df, aes(x = as.factor(time), y = value, color = type, shape = type, group = type)) +
      geom_point(size = 5) +
      geom_line(size = 1.5) +
      theme(text=element_text(family="fzltxh", size=22,colour = "#404040")) +
      xlab('') +
      scale_y_continuous(sec.axis = sec_axis(~ . * (max_rounded_cn-1) / max_rounded_af + 1, name = '扩增倍数', labels = scaleFUN),
                         name = '突变丰度（%）',
                         labels = scaleFUN,
                         limits = c(0, max_rounded_af)) +
      theme(plot.margin=unit(c(2,2,2,2),'mm'),
            legend.box.spacing = unit(1, 'mm'),
            legend.title = element_blank(),
            legend.text = element_text(size = 35),
            legend.key.height = unit(2, 'line'),
            legend.key.width = unit(3, 'line'),
            axis.title.y = element_text(margin = margin(t = 0, r = 20, b = 0, l = 0), angle = 90, vjust = 0.5),
            axis.title.y.right = element_text(margin = margin(t = 0, r = 0, b = 0, l = 20), angle = 270, vjust = 0.5),
            axis.title.x = element_text(margin = margin(t = 20, r = 0, b = 0, l = 0)),
            axis.text = element_text(size = 40),
            axis.title = element_text(size = 50, face = 'bold'),
            panel.background = element_rect(fill = 'white', colour = 'grey50'),
            panel.grid.major.y = element_line(color = 'black'),
            panel.grid.minor.y = element_line(color = 'black'),
            panel.grid.major.x = element_blank(),
            panel.grid.minor.x = element_blank())+
      guides(colour=guide_legend(ncol=legend_col))
    ggsave(filename = out_file_name, width = 12+(legend_col-1)*2, height = 6, limitsize = F)
  }
  # dev.off()
}


my_plot_fun(file_name, output_name)




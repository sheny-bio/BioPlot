#!/dssg/softwares/R/R-3.6.0/lib64/R/bin/Rscript
# .libPaths(c("/dssg/home/weiyl/R/x86_64-pc-linux-gnu-library/3.6", "/dssg/softwares/R/R-3.6.0/lib64/R/library" ))

library(optparse)
option_list<-list(make_option(c("--clinfile"), type="character", default=NULL,
                              help="Clinical information sheet, tsv format with header, 1st colomn must be SampleID", metavar="character"),
                  make_option(c("--types"), type="character", default=NULL,
                              help="alteration types, used in corresponding subplot, comma separated. ", metavar="character"),
                  make_option(c("--files"), type="character", default=NULL,
                              help="alteration files, comma separated, each file is TSV format, 3 colomns {SampleID\tabGene\tabMuationType}. corresponds to --types",
                              metavar="character"),
                  make_option(c("--outfile"), type="character", default="tmp_oncorint.pdf",
                              help="outfile name.", metavar="character"),
                  make_option(c("--gene"), type="character", default=NULL,
                              help="genes used in per subplot, All genes used if NULL",
                              metavar="character"),
                  make_option(c("--width"), type="integer", default=12,
                              help="outfile width", metavar="integer"),
                  make_option(c("--height"), type="integer", default=5.5,
                              help="outfile height", metavar="integer"),
                  make_option(c("--color"), type="character", default=NULL,
                              help="configure file of color, 1st column is detailed alteration type and 2nd is color.", metavar="character"),
                  make_option(c("--column_split"), type="character", default=NULL,
                              help="column split, one of colnames in clincal file, default NULL",
                              metavar="character")
)
opt_parser <- OptionParser(option_list=option_list)
opt <- parse_args(opt_parser)


library(ComplexHeatmap)
library(reshape2)


# Test --------------------------------------------------------------------
# opt$clinfile = "demo_cln_info.tsv"
# opt$types = "mutations,CNV,oncogenic,Arm CNV"
# opt$files = "demo_mutation.tsv,demo_cnv.tsv,demo_oncogenic.tsv,demo_arm.tsv"
# opt$gene = "demo_gene.tsv"
# opt$color = "demo_color.tsv"


# function converts data frame to oncoprint matrix   -----------------------
matrix_to_list_sub = function(df, samples, genes = NULL){
    colnames(df) = c("SampleID", "Gene", "VariantClassification")
    df = df[df$SampleID %in% samples,]
    if (!is.null(genes)){df = df[df$Gene %in% genes,]}
    
    library(reshape2)
    variant_list = list()
    for (vtype in unique(df$VariantClassification)){
        tmp_df = df[df$VariantClassification == vtype,,drop=F]
        tmp_matrix = dcast(tmp_df, Gene ~ SampleID, fun.aggregate = length)
        rownames(tmp_matrix) = tmp_matrix[,1]
        tmp_matrix = tmp_matrix[,2:ncol(tmp_matrix),drop=F]
        tmp_matrix[is.na(tmp_matrix)] = "0"
        
        samples_miss = setdiff(samples, colnames(tmp_matrix))
        if (length(samples_miss) > 0){
            tmp_matrix = cbind(tmp_matrix, matrix(0, ncol = length(samples_miss), nrow = nrow(tmp_matrix),
                                                  dimnames = list(rownames(tmp_matrix), samples_miss)))
        }
        genes_miss = setdiff(genes, rownames(tmp_matrix))
        if (length(genes_miss) > 0 ){
            tmp_matrix = rbind(tmp_matrix, matrix(0, ncol = ncol(tmp_matrix), nrow = length(genes_miss),
                                                  dimnames = list(genes_miss, colnames(tmp_matrix))))
        }
        variant_list[[vtype]] = as.matrix(tmp_matrix[,samples])
    }
    return(variant_list)
}


# cln info and alteration data  ----------------------------------------------------------------

cln_info = read.delim(opt$clinfile, stringsAsFactors = F)
rownames(cln_info) = cln_info$SampleID
altertypes = unlist(strsplit(opt$types, split = ","))
alterfiles = unlist(strsplit(opt$files, split = ","))

df_genes = data.frame(altertypes = character(), genes = character())
if (!is.null(opt$gene)){
    tmp_genes = read.delim(opt$gene, header = T, stringsAsFactors = F)[,1:2]
    colnames(tmp_genes) = c("altertypes", "genes")
    tmp_genes = unique.data.frame(tmp_genes)
    df_genes = rbind(df_genes, tmp_genes)
}
alterdata = list()
detail_muts = vector()
samples = cln_info$SampleID
for (i in 1:length(altertypes)){
    tmp = read.delim(alterfiles[i], stringsAsFactors = F)
    detail_muts = c(detail_muts, unique(tmp[,3]))
    tmp_genes_used = df_genes[df_genes$altertypes %in% altertypes[i], "genes",drop = T]
    if (length(tmp_genes_used) == 0){ 
        tmp_genes_used = unique(tmp[,2])
    }
    tmp = matrix_to_list_sub(tmp, samples = samples, genes = tmp_genes_used)
    alterdata[[altertypes[i]]] = tmp
}



# colors used  ------------------------------------------------------------
cln_info_colnames = colnames(cln_info)
cln_info_colnames = setdiff(cln_info_colnames, "SampleID")
if (is.null(opt$color)){
    library(RColorBrewer)
    qual_col_pals = brewer.pal.info[brewer.pal.info$category == "qual",]
    col_vector = unlist(mapply(brewer.pal, qual_col_pals$maxcolors, rownames(qual_col_pals)))
    # discard colors
    col_vector = col_vector[-grep("^#FFFF", col_vector)]
    # col_vector = col_vector[-which(col_vector %in% c('#386CB0', '#666666', '#1B9E77', '#7570B3', '#66A61E', 
    #    '#1F78B4', '#33A02C', '#6A3D9A', '#B15928',' #FFED6F', '#F2F2F2', '#FFD92F', "#FFED6F"))]
    # col_vector = rev(col_vector)
    color_list <<- list() # global
    for (i in 1:length(detail_muts)){
        color_list[[detail_muts[i]]] = col_vector[i]
    }
    
    # sample annotation
    color_annot = list()
    annot_type = vector()
    for (cln_column in cln_info_colnames){
        annot_type = c(annot_type, unique(cln_info[, cln_column]))
    }
    color_annot = col_vector[(length(color_list)+1):(length(color_list)+length(annot_type))]
    names(color_annot) = annot_type
    
} else {
    color_df = read.delim(opt$color, header = F, stringsAsFactors = F)
    col_vector = list()
    for (row_index in 1:nrow(color_df)){
        col_vector[[color_df[row_index,1]]] = color_df[row_index,2]
    }
    color_list = col_vector
    color_annot = col_vector
}


# oncoprint ---------------------------------------------------------------

alter_fun = list()
alter_fun[["background"]] = function(x, y, w, h) {grid.rect(x, y, w-unit(0.5, "mm"), h-unit(0.5, "mm"), gp = gpar(fill = "#E5E5E5", col = NA))}
for (mut_type in detail_muts){
    cmd = paste0("alter_fun[[\"",mut_type,"\"]] = function(x,y,w,h){grid.rect(x, y, w,h, gp = gpar(fill=\"",color_list[[mut_type]], "\", col = NA))}")
    eval(parse(text = cmd))
}

cln_color_list = list()
for (cln_col in cln_info_colnames){
    cln_color_list[[cln_col]] = unlist(color_annot)
}

ha = columnAnnotation(df = cln_info[, cln_info_colnames], col = cln_color_list)

if (is.null(opt$column_split)){
    column_split = NULL
} else {
    column_split = cln_info[,opt$column_split, drop=F]
}

plot_list = list()
for (i in 1:length(altertypes)) {
    plot_list[[altertypes[i]]] = oncoPrint(unify_mat_list(alterdata[[altertypes[i]]]), 
                                        alter_fun = alter_fun, 
                                        col = color_list, 
                                        column_split = column_split,
                                        right_annotation = NULL,
                                        top_annotation = NULL,
                                        heatmap_legend_param = list(title= altertypes[i]),
                                        pct_gp = gpar(fontsize = 7, fontface = "italic"),
                                        row_title = altertypes[i],
                                        row_title_gp = gpar(fontsize = 12),
                                        column_title = NULL,
                                        row_names_side = "left", 
                                        pct_side = "right")
}

plots_all = ha
for (alter_type in altertypes){
    plots_all =  plots_all %v% plot_list[[alter_type]]  
}

outfile = ifelse(grepl(".pdf$", opt$outfile), opt$outfile, paste0(opt$outfile, ".pdf"))
pdf(outfile, width = opt$width, height = opt$height)
draw(plots_all , heatmap_legend_side  = "right" )
dev.off()

outfile = ifelse(grepl(".png$", opt$outfile), opt$outfile, paste0(opt$outfile, ".png"))
png(outfile)
draw(plots_all , heatmap_legend_side  = "right")
dev.off()


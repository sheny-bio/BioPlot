# plot HRD cutoff density figure

library(showtext)
library(ggplot2)
library(RColorBrewer)

args=commandArgs(T)


file.data <- args[1]
patient_hrd <- args[2]
file.outfile <- args[3]
file.font <- args[4]

font_add("SansHans", file.font)
showtext_auto()
data <- read.table(file.data,header=T,sep="\t")


# calc cutoff
cutoff <- data[data$BRCA_status == "Deficient", ]
cutoff <- cutoff[order(cutoff$HRD, decreasing = TRUE), ]
site <- ceiling(nrow(cutoff) * 0.95)
cutoff <- cutoff$HRD[site]

data$HRD_status[data$HRD>=cutoff]="HRD_High"
data$HRD_status[data$HRD< cutoff]="HRD_Low"
data$HRD_status=factor(data$HRD,levels=c("HRD_Low","HRD_High"))

data$BRCA_status=factor(data$BRCA_status,levels=c("Intact","Deficient"))

p <- ggplot(data,aes(x=HRD,fill= BRCA_status, color= BRCA_status))+
  geom_density(aes(y= 10*..count../208),alpha=0.5) +
  geom_segment(aes(x=38, y=0, xend=38, yend=0.1), size=1.5, linetype="dotted", colour="#4472C4") +
  geom_segment(aes(x=115, y=0.108, xend=122, yend=0.108), size=1.5, linetype="dotted", color="#4472C4") +
  #geom_text(aes(x=132, y=0.108), label="HRD阳性阈值(38)", colour="black", size=3.5, family="SansHans") +
  annotate("text", x=132, y=0.108, label="HRD阳性阈值(38)", color = "black", size=3.5, family="SansHans") +


  scale_fill_manual(values =  c("#A2C4E6", "royalblue4"),labels = c("BRCA未失活", "BRCA明确失活"),name="BRCA状态") +
  scale_color_manual(values =  c("#A2C4E6", "royalblue4"),labels = c("BRCA未失活", "BRCA明确失活"),name="BRCA状态") +

  scale_x_continuous(expand = c(0, 0),limits = c(0, 145), breaks = c(0, 20, 40, 60, 80, 100, 120, 140)) +
  scale_y_continuous(expand = c(0, 0), limits = c(0, 0.125)) +

  xlab("HRD评分")+ylab("HRD值分布") +
  theme_classic() +
  theme(
    text = element_text(size=16, family="SansHans"),
    axis.title.x = element_text(size = 13),
    axis.title.y = element_text(size = 13),
    legend.title = element_blank(),
    legend.text = element_text(size = 9, colour = "#7C7976", family="SansHans"),
    legend.position = c(.965, 0.25),
    legend.justification = c("right", "top"),
    legend.box.just = "right",
    legend.margin = margin(6, 6, 6, 6)
  )



patient_hrd <- read.csv(patient_hrd, sep = "\t", stringsAsFactors = FALSE)

pre.color <- c("firebrick","#f0d43a","royalblue4","black","#057748")

for (index in c(1: dim(patient_hrd)[1])){
  hrd <- patient_hrd[index, 'HRD.sum']
  id <- patient_hrd[index, 'Sample']
  id <- unlist(strsplit(id, "-"))[1]
  color <- pre.color[index]
  seg.y <- 0.108 - (index * 0.007)

  loop_hrd <- paste0('geom_segment(aes(x = ', hrd, ', y = 0, xend = ', hrd, ', yend = 0.1), linetype="solid",colour ="', color, '",size=1.5)')
  loop_seg <- paste0('geom_segment(aes(x = 115, y = ', seg.y, ', xend = 122, yend = ', seg.y, '), size=1.5,color="', color, '")')
  # loop_text <- paste0('geom_text(aes(x=130,y=', seg.y, '),label="', id, '",color="black", size=3.5, fontface="plain")')
  loop_text <- paste0('annotate("text", x=130, y=', seg.y, ', label="', id, '", color="black", size=3.5, , family="SansHans")')

  p <- p + eval(parse(text=loop_hrd))
  p <- p + eval(parse(text = loop_seg))
  p <- p + eval(parse(text = loop_text))
}

f.pdf <- gsub("jpg", "pdf", file.outfile)
print(f.pdf)
ggsave(p, filename = f.pdf, width = 10, height = 6, dpi = 300)
try({
    jpeg(file.outfile,width=900,height=400,res=100)
    print(p)
    dev.off()
},  silent = TRUE)
#!/bin/bash

path="/mnt/ssd1/huiguo/profile/profile"
K=10
length=1
mode="eager"
keyword="time"
benchmarks="alexnet attention_is_all_you BERT_pytorch demucs densenet121 dlrm fastNLP LearningToPaint maml mnasnet1_0 mobilenet_v2 pytorch_mobilenet_v3 pytorch_stargan resnet18 resnet50 resnext50_32x4d shufflenet_v2_x1_0 squeezenet1_1 vgg16 yolov3"
summary=true
top=false


RED='\033[0;31m'
GREEN='\033[0,32m'
BLUE='\033[0,34m'
NC='\033[0m' # No Color
helpFunction()
{
   echo ""
   echo "Usage: $0 [-p]/[[-k keyword] [-m mode] [-b 'benchmarks'] [-s]/[-t size]]"
   echo -e "\t-p print the benchmarks"
   echo -e "\t-m mode: 'jit'/'eager'"
   echo -e "\t-k the keyword used to group ops, 'time'(in default) or 'calls'"
   echo -e "\t-b the benchmarks (all benchmarks in default)"
   echo -e "\t-s print the summary of aten ops and execution time (true in default)"
   echo -e "\t-t print the top K t-size aten op patterns of the benchmarks (print nothing in default)"
   exit 1 # Exit script after printing help
}
print_benchmarks()
{
  for benchmark in $benchmarks; do
    bpre=${benchmark}_${mode}_cpu_eval
    comfile=$path/$bpre/${bpre}_communities_by_$keyword.txt
    opfile=$path/$bpre/${bpre}_op_patterns_by_${keyword}_1.txt
    if [ -f $comfile -a -f $opfile ]; then 
      echo -e "${GREEN}$benchmark${NC}"
    fi
  done
}

while getopts "k:b:t:m:ph" opt
do
   case "$opt" in
      k) keyword="$OPTARG";;
      m) mode="$OPTARG";;
      b) benchmarks="$OPTARG";;
      t) top=true
         summary=false
         length="$OPTARG";;
      p) print_benchmarks
         exit 0;;
      h) helpFunction
         exit 0;;
      ?) helpFunction 
         exit -1;; # Print helpFunction in case parameter is non-existent
   esac
done

print_summary()
{
  for benchmark in $benchmarks; do
    bpre=${benchmark}_${mode}_cpu_eval
    echo -e "Benchmark ${GREEN}$benchmark${NC}"
    echo "------------------------------------"

    # print communities
    comfile=$path/$bpre/${bpre}_communities_by_$keyword.txt
    if [ -f $comfile ];then
      cat $comfile
    fi
  
    aten_calls=0
    tabfile=$path/$bpre.tab
    opfile=$path/$bpre/${bpre}_op_patterns_by_${keyword}_1.txt
    if [ -f $opfile ];then
      echo ""
      n=`cat $opfile | wc -l`
      # print total time
      k1=$((n-5))
      k2=$((n-4))
      timestr=`sed -n "${k1},${k2}p" $opfile`
      aten_time=`sed -n "${k1}p" $opfile |  sed -e "s/ Aten total time: //g" -e "s/s//"`
      model_time=`sed -n "${k2}p" $opfile | sed -e "s/Model total time: //g" -e "s/s//"`
      echo "$timestr"
      # print aten op calls
      k1=$((n-3))
      callstr=`sed -n "${k1}p" $opfile`
      echo "$callstr"
      aten_calls=`echo $callstr | cut -d ',' -f 1 | sed -e "s/Aten calls: //g" -e "s/ //g"`
    fi

    echo ""
    tabfile=$path/$bpre.tab
    realtimestr=`tail -n 1 $tabfile`
    echo $realtimestr
    realtime=`echo $realtimestr | sed -e "s/Time without profiling: //g" -e "s/s\.//g"`
    atenps=`echo "scale=2; $aten_calls/$realtime" | bc -l` 
    echo "Aten calls per second: $atenps"
    atentime1=`echo "scale=2; $aten_time/$model_time" | bc -l`
    atentime2=`echo "scale=2; $aten_time/$realtime" | bc -l`
    echo "Aten time per second: $atentime1 ~ $atentime2"
    
  done
}

print_top_patterns()
{
  for benchmark in $benchmarks; do
    bpre=${benchmark}_${mode}_cpu_eval
    echo -e "Benchmark ${GREEN}$benchmark${NC}"
    echo "------------------------------------"

    opfile=$path/$bpre/${bpre}_op_patterns_by_${keyword}_${length}.txt
    if [ -f $opfile ];then
      k=$((K+2))
      topstr=`sed -n "1,${k}p" $opfile`
      echo "$topstr"
    fi
  done
}

echo -e "${BLUE}mode=$mode${NC}"
echo -e "${BLUE}keyword=$keyword${NC}"
if [ "$summary" = true ]; then
  print_summary
  else if [ "$top" = true ]; then
    print_top_patterns
  fi
fi

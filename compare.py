from pathlib import Path
import networkx as nx
from trace_analyzer import tracegraph, kpath, profiledir
import sys, getopt

device='cpu'
phase='eval'

keyword='dur'

def print_items(items):
    print("{:>25} {:>25} {:>25} {:>25} {:>25} {:>25}".format("Aten ops", "eager time(ms)", "eager calls", "jit time(ms)", "jit calls", "eager/jit"))
    print("-------------------------------------------------------------------------------------------")
    for e_ops, j_time, j_calls, e_time, e_calls, c in items:
        if (c=='-'):
            if (j_calls!=e_calls):
                print("\033[1m{:>25} {:>25.2f} {:>25} {:>25.2f} {:>25} {:>25}\033[0m".format(e_ops, e_time/1e3, int(e_calls), j_time/1e3, int(j_calls), c))
            else:
                print("{:>25} {:>25.2f} {:>25} {:>25.2f} {:>25} {:>25}".format(e_ops, e_time/1e3, int(e_calls), j_time/1e3, int(j_calls), c))
        else:
            if (j_calls!=e_calls):
                print("\033[1m{:>25} {:>25.2f} {:>25} {:>25.2f} {:>25} {:>25.5f}\033[0m".format(e_ops, e_time/1e3, int(e_calls), j_time/1e3, int(j_calls), c))
            else:
                print("{:>25} {:>25.2f} {:>25} {:>25.2f} {:>25} {:>25.5f}".format(e_ops, e_time/1e3, int(e_calls), j_time/1e3, int(j_calls), c))

def compare(benchmark):
    basepath = Path(profiledir)
    jit_name = benchmark+'_jit_'+device+'_'+phase+'.trace'
    eager_name = benchmark+'_eager_'+device+'_'+phase+'.trace'

    ## compare aten op summary and time
    summay=''
    jit_graph = tracegraph(str(basepath/jit_name))
    eager_graph = tracegraph(str(basepath/eager_name))
    jit_nodes = jit_graph.sorted_nodes(keyword)
    #eager_nodes = eager_graph.sorted_nodes(keyword)
    items=[]
    for n, time, perf, calls in jit_nodes:
        items.append([n, time, calls])
        if n in eager_graph.graph:
            etime, ecalls = eager_graph.graph.nodes[n]['dur'], eager_graph.graph.nodes[n]['calls']
            items[-1].extend([etime, ecalls, etime/time])
            eager_graph.graph.remove_node(n)
        else:
            items[-1].extend([0, 0, '-'])

    jtime, jcalls = 0, 0
    for n in eager_graph.graph.nodes():
        etime, ecalls = eager_graph.graph.nodes[n]['dur'], eager_graph.graph.nodes[n]['calls']
        items.append([n, jtime, jcalls, etime, ecalls, '-'])

    print_items(items)

    print("\n")
    print("{:>30} {:>30} {:>30}".format("", "Eager", "jit"))
    print("-------------------------------------------------------------------------------------------")
    print("{:>30} {:>30.2f} {:>30.2f}".format("Aten time(ms)", eager_graph.aten_time/1e3, jit_graph.aten_time/1e3))
    print("{:>30} {:>30.2f} {:>30.2f}".format("Model time(ms)", eager_graph.model_time/1e3, jit_graph.model_time/1e3))
    print("{:>30} {:>30} {:>30}".format("Top layer Aten calls", eager_graph.top_aten_calls, jit_graph.top_aten_calls))
    print("{:>30} {:>30} {:>30}".format("All Aten calls", eager_graph.aten_calls, jit_graph.aten_calls))

def obtain_benchmarks():
    basepath = Path(profiledir)
    tracefiles = (entry for entry in basepath.iterdir() if entry.is_file() and entry.name.find('.trace')!=-1)

    benchmarks_jit=set()
    benchmarks_eager=set()
    for tracefile in tracefiles:
        i = tracefile.name.find('_'+device+'_'+phase)
        if (i==-1):
            continue
        name=tracefile.name[:i]
        if name.endswith('_jit'):
            benchmarks_jit.add(name[:-4])
        elif name.endswith('_eager'):
            benchmarks_eager.add(name[:-6])
    return benchmarks_jit & benchmarks_eager

def print_benchmarks():
    benchmarks=obtain_benchmarks()
    for benchmark in benchmarks:
        print(f'{benchmark}')

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hpb:",["benchmark="])
    except getopt.GetoptError:
        print("compare.py [-p]/[-b benchmark]")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("compare.py [-p]/[-b benchmark]")
            sys.exit()
        elif opt in ("-b", "--benchmark"):
            compare(arg)
        elif opt in ("-p", "--print"):
            print_benchmarks()

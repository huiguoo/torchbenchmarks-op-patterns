from pathlib import Path
import networkx as nx
from trace_analyzer import tracegraph, kpath, profiledir
import sys, getopt
import json

device='cpu'
phase='eval'

keyword='dur'
frealtime="realtime.json"

def print_items(items):
    print("{:>25} {:>25} {:>25} {:>25} {:>25}".format("Aten op", "time %", "callees per call", "calls", "time(ms)"))
    print("-------------------------------------------------------------------------------------------------------------------------------")
    for op, perc, calleespc, calls, time in items:
        print("\033[0m{:>25} {:>25.2f} {:>25.2f} {:>25} {:>25.2f}\033[0m".format(op, perc, calleespc, calls, time/1e3))

def print_benchmark_items(items):
    print("{:>25} {:>25} {:>25} {:>25} {:>25}".format("Benchmark", "time %", "callees per call", "calls", "time(s)"))
    print("-------------------------------------------------------------------------------------------------------------------------------")
    for node in items:
        benchmark, perc, calleespc, calls, time = node['benchmark'], node['perc'], node['calleespc'], node['calls'], node['time'] 
        print("\033[0m{:>25} {:>25.2f} {:>25.2f} {:>25} {:>25.2f}\033[0m".format(benchmark, perc, calleespc, calls, time/1e6))

def oplist(filename):
    ops = set()
    with open(filename) as f:
        ops = set(json.load(f))
    return ops  

def printer(benchmark):
    benchstr = benchmark+'_eager_'+device+'_'+phase
    basepath = Path(profiledir)/benchstr

    stats = {}
    with open(str(basepath/(benchstr+'_stats_by_time.json'))) as f:
        stats = json.load(f)
    
    items=[]
    for node in stats['atenops']:
        name, perc, calleespc, calls, time = node['atenop'], node['perc'], node['calleespc'], node['calls'], node['time']
        items.append([name, perc, calleespc, calls, time])

    print_items(items)
    
    with open(profiledir+'/'+frealtime) as f:
        realtime = json.load(f)

    print("\n")
    print("original aten: time={:.3f}%; callees per call={:.3f}".format(stats['atentps']*100, stats['atencallees']-1))
    return(stats['atentps']*100, stats['atencallees']-1, stats['atencps'], stats['modeltime'], realtime[benchmark])

def print_all_benchmark_stats():
    benchmarks=obtain_benchmarks()
    fnull = open('/dev/null', 'w')
    oriout = sys.stdout
    print("{:>20} {:>20} {:>20} {:>20} {:>20} {:>20}".format("benchmark", "aten time(%)", "aten callees", "aten per second", "model time(s)", "real model time(s)"))
    for benchmark in benchmarks:
        sys.stdout = fnull
        score, callees, atenps, modeltime, realmodeltime = printer(benchmark)
        sys.stdout = oriout
        print("{:>20} {:>20.3f}% {:>20.3f} {:>20.3f} {:>20.3f} {:>20.3f}".format(benchmark, score, callees, atenps, modeltime, realmodeltime))

def summary(k):
    benchmarks=obtain_benchmarks()
    atenops=[]
    for benchmark in benchmarks:
        benchstr = benchmark+'_eager_'+device+'_'+phase
        basepath = Path(profiledir)/benchstr
        with open(str(basepath/(benchstr+'_stats_by_time.json'))) as f:
            stats = json.load(f)
            for node in stats['atenops']:
                node['benchmark'] = benchmark
                atenops.append(node)

    atenops.sort(reverse=1, key=lambda x: x['perc'])

    topops = {}
    for item in atenops:
        op = item['atenop']
        if op in topops.keys():
            topops[op].append(item)
        else:
            if len(topops) == k:
                break
            else:
                topops[op] = [item]

    for op in topops.keys():
        print(("\n\033[1m{:<20}\033[0m").format(op))
        print_benchmark_items(topops[op])

def obtain_benchmarks():
    basepath = Path(profiledir)
    tracefiles = (entry for entry in basepath.iterdir() if entry.is_file() and entry.name.find('.trace')!=-1)

    benchmarks=set()
    for tracefile in tracefiles:
        i = tracefile.name.find('_'+device+'_'+phase)
        if (i==-1):
            continue
        name=tracefile.name[:i]
        if name.endswith('_eager'):
            benchmarks.add(name[:-6])
    return benchmarks

def print_benchmarks():
    benchmarks=obtain_benchmarks()
    for benchmark in benchmarks:
        print(f'{benchmark}')

def print_all_benchmark():
    benchmarks=obtain_benchmarks()
    for benchmark in benchmarks:
        print(f'\n\033[1m{benchmark}\033[0m')
        printer(benchmark)


if __name__ == "__main__":
    benchmark=""
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hpb:as:",["benchmark="])
    except getopt.GetoptError:
        print("filter.py [-p]/[-b benchmark]/[-a]/[-s K-the sumary of top K aten ops]")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("filter.py [-p]/[-b benchmark]/[-a]/[-s K - the sumary of top K aten ops]")
            sys.exit()
        elif opt in ("-b", "--benchmark"):
            benchmark=arg
            printer(benchmark)
            sys.exit() 
        elif opt in ("-p", "--print"):
            print_benchmarks()
            sys.exit() 
        elif opt == '-a':
            print_all_benchmark_stats()
            sys.exit() 
        elif opt == '-s':
            summary(int(arg))
            sys.exit() 
    print_all_benchmark()

import os, sys, json, collections
from pathlib import Path
import networkx as nx
from networkx.algorithms import community as com

profiledir="/mnt/ssd1/huiguo/test/profile"
err_threshold=1e-6

class tracegraph:
    def __init__(self, tracefile):
        G=nx.DiGraph()
        with open(tracefile) as json_file:
            data = json.load(json_file)
        pre, self.aten_time, self.clock = None, 0, 0
        for event in data:
            self.clock=max(self.clock, event['ts'])
            if event['name'].find('aten::')==-1 or event['ph']!='X':
                continue

            if event['ts']+event['dur']<self.clock-err_threshold:
                continue

            # update nodes
            name, dur = event['name'], event['dur']
            if not G.has_node(name):
                G.add_node(name, dur=dur, calls=1)
            else:
                G.nodes[name]['dur'] = G.nodes[name]['dur']+dur
                G.nodes[name]['calls'] = G.nodes[name]['calls']+dur
            self.aten_time, self.clock=self.aten_time+dur, event['ts']+dur

            # update edges    
            if pre!=None:
                if G.has_edge(pre['name'], name):
                    edata = G.get_edge_data(pre['name'], name)
                    G.add_edge(pre['name'], name, calls=edata['calls']+1, dur=edata['dur']+dur+pre['dur'])
                else:
                    G.add_edge(pre['name'], name, calls=1, dur=dur+pre['dur'])
            pre = event
        self.graph, self.model_time = G, data[-1]['ts']+data[-1]['dur']
    
    def sorted_nodes(self, keyword):
        nodes=[]
        for n in self.graph.nodes():
            nodes.append((n, self.graph.nodes[n]['dur'], self.graph.nodes[n]['dur']/self.model_time, self.graph.nodes[n]['calls']))
        if keyword=='calls':
            id=-1
        elif keyword=='dur':
            id=-3
        else:
            print("Error: set keyword to be 'calls' or 'dur'")
            return []

        nodes.sort(reverse=1, key=lambda x: x[id])
        return nodes
    
    def sorted_edges(self, keyword):
        edges=[]
        for m, n in self.graph.edges():
            time, calls = self.graph.get_edge_data(m, n)['dur'], self.graph.get_edge_data(m, n)['calls']
            edges.append((m, n, time, time/self.model_time, calls))

        if keyword=='calls':
            id=-1
        elif keyword=='dur':
            id=-3
        else:
            print("Error: set keyword to be 'calls' or 'dur'")
            return []

        edges.sort(reverse=1, key=lambda x: x[id])
        return edges
    
    def community_detection(self, keyword):
        if keyword!='calls' and keyword!='dur':
            print("Error: set keyword to be 'calls' or 'dur'")
            return []
        
        #comms = com.greedy_modularity_communities(self.graph, weight=keyword)
        comms = com.asyn_lpa_communities(self.graph, weight=keyword)
        for c in list(comms):
            print(f"Community: {c}")
        return list(comms)

class kpath:
    def __init__(self, tracefile, k):
        self.k, self.kpaths = k, {}
        self.aten_time, self.aten_calls, self.top_aten_calls = 0, 0, 0
        self.debug_last_top_aten = None
        
        with open(tracefile) as json_file:
            data = json.load(json_file)
        if self.k<=0 or self.k > len(data) or len(data)<=0:
            return

        paths, self.clock = collections.deque(), 0   
        for event in data:
            self.clock = max(self.clock, event['ts'])
            
            # skip if not aten complete event
            if event['name'].find('aten::')!=-1 and event['ph']=='X':
                self.aten_calls = self.aten_calls+1
            else:
                continue
            # skip if not at top layer
            if event['ts']+event['dur']<self.clock-err_threshold:
                continue
            self.top_aten_calls = self.top_aten_calls+1

            # count the first path if its size is k
            paths.append([0])
            if len(paths)==k+1:
                kpath=tuple(paths[0][-k:])
                time=paths[0][0]
                if kpath in self.kpaths:
                    self.kpaths[kpath] = (self.kpaths[kpath][0] + time, self.kpaths[kpath][1]+1)
                else:
                    self.kpaths[kpath] = (time, 1)
                paths.popleft()

            self.aten_time, self.clock = self.aten_time+event['dur'], event['ts']+event['dur']
            self.debug_last_top_aten = event

            for i in range(len(paths)):
                paths[i].append(event['name'])
                paths[i][0] = paths[i][0]+event['dur']

        self.model_time = data[-1]['ts']+data[-1]['dur']
    
    def sorted_kpaths(self, keyword):
        kpathlist=[]
        for p, v in self.kpaths.items(): 
            t, c = v
            kpathlist.append([p, t, t/self.model_time, c])

        if keyword=='calls':
            id=-1
        elif keyword=='dur':
            id=-2
        else:
            print("Error: set keyword to be 'calls' or 'dur'")
            return kpathlist

        kpathlist.sort(reverse=1, key=lambda x: x[id])
        return kpathlist

    def print_topKpaths(self, keyword, n): 
        if keyword!='calls' and keyword!='dur':
            print("Error: set keyword to be 'calls' or 'dur'")
            return []
        kpathlist=self.sorted_kpaths(keyword)

        n = min(n, len(kpathlist))
        topstr="Top "
        if n==len(kpathlist):
            topstr=""
        if keyword=='dur':
            keyword = 'time'
        print(f"kList({self.k}),            Time(us),                Time%,   Calls ({topstr}{n}, sorted by {keyword})")
        print("-------------------------------------------------------------")
        for i in range(n):
            print(f"{kpathlist[i][0]}, {kpathlist[i][1]}, {kpathlist[i][2]*100}%, {kpathlist[i][3]}");

        print(f"Aten total time : {self.aten_time}us")
        print(f"Model total time: {self.model_time}us")
        print(f"Aten calls: {self.aten_calls} , Top layer Aten calls: {self.top_aten_calls}\n")
        print(f"debug info:\nlast top layer aten op: {self.debug_last_top_aten}")

    def print_kpaths(self, keyword):
        self.print_topKpaths(keyword, len(self.kpaths.items())) 

def analyze():
    basepath = Path(profiledir)
    files_in_basepath = (entry for entry in basepath.iterdir() if entry.is_file())
    for item in files_in_basepath:
        if item.name.find('.trace')!=-1:
            benchmark=item.name[:-6]
            print(f"processing {item.name}")
            bmdir = basepath/benchmark
            os.makedirs(str(bmdir), exist_ok=True)

            # path of length K
            ori_stdout = sys.stdout
            for k in range(1, 11):
                kp = kpath(str(basepath/item.name), k)
                with open(str(bmdir)+'/'+benchmark+'_op_patterns_by_time_'+str(k)+'.txt', 'w') as ftab:
                    sys.stdout = ftab
                    kp.print_kpaths('dur')
                with open(str(bmdir)+'/'+benchmark+'_op_patterns_by_calls_'+str(k)+'.txt', 'w') as ftab:
                    sys.stdout = ftab
                    kp.print_kpaths('calls')
                sys.stdout = ori_stdout
            # communities
            G = tracegraph(str(basepath/item.name))
            with open(str(bmdir)+'/'+benchmark+'_communities_by_time.txt', 'w') as ftab:
                sys.stdout = ftab
                G.community_detection('dur')
            with open(str(bmdir)+'/'+benchmark+'_communities_by_calls.txt', 'w') as ftab:
                sys.stdout = ftab
                G.community_detection('calls')
            sys.stdout = ori_stdout

def test():   
    ftrace="attention_is_all_you_need_pytorch_cpu_train.trace"
    G = tracegraph(ftrace)
    G.community_detection('dur')
    
    kp = kpath(ftrace, 1)
    kp.print_topKpaths('dur', 50)

if __name__ == "__main__":
    analyze()

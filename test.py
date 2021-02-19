import torch
import numpy as np
from torch import nn
import torch.autograd.profiler as profiler

class MyModule(nn.Module):
    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super(MyModule, self).__init__()
        self.linear = nn.Linear(in_features, out_features, bias)

    def forward(self, input, mask):
        with profiler.record_function("LINEAR PASS"):
            out = self.linear(input)

        with profiler.record_function("MASK INDICES"):
            threshold = out.sum(axis=1).mean().item()
            hi_idx = np.argwhere(mask.cpu().numpy() > threshold)
            #hi_idx = torch.from_numpy(hi_idx).cuda()
            hi_idx = torch.from_numpy(hi_idx)

        return out, hi_idx


#model = MyModule(500, 10).cuda()
#input = torch.rand(128, 500).cuda()
#mask = torch.rand((500, 500, 500), dtype=torch.double).cuda()
model = MyModule(500, 10)
input = torch.rand(128, 500)
mask = torch.rand((500, 500, 500), dtype=torch.double)

# warm-up
model(input, mask)

#with profiler.profile(use_cuda=True, record_shapes=True, with_stack=True, profile_memory=False) as prof:
with profiler.profile(record_shapes=True, with_stack=True) as prof:
    out, idx = model(input, mask)


#print(prof.key_averages(group_by_stack_n=5).table(sort_by='self_cpu_time_total', row_limit=5))
print(prof.key_averages().table(sort_by='self_cpu_time_total'))
prof.export_chrome_trace("/mnt/ssd1/huiguo/test/test.trace")

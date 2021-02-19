import torch

torch.__version__

torch._C._jit_override_can_fuse_on_cpu(True)

def sigmoid(x):
        return 1 / (1 + torch.exp(-x))

script_sigmoid = torch.jit.script(sigmoid)

x = torch.randn((10, 10, 256, 3))

torch.allclose(sigmoid(x), torch.sigmoid(x))
torch.allclose(script_sigmoid(x), torch.sigmoid(x))

print('sigmoid')
#timeit sigmoid(x)

print('torch.sigmoid')
#timeit torch.sigmoid(x)

print('script_sigmoid')
warmup = [script_sigmoid(x) for i in range(4)]
#timeit script_sigmoid(x)

import pickle
import pathlib

data = []

for i in pathlib.Path(".").glob("{0}*.pickle".format("sample")):
    with open(i, "rb") as f:
        loaded = pickle.load(f)
        task = loaded["task"]
        result = pickle.loads(loaded["result"])
        data.append((len(task), result))

lengths = [10000*i for i in range(1, 10 + 1)]
agg = {l: 0 for l in lengths}
for k, v in data:
    agg[k] += v
agg = {l: agg[l]/10 for l in lengths}

print(agg)
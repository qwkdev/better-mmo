import json
import math

with open('data.json') as f:
	data = json.load(f)

n = 3

s = math.ceil(len(data)/n)
for i in range(n):
	with open(f'data{i+1}.json', 'w') as f:
		json.dump({k: data[k] for k in list(data.keys())[i*s:(i+1)*s]}, f, indent=4)
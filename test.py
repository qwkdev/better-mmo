import json

with open('data.json') as f:
	data = json.load(f)

m = {k: v['id'] for k, v in data.items()}

with open('map.json', 'w') as f:
	json.dump(m, f, indent=4)
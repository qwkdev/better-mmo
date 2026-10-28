# import json

import requests as rq
from bs4 import BeautifulSoup

URL = 'https://mymusiconline.co.uk/'

# TODO: Errors; Higher Diminished triad: Table -> /404, List -> /diminished-7th-2
# TODO: Tables Images (triplets) Links in desc (harmonics)
def concept(cid: str) -> dict:
	r = rq.get(URL+cid).content
	soup = BeautifulSoup(r, 'html.parser')
	resp = {}

	resp['name'] = soup.select_one('h1.entry-title.post-title').text
	content = soup.select_one('div.entry-content')
	children = [i for i in content.children if i.name == 'p' and i.text.replace('\xa0', '')]

	rm = []
	for n, i in enumerate(children):
		if (header := i.select_one('strong span')) and header.text == 'Related Concepts':
			if resp.get('rel') is None: resp['rel'] = []
			resp['rel'].extend([j['href'].split(URL)[1] for j in i.select('a')])
			rm.append(n)
		if i.select_one('span a'):
			rm.append(n)
	
	resp['desc'] = '\n'.join([i.text for n, i in enumerate(children) if n not in rm])
	if (audio := content.select_one('audio source')):
		resp['audio'] = audio['src'].split('?')[0]
	return resp

print(concept(input()))
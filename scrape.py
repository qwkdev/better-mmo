import json
import os
import re
import time

import requests as rq
from bs4 import BeautifulSoup, NavigableString, Tag

URL = 'https://mymusiconline.co.uk/'

def get(path: str):
	return BeautifulSoup(rq.get(URL+path).content, 'html.parser')

def ansiml(markup: str) -> str:
	ctx: list[str] = []
	in_tag: bool = False
	t: str = ''
	r: str = ''
	for n, c in enumerate(markup):
		if in_tag:
			if c == '>':
				in_tag = False

				if t[0] == '/':
					if t[1:] in [i[0] for i in ctx]:
						ctx.pop(len(ctx) - 1 - [i[0] for i in ctx[::-1]].index(t[1:]))
					r += f"\033[{';'.join(['0', *[i[1] for i in ctx]])}m"
				else:
					ac: str = {'red': '31', 'orange': '33', 'yellow': '33', 'green': '32', 'blue': '34', 'dark-blue': '34', 'dblue': '34', 'purple': '35', 'magenta': '35', 'pink': '35', 'cyan': '36', 'lblue': '36', 'light-blue': '36', 'grey': '37', 'gray': '37', 'black': '30', 'dark': '30', 'bold': '1', 'strong': '1', 'b': '1', 'em': '1', 'dim': '2', 'i': '3', 'italic': '3', 'u': '4', 'underline': '4', 'blink': '5', 'flash': '5', 'invert': '7', 'hidden': '8', 's': '9', 'strike': '9', 'strikethrough': '9'
					}.get(t.split(' ', 1)[0], t.split(' ', 1)[0])

					if t.endswith(('bg', 'background')) and ac[0] == '3':
						if len(ac) == 2:
							ac = f'4{ac[1]}'
						elif ac[1] == '8':
							ac = f'4{ac[1:]}'
					r += f'\033[{ac}m'
					ctx.append([t.split(' ', 1)[0], ac])
				t = ''
			else:
				t += c
		else:
			if c == '<' and ('' if n == 0 else markup[n-1]) != '\\':
				in_tag = True
				r += t
				t = ''
			else:
				t += c

	if not in_tag: r += t
	return f'{r}\033[0m'

ctst = 0
cur_task: str | None = None
def task(name: str | None=None, update: str | None=None) -> None:
	global cur_task, ctst

	if update:
		print(ansiml(f"\r{' '*(os.get_terminal_size()[0])}\r<dark>[{time.strftime('%H:%M:%S')}] {cur_task}... ({update})</dark>"), end='', flush=True)
		return

	if cur_task is not None:
		print(ansiml(f"\r{' '*(os.get_terminal_size()[0])}\r<green>[{time.strftime('%H:%M:%S')}] {cur_task}</green> <dark>[{round(time.perf_counter()-ctst, 3)}s]</dark>"))

	if name is None:
		cur_task = None
		return

	cur_task, ctst = name, time.perf_counter()
	print(ansiml(f"<dark>[{time.strftime('%H:%M:%S')}] {name}...</dark>"), end='', flush=True)

def parse_url(url: str) -> str:
	# Assuming url is a concept
	return '/c/' + url.split(URL)[1]

def parse_desc(ele) -> list:
	if ele.name == 'table':
		table = []
		for row in ele.select('tr'):
			temp = []
			for c in row.select('td'):
				if (img := c.select_one('img')):
					temp.append(['image', img['src']])
				else:
					temp.append(c.text.replace('\xa0', ''))
			table.append(temp)
		return [['table', table]]
	if ele.name == 'audio':
		if not (src := ele.get('src')): src = ele.select_one('source')['src']
		return [['audio', src.split('?')[0]]]

	resp = []
	for i in ele.contents:
		if isinstance(i, Tag):
			if i.name in ['span', 'strong', 'em', 'table', 'audio']:
				resp.extend(parse_desc(i))
				continue

			match i.name:
				case 'a': resp.append(['link', parse_url(i['href']), i.text.replace('\xa0', '')])
				# case 'source': resp.append(['audio', i['src'].split('?')[0]])
				case 'img': resp.append(['image', i['src']])
				case 'br':
					if resp and isinstance(resp[-1], str):
						resp[-1] += '\n'
				case _: raise TypeError('Unknown tag:', i)
		elif isinstance(i, NavigableString): resp.append(i.text.replace('\xa0', ''))
		else: raise TypeError('Unknown element:', i)
	return resp

def flatten(s: str, *delim: str) -> str:
	for d in delim: s = d.join(i for i in s.split(d) if i)
	return s

def concept(cid: str) -> dict:
	soup = get(cid)
	resp = {}

	if soup.find(id='404'):
		raise ValueError('Error 404 -', cid)

	resp['name'] = soup.select_one('h1.entry-title.post-title').text
	content = soup.select_one('div.entry-content')
	children = [i for i in content.children if (i.name == 'p' and i.text.replace('\xa0', '')) or i.name in ['audio', 'table']]

	rm = []
	for n, i in enumerate(children):
		if (header := i.select_one('strong span')) and header.text == 'Related Concepts':
			if resp.get('rel') is None: resp['rel'] = []
			resp['rel'].extend([j['href'].split(URL)[1] for j in i.select('a')])
			rm.append(n)
		if (link := i.select_one('span a')) and link.text.startswith('Back to ') and link.text.endswith(' Music'):
			rm.append(n)
	
	parsed = [parse_desc(i) for n, i in enumerate(children) if n not in rm]
	resp['desc'] = []
	
	for p in parsed:
		new_loop = True
		for i in p:
			if isinstance(i, str) and resp['desc'] and isinstance(resp['desc'][-1], str):
				resp['desc'][-1] += ('\n' if new_loop else '')+i
			else: resp['desc'].append(i)
			new_loop = False
	resp['desc'] = [flatten(i, '\n', ' ', '\n') if isinstance(i, str) else i for i in resp['desc']]

	resp['id'] = '-'.join(i for i in re.sub(r'[^0-9a-z\s-]', '',
		resp['name'].lower()
			.replace('/', ' ')
			.replace('è', 'e')
			.replace('(voice)', 'v')
	).split(' ') if i)
	return resp

def get_concepts(path: str) -> set[str]:
	return {fixid.get(i['href'].split(URL)[1], i['href'].split(URL)[1]) for i in get(path).select('td a')}

fixlevel = {
	'legato': ['n3'],
	'off-the-beat': ['n3'],
	'tuned-percussion': ['n4'],
	'untuned-percussion': ['n4'],
	'mezzo-forte': ['n5'],
	'mezzo-piano': ['n5'],
}
fixid = {
	'penatonic': 'pentatonic',
	'gospel': 'gospel-2',
	'diminished-triad': 'diminished-7th-2'
}
def get_all_concepts() -> dict[str, list[str]]:
	resp = {'n3': [], 'n4': [], 'n5': [], 'h': [], 'ah': []}
	table = get('a-z-concepts-list-2').select_one('tbody')
	for row in table.select('tr')[1:]:
		c = row.select_one('a')['href'].split(URL)[1]
		c = fixid.get(c, c)
		for k in (fixlevel[c] if c in fixlevel else [i.text for i in row.select('td:not(.has-text-align-left)') if i.text]):
			resp[k.lower()].append(c)
	resp = {k: set(v) for k, v in resp.items()}
	return resp

conceptnames = {
	'n3': 'national-3-concepts',
	'n4': 'national-4-concepts',
	'n5': 'national-5-concepts',
	'h': 'music-concepts-higher',
	'ah': 'advanced-higher-concepts'
}

task('Loading concept lists')
conceptlist = get_all_concepts()
for c, path in conceptnames.items():
	conceptnames[c] = sorted(get_concepts(path) | conceptlist[c])

concepts = {}
for k, v in conceptnames.items():
	for c in v:
		if c not in concepts: concepts[c] = k
		else: 
			if not isinstance(concepts[c], list):
				concepts[c] = [concepts[c]]
			concepts[c].append(k)

lc = max(*[len(i) for i in concepts])
cl = len(concepts.keys())
task('Scraping')
for n, (k, v) in enumerate(concepts.items()):
	task(update=f'{k:>{lc}} [{n:>{len(str(cl))}}/{cl}]')
	concepts[k] = {'levels': v, **concept(k)}

	with open('data.json', 'w') as f:
		json.dump(concepts, f, indent=4)

task()

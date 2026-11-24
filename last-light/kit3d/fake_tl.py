"""Placeholder tl.json from script.json (word timings guessed) so a scene can be laid out before the voice exists."""
import json, sys
d = sys.argv[1]; num, author = sys.argv[2], sys.argv[3]
s = json.load(open(f'{d}/script.json')); t = 0.3; lines = {}
for l in s:
    words = []
    for w in l['text'].split():
        dur = 0.36 + 0.3 * w.endswith(('.', '...', ',')); words.append([w, t, t + dur - 0.05]); t += dur
    lines[l['id']] = {'start': words[0][1], 'end': words[-1][2], 'words': words}; t += 0.5
end = t + 0.8
json.dump({'lines': lines, 'end': end + 3, 'cardAt': end, 'channel': 'LAST LIGHT',
           'credit': [f'Based on SCP-{num} by {author}', f'scp-wiki.wikidot.com/scp-{num}', 'Licensed CC BY-SA 3.0']}, open(f'{d}/tl.json', 'w'))
print(round(end + 3, 1))

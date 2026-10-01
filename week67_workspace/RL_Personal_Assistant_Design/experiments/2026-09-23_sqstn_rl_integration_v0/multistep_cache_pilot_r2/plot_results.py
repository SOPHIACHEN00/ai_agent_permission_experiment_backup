"""Generate two exact descriptive SVGs from verified results; no ML execution."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
proof = json.loads((HERE/'comparison_verification.json').read_text(encoding='utf-8'))
assert proof['status'] == 'PASS'
rows = proof['per_seed']
evaluation = [json.loads(s) for s in (HERE/'server_evidence/unpacked/run/evaluation.jsonl').read_text(encoding='utf-8').splitlines()]
output = HERE/'analysis-output/figures'
output.mkdir(parents=True, exist_ok=True)
names = {'ddqn_b': 'DDQN B', 'wp_fts_public_transfer_v0': 'MAB WP-FTS', 'fixed_rule': 'Fixed rule'}
colors = {'ddqn_b': '#0072B2', 'wp_fts_public_transfer_v0': '#009E73', 'fixed_rule': '#555555'}


def element(parent, tag, **attrs):
    return ET.SubElement(parent, tag, {k.replace('_','-'): str(v) for k,v in attrs.items()})


def label(parent, x, y, value, **attrs):
    element(parent, 'text', x=x, y=y, **attrs).text = str(value)


def canvas(title):
    root = ET.Element('svg', {'xmlns':'http://www.w3.org/2000/svg', 'width':'960', 'height':'470',
                             'viewBox':'0 0 960 470', 'font-family':'Arial, sans-serif', 'font-size':'16'})
    element(root, 'rect', width=960, height=470, fill='white')
    label(root, 25, 32, title, font_size=21, font_weight='bold')
    return root


main = canvas('Task completion: both fixed learner seeds, same four dev scenarios')
for tick in (0,.25,.5,.75,1):
    x = 220 + 500*tick
    element(main, 'line', x1=x, x2=x, y1=65, y2=380, stroke='#dddddd')
    label(main, x, 408, f'{tick:.0%}', text_anchor='middle')
for i,row in enumerate(rows):
    y = 88+i*49
    label(main, 25, y+20, f"{names[row['method']]} / {row['seed']}")
    width = 500*row['success_rate']
    element(main, 'rect', x=220, y=y, width=width, height=28, fill=colors[row['method']])
    label(main, 232+width, y+20, f"{row['successes']}/4")
label(main, 25, 448, 'Individual runs shown; no CI, significance markers, smoothing or hidden seeds.', font_size=14)
ET.ElementTree(main).write(output/'01-success-by-seed.svg', encoding='utf-8', xml_declaration=True)

matrix = canvas('Where completion fails: fixed dev scenario breakdown')
families = ('continuous','once','scope_denial','disable_refresh')
short = ('Continuous','Once','Scope refusal','Disable/refresh')
for j,name in enumerate(short):
    label(matrix, 280+j*158, 73, name, text_anchor='middle', font_size=15)
for i,row in enumerate(rows):
    y=91+i*49
    label(matrix, 25, y+23, f"{names[row['method']]} / {row['seed']}")
    for j,family in enumerate(families):
        selected = [r for r in evaluation if r['method']==row['method'] and r['seed']==row['seed'] and r['family']==family]
        assert len(selected)==1
        value=int(selected[0]['task_success'])
        element(matrix, 'rect', x=218+j*158, y=y, width=124, height=33,
                fill='#0072B2' if value else '#eeeeee', stroke='#aaaaaa')
        label(matrix, 280+j*158, y+23, value, text_anchor='middle', fill='white' if value else '#222222')
label(matrix,25,420,'1 = completed both protected steps; 0 = not completed (including safe refusal).',font_size=14)
label(matrix,25,448,'Each cell is a fixed scenario outcome, not an independent human participant.',font_size=14)
ET.ElementTree(matrix).write(output/'02-scenario-breakdown.svg', encoding='utf-8', xml_declaration=True)
for path in output.glob('*.svg'):
    ET.parse(path)
print(json.dumps({'svg_figures':2,'source':'comparison_verification.json','individual_seeds':2,'dev_graphs':4}))

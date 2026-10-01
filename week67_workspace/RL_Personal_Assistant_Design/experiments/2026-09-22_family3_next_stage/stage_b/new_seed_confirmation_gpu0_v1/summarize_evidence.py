"""Small descriptive analysis and dependency-free SVGs; no model execution."""
from __future__ import annotations

import csv
import hashlib
import json
from fractions import Fraction
from html import escape
from math import comb
from pathlib import Path
from statistics import stdev

HERE = Path(__file__).resolve().parent
OUT = HERE / 'analysis-output'
COLORS = ('#0072B2', '#D55E00', '#009E73')
SEEDS = (401, 503, 607)


def interval(k: int, n: int) -> list[float]:
    """Marginal two-sided 95% Clopper-Pearson interval for seed-win probability."""
    def solve(cdf, level):
        low, high = 0.0, 1.0
        for _ in range(80):
            middle = (low + high) / 2
            if cdf(middle) < level:
                low = middle
            else:
                high = middle
        return (low + high) / 2
    tail = lambda p, first: sum(comb(n, j) * p**j * (1-p)**(n-j) for j in range(first, n+1))
    return [0.0 if k == 0 else solve(lambda p: tail(p, k), .025),
            1.0 if k == n else solve(lambda p: tail(p, k+1), .975)]


def plot(name: str, labels: list[str], seed_values: list[list[float]],
         refs: list[float], upper: float, connect: bool, means: list[float] | None = None) -> None:
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="520" viewBox="0 0 1000 520">',
             '<rect width="1000" height="520" fill="white"/>',
             '<g font-family="Segoe UI,Arial,sans-serif" fill="#17212b">']
    def text(x, y, label, size=15, anchor='start'):
        parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">{escape(label)}</text>')
    def line(x1, y1, x2, y2, color, dash=''):
        parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
    ymap = lambda value: 415 - value / upper * 350
    xs = [125 + 600*j/(len(labels)-1) for j in range(len(labels))]
    for j in range(5):
        value = upper*j/4
        line(80, ymap(value), 765, ymap(value), '#e1e5e9')
        text(65, ymap(value)+5, f'{value:.2f}', anchor='end')
    line(80, 65, 80, 415, '#64748b')
    text(80, 30, 'Exact validation success probability', 20)
    text(795, 75, 'Training seed', 15)
    for i, (values, color, seed) in enumerate(zip(seed_values, COLORS, SEEDS)):
        shifted = [x + (i-1)*12 for x in xs]
        if connect:
            for j in range(len(labels)-1):
                line(shifted[j], ymap(values[j]), shifted[j+1], ymap(values[j+1]), color, '4 3')
        for x, value in zip(shifted, values):
            assert 0 <= value <= upper
            y = ymap(value)
            if i == 0:
                marker = f'<circle cx="{x}" cy="{y}" r="5"'
            elif i == 1:
                marker = f'<rect x="{x-5}" y="{y-5}" width="10" height="10"'
            else:
                marker = f'<polygon points="{x},{y-6} {x-6},{y+5} {x+6},{y+5}"'
            parts.append(marker + f' fill="{color}"><title>Seed {seed}: {value:.6f}</title></'+('circle' if i == 0 else 'rect' if i == 1 else 'polygon')+'>')
        text(795, 104+i*25, f'{seed}  (color + shape)', 14)
        parts.append(f'<rect x="965" y="{94+i*25}" width="10" height="10" fill="{color}"/>')
    if len(set(refs)) == 1:
        line(80, ymap(refs[0]), 765, ymap(refs[0]), '#687280', '6 4')
        text(795, 208, f'DP optimum {refs[0]:.4f}', 14)
    else:
        for x, value in zip(xs, refs):
            line(x-40, ymap(value), x+40, ymap(value), '#17212b', '6 4')
        text(795, 208, 'Dashed: cell DP optimum', 14)
    if means:
        for x, value in zip(xs, means):
            y = ymap(value)
            parts.append(f'<polygon points="{x},{y-7} {x+7},{y} {x},{y+7} {x-7},{y}" fill="#17212b"/>')
        text(795, 238, 'Black diamond: mean', 14)
    for x, label in zip(xs, labels):
        for k, segment in enumerate(label.split('|')):
            text(x, 440+k*19, segment, 14, 'middle')
    text(80, 498, 'All three new seeds shown; no smoothing/error bars. Fixed candidate, reused validation graphs; not test.', 13)
    parts.append('</g></svg>')
    (OUT/'figures'/name).write_text('\n'.join(parts), encoding='utf-8')


def main() -> None:
    verification = json.loads((HERE/'postflight_verification.json').read_text(encoding='utf-8'))
    assert verification['status'] == 'PASS'
    (OUT/'figures').mkdir(parents=True, exist_ok=True)
    summaries = verification['summaries']
    stats = []
    for row in summaries:
        values = list(row['seed_values'].values())
        diffs = list(row['paired_improvements'].values())
        item = {'config': row['config_id'], 'n_seeds': 3, 'mean': row['mean_value_decimal'],
                'sample_sd': stdev(values), 'paired_mean_change': sum(diffs)/3,
                'paired_changes': diffs}
        if row is not summaries[0]:
            wins, n = sum(x > 0 for x in diffs), sum(x != 0 for x in diffs)
            p = min(1., 2*sum(comb(n, j) for j in range(min(wins, n-wins)+1))/2**n)
            item.update(wins=wins, losses=sum(x<0 for x in diffs), ties=sum(x==0 for x in diffs), non_tied_pairs=n, sign_test_p=p,
                        marginal_non_tied_seed_win_probability_95ci=interval(wins, n))
        stats.append(item)
    ordered = sorted(stats[1:], key=lambda r: r['sign_test_p'])
    previous = 0.
    for rank, row in enumerate(ordered):
        previous = max(previous, min(1., (len(ordered)-rank)*row['sign_test_p']))
        row['holm_adjusted_p'] = previous
    (OUT/'descriptive_statistics.json').write_text(json.dumps({'statistics': stats,
        'inference_caveat': 'Fixed candidate chosen before these seeds. Direction-only sign/CI assume independent representative seed pairs and exclude ties. CI concerns conditional win probability among non-tied pairs, not mean policy value/gain. n=3 on reused validation graphs does not establish broad population or held-out test generalization.'}, indent=2)+'\n', encoding='utf-8')
    seeds = SEEDS
    plot('figure-01-paired-seeds.svg', ['A: lr .001|update every 4', 'B: lr .0003|update every 4'],
         [[r['seed_values'][str(seed)] for r in summaries] for seed in seeds], [.7075]*2, .8, True,
         [r['mean_value_decimal'] for r in summaries])
    with (HERE/'exact_values.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = [r for r in csv.DictReader(stream) if r['config_id']=='b_lr3e4_every4']
    coords = [('br05','original'), ('br05','prompt_toggle'), ('br06','original'), ('br06','prompt_toggle')]
    lookup = {(int(r['seed']),r['graph_id'],r['condition']):float(Fraction(r['value'])) for r in rows}
    plot('figure-02-fixed-candidate-cells.svg', ['br05|original','br05|prompt_toggle','br06|original','br06|prompt_toggle'],
         [[lookup[seed,g,c] for g,c in coords] for seed in seeds], [.5,.6,.93,.8], 1., False)
    import xml.etree.ElementTree as ET
    for path in (OUT/'figures').glob('*.svg'):
        ET.parse(path)
    print(json.dumps({'status':'PASS','figures':2,'statistics':stats}))


if __name__ == '__main__':
    main()

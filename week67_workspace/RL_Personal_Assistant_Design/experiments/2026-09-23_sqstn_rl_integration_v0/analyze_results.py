"""Descriptive two-seed engineering analysis; no new experiments or inference."""
from collections import defaultdict
import hashlib
from html import escape
import json
from pathlib import Path
from statistics import mean, stdev
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent


def main():
    verification = json.loads((HERE/'postflight_verification.json').read_text())
    assert verification['status'] == 'PASS'
    run = HERE/'server_evidence/unpacked/run'
    evaluation = [json.loads(line) for line in (run/'evaluation.jsonl').read_text().splitlines()]
    groups = json.loads((run/'training_groups.json').read_text())
    output = HERE/'analysis-output'
    figures = output/'figures'
    figures.mkdir(parents=True, exist_ok=False)
    methods = ('ddqn_b', 'wp_fts_public_transfer_v0', 'fixed_rule')
    names = ('DDQN B', 'WP-FTS transfer', 'Fixed rule')
    per_seed = verification['per_seed']
    stats = {}
    for method in methods:
        subset = [row for row in per_seed if row['method'] == method]
        rates = [row['success_rate'] for row in subset]
        stats[method] = {'seeds': [row['seed'] for row in subset], 'values': rates,
                         'mean': mean(rates), 'sample_sd': stdev(rates), 'min': min(rates), 'max': max(rates),
                         'episodes_per_seed': 8, 'successes': sum(row['successes'] for row in subset),
                         'requests': sum(row['requests'] for row in subset),
                         'ci95': None, 'p_value': None, 'inference': 'NOT_SUPPORTED_BY_TWO_SEED_FIXED_FIXTURE_PILOT'}
    traces = verification['dev_action_traces']
    identical = all(traces[f'wp_fts_public_transfer_v0_seed{seed}_dev{case}'] == traces[f'fixed_rule_seed{seed}_dev{case}']
                    for seed in (1301,1601) for case in range(8))
    assert identical
    all_stats = {'methods': stats, 'ddqn_minus_mab_percentage_points': [0,-50],
                 'paired_mean_difference_percentage_points': -25, 'mab_rule_all_dev_action_traces_equal': identical,
                 'scientific_unit': 'two training seeds on the same fixed eight development cases; not 48 independent samples',
                 'test_opened': False, 'live_api': False,
                 'source_hashes': {name: hashlib.sha256((run/name).read_bytes()).hexdigest()
                                   for name in ('evaluation.jsonl','training_groups.json','completion.json','config.json')}}
    (output/'statistics.json').write_text(json.dumps(all_stats, indent=2), encoding='utf-8')
    def svg_start(w,h,title):
        return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                f'<title>{escape(title)}</title><rect width="100%" height="100%" fill="white"/>',
                '<g font-family="Arial,sans-serif" font-size="14" fill="#202020">']
    def text(parts,x,y,label,extra=''):
        parts.append(f'<text x="{x}" y="{y}" {extra}>{escape(str(label))}</text>')
    parts = svg_start(820,365,'Fixture task completion by training seed; no population inference')
    text(parts,25,28,'Fixed synthetic dev cases: task completion by seed')
    for tick in range(5):
        x = 205 + tick*130
        parts.append(f'<line x1="{x}" y1="52" x2="{x}" y2="290" stroke="#dddddd"/>')
        text(parts,x,315,f'{tick*25}%', 'text-anchor="middle"')
    for index, (method,name) in enumerate(zip(methods,names)):
        y = 82+index*77
        text(parts,20,y+14,name)
        for j, (seed,color) in enumerate(((1301,'#0072B2'),(1601,'#E69F00'))):
            value = stats[method]['values'][j]
            width = value*520
            yy = y+j*27
            parts.append(f'<rect x="205" y="{yy-12}" width="{width}" height="19" fill="{color}"/>')
            text(parts,215+width,yy+3,f'{seed}: {int(value*8)}/8')
    text(parts,25,346,'Every seed is shown; zero length = 0. No CI/error bars: only two fixed-fixture runs.')
    parts.append('</g></svg>')
    (figures/'figure-01-seeds.svg').write_text('\n'.join(parts),encoding='utf-8')
    parts = svg_start(950,415,'Task completion by case and method-seed; 0 does not imply unsafe behavior')
    text(parts,20,25,'Per-case completion (1 = completed, 0 = not completed)')
    columns = [(method,seed) for method in methods for seed in (1301,1601)]
    for j,(method,seed) in enumerate(columns):
        text(parts,335+j*98,53,f'{("DDQN","MAB","Rule")[j//2]} {seed}','text-anchor="middle"')
    lookup = {(row['method'],row['seed'],row['case_index']):row for row in evaluation}
    for i in range(8):
        y = 70+i*34
        case_name = lookup[('ddqn_b',1301,i)]['scenario_id'].removeprefix('sqstn_v0_dev_')
        text(parts,20,y+19,case_name)
        for j,(method,seed) in enumerate(columns):
            value = int(lookup[(method,seed,i)]['task_success'])
            color = '#0072B2' if value else '#e5e5e5'
            parts.append(f'<rect x="{290+j*98}" y="{y}" width="90" height="29" fill="{color}"/>')
            text(parts,335+j*98,y+20,value,f'text-anchor="middle" fill="{"white" if value else "#202020"}"')
    text(parts,20,373,'Four denial-bearing cases cannot complete through the declared consent path; safe exit is still task reward 0.')
    text(parts,20,398,'disable_refresh is a fixture name: evaluated policies did not choose disable; lifecycle is checked separately.')
    parts.append('</g></svg>')
    (figures/'figure-02-cases.svg').write_text('\n'.join(parts),encoding='utf-8')
    for path in figures.glob('*.svg'):
        ET.parse(path)
    table = '| Method | Seed1301 | Seed1601 | Mean ± sample SD | Requests /16 episodes |\n|---|---:|---:|---:|---:|\n'
    for method,name in zip(methods,names):
        row = stats[method]
        table += f'| {name} | {row["values"][0]:.3f} | {row["values"][1]:.3f} | {row["mean"]:.3f} ± {row["sample_sd"]:.3f} | {row["requests"]} |\n'
    analysis = '''# S-QSTN–RL v0 descriptive engineering analysis

Question: Does the fixed-response public interface work with all three controllers,
and what behavior appears at the predeclared tiny budget? Primary performance
metric: environment task-completion rate (higher better), not permission-label accuracy.
Evidence provenance: statistics.json hashes; postflight_verification.json PASS.
Unit: two seeds per learned method on the same eight fixed dev cases. The48rows
are not48independent repetitions. No parameter/seed selection or test data.

'''+table+'''
## Observations and limits

- Engineering pass:4800transitions,48evaluations,4checkpoints,2451verified chain pairs;
  invalid actions/unauthorized effects/adapter faults all0. API calls0.
- DDQN seed1301 completes4/8 but asks23times; on deny_reask it repeatedly asks until
  horizon8, also after the second answer in once_then_deny. This is mask-legal
  yet undesirable behavior; zero hard violations is not permission etiquette.
- DDQN seed1601 completes0/8, asks0times and immediately DENY_WITH_REASON in all8.
  Training also has0successful episodes (versus71for1301): missing positive task
  feedback is observed here, but no causal training diagnosis was performed.
- Both MAB runs and the rule complete4/8,11requests/seed. Their full public action
  sequences match for all16matched dev cases, consistent with the fixed mapping
  dominating this easy fixture set; not proof of equivalent learned values.
- Four cases contain denial and retain task reward0 even for safe fallback. Do not
  relabel that as task success or interpret50%as50%unsafe decisions.
- B is hyperparameter transfer to a newly initialized31-state/16-candidate-feature
  model, not reuse of the old18-dimensional checkpoint.237updates/seed do not reach
  target sync250. This is not a convergence-budget comparison.
- MAB predicts four responses but deny_reask/once/reuse share the initial request
  mapping; its joint-label objective differs from DDQN task reward. This is a
  system-level adapter comparison, not a matched long-term credit ablation.
- The fixture named disable_refresh is not an exogenous disable intervention.
  No evaluated controller selected disable. Separate interface test covers the
  disable->refresh lifecycle; no learned-recovery claim is permitted.

## Claim Candidates

- Claim: offline fixed-response wiring is verified for this frozen pilot.
  - Source evidence: postflight receipt, interface/CUDA outputs and frozen bundle.
  - Allowed wording: the bounded fixture pipeline completed with the recorded audits.
  - Forbidden stronger wording: live S-QSTN, general agent safety or RL superiority proved.
  - Uncertainty: no live API, short synthetic tasks, limited sampled paths.
  - Next check: up to4authorized live permission answers, no extra training.
  - Decision: keep.
- Claim: DDQN is seed-sensitive at this engineering budget.
  - Source evidence: all16DDQN dev rows and2400DDQN training steps.
  - Allowed wording: observed4/8versus0/8; no seed discarded.
  - Forbidden stronger wording: DDQN is generally inferior or B no longer helps.
  - Uncertainty: n2, new task/schema, tiny update budget and unmatched learning objectives.
  - Next check: inspect saved coverage before designing any separate learning study.
  - Decision: keep as descriptive only.
'''
    (output/'analysis-report.md').write_text(analysis,encoding='utf-8')
    appendix = '''# Statistical appendix

'''+table+'''
All values are completion fractions across the same8fixed synthetic cases. Sample
SD describes only variation between the two training seeds; zero MAB/rule SD is
not evidence of population stability. DDQN range[0,.5]; MAB/rule range[.5,.5].
Paired DDQN-minus-MAB and DDQN-minus-rule differences are[0,-.5], mean-.25
(-25percentage points). MAB-minus-rule difference is0for both seeds.

No confidence interval or significance test is reported: n2cannot support a useful
normality check, fixtures were engineered rather than randomly sampled, and the
budget targets plumbing rather than performance inference. No multiple-comparison
claim is made; correction is therefore not applicable. Do not treat16episodes per
method or48rows as independent binomial draws. No bootstrap illusion or best-seed selection.

MAB label feedback is a separate online-training statistic:214/545and208/544correct
actual-request predictions (about39.27%and38.24%). It cannot be compared with old
51.083%survey performance or with task completion. No feedback when no question.

No old0.05regret gate is passed or redefined. Original five-seed B result stays
mean.545,near-optimal0/5; this separate integration has no DP/regret certificate.
'''
    (output/'stats-appendix.md').write_text(appendix,encoding='utf-8')
    catalog = '''# Figure catalog

## figure-01-seeds.svg

Purpose: expose seed dependence rather than hide it inside a pooled rate.
Source: verified48-row evaluation, summarized into six method-seed values.
Axes: completion percentage0–100, method; each colored bar is one labeled seed.
No error bars, CI or significance markers; individual values are shown, not smoothed.
Observation: DDQN goes4/8to0/8; MAB and rule stay4/8. Decision: no superiority claim,
no best-seed promotion or automatic retraining from this engineering pilot.

## figure-02-cases.svg

Purpose: separate shared refusal-related noncompletion from DDQN-specific losses.
Rows:eightcases; columns:method×seed; cells actual task-completion0/1, not safety.
Observation: four denial-bearing rows are0for all; DDQN1601also loses all allowing
rows. Decision: do not count safe refusal as a software fault or relax success rules.
disable_refresh label does not prove a disable intervention actually occurred.

Files are reproducible SVGs from analyze_results.py, XML parsed successfully.
Internal exploratory figures only; no claim of publication/visual QA certification.
'''
    (output/'figure-catalog.md').write_text(catalog,encoding='utf-8')
    print(json.dumps({'analysis': 'COMPLETE_DESCRIPTIVE_ONLY', 'methods': stats,
                      'figures': 2, 'mab_rule_actions_equal': identical}))


if __name__ == '__main__':
    main()

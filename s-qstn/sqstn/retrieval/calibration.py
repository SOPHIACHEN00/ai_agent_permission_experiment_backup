"""Reference-only population calibration; never reads evaluator GT or targets."""
import hashlib
import json
from copy import deepcopy
import math

import numpy as np
from scipy.optimize import linprog

from .population import PROFILE_WEIGHTS
from sqstn.core.runtime import LABELS

PROFILES = tuple(PROFILE_WEIGHTS)
SEED = 'sqstn24-calibration-42'
# Never / No once / Yes once / Always. Soft tendencies, not respondent classes.
AFFINITY = np.array([[.5, .6, 1., 4.], [.5, 2., 3., .5], [4., 2., .7, .3]])


def reference_distribution(evidence: dict) -> np.ndarray | None:
    cases = evidence['cases']
    if not cases:
        return None
    exact = [c for c in cases if c['exact']]
    selected = exact or cases
    weights = np.array([1. if exact else max(c['similarity'], 0.) ** 2 for c in selected])
    if weights.sum() <= 0:
        return None
    return np.average(np.array([c['shares'] for c in selected]), axis=0, weights=weights)


def conditioned_distributions(shares: list[float], power: float = 1.) -> np.ndarray:
    """IPF preserves all-population frequencies while expressing soft tendencies."""
    p = np.asarray(shares, dtype=float)
    if p.shape != (4,) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1):
        raise ValueError('Expected four nonnegative shares summing to one')
    if not math.isfinite(power) or not 0 <= power <= 4:
        raise ValueError('Affinity power must be between zero and four')
    w = np.array(list(PROFILE_WEIGHTS.values()))
    joint = w[:, None] * p[None, :] * AFFINITY ** power
    for _ in range(1000):
        joint *= (w / joint.sum(axis=1))[:, None]
        columns = joint.sum(axis=0)
        joint *= np.divide(p, columns, out=np.zeros(4), where=columns > 0)[None, :]
        if np.max(np.abs(joint.sum(axis=1) - w)) < 1e-12:
            break
    else:
        raise ValueError('Conditional distribution did not converge')
    return joint / w[:, None]


def recommend(evidence: dict, profile: str, case_id: str, *, sample_id: str = '0',
              power: float = 1., policy: str = 'anchored', choice_multipliers: list[float] | None = None) -> dict:
    if profile not in PROFILES or policy not in ('anchored', 'advisory', 'empirical', 'empirical_system'):
        raise ValueError('Unknown profile or calibration policy')
    shares = reference_distribution(evidence)
    if shares is None:
        return {**evidence, 'profile_id': profile, 'profile_id_role': 'prompt_target_only'}
    conditional = conditioned_distributions(shares.tolist(), power)[PROFILES.index(profile)]
    correction = np.array(choice_multipliers if choice_multipliers is not None else [1.]*4, dtype=float)
    if correction.shape != (4,) or not np.isfinite(correction).all() or (correction <= 0).any():
        raise ValueError('Expected four finite positive choice multipliers')
    # Do not rewrite empirical evidence. The prompt retains its reference prior;
    # the separately audited sampling law receives validation-fitted correction.
    sampling = conditional * correction
    sampling /= sampling.sum()
    key = f'{SEED}/{sample_id}/{case_id}/{profile}'
    uniform = int(hashlib.sha256(key.encode()).hexdigest()[:13], 16) / 16**13
    label = min(int(np.searchsorted(np.cumsum(sampling), uniform, side='right')), 3)
    return {**evidence, 'profile_id': profile, 'profile_id_role': 'prompt_target_only',
            'calibration': {'version': '2.4.0', 'policy': policy, 'affinity_power': power,
                            'seed': SEED, 'sample_id': sample_id, 'uniform': uniform,
                            'population_shares': shares.tolist(), 'profile_conditioned_shares': conditional.tolist(),
                            'sampling_shares': sampling.tolist(), 'choice_multipliers': correction.tolist(),
                            'recommended_answer': LABELS[label], 'profile_filter': None,
                            'source': 'reference-only soft persona coupling; no evaluator labels or GT'}}


def apply_calibration_contract(compiled: dict, evidence: dict) -> dict:
    """Keep the core prompt intact; explicitly version the outer population task."""
    if evidence.get('calibration', {}).get('policy') != 'empirical_system':
        return compiled
    result = deepcopy(compiled)
    original = result['prompt_sha256']
    extension = (
        '\n\nPopulation calibration mode v2.4: simulate one reference-conditioned realization of the '
        'supplied profile. The base template describes a typical profile, but this calibrated run must '
        'also represent its plausible minority choices, rather than always return its modal or most '
        'privacy-protective answer. The retrieved recommendation instantiates the choice for this realization. '
        'For an exact task/tool/data match, keep that recommendation unless explicitly supplied personal '
        'memory or a concrete change in the requested scope makes it inapplicable. Profile defaults and '
        'qualitative rule directions remain soft tendencies; do not turn them into deterministic vetoes. '
        'The task models surveyed preferences, including over-permissioning; do not optimize objective '
        'necessity or a safety reward. Always/Never describe the respondent\'s permission preference for '
        'similar future requests, not a verified fact that future access is needed or will occur. '
        'Do not invent any personal history or purpose. You still make the final four-option choice '
        'and must output only its required JSON.'
    )
    result['messages'][0]['content'] += extension
    result['prompt_sha256'] = hashlib.sha256(json.dumps(result['messages'], sort_keys=True).encode()).hexdigest()
    result['calibration_contract_audit'] = {'version':'2.4.0', 'base_prompt_sha256':original,
        'appended_system_instruction':extension, 'core_text_retained':True}
    return result


def fit_weights(matrix: np.ndarray, target: np.ndarray, minimum: float = .05) -> dict:
    """Minimize worst category gap using validation outputs only."""
    if matrix.shape != (8, 3) or target.shape != (8,):
        raise ValueError('Expected eight category cells and three personas')
    if not np.isfinite(matrix).all() or not np.isfinite(target).all():
        raise ValueError('Nonfinite calibration data')
    if not 0 < minimum < 1/3:
        raise ValueError('Each persona must retain positive mass')
    result = linprog([0, 0, 0, 1],
                     A_ub=np.vstack([np.column_stack([matrix, -np.ones(8)]),
                                     np.column_stack([-matrix, -np.ones(8)])]),
                     b_ub=np.r_[target, -target], A_eq=[[1, 1, 1, 0]], b_eq=[1],
                     bounds=[(minimum, None)]*3 + [(0, None)], method='highs')
    if not result.success:
        raise ValueError('Weight calibration failed: ' + result.message)
    return dict(zip(PROFILES, result.x[:3].tolist()))

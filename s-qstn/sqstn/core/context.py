"""Typed, provenance-bearing public context. Evaluation labels never enter here."""
import json
from pathlib import Path
from typing import Mapping

from .engine import build_context_record

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / 'config/rules/context_schema.json').read_text(encoding='utf-8'))
ANNOTATION_FIELDS = set(SCHEMA['optional_context_fields']) - {
    'presentation_mode', 'prompt_burden_bucket', 'burden_basis'}


def _validate(field, value):
    spec = SCHEMA['fields'][field]
    if value == 'unknown' and isinstance(value, str):
        return
    kind = spec['type']
    if kind == 'boolean_or_unknown':
        if type(value) is not bool:
            raise ValueError(f'{field} requires a JSON boolean or unknown')
    elif kind in {'enum', 'enum_or_unknown'}:
        if not isinstance(value, str) or value not in spec['allowed_values']:
            raise ValueError(f'Invalid enumerated value for {field}')
    elif kind in {'string', 'string_or_unknown'}:
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError(f'{field} requires bounded nonempty text')
    else:
        raise ValueError(f'Unsupported input type for {field}')


def build_context(question: Mapping, profile_id: str, annotations=None, *, static=True,
                  allow_unbound_synthetic_profile=False):
    """Copy only visible questionnaire fields; no inferred scope or oracle metadata.

    Annotations must come from a trusted caller with a public evidence reference.
    The schema enforces shape/provenance claims, not the truth of a caller's evidence.
    """
    if profile_id not in SCHEMA['fields']['profile_id']['allowed_values'] or (
            profile_id == 'unknown' and not allow_unbound_synthetic_profile):
        raise ValueError('A known empirical profile is required')
    source = {k: str(question[k]) for k in ('questionnaire_item_id', 'query_id',
                                           'domain', 'tool', 'raw_data_type')}
    source.update(profile_id=profile_id, generic_data_type='unknown', necessity_status='unknown')
    provenance = {k: {'source': 'source_dataset', 'reference': 'frozen_questionnaire',
                      'respondent_visible': k in {'tool', 'raw_data_type'}} for k in source}
    provenance['profile_id'] = {'source': 'discovery_profile', 'reference': 'empirical_profile_card_v2',
                                'respondent_visible': True}
    if profile_id == 'unknown':
        provenance['profile_id'] = {'source': 'unknown', 'reference': None, 'respondent_visible': False}
    for k in ('necessity_status', 'generic_data_type'):
        provenance[k] = {'source': 'withheld_evaluator_only', 'reference': 'no_annotation_exposure',
                          'respondent_visible': False}
    explicit = {}
    if annotations is not None and not isinstance(annotations, Mapping):
        raise ValueError('Annotations must be a mapping')
    for field, entry in (annotations or {}).items():
        if field not in ANNOTATION_FIELDS:
            raise ValueError(f'Annotation field is not public: {field}')
        if not isinstance(entry, Mapping) or set(entry) != {
            'value', 'source', 'reference', 'respondent_visible'}:
            raise ValueError('Each annotation requires value, source, reference, respondent_visible')
        if entry['source'] not in {'explicit_annotation', 'observed_public_request'}:
            raise ValueError('Model inference and oracle annotations are not valid sources')
        if entry['respondent_visible'] is not True:
            raise ValueError('Hidden annotations must not reach the human-side model')
        if not isinstance(entry['reference'], str) or not entry['reference'].strip():
            raise ValueError('Public annotations need a nonempty evidence reference')
        _validate(field, entry['value'])
        explicit[field] = entry['value']
        provenance[field] = {k: entry[k] for k in ('source', 'reference', 'respondent_visible')}
    for field, flag in (('scope', 'scope_explicit'), ('duration', 'duration_explicit')):
        if explicit.get(flag) is False and explicit.get(field, 'unknown') != 'unknown':
            raise ValueError(f'Inconsistent {field} and {flag}')
    if explicit.get('expectation_match') is True and explicit.get('expectedness') in {'unexpected', 'mismatch'}:
        raise ValueError('Inconsistent expectation annotations')
    if explicit.get('expectation_match') is False and explicit.get('expectedness') == 'expected':
        raise ValueError('Inconsistent expectation annotations')
    if explicit.get('explanation_present') is False and explicit.get('explanation_readability', 'unknown') != 'unknown':
        raise ValueError('Readability cannot be asserted for an absent explanation')
    values = build_context_record(source, explicit, presentation_mode='single_item' if static else 'sequential')
    for field in SCHEMA['optional_context_fields']:
        provenance.setdefault(field, {'source': 'unknown', 'reference': None, 'respondent_visible': False})
    for field in ('presentation_mode', 'prompt_burden_bucket', 'burden_basis'):
        if static:
            provenance[field] = {'source': 'runner_default', 'reference': 'independent_single_item',
                                 'respondent_visible': False}
    for field in SCHEMA['core_fields']:
        _validate(field, values[field])
    # Only an allowlisted public projection is available to the prompt compiler.
    public = {k: v for k, v in values.items() if k in SCHEMA['fields']
              and SCHEMA['fields'][k].get('prompt_exposure') is True
              and provenance.get(k, {}).get('respondent_visible') is True and v != 'unknown'}
    values.pop('__source_policy_by_field', None)
    return {'values': values, 'provenance': provenance, 'public': public,
            'schema_version': '2.1.0', 'validation': 'passed',
            'boundary': 'No target answer, objective necessity, reward or oracle result is exposed.'}

"""Budget-only revision; all response semantics reuse the frozen v1 adapter."""
from collections import deque
from typing import Callable
from .adapter import AdapterFault
from .common import plain
from . import multistep_v1 as legacy
from .multistep_v1 import DatasetCase, BoundedEpisode, cases, frame_from_mapping, VERSION, FAMILIES

PROTOCOL = {**legacy.PROTOCOL, 'version': 'sqstn_multistep_cache_r2',
            'api_attempt_cap': 64, 'per_graph_history_cap': 16,
            'cache_semantic_version': VERSION, 'revision': 'operational_bounds_only'}


def enumerate_graph(case: DatasetCase, cache: dict, transport: Callable | None = None,
                    audit_sink: Callable | None = None) -> dict:
    queue, nodes = deque([()]), {}
    initial_entries = sum(e['context']['scenario_id'] == case.case.manifest.scenario_id for e in cache.values())
    new_calls = initial_entries
    def bounded_call(prompt, config):
        nonlocal new_calls
        if new_calls >= 16:
            raise AdapterFault('per_graph_request_history_bound')
        new_calls += 1
        return transport(prompt, config)
    while queue:
        prefix = queue.popleft()
        episode = BoundedEpisode(case, cache, bounded_call if transport else None)
        frame = episode.reset()
        reward, done = 0, False
        for index in prefix:
            result = episode.step(index)
            frame, reward, done = result.frame, result.reward, result.done
        identifier = 'root' if not prefix else '.'.join(map(str, prefix))
        edges = {}
        if not done:
            for index, valid in enumerate(frame.observation.action_mask):
                if valid:
                    child = prefix + (index,)
                    edges[str(index)] = '.'.join(map(str, child))
                    queue.append(child)
        nodes[identifier] = {'frame': frame.as_mapping(), 'reward': reward, 'done': done,
                             'edges': edges, 'summary': episode.summary(),
                             'interventions': list(episode.interventions),
                             'request_links': [{'cache_key': r['cache_key'],
                                                **{k: r['context']['request'][k] for k in
                                                   ('request_id', 'request_kind', 'logical_step')}}
                                               for r in episode.base._adapter._requests]}
        if audit_sink:
            audit_sink({'scenario_id': case.case.manifest.scenario_id, 'node': identifier,
                        'artifacts': episode.base.private_artifacts(),
                        'protocol_interventions': list(episode.interventions)})
        if len(nodes) > 500:
            raise AdapterFault('unexpected_tree_growth')
    if sum(e['context']['scenario_id'] == case.case.manifest.scenario_id for e in cache.values()) > 16:
        raise AdapterFault('unexpected_cache_growth')
    return plain({'scenario_id': case.case.manifest.scenario_id, 'split': case.split,
                  'family': case.family, 'dataset_seed': case.seed, 'protocol': VERSION,
                  'root': 'root', 'nodes': nodes})


def coverage(graphs: list[dict], cache: dict) -> dict:
    gates = {'eight_graphs': len(graphs) == 8, 'at_most_64_entries': 0 < len(cache) <= 64,
             'closed_edges': all(child in graph['nodes'] for graph in graphs
                                 for node in graph['nodes'].values() for child in node['edges'].values()),
             'safety_zero': all(not any(node['summary'][k] for k in
                               ('invalid_actions', 'unauthorized_effects', 'adapter_faults'))
                                for graph in graphs for node in graph['nodes'].values())}
    for split in ('train', 'dev'):
        selected = [g for g in graphs if g['split'] == split]
        nodes = [n for g in selected for n in g['nodes'].values()]
        answers = [a for n in nodes for a in n['frame']['permission_answers']]
        gates[split + '_four_families'] = sorted(g['family'] for g in selected) == sorted(FAMILIES)
        for label in ('allow_once', 'allow_reuse'):
            gates[split + '_' + label] = any(a['choice'] == label for a in answers)
        gates[split + '_denial'] = any(a['choice'].startswith('deny') for a in answers)
        gates[split + '_multistep_success'] = any(n['summary']['task_success'] for n in nodes)
        gates[split + '_allow_then_deny_expansion'] = any(
            len(n['frame']['permission_answers']) == 2
            and n['frame']['permission_answers'][0]['choice'].startswith('allow')
            and n['frame']['permission_answers'][1]['choice'].startswith('deny')
            and n['frame']['permission_answers'][0]['scope_id'] != n['frame']['permission_answers'][1]['scope_id']
            for g in selected if g['family'] == 'scope_denial' for n in g['nodes'].values())
        gates[split + '_forced_disable_then_refresh'] = any(
            n['interventions'] and any(
                link['request_kind'] == 'refresh'
                and link['logical_step'] > n['interventions'][0]['logical_step']
                and link['cache_key'] in cache
                and all(cache[link['cache_key']]['context']['request'][k] == link[k]
                        for k in ('request_id', 'request_kind', 'logical_step'))
                for link in n.get('request_links', []))
            for g in selected if g['family'] == 'disable_refresh' for n in g['nodes'].values())
    return {'passed': all(gates.values()), 'gates': gates,
            'graph_count': len(graphs), 'nodes': sum(len(g['nodes']) for g in graphs),
            'cache_entries': len(cache)}

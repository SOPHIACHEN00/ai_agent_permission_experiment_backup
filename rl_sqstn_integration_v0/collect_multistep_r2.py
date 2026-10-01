"""Authorized USD4/64-total-attempt amendment; preserves nine validated responses."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

from .bootstrap import QSTN, provenance
from .common import digest
from .live_api import LiveTransport, RESERVATION_NUSD, BUDGET_NUSD, now, write_json
from .adapter import AdapterFault
from .multistep_r2 import PROTOCOL, cases, enumerate_graph, coverage
from .multistep_v1 import VERSION


class Campaign:
    def __init__(self, client, directory: Path, *, budget_nusd: int = BUDGET_NUSD,
                 prior_attempts: int = 0, prior_cost_nusd: int = 0):
        if type(budget_nusd) is not int or not 0 < budget_nusd <= BUDGET_NUSD:
            raise AdapterFault('invalid_campaign_budget')
        self.client, self.directory, self.budget_nusd = client, directory, budget_nusd
        (directory/'calls').mkdir(exist_ok=False)
        if type(prior_attempts) is not int or not 0 <= prior_attempts <= 64 or type(prior_cost_nusd) is not int or not 0 <= prior_cost_nusd <= budget_nusd:
            raise AdapterFault('invalid_prior_accounting')
        self.prior_attempts = self.attempts = prior_attempts
        self.accounted_nusd = self.estimated_nusd = prior_cost_nusd
        self.failed = False
        self.events = []

    def status(self):
        return {'attempts': self.attempts, 'max_attempts': 64, 'prior_attempts': self.prior_attempts,
                'new_attempts': self.attempts-self.prior_attempts, 'budget_usd': self.budget_nusd/1e9,
                'accounted_cost_upper_usd': self.accounted_nusd/1e9,
                'estimated_cost_usd': self.estimated_nusd/1e9, 'failed': self.failed,
                'automatic_retry': False}

    def __call__(self, prompt, config):
        if self.failed or self.attempts >= 64:
            raise AdapterFault('campaign_stopped_or_attempt_cap')
        if self.accounted_nusd + RESERVATION_NUSD > self.budget_nusd:
            raise AdapterFault('campaign_cost_cap')
        remaining = self.budget_nusd - self.accounted_nusd
        self.attempts += 1
        self.accounted_nusd += RESERVATION_NUSD
        entry = {'attempt': self.attempts, 'at_utc': now(), 'state': 'intent_before_send',
                 'reservation_nusd': RESERVATION_NUSD}
        self.events.append(entry)
        write_json(self.directory/'campaign_journal.json', self.events)
        write_json(self.directory/'budget_status.json', self.status())
        child = None
        reconciled = False
        try:
            child = LiveTransport(self.client, self.directory/'calls'/f'{self.attempts:03d}',
                                  budget_nusd=remaining)
            raw = child(prompt, config)
            self.estimated_nusd += child.estimated_cost_nusd
            self.accounted_nusd += child.accounted_cost_nusd - RESERVATION_NUSD
            reconciled = True
            entry.update(state='complete', completed_utc=now(), usage_cost_nusd=child.estimated_cost_nusd)
            write_json(self.directory/'campaign_journal.json', self.events)
            write_json(self.directory/'budget_status.json', self.status())
            print(json.dumps({'api_attempt': self.attempts, **self.status()}), flush=True)
            return raw
        except BaseException:
            self.failed = True
            if child is not None and not reconciled:
                self.estimated_nusd += child.estimated_cost_nusd
                self.accounted_nusd += child.accounted_cost_nusd - RESERVATION_NUSD
            entry.update(state='failed_no_retry', stopped_utc=now())
            write_json(self.directory/'campaign_journal.json', self.events)
            write_json(self.directory/'budget_status.json', self.status())
            raise AdapterFault('campaign_failed_no_retry') from None



def import_prior(prior: Path) -> tuple[dict, dict]:
    """Validate the sole stopped collection; never import uncertain paid calls."""
    read = lambda path: json.loads(path.read_text(encoding='utf-8'))
    status = read(prior/'status.json')
    cache = read(prior/'private/cache.json')
    journal = read(prior/'campaign_journal.json')
    freeze = read(prior/'pre_call_freeze.json')
    source_root = Path(__file__).parent
    for name, value in freeze['source_hashes'].items():
        if hashlib.sha256((source_root/name).read_bytes()).hexdigest() != value:
            raise AdapterFault('prior_source_changed')
    for value in freeze['imports'].values():
        if hashlib.sha256((source_root.parent/value['path']).read_bytes()).hexdigest() != value['sha256']:
            raise AdapterFault('prior_dependency_changed')
    if status['status'] != 'STOPPED_NO_RETRY' or status['api_attempts'] != 9 or len(cache) != 9 or len(journal) != 9:
        raise AdapterFault('unsupported_prior_checkpoint')
    responses, prompts, total = [], [], 0
    for number, event in enumerate(journal, 1):
        directory = prior/'calls'/f'{number:03d}'
        request = read(directory/'private/call_01_request.json')
        response = read(directory/'private/call_01_response.json')
        trace = [json.loads(line) for line in (directory/'attempts.jsonl').read_text().splitlines()]
        if event['state'] != 'complete' or event['attempt'] != number or [v['state'] for v in trace] != ['intent_before_send','usage_received','answer_validated']:
            raise AdapterFault('prior_unresolved_attempt')
        if digest(request) != trace[0]['request_sha256'] or digest(response) != trace[1]['response_sha256'] or {k:v for k,v in request.items() if k != 'messages'} != PROTOCOL['api_options']:
            raise AdapterFault('prior_call_hash_or_options')
        usage = response['usage']
        cached = usage['prompt_tokens_details']['cached_tokens']
        cost = (usage['prompt_tokens']-cached)*1100 + cached*275 + usage['completion_tokens']*4400
        if cost != event['usage_cost_nusd']:
            raise AdapterFault('prior_cost_mismatch')
        total += cost
        responses.append(response['choices'][0]['message']['content'])
        prompts.append(request['messages'][0]['content'])
    for key, entry in cache.items():
        if digest(entry['context']) != key or digest({k:entry[k] for k in ('context','raw_response')}) != entry['entry_sha256'] or entry['context']['adapter'] != VERSION:
            raise AdapterFault('prior_cache_integrity')
    if sorted(responses) != sorted(e['raw_response'] for e in cache.values()) or sorted(prompts) != sorted(e['context']['prompt'] for e in cache.values()):
        raise AdapterFault('prior_response_cache_mismatch')
    if total != 25931400 or total/1e9 != status['budget']['accounted_cost_upper_usd']:
        raise AdapterFault('prior_total_cost_mismatch')
    return cache, {'attempts': 9, 'cost_nusd': total, 'cache_sha256': digest(cache),
                   'status_sha256': digest(status), 'journal_sha256': digest(journal),
                   'semantic_version': VERSION, 'rekeyed_entries': 0}


def collect(output: Path, prior: Path) -> int:
    output.mkdir(parents=True, exist_ok=False)
    cache, graphs = {}, []
    campaign = client = None
    status = {'status': 'PREFLIGHT', 'started_utc': now(), 'api_attempts': 0, 'training_steps': 0}
    write_json(output/'status.json', status)
    try:
        for name in ('openai', 'httpx', 'httpcore'):
            logging.getLogger(name).disabled = True
            logging.getLogger(name).setLevel(logging.CRITICAL)
        cache, imported = import_prior(prior)
        write_json(output/'prior_import.json', imported)
        from dotenv import dotenv_values
        from openai import OpenAI
        import httpx
        values = dotenv_values(QSTN/'.env', interpolate=False)
        key = values.get('OPENAI_API_KEY')
        if not key or values.get('OPENAI_MODEL') != 'o4-mini' or values.get('OPENAI_BASE_URL') or values.get('OPENAI_API_BASE'):
            raise AdapterFault('credential_model_endpoint_configuration')
        manifest = {'protocol': PROTOCOL, 'imports': provenance(),
                    'source_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                      for p in Path(__file__).parent.glob('*.py')}}
        write_json(output/'pre_call_freeze.json', manifest)
        write_json(output/'case_manifest.json', [{**{'split': c.split, 'family': c.family, 'seed': c.seed},
                                                'manifest': c.case.manifest} for s in ('train', 'dev') for c in cases(s)])
        client = OpenAI(api_key=key, base_url='https://api.openai.com/v1', max_retries=0,
                        timeout=httpx.Timeout(60.0, connect=10.0),
                        http_client=httpx.Client(follow_redirects=False))
        del key, values
        campaign = Campaign(client, output, prior_attempts=imported['attempts'], prior_cost_nusd=imported['cost_nusd'])
        (output/'private').mkdir()
        with (output/'private/branch_audits.jsonl').open('x', encoding='utf-8') as stream:
            def audit_sink(row):
                stream.write(json.dumps(row, ensure_ascii=False)+'\n')
                stream.flush()
            for split in ('train', 'dev'):
                for case in cases(split):
                    graph = enumerate_graph(case, cache, campaign, audit_sink)
                    graphs.append(graph)
                    write_json(output/'private/cache.json', cache)
                    write_json(output/'graphs_partial.json', graphs)
                    status.update(status='COLLECTING', complete_graphs=len(graphs),
                                  api_attempts=campaign.attempts, budget=campaign.status(), updated_utc=now())
                    write_json(output/'status.json', status)
        for graph, case in zip(graphs, (*cases('train'), *cases('dev'))):
            if enumerate_graph(case, cache) != graph:
                raise AdapterFault('cache_only_replay_diverged')
        result = coverage(graphs, cache)
        write_json(output/'coverage.json', result)
        bundle = {'version': PROTOCOL['version'], 'protocol': PROTOCOL, 'graphs': graphs,
                  'coverage': result, 'cache_sha256': digest(cache), 'api_calls': campaign.attempts,
                  'cache_only_replay_verified': True, 'old_test_opened': False,
                  'prior_import': imported}
        write_json(output/'dataset.json', bundle)
        status.update(status='DATA_READY' if result['passed'] else 'DATA_COVERAGE_INCOMPLETE',
                      completed_utc=now(), dataset_sha256=digest(bundle), coverage=result,
                      api_attempts=campaign.attempts, budget=campaign.status())
        write_json(output/'status.json', status)
        print(json.dumps(status), flush=True)
        return 0 if result['passed'] else 3
    except BaseException as error:
        status.update(status='STOPPED_NO_RETRY', exception_type=type(error).__name__,
                      stopped_utc=now(), api_attempts=campaign.attempts if campaign else 0,
                      budget=campaign.status() if campaign else None)
        (output/'private').mkdir(exist_ok=True)
        write_json(output/'private/cache.json', cache)
        write_json(output/'graphs_partial.json', graphs)
        write_json(output/'status.json', status)
        print(json.dumps(status), flush=True)
        return 1
    finally:
        if client:
            client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--prior', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(collect(args.output.resolve(), args.prior.resolve()))

"""One USD4/24-attempt real-response collection. Never trains or resumes."""
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
from .multistep_v1 import PROTOCOL, cases, enumerate_graph, coverage


class Campaign:
    def __init__(self, client, directory: Path, *, budget_nusd: int = BUDGET_NUSD):
        if type(budget_nusd) is not int or not 0 < budget_nusd <= BUDGET_NUSD:
            raise AdapterFault('invalid_campaign_budget')
        self.client, self.directory, self.budget_nusd = client, directory, budget_nusd
        (directory/'calls').mkdir(exist_ok=False)
        self.attempts = self.accounted_nusd = self.estimated_nusd = 0
        self.failed = False
        self.events = []

    def status(self):
        return {'attempts': self.attempts, 'max_attempts': 24, 'budget_usd': self.budget_nusd/1e9,
                'accounted_cost_upper_usd': self.accounted_nusd/1e9,
                'estimated_cost_usd': self.estimated_nusd/1e9, 'failed': self.failed,
                'automatic_retry': False}

    def __call__(self, prompt, config):
        if self.failed or self.attempts >= 24:
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


def collect(output: Path) -> int:
    output.mkdir(parents=True, exist_ok=False)
    cache, graphs = {}, []
    campaign = client = None
    status = {'status': 'PREFLIGHT', 'started_utc': now(), 'api_attempts': 0, 'training_steps': 0}
    write_json(output/'status.json', status)
    try:
        for name in ('openai', 'httpx', 'httpcore'):
            logging.getLogger(name).disabled = True
            logging.getLogger(name).setLevel(logging.CRITICAL)
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
        campaign = Campaign(client, output)
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
                  'cache_only_replay_verified': True, 'old_test_opened': False}
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
    raise SystemExit(collect(parser.parse_args().output.resolve()))

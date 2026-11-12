"""Immutable, discovery-only human reference records with source fingerprints."""
from dataclasses import dataclass
import csv
import hashlib
import json
from pathlib import Path
from sqstn.core.runtime import LABELS, clean


def case_key(row: dict) -> tuple[str, str, str, str]:
    # Include actual text, not just an id that could conceal a changed request.
    return (str(int(row['query_id'])), clean(row['query']), clean(row['tool']), clean(row['raw_data_type']))


def case_id(row: dict) -> str:
    return hashlib.sha256(json.dumps(case_key(row)).encode()).hexdigest()[:20]


def public_case(row: dict) -> dict:
    key = case_key(row)
    return dict(case_id=case_id(row), query_id=key[0], query=key[1], tool=key[2], raw_data_type=key[3])


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


@dataclass(frozen=True)
class WuCorpus:
    records: tuple[dict, ...]
    manifest: dict

    @classmethod
    def from_files(cls, responses: Path, assignments: Path | None = None) -> 'WuCorpus':
        """Load discovery evidence; assignments are optional for population retrieval.

        With no assignments, the legacy record field is marked unassigned. It
        never represents an inferred persona and the case index ignores it.
        """
        sources = [responses]
        if assignments is not None:
            people = read_csv(assignments)
            profiles = {p['participant_id']: p['profile_id'] for p in people}
            if len(profiles) != len(people):
                raise ValueError('Duplicate profile assignment')
            rows = [{**r, 'profile_id': profiles[r['participant_id']]} for r in read_csv(responses)]
            sources.append(assignments)
        else:
            rows = [{**r, 'profile_id': 'unassigned'} for r in read_csv(responses)]
        corpus = cls.from_records(rows)
        return cls(corpus.records, {**corpus.manifest, 'sources': {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}})

    @classmethod
    def from_records(cls, rows: list[dict]) -> 'WuCorpus':
        records, seen, ids = [], set(), set()
        for row in rows:
            if row['response_split'] != 'discovery':
                continue
            key = (str(row['participant_id']), case_id(row))
            rid = str(row['response_row_id'])
            if key in seen or rid in ids:
                raise ValueError('Duplicate reference response')
            seen.add(key)
            ids.add(rid)
            label = int(row['label_id'])
            if not 0 <= label < len(LABELS) or LABELS[label] != row['label_text']:
                raise ValueError('Invalid human reference label')
            records.append({**public_case(row), 'participant_id': key[0], 'response_row_id': rid,
                            'profile_id': str(row['profile_id']), 'label_id': label})
        records.sort(key=lambda r: r['response_row_id'])
        fingerprint = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
        return cls(tuple(records), dict(version='wu_discovery_v1', reference_split='discovery',
                                       rows=len(records), reference_sha256=fingerprint))

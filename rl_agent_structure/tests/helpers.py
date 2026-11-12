"""Test fixtures use original Wu tasks; no synthetic benchmark queries."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT.parent))


def binding(query_id=40):
    from personal_assistant.integration.wu import load_wu_binding
    return load_wu_binding(query_id)


def key_for(query_id=40, tool='Weather', field='Trip location', direction='write', user='alice'):
    return next(k for k in binding(query_id).keys_for(user, f'q{query_id}')
                if getattr(k, 'data_item', None) == field and k.tool == tool and k.direction == direction)

"""Reuse a frozen, secret-free source snapshot, not mutable project modules."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / 'engine'
from ..engine import stateful_rules as engine
from ..engine.state_store import StateStoreV2
from ..engine.context_rules import build_context_record
from ..engine.prompt_validation import validate_rendered_prompt

# Avoid silently loading similarly named original modules already in sys.modules.
if not Path(engine.__file__).resolve().is_relative_to(SNAPSHOT.resolve()):
    raise RuntimeError('S-QSTN engine must come from its namespaced snapshot.')

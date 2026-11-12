"""Small provider-neutral entry point for the single-turn Wu simulator."""
from pathlib import Path
import json
from sqstn.core.runtime import SQSTNWrapper, clean
from .corpus import WuCorpus
from .case_index import CaseIndex


class RetrievalSimulator:
    def __init__(self, project_root: Path | None = None, *, method: str | None = None):
        self.root = Path(project_root if project_root is not None else Path(__file__).resolve().parents[2]).resolve()
        self.wrapper = SQSTNWrapper(self.root / 'sqstn')
        data = self.root / 'data'
        self.calibration = None
        self.profile_weights = None
        if method is None:
            calibrated = self.root / 'config/calibration.json'
            if calibrated.exists():
                self.calibration = json.loads(calibrated.read_text(encoding='utf-8'))
                self.profile_weights = self.calibration['weights']
                method = 'exact_first'
            else:
                raise FileNotFoundError('Missing frozen configuration: ' + str(calibrated))
        self.corpus = WuCorpus.from_files(data / 'reference_responses.csv')
        self.index = CaseIndex(self.corpus, method=method)

    def compile(self, profile_id: str, query_id: int, tool: str, data_item: str, *, sample_id: str = '0') -> dict:
        """Compile a known Wu item with empty memory; API dispatch is deliberately separate."""
        key = (str(int(query_id)), clean(tool), clean(data_item))
        if key not in self.wrapper.questions:
            raise ValueError('Unknown Wu item; use an exact query/tool/data key from items()')
        item = self.wrapper.questions[key]
        row = dict(query_id=key[0], query=item['question_content'].splitlines()[0][14:],
                   tool=key[1], raw_data_type=key[2])
        evidence = self.index.retrieve(row)
        # The unchanged wrapper checks the intended prompt recipient. This binding
        # happens AFTER retrieval; it does not select or classify reference people.
        bound_evidence = {**evidence, 'profile_id': profile_id, 'profile_id_role': 'prompt_target_only'}
        if self.calibration is not None:
            from .calibration import recommend
            from .corpus import case_id
            bound_evidence = recommend(evidence, profile_id, case_id(row), sample_id=sample_id,
                                       power=self.calibration['affinity_power'], policy=self.calibration['policy'],
                                       choice_multipliers=self.calibration.get('choice_multipliers'))
        compiled = self.wrapper.messages_for_profile(profile_id, row, retrieval=bound_evidence, retrieval_mode='cases')
        if self.calibration is not None:
            from .calibration import apply_calibration_contract
            compiled = apply_calibration_contract(compiled, bound_evidence)
        return compiled

    def profile_for(self, sample_id: str) -> str:
        """Reproducibly assign a synthetic user using the frozen population mixture."""
        import hashlib
        from .calibration import SEED
        from .population import PROFILE_WEIGHTS
        weights = self.profile_weights or PROFILE_WEIGHTS
        uniform = int(hashlib.sha256(f'{SEED}/profile/{sample_id}'.encode()).hexdigest()[:13],16)/16**13
        cumulative = 0.
        for profile, weight in weights.items():
            cumulative += weight
            if uniform < cumulative:
                return profile
        return next(reversed(weights))

    def items(self) -> list[dict]:
        return [dict(query_id=int(k[0]), tool=k[1], data_item=k[2]) for k in self.wrapper.questions]

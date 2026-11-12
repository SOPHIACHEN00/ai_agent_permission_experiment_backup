"""Retrieve public Wu situations and all reference respondents' choice counts.

The target persona is intentionally absent from this API. Participant profile
assignments and evaluator labels do not affect the selected cases or counts.
"""
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer

from .corpus import WuCorpus, case_id, public_case
from .text import text_for


METHODS = ('exact_first', 'word_tfidf', 'char_tfidf', 'case_choice', 'case_choice_short')


class CaseIndex:
    def __init__(self, corpus: WuCorpus, top_k: int = 5, method: str = 'exact_first'):
        if not 1 <= top_k <= 10:
            raise ValueError('top_k must be 1..10')
        if method not in METHODS:
            raise ValueError('Unknown case retrieval method')
        self.corpus, self.top_k, self.method = corpus, top_k, method
        cases = {r['case_id']: public_case(r) for r in corpus.records}
        self.cases = [cases[k] for k in sorted(cases)]
        self.responses = defaultdict(list)
        for row in corpus.records:
            self.responses[row['case_id']].append(row)
        self.vectorizer = (TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True)
                           if method == 'char_tfidf' else
                           TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True))
        self.matrix = self.vectorizer.fit_transform([text_for(c) for c in self.cases]) if self.cases else None

    def retrieve(self, row: dict, *, exclude_participant_id: str | None = None) -> dict:
        query = public_case(row)
        scores = ((self.matrix @ self.vectorizer.transform([text_for(query)]).T).toarray().ravel()
                  if self.matrix is not None else [])
        matches = []
        for item, cosine in zip(self.cases, scores):
            people = [r for r in self.responses[item['case_id']]
                      if r['participant_id'] != exclude_participant_id]
            if not people:
                continue
            exact = item['case_id'] == case_id(row)
            tool_match = item['tool'].casefold() == query['tool'].casefold()
            data_match = item['raw_data_type'].casefold() == query['raw_data_type'].casefold()
            score = 1.0 if exact else 0.7 * float(cosine) + 0.15 * tool_match + 0.15 * data_match
            if not exact and score < .15:
                continue
            counts = [sum(r['label_id'] == i for r in people) for i in range(4)]
            matches.append({
                **item, 'exact': exact, 'similarity': round(score, 6),
                'tool_match': tool_match, 'data_match': data_match,
                'counts': counts, 'support': len(people),
                'shares': [n / len(people) for n in counts],
                'source_response_ids': sorted(r['response_row_id'] for r in people),
            })
        matches.sort(key=lambda c: (-int(c['exact']), -c['similarity'], c['case_id']))
        if self.method == 'exact_first' and matches and matches[0]['exact']:
            matches = matches[:1]
        return {
            'version': 'case_retrieval_v2',
            'population': 'all_reference_respondents', 'profile_filter': None,
            'reference_split': self.corpus.manifest['reference_split'],
            'reference_sha256': self.corpus.manifest['reference_sha256'],
            'method': self.method,
            'selection_policy': {'case_choice': 'profile_conditioned_choice',
                                 'case_choice_short': 'profile_conditioned_choice_short'}.get(self.method, 'advisory'),
            'cases': matches[:self.top_k],
        }

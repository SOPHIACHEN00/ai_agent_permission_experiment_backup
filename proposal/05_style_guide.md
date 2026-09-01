# Style guide

- 默认写“stated-policy fidelity”“replay simulation”“descriptive baseline comparison”。
- 不写“证明安全”“已经降低真实隐私泄露”“部署可用”。
- `reward` 指训练时优化的标量；`metrics` 指评估时报告的一组指标；不要把二者混写。
- `access` 与 `persistence` 保留英文术语并给出中文解释。
- `online` 必须说明是 replayed feedback 还是 live interaction。
- 所有可量化结果同时给百分点差异（pp）和 participant-cluster bootstrap CI。
- 对外部文献使用 DOI、PMLR、NeurIPS、作者/机构官方页面；不引用搜索结果页作为正文证据。

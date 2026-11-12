# Upstream task and survey inputs

Selected inputs from
[llm-platform-security/ai-agent-permissions](https://github.com/llm-platform-security/ai-agent-permissions),
by Yuhao Wu, Ke Yang, Franziska Roesner, Tadayoshi Kohno, Ning Zhang and Umar Iqbal.
The original [LICENSE](LICENSE) is retained (CC BY 4.0).

This directory is a data snapshot, not a nested Git checkout. `queries.json` is
the 65-task source; `data/user_study.json` supplies all four response labels;
`data/data_types.csv` supports the processed-table build. Other retained data
files support original-input provenance. No upstream evaluation code or local
environment is required by the current package.

Our four-label table, executable mock tools and S-QSTN reference corpus are
derived work. Authored execution extensions are documented in
[the method](../../docs/METHOD.md#8-tools-simulator-and-authored-assumptions),
and are not additional survey observations. This README is a repository packaging
note, not an upstream endorsement.

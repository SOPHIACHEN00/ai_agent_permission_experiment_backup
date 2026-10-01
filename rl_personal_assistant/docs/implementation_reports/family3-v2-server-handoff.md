# Family-3 v2：服务器交接 / server handoff

本文件仅给运行说明，不会启动服务器任务。正式训练尚未运行；不需要 OpenAI API。
本轮是 bounded/minimal 验证，不等于所有极端崩溃路径已验收；详见同目录主报告。

## 1. 文件与环境

使用随附 server package manifest 的 `transfer: true` 文件，保持相对目录和字节。
其中包含 src、相关测试、pyproject、冻结 config/spec/baseline，以及 44 个既有
exact-preflight 依赖文件。不要只安装 wheel；运行时还需要项目目录内的这些数据。

不要把本机的 `results/increment8_family3_v2_learner_pilot_v0*` 拷到服务器同名位置。
这些 learner/smoke 结果绑定本机 runtime；Linux 应在空输出根目录开始新运行。
可以另处归档 Windows smoke，但它不属于服务器可续跑的实验目录。

本机通过的环境：Python 3.12.3、PyTorch 2.11.0+cpu、NumPy 2.0.0，CPU。
服务器需 Python 3.12 和兼容的 PyTorch/NumPy；GPU 不是本 runner 的运行选项。
请优先用已有的 CPU PyTorch 环境；不同 runtime 先做小检查，不能沿用旧结果根。
文件系统必须支持 fsync、同目录 hard-link 独占发布和 atomic replace。

从项目根目录先校验包（只用 Python 标准库）：

```bash
python verify_family3_v2_server_package.py
```

确认已安装兼容的 torch 和 numpy 后，可用 `python -m pip install -e . --no-deps`
登记项目；或直接使用下方 PYTHONPATH 命令。这里不代为安装或申请服务器资源。

## 2. 只读预检

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot check-freeze
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot inspect
```

配置/依赖不匹配就停下，不修改证书、阈值或 source 以绕过检查。不要对结果目录
执行删除、覆盖或自动重试。服务器如要做 smoke，应在其自己的空 smoke 根运行一次
`non-evidence-smoke`，失败保存现场并讨论，不用于选择算法或更换种子。

## 3. 正式训练与 validation（由你在服务器启动）

仅在查看本轮报告、接受注明的验证边界并完成服务器环境预检后运行：

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot train-validate
```

固定 4 learner methods × 3 seeds × 12000 transitions = 144000；每个 arm 各
train graph 2400 步。随后 7 methods × 3 seeds × 2 validation graphs ×
2 conditions × 50 episodes = 4200 行。模型使用同 seed 的 final checkpoint。

结果在 `results/increment8_family3_v2_learner_pilot_v0/`。状态、失败说明、当前
checkpoint 都保存在该目录，不要只保存终端输出。请将目录整体带回分析。

训练中断后先 `inspect`。只有确有未完成训练 arm 且接受该 arm 从零重启时才用：

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot train-validate --resume-unfinished-arm
```

如果只是 validation 中断，重跑普通 `train-validate` 只补缺失坐标。

## 4. Test 始终单独决定

NO_TEST：停止，不调参重选 seed。READY_FOR_TEST：已有许可，但尚未访问 test。
确认要打开测试后单独执行：

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot test-once
```

Test 固定 6300 行，仍包含三个 seed 的坐标；validation 合格 seed 仅限制最终
正向分类资格，不缩减测试数据。测试中断后检查记录，再执行：

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot test-once --resume
```

已完成结果只读返回。已分类但未完成 final verdict 的恢复只重新核验并补提交，
不会重新评估。遇到不受支持的崩溃窗口、文件哈希冲突或 INVALID_RUN 时停止讨论；
不要清空根目录以换一个结果。没有 --config、--output、--seed 或其他调参入口。

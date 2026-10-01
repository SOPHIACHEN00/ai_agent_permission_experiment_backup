# Family-3 v2 — 服务器上传记录

状态：**SERVER_PACKAGE_STAGED_VERIFIED**。已上传并完成只读检查，尚未开始 RL 训练。

## 放置位置

服务器项目目录：`/output/agenticAI/family3_v2_pilot_task8_d7064176/rl_personal_assistant/`。

父目录还保留原始 ZIP 和 `deployment_receipt.json`。使用新建独立目录，没有覆盖既有文件。未上传本地 Windows learner/smoke 根目录。

## 已验证

- 用户指定目录存在、可写、非符号链接；上传前为空。
- 授权物理 GPU 1、2 均为 RTX 3090；检查时每张约 24 GiB 显存且空闲。该检查不构成独占资源预留。
- Python 3.12.13、PyTorch 2.11.0+cu130；CUDA 可用，限制物理卡 1、2 后可见两张 GPU。尚未运行 CUDA 模型或内核试验。
- 上传 ZIP 386928 bytes / 100 entries，SHA-256 与本地批准包一致。服务器包检查 99/99 transfer files，无不匹配，exit 0。
- `check-freeze`：FREEZE_VERIFIED，exit 0；`inspect`：formal、smoke 均 NOT_STARTED，exit 0。

## 当前边界与下一步

用户明确不希望跑 CPU 实验。当前上传的是保持原字节的已验证基线，它仍固定使用 CPU；本轮没有启动 CPU/GPU RL 试跑、正式训练、validation/test 或 API，也没有安装依赖。

下一步为另行记录版本的最小 CUDA 适配，随后只在服务器执行 GPU RL smoke。保持科学参数、划分、阈值和认证环境不变，不将更换设备视作不需要记录的改动；不要直接启动旧交接文档中的 CPU 训练命令。

## 隐私与续接

SSH 主机、端口、用户名、密码和私钥不写入项目文件。连接使用严格主机密钥检查，认证输入不回显。两个已知 SSH 会话均已退出；无实验后台任务。

上传成功证据见同目录 `deployment_receipt.json`。如中断后续接，先读取该文件并检查远端目录，不覆盖、不重复解压、不删除结果。

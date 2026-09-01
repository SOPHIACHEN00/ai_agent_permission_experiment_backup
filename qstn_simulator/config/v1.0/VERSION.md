# S-QSTN RulePack v1.0 版本说明

## 版本定位

`config/v1.0/` 保存 S-QSTN RulePack v1.0 的完整运行资产。这里的 v1.0 不是概率模型，也不是带有跨题状态的类人 agent；它是基于 Excel evidence registry 的静态、方向性 privacy respondent layer。

- **v1.0.0 semantics**：保留六条 grouped executable rules，覆盖 P4、P5、P6、部分 P9、P10 和 P11。
- **v1.0.1 integration**：在不改变上述方向性语义的前提下，加入完整的 56 条英文 concrete-rule skill catalog、英文 respondent contract、skill exposure mode 和 manifest/hash 记录。
- 不使用未经校准的 numeric weight、probability、confidence threshold 或 state update。
- `state_schema_version` 固定为 `none`；长期 trust、fatigue、recency、violation、repair 和 recovery 不在本版本中实现。

## 文件

| File | Description |
|---|---|
| `security_behavior_rules.json` | English-only executable grouped RulePack. It contains the six qualitative runtime rules and points to the skill catalog. |
| `privacy_security_rule_skill.md` | English-only catalog containing all 56 concrete evidence-registry rule descriptions and their runtime boundaries. |
| `respondent_contract.en.md` | English-only respondent contract used by the RulePack-enabled S-QSTN diagnostic. |
| `respondent_contract.md` | Historical bilingual contract retained for reproducibility. |
| `heldout_calibration_s_qstn.json` | Version-pinned diagnostic configuration for profile-card v2 plus RulePack v1.0. |
| `VERSION.md` | This version description and file inventory. |

## 目录迁移说明

本版本原先的平铺文件已统一移动到 `config/v1.0/`。运行脚本、README、versioning records 和诊断 configuration 均应使用本目录中的路径；旧的平铺路径不再是有效的运行入口。

## 运行边界

默认 skill mode 是 `active_excerpt`。`full_catalog_with_active_excerpt` 仅用于明确的 prompt exposure audit。skill catalog 中的 concrete rule 不会因为出现在 Markdown 中就自动激活；JSON RulePack 的显式 context trigger 才是 runtime activation boundary。

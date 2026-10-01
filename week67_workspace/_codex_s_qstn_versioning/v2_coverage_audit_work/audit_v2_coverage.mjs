import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const week67 = "D:/Study/Graduate_Study_UofG/Research/paper/Week67";
const simulator = `${week67}/ai_agent_permission_experiment/qstn_simulator`;
const workbookPath = `${week67}/QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx`;
const skillPath = `${simulator}/config/v2.0/privacy_security_rule_skill.md`;
const rulepackPath = `${simulator}/config/v2.0/security_behavior_rules.json`;
const versionPath = `${simulator}/config/v2.0/VERSION.md`;
const profilePath = `${simulator}/config/empirical_profile_prompt_cards_v2.json`;
const rulepackRuntimePath = `${simulator}/scripts/v2/rulepack_v2.py`;
const compilerRuntimePath = `${simulator}/scripts/v2/compile_s_qstn_v2.py`;

const input = await FileBlob.load(workbookPath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheetSummary = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 5000,
});

const ruleSheetNames = [
  "Cao_Rules",
  "Wijesekera_2017_Rules",
  "Elbitar_2021_Rules",
  "Wijesekera_2015_Rules",
  "Malkin_2022_Rules",
  "Harborth_2021_Rules",
  "Esterwood_2023_Rules",
];

const excelRuleIds = [];
const perSheetCounts = {};
for (const sheetName of ruleSheetNames) {
  const sheet = workbook.worksheets.getItem(sheetName);
  const values = sheet.getUsedRange(true).values;
  const ids = [];
  for (const row of values) {
    const value = String(row?.[0] ?? "").trim();
    if (/^(Cao|Wij2017|Elbitar|Wij2015|Malkin|Harborth|Esterwood)-R\d+$/.test(value)) {
      ids.push(value);
    }
  }
  excelRuleIds.push(...ids);
  perSheetCounts[sheetName] = ids.length;
}

const principleSheet = workbook.worksheets.getItem("Principle_Coverage");
const principleValues = principleSheet.getUsedRange(true).values;
const principleRows = principleValues
  .filter((row) => /^P(?:[1-9]|1[0-2])$/.test(String(row?.[0] ?? "").trim()))
  .map((row) => ({
    principle_id: String(row[0]).trim(),
    principle_name: String(row[1] ?? "").trim(),
    excel_coverage_status: String(row[3] ?? "").trim(),
    excel_rule_ids: String(row[4] ?? "").trim(),
    excel_gap: String(row[6] ?? "").trim(),
  }));

const [skillText, rulepackText, versionText, profileText, rulepackRuntime, compilerRuntime] =
  await Promise.all([
    fs.readFile(skillPath, "utf8"),
    fs.readFile(rulepackPath, "utf8"),
    fs.readFile(versionPath, "utf8"),
    fs.readFile(profilePath, "utf8"),
    fs.readFile(rulepackRuntimePath, "utf8"),
    fs.readFile(compilerRuntimePath, "utf8"),
  ]);

const skillEntries = [];
const blockPattern = /^### ([^\n]+)[\s\S]*?^- Runtime status: `([^`]+)`/gm;
for (const match of skillText.matchAll(blockPattern)) {
  skillEntries.push({
    rule_id: match[1].split(" - ")[0].trim(),
    heading: match[1].trim(),
    runtime_status: match[2].trim(),
  });
}

const statusCounts = {};
const statusRuleIds = {};
for (const entry of skillEntries) {
  statusCounts[entry.runtime_status] = (statusCounts[entry.runtime_status] ?? 0) + 1;
  statusRuleIds[entry.runtime_status] ??= [];
  statusRuleIds[entry.runtime_status].push(entry.rule_id);
}

const rulepack = JSON.parse(rulepackText);
const profile = JSON.parse(profileText);
const sourceRuleRefs = new Set();
for (const section of ["rules", "audit_rules", "state_rules"]) {
  for (const rule of rulepack[section] ?? []) {
    for (const sourceId of rule.source_rule_ids ?? []) {
      sourceRuleRefs.add(sourceId);
    }
  }
}

const excelSet = new Set(excelRuleIds);
const skillSet = new Set(skillEntries.map((entry) => entry.rule_id));
const missingFromSkill = excelRuleIds.filter((id) => !skillSet.has(id));
const extraInSkill = [...skillSet].filter((id) => !excelSet.has(id));
const activeRuleIds = new Set(statusRuleIds.active_grouped ?? []);
const activeNotReferencedByJson = [...activeRuleIds].filter((id) => !sourceRuleRefs.has(id));
const referencedNonActive = [...sourceRuleRefs].filter((id) => !activeRuleIds.has(id));

const runtimeImports = `${rulepackRuntime}\n${compilerRuntime}`;
const codeDependency = {
  imports_v1: runtimeImports.includes("scripts.v1"),
  imports_v1_1: runtimeImports.includes("scripts.v1_1"),
};

const result = {
  workbook_sheets: sheetSummary.ndjson,
  excel: {
    rule_count: excelRuleIds.length,
    unique_rule_count: new Set(excelRuleIds).size,
    per_sheet_counts: perSheetCounts,
    principle_count: principleRows.length,
    principle_rows: principleRows,
  },
  skill_catalog: {
    entry_count: skillEntries.length,
    status_counts: statusCounts,
    status_rule_ids: statusRuleIds,
    missing_from_skill: missingFromSkill,
    extra_in_skill: extraInSkill,
    active_not_referenced_by_json: activeNotReferencedByJson,
    referenced_non_active: referencedNonActive,
  },
  rulepack: {
    version: rulepack.version,
    parent_rule_pack_version: rulepack.parent_rule_pack_version,
    calibration_status: rulepack.calibration_status,
    grouped_rule_count: (rulepack.rules ?? []).length,
    audit_rule_count: (rulepack.audit_rules ?? []).length,
    state_rule_count: (rulepack.state_rules ?? []).length,
    source_rule_reference_count: sourceRuleRefs.size,
    supported_principles: rulepack.supported_principles,
    audit_only_principles: rulepack.audit_only_principles,
    deferred_principles: rulepack.deferred_principles,
  },
  profile: {
    card_version: profile.card_version,
    intended_use: profile.intended_use,
    source_response_split: profile.source_response_split,
    profile_ids: (profile.cards ?? []).map((card) => card.profile_id),
  },
  code_dependency: codeDependency,
  version_nonclaims_present: {
    not_human_memory_model: versionText.includes("not a human-memory model"),
    no_formal_human_calibration: versionText.includes("does not perform formal human calibration"),
  },
};

console.log(JSON.stringify(result, null, 2));
process.exit(0);

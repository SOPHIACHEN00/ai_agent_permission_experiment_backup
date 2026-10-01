import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/Study/Graduate_Study_UofG/Research/paper/Week67/QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx";
const outputPath = "D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_s_qstn_versioning/evidence_snapshot.json";

const workbook = await SpreadsheetFile.importXlsx(await FileBlob.load(inputPath));
const principlesSheet = workbook.worksheets.getItem("Principle_Coverage");
const principleValues = principlesSheet.getUsedRange(true).values;
const principles = principleValues.slice(6).filter((row) => row[0]).map((row) => ({
  id: row[0],
  english: row[1],
  chinese: row[2],
  status: row[3],
  rule_ids: row[4],
  covered: row[5],
  gap: row[6],
  layer: row[7],
  priority: row[8],
}));

const ruleSheets = [
  "Cao_Rules",
  "Wijesekera_2017_Rules",
  "Elbitar_2021_Rules",
  "Wijesekera_2015_Rules",
  "Malkin_2022_Rules",
  "Harborth_2021_Rules",
  "Esterwood_2023_Rules",
];
const rules = [];
for (const sheetName of ruleSheets) {
  const rows = workbook.worksheets.getItem(sheetName).getUsedRange(true).values;
  for (const row of rows.slice(4)) {
    if (!row[0]) continue;
    rules.push({
      sheet: sheetName,
      rule_id: row[0],
      name: row[1],
      summary: row[2],
      evidence_rating: row[3],
      model_rule: row[4],
      evidence_boundary: row[8],
    });
  }
}

const snapshot = {
  workbook_summary: await workbook.inspect({ kind: "workbook,sheet", maxChars: 4000 }),
  principles,
  rules,
};
await fs.writeFile(outputPath, JSON.stringify(snapshot, null, 2), "utf8");

console.log("=== PRINCIPLES ===");
console.log(JSON.stringify(principles, null, 2));
console.log("=== RULE COUNT ===");
console.log(rules.length);
console.log("=== RULE INDEX ===");
console.log(JSON.stringify(rules.map(({ sheet, rule_id, name, evidence_rating }) => ({ sheet, rule_id, name, evidence_rating })), null, 2));
console.log(`Saved ${outputPath}`);

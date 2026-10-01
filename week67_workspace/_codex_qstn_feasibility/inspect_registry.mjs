import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/Study/Graduate_Study_UofG/Research/paper/Week67/QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx";
const outputPath = "D:/Study/Graduate_Study_UofG/Research/paper/Week67/_codex_qstn_feasibility/registry_data.json";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const summary = await workbook.inspect({
  kind: "workbook,sheet,table,definedName",
  maxChars: 12000,
  tableMaxRows: 8,
  tableMaxCols: 16,
  tableMaxCellChars: 120,
});
console.log("=== SUMMARY ===");
console.log(summary.ndjson ?? summary);

const sheetInfo = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 4000 });
console.log("=== SHEETS ===");
console.log(sheetInfo.ndjson ?? sheetInfo);

const data = {};
for (let i = 0; i < 30; i += 1) {
  let sheet;
  try {
    sheet = workbook.worksheets.getItemAt(i);
  } catch {
    break;
  }
  if (!sheet) break;
  const used = sheet.getUsedRange(true);
  if (!used) continue;
  const values = used.values;
  const formulas = used.formulas;
  data[sheet.name] = {
    address: used.address ?? null,
    rowCount: values?.length ?? 0,
    colCount: values?.[0]?.length ?? 0,
    values,
    formulas,
  };
  console.log(`=== ${sheet.name} ${used.address ?? ""} (${values?.length ?? 0}x${values?.[0]?.length ?? 0}) ===`);
  console.log(JSON.stringify(values?.slice(0, 12), null, 2));
}

await fs.writeFile(outputPath, JSON.stringify(data, null, 2), "utf8");
console.log(`Saved ${outputPath}`);

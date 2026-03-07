#!/usr/bin/env node

/**
 * Financial Planning Report Generator
 *
 * Usage:
 *   node src/index.js              Generate both PDF and interactive reports
 *   node src/index.js --pdf        Generate PDF report only
 *   node src/index.js --interactive Generate interactive HTML report only
 *   node src/index.js --all        Generate all reports (same as default)
 */

const path = require("path");
const fs = require("fs");
const { buildPDFReport } = require("./pdf-report");
const { buildInteractiveReport } = require("./interactive-report");

const OUTPUT_DIR = path.join(__dirname, "..", "output");

async function main() {
  const args = process.argv.slice(2);
  const pdfOnly = args.includes("--pdf");
  const interactiveOnly = args.includes("--interactive");
  const generateAll = !pdfOnly && !interactiveOnly;

  // Ensure output directory exists
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log("╔══════════════════════════════════════════════╗");
  console.log("║   Financial Planning Report Generator        ║");
  console.log("╚══════════════════════════════════════════════╝\n");

  if (generateAll || interactiveOnly) {
    console.log("  Generating interactive HTML report...");
    const htmlPath = buildInteractiveReport(OUTPUT_DIR);
    console.log(`  ✓ Interactive report: ${htmlPath}\n`);
  }

  if (generateAll || pdfOnly) {
    console.log("  Generating PDF report...");
    const pdfPath = await buildPDFReport(OUTPUT_DIR);
    console.log(`  ✓ PDF report: ${pdfPath}\n`);
  }

  console.log("  Done! Open the files in the output/ directory to view your reports.");
}

main().catch((err) => {
  console.error("Error generating reports:", err);
  process.exit(1);
});

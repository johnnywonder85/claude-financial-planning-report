/**
 * PDF report generator using PDFKit.
 * Creates a professional multi-page financial planning PDF.
 */

const fs = require("fs");
const path = require("path");
const PDFDocument = require("pdfkit");
const { financialData, formatCurrency, formatPercent } = require("./data");

const COLORS = {
  primary: "#1e40af",
  primaryLight: "#3b82f6",
  success: "#059669",
  warning: "#d97706",
  danger: "#dc2626",
  text: "#1e293b",
  muted: "#64748b",
  border: "#e2e8f0",
  bg: "#f8fafc",
  white: "#ffffff",
};

function drawHeader(doc) {
  doc.rect(0, 0, doc.page.width, 120).fill(COLORS.primary);
  doc.fontSize(28).fillColor(COLORS.white).text("Financial Planning Report", 50, 35);
  doc.fontSize(12).fillColor("#bfdbfe").text(`Prepared for ${financialData.profile.name}  |  ${financialData.profile.date}`, 50, 72);
  doc.text(`Plan Horizon: ${financialData.profile.planHorizon}  |  ${financialData.profile.advisor}`, 50, 90);
  doc.fillColor(COLORS.text);
  return 140;
}

function drawSectionTitle(doc, title, y) {
  doc.fontSize(18).fillColor(COLORS.primary).text(title, 50, y);
  doc.moveTo(50, y + 24).lineTo(545, y + 24).strokeColor(COLORS.border).lineWidth(1).stroke();
  return y + 36;
}

function drawKPI(doc, label, value, x, y, width) {
  doc.roundedRect(x, y, width, 60, 6).fillAndStroke(COLORS.bg, COLORS.border);
  doc.fontSize(20).fillColor(COLORS.primary).text(value, x, y + 10, { width, align: "center" });
  doc.fontSize(9).fillColor(COLORS.muted).text(label, x, y + 38, { width, align: "center" });
}

function drawTable(doc, headers, rows, x, startY, colWidths) {
  let y = startY;
  const totalWidth = colWidths.reduce((a, b) => a + b, 0);

  // Header
  doc.rect(x, y, totalWidth, 22).fill("#eef2ff");
  let cx = x;
  headers.forEach((h, i) => {
    doc.fontSize(9).fillColor(COLORS.muted).text(h, cx + 6, y + 6, { width: colWidths[i] - 12 });
    cx += colWidths[i];
  });
  y += 22;

  // Rows
  rows.forEach((row, ri) => {
    if (ri % 2 === 0) doc.rect(x, y, totalWidth, 20).fill("#fafbfc");
    cx = x;
    row.forEach((cell, ci) => {
      const isAmount = ci === row.length - 1;
      doc.fontSize(10).fillColor(COLORS.text).text(cell, cx + 6, y + 4, {
        width: colWidths[ci] - 12,
        align: isAmount ? "right" : "left",
      });
      cx += colWidths[ci];
    });
    y += 20;
  });
  return y;
}

function drawProgressBar(doc, x, y, width, pct, onTrack) {
  doc.roundedRect(x, y, width, 8, 4).fill(COLORS.border);
  const fillWidth = Math.max(4, (pct / 100) * width);
  doc.roundedRect(x, y, fillWidth, 8, 4).fill(onTrack ? COLORS.success : COLORS.warning);
}

function drawSimpleBar(doc, x, y, width, height, values, maxVal, colors) {
  const barWidth = (width / values.length) * 0.7;
  const gap = (width / values.length) * 0.3;
  values.forEach((v, i) => {
    const barH = (v / maxVal) * height;
    const bx = x + i * (barWidth + gap);
    doc.rect(bx, y + height - barH, barWidth, barH).fill(colors[i % colors.length]);
  });
}

function buildPDFReport(outputDir) {
  return new Promise((resolve, reject) => {
    const d = financialData;
    const outputPath = path.join(outputDir, "financial-report.pdf");
    const doc = new PDFDocument({ size: "letter", margins: { top: 50, bottom: 50, left: 50, right: 50 }, bufferPages: true });
    const stream = fs.createWriteStream(outputPath);
    doc.pipe(stream);

    // ─── PAGE 1: Overview ───
    let y = drawHeader(doc);
    y = drawSectionTitle(doc, "Financial Overview", y);

    const kpiW = 118;
    const kpiGap = 7;
    drawKPI(doc, "Net Worth", formatCurrency(d.summary.netWorth), 50, y, kpiW);
    drawKPI(doc, "Annual Income", formatCurrency(d.summary.annualIncome), 50 + kpiW + kpiGap, y, kpiW);
    drawKPI(doc, "Annual Expenses", formatCurrency(d.summary.annualExpenses), 50 + 2 * (kpiW + kpiGap), y, kpiW);
    drawKPI(doc, "Savings Rate", formatPercent(d.summary.savingsRate), 50 + 3 * (kpiW + kpiGap), y, kpiW);
    y += 80;

    // Assets table
    y = drawSectionTitle(doc, "Assets", y);
    const assetRows = d.assets.map((a) => [a.category, formatCurrency(a.value)]);
    assetRows.push(["TOTAL", formatCurrency(d.summary.totalAssets)]);
    y = drawTable(doc, ["Category", "Value"], assetRows, 50, y, [340, 155]);
    y += 16;

    // Liabilities table
    y = drawSectionTitle(doc, "Liabilities", y);
    const liabRows = d.liabilities.map((l) => [l.category, `${l.rate}%`, formatCurrency(l.monthlyPayment), formatCurrency(l.value)]);
    liabRows.push(["TOTAL", "", "", formatCurrency(d.summary.totalLiabilities)]);
    y = drawTable(doc, ["Category", "Rate", "Monthly", "Balance"], liabRows, 50, y, [200, 70, 110, 115]);

    // ─── PAGE 2: Income, Expenses, Portfolio ───
    doc.addPage();
    y = 50;
    y = drawSectionTitle(doc, "Income Sources", y);
    const incomeRows = d.income.labels.map((l, i) => [l, formatCurrency(d.income.values[i])]);
    incomeRows.push(["TOTAL", formatCurrency(d.income.values.reduce((a, b) => a + b, 0))]);
    y = drawTable(doc, ["Source", "Annual Amount"], incomeRows, 50, y, [340, 155]);
    y += 24;

    y = drawSectionTitle(doc, "Expense Breakdown", y);
    const expenseRows = d.expenses.labels.map((l, i) => [l, formatCurrency(d.expenses.values[i])]);
    expenseRows.push(["TOTAL", formatCurrency(d.expenses.values.reduce((a, b) => a + b, 0))]);
    y = drawTable(doc, ["Category", "Annual Amount"], expenseRows, 50, y, [340, 155]);
    y += 24;

    y = drawSectionTitle(doc, "Portfolio Allocation", y);
    const allocRows = d.portfolioAllocation.labels.map((l, i) => [l, `${d.portfolioAllocation.values[i]}%`]);
    y = drawTable(doc, ["Asset Class", "Allocation"], allocRows, 50, y, [340, 155]);

    // ─── PAGE 3: Goals & Projections ───
    doc.addPage();
    y = 50;
    y = drawSectionTitle(doc, "Financial Goals", y);

    d.goals.forEach((g) => {
      const pct = Math.min(100, ((g.current / g.target) * 100)).toFixed(1);
      doc.fontSize(13).fillColor(COLORS.text).text(g.name, 50, y);
      const statusColor = g.onTrack ? COLORS.success : COLORS.danger;
      const statusText = g.onTrack ? "On Track" : "Needs Attention";
      doc.fontSize(9).fillColor(statusColor).text(statusText, 420, y, { width: 125, align: "right" });
      y += 20;
      drawProgressBar(doc, 50, y, 495, parseFloat(pct), g.onTrack);
      y += 14;
      doc.fontSize(9).fillColor(COLORS.muted).text(
        `${formatCurrency(g.current)} of ${formatCurrency(g.target)} (${pct}%)  |  ${g.yearsLeft} years remaining  |  ${formatCurrency(g.monthlyNeeded)}/mo needed`,
        50, y
      );
      y += 26;
    });
    y += 12;

    y = drawSectionTitle(doc, "Net Worth Projections", y);
    doc.fontSize(10).fillColor(COLORS.muted).text("Projections based on conservative (5%), moderate (7%), and aggressive (10%) annual returns.", 50, y);
    y += 20;

    const projRows = d.projections.years.map((yr, i) => [
      yr.toString(),
      formatCurrency(d.projections.conservative[i]),
      formatCurrency(d.projections.moderate[i]),
      formatCurrency(d.projections.aggressive[i]),
    ]);
    y = drawTable(doc, ["Year", "Conservative (5%)", "Moderate (7%)", "Aggressive (10%)"], projRows, 50, y, [80, 140, 140, 135]);

    // ─── PAGE 4: Recommendations ───
    doc.addPage();
    y = 50;
    y = drawSectionTitle(doc, "Recommendations", y);

    d.recommendations.forEach((r, i) => {
      // Card background
      doc.roundedRect(50, y, 495, 78, 6).fillAndStroke(COLORS.bg, COLORS.border);
      doc.fontSize(13).fillColor(COLORS.primary).text(`${i + 1}. ${r.title}`, 62, y + 10, { width: 380 });

      const impactColor = r.impact === "High" ? COLORS.primary : COLORS.warning;
      doc.fontSize(9).fillColor(impactColor).text(`${r.impact} Impact`, 440, y + 12, { width: 95, align: "right" });
      doc.fontSize(10).fillColor(COLORS.text).text(r.description, 62, y + 30, { width: 470 });
      doc.fontSize(9).fillColor(COLORS.muted).text(`Timeline: ${r.timeline}`, 62, y + 58);
      y += 92;
    });

    y += 16;
    y = drawSectionTitle(doc, "Risk Profile", y);
    doc.fontSize(36).fillColor(COLORS.primary).text(d.riskScore.score.toString(), 50, y, { width: 495, align: "center" });
    y += 48;
    doc.fontSize(16).fillColor(COLORS.text).text(d.riskScore.label, 50, y, { width: 495, align: "center" });
    y += 24;
    doc.fontSize(11).fillColor(COLORS.muted).text(d.riskScore.description, 100, y, { width: 395, align: "center" });

    // Footer on all pages
    const pageCount = doc.bufferedPageRange().count;
    for (let i = 0; i < pageCount; i++) {
      doc.switchToPage(i);
      doc.fontSize(8).fillColor(COLORS.muted)
        .text(`${d.profile.advisor}  |  Confidential  |  Page ${i + 1} of ${pageCount}`, 50, doc.page.height - 40, {
          width: 495,
          align: "center",
        });
    }

    doc.end();
    stream.on("finish", () => resolve(outputPath));
    stream.on("error", reject);
  });
}

module.exports = { buildPDFReport };

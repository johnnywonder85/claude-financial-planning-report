/**
 * Interactive HTML report generator.
 * Creates a self-contained HTML file with Chart.js dashboards.
 */

const fs = require("fs");
const path = require("path");
const { financialData, formatCurrency, formatPercent } = require("./data");

function generateGoalCards(goals) {
  return goals
    .map((g) => {
      const pct = Math.min(100, ((g.current / g.target) * 100).toFixed(1));
      const statusClass = g.onTrack ? "on-track" : "off-track";
      const statusLabel = g.onTrack ? "On Track" : "Needs Attention";
      return `
      <div class="goal-card">
        <div class="goal-header">
          <h4>${g.name}</h4>
          <span class="badge ${statusClass}">${statusLabel}</span>
        </div>
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%"></div></div>
        <div class="goal-details">
          <span>${formatCurrency(g.current)} of ${formatCurrency(g.target)}</span>
          <span>${pct}%</span>
        </div>
        <p class="goal-meta">${g.yearsLeft} years remaining &middot; ${formatCurrency(g.monthlyNeeded)}/mo needed</p>
      </div>`;
    })
    .join("\n");
}

function generateRecommendations(recs) {
  return recs
    .map(
      (r) => `
      <div class="rec-card">
        <div class="rec-header">
          <h4>${r.title}</h4>
          <span class="badge impact-${r.impact.toLowerCase()}">${r.impact} Impact</span>
        </div>
        <p>${r.description}</p>
        <span class="rec-timeline">Timeline: ${r.timeline}</span>
      </div>`
    )
    .join("\n");
}

function generateBalanceSheet(assets, liabilities) {
  const assetRows = assets.map((a) => `<tr><td>${a.category}</td><td class="amount positive">${formatCurrency(a.value)}</td></tr>`).join("");
  const liabRows = liabilities.map((l) => `<tr><td>${l.category} <small>(${l.rate}% APR)</small></td><td class="amount negative">${formatCurrency(l.value)}</td></tr>`).join("");
  return { assetRows, liabRows };
}

function generateHTML() {
  const d = financialData;
  const { assetRows, liabRows } = generateBalanceSheet(d.assets, d.liabilities);

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Financial Planning Report — ${d.profile.name}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --primary: #1e40af;
    --primary-light: #3b82f6;
    --success: #059669;
    --warning: #d97706;
    --danger: #dc2626;
    --bg: #f8fafc;
    --card: #ffffff;
    --text: #1e293b;
    --text-muted: #64748b;
    --border: #e2e8f0;
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --radius: 12px;
  }
  [data-theme="dark"] {
    --primary: #60a5fa;
    --primary-light: #93c5fd;
    --bg: #0f172a;
    --card: #1e293b;
    --text: #f1f5f9;
    --text-muted: #94a3b8;
    --border: #334155;
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  header { background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%); color: #fff; padding: 40px 0; margin-bottom: 32px; }
  header .container { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
  header h1 { font-size: 28px; font-weight: 700; }
  header p { opacity: 0.9; font-size: 14px; }
  .header-right { text-align: right; }
  .theme-toggle { background: rgba(255,255,255,0.2); border: none; color: #fff; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 14px; }
  .theme-toggle:hover { background: rgba(255,255,255,0.3); }

  /* Navigation tabs */
  .tabs { display: flex; gap: 4px; background: var(--card); border-radius: var(--radius); padding: 4px; margin-bottom: 24px; border: 1px solid var(--border); overflow-x: auto; }
  .tab { padding: 10px 20px; border: none; background: none; cursor: pointer; border-radius: 8px; font-size: 14px; font-weight: 500; color: var(--text-muted); white-space: nowrap; transition: all 0.2s; }
  .tab:hover { background: var(--bg); color: var(--text); }
  .tab.active { background: var(--primary); color: #fff; }
  .section { display: none; }
  .section.active { display: block; }

  /* Cards & Grid */
  .grid { display: grid; gap: 20px; }
  .grid-2 { grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); }
  .grid-3 { grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); }
  .grid-4 { grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); }
  .card { background: var(--card); border-radius: var(--radius); padding: 24px; box-shadow: var(--shadow); border: 1px solid var(--border); }
  .card h3 { font-size: 16px; color: var(--text-muted); margin-bottom: 16px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

  /* KPI cards */
  .kpi { text-align: center; }
  .kpi .value { font-size: 32px; font-weight: 700; color: var(--primary); }
  .kpi .label { font-size: 13px; color: var(--text-muted); margin-top: 4px; }

  /* Charts */
  .chart-container { position: relative; width: 100%; max-height: 350px; }
  canvas { max-width: 100%; }

  /* Tables */
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); font-size: 14px; }
  th { font-weight: 600; color: var(--text-muted); font-size: 12px; text-transform: uppercase; }
  .amount { text-align: right; font-variant-numeric: tabular-nums; font-weight: 500; }
  .positive { color: var(--success); }
  .negative { color: var(--danger); }

  /* Goals */
  .goal-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
  .goal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
  .goal-header h4 { font-size: 16px; }
  .progress-bar { height: 8px; background: var(--border); border-radius: 4px; overflow: hidden; margin-bottom: 8px; }
  .progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary), var(--primary-light)); border-radius: 4px; transition: width 1s ease; }
  .goal-details { display: flex; justify-content: space-between; font-size: 13px; color: var(--text-muted); }
  .goal-meta { font-size: 12px; color: var(--text-muted); margin-top: 8px; }

  /* Badges */
  .badge { padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }
  .on-track { background: #d1fae5; color: #065f46; }
  .off-track { background: #fee2e2; color: #991b1b; }
  .impact-high { background: #dbeafe; color: #1e40af; }
  .impact-medium { background: #fef3c7; color: #92400e; }
  [data-theme="dark"] .on-track { background: #064e3b; color: #6ee7b7; }
  [data-theme="dark"] .off-track { background: #7f1d1d; color: #fca5a5; }
  [data-theme="dark"] .impact-high { background: #1e3a5f; color: #93c5fd; }
  [data-theme="dark"] .impact-medium { background: #78350f; color: #fcd34d; }

  /* Recommendations */
  .rec-card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; }
  .rec-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; flex-wrap: wrap; gap: 8px; }
  .rec-header h4 { font-size: 15px; }
  .rec-card p { font-size: 14px; color: var(--text-muted); margin-bottom: 8px; }
  .rec-timeline { font-size: 12px; color: var(--primary); font-weight: 500; }

  /* Risk meter */
  .risk-meter { text-align: center; padding: 24px; }
  .risk-gauge { width: 200px; height: 100px; margin: 0 auto 16px; position: relative; }
  .risk-score { font-size: 48px; font-weight: 700; color: var(--primary); }
  .risk-label { font-size: 18px; font-weight: 600; margin: 8px 0; }
  .risk-desc { font-size: 14px; color: var(--text-muted); max-width: 400px; margin: 0 auto; }

  /* Print */
  @media print {
    header { background: #1e40af !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .tabs, .theme-toggle { display: none; }
    .section { display: block !important; page-break-inside: avoid; margin-bottom: 24px; }
  }
  @media (max-width: 768px) {
    header h1 { font-size: 22px; }
    .kpi .value { font-size: 24px; }
    .container { padding: 16px; }
  }
</style>
</head>
<body>
<header>
  <div class="container">
    <div>
      <h1>Financial Planning Report</h1>
      <p>Prepared for <strong>${d.profile.name}</strong> &middot; ${d.profile.date}</p>
      <p>Plan Horizon: ${d.profile.planHorizon}</p>
    </div>
    <div class="header-right">
      <p>${d.profile.advisor}</p>
      <button class="theme-toggle" onclick="toggleTheme()">Toggle Dark Mode</button>
    </div>
  </div>
</header>

<div class="container">
  <div class="tabs">
    <button class="tab active" onclick="showSection('overview')">Overview</button>
    <button class="tab" onclick="showSection('income-expenses')">Income & Expenses</button>
    <button class="tab" onclick="showSection('portfolio')">Portfolio</button>
    <button class="tab" onclick="showSection('balance-sheet')">Balance Sheet</button>
    <button class="tab" onclick="showSection('goals')">Goals</button>
    <button class="tab" onclick="showSection('projections')">Projections</button>
    <button class="tab" onclick="showSection('recommendations')">Recommendations</button>
  </div>

  <!-- OVERVIEW -->
  <div id="overview" class="section active">
    <div class="grid grid-4" style="margin-bottom:24px">
      <div class="card kpi"><div class="value">${formatCurrency(d.summary.netWorth)}</div><div class="label">Net Worth</div></div>
      <div class="card kpi"><div class="value">${formatCurrency(d.summary.annualIncome)}</div><div class="label">Annual Income</div></div>
      <div class="card kpi"><div class="value">${formatPercent(d.summary.savingsRate)}</div><div class="label">Savings Rate</div></div>
      <div class="card kpi"><div class="value">${d.summary.emergencyFundMonths}</div><div class="label">Emergency Fund (months)</div></div>
    </div>
    <div class="grid grid-2">
      <div class="card">
        <h3>Net Worth Breakdown</h3>
        <div class="chart-container"><canvas id="netWorthChart"></canvas></div>
      </div>
      <div class="card risk-meter">
        <h3>Risk Profile</h3>
        <div class="risk-score">${d.riskScore.score}</div>
        <div class="risk-label">${d.riskScore.label}</div>
        <p class="risk-desc">${d.riskScore.description}</p>
      </div>
    </div>
  </div>

  <!-- INCOME & EXPENSES -->
  <div id="income-expenses" class="section">
    <div class="grid grid-2" style="margin-bottom:24px">
      <div class="card">
        <h3>Income Sources</h3>
        <div class="chart-container"><canvas id="incomeChart"></canvas></div>
      </div>
      <div class="card">
        <h3>Expense Breakdown</h3>
        <div class="chart-container"><canvas id="expenseChart"></canvas></div>
      </div>
    </div>
    <div class="card">
      <h3>Monthly Cash Flow (12-Month View)</h3>
      <div class="chart-container"><canvas id="cashFlowChart"></canvas></div>
    </div>
  </div>

  <!-- PORTFOLIO -->
  <div id="portfolio" class="section">
    <div class="grid grid-2">
      <div class="card">
        <h3>Asset Allocation</h3>
        <div class="chart-container"><canvas id="allocationChart"></canvas></div>
      </div>
      <div class="card">
        <h3>Allocation Details</h3>
        <table>
          <thead><tr><th>Asset Class</th><th class="amount">Allocation</th></tr></thead>
          <tbody>
            ${d.portfolioAllocation.labels.map((l, i) => `<tr><td>${l}</td><td class="amount">${d.portfolioAllocation.values[i]}%</td></tr>`).join("")}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- BALANCE SHEET -->
  <div id="balance-sheet" class="section">
    <div class="grid grid-2">
      <div class="card">
        <h3>Assets — ${formatCurrency(d.summary.totalAssets)}</h3>
        <table>
          <thead><tr><th>Category</th><th class="amount">Value</th></tr></thead>
          <tbody>${assetRows}</tbody>
        </table>
      </div>
      <div class="card">
        <h3>Liabilities — ${formatCurrency(d.summary.totalLiabilities)}</h3>
        <table>
          <thead><tr><th>Category</th><th class="amount">Balance</th></tr></thead>
          <tbody>${liabRows}</tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- GOALS -->
  <div id="goals" class="section">
    <div class="grid grid-2">
      ${generateGoalCards(d.goals)}
    </div>
  </div>

  <!-- PROJECTIONS -->
  <div id="projections" class="section">
    <div class="card">
      <h3>Net Worth Projections (Conservative / Moderate / Aggressive)</h3>
      <div class="chart-container"><canvas id="projectionsChart"></canvas></div>
    </div>
  </div>

  <!-- RECOMMENDATIONS -->
  <div id="recommendations" class="section">
    <div class="grid grid-2">
      ${generateRecommendations(d.recommendations)}
    </div>
  </div>
</div>

<script>
// Theme toggle
function toggleTheme() {
  document.body.dataset.theme = document.body.dataset.theme === 'dark' ? '' : 'dark';
  Object.values(Chart.instances).forEach(c => {
    c.options.plugins.legend.labels.color = getComputedStyle(document.body).getPropertyValue('--text-muted').trim();
    c.update();
  });
}

// Tab navigation
function showSection(id) {
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  event.target.classList.add('active');
}

// Chart defaults
Chart.defaults.font.family = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif";
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

const data = ${JSON.stringify(d)};

// Net Worth donut
new Chart(document.getElementById('netWorthChart'), {
  type: 'doughnut',
  data: {
    labels: ['Assets', 'Liabilities'],
    datasets: [{
      data: [${d.summary.totalAssets}, ${d.summary.totalLiabilities}],
      backgroundColor: ['#2563eb', '#dc2626'],
      borderWidth: 0
    }]
  },
  options: { cutout: '65%', plugins: { legend: { position: 'bottom' } } }
});

// Income chart
new Chart(document.getElementById('incomeChart'), {
  type: 'doughnut',
  data: {
    labels: ${JSON.stringify(d.income.labels)},
    datasets: [{ data: ${JSON.stringify(d.income.values)}, backgroundColor: ['#2563eb','#7c3aed','#059669','#d97706','#ec4899'], borderWidth: 0 }]
  },
  options: { cutout: '55%', plugins: { legend: { position: 'bottom' } } }
});

// Expense chart
new Chart(document.getElementById('expenseChart'), {
  type: 'bar',
  data: {
    labels: ${JSON.stringify(d.expenses.labels)},
    datasets: [{ label: 'Annual ($)', data: ${JSON.stringify(d.expenses.values)}, backgroundColor: '#3b82f6', borderRadius: 6 }]
  },
  options: { indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { ticks: { callback: v => '$' + (v/1000) + 'k' } } } }
});

// Cash flow chart
new Chart(document.getElementById('cashFlowChart'), {
  type: 'bar',
  data: {
    labels: ${JSON.stringify(d.monthlyBudget.labels)},
    datasets: [
      { label: 'Income', data: ${JSON.stringify(d.monthlyBudget.income)}, backgroundColor: '#059669', borderRadius: 4 },
      { label: 'Expenses', data: ${JSON.stringify(d.monthlyBudget.expenses)}, backgroundColor: '#dc2626', borderRadius: 4 }
    ]
  },
  options: { plugins: { legend: { position: 'top' } }, scales: { y: { ticks: { callback: v => '$' + (v/1000) + 'k' } } } }
});

// Allocation pie
new Chart(document.getElementById('allocationChart'), {
  type: 'pie',
  data: {
    labels: ${JSON.stringify(d.portfolioAllocation.labels)},
    datasets: [{ data: ${JSON.stringify(d.portfolioAllocation.values)}, backgroundColor: ${JSON.stringify(d.portfolioAllocation.colors)}, borderWidth: 0 }]
  },
  options: { plugins: { legend: { position: 'bottom' } } }
});

// Projections line chart
new Chart(document.getElementById('projectionsChart'), {
  type: 'line',
  data: {
    labels: ${JSON.stringify(d.projections.years)},
    datasets: [
      { label: 'Conservative (5%)', data: ${JSON.stringify(d.projections.conservative)}, borderColor: '#6b7280', backgroundColor: 'rgba(107,114,128,0.1)', fill: true, tension: 0.3 },
      { label: 'Moderate (7%)', data: ${JSON.stringify(d.projections.moderate)}, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.1)', fill: true, tension: 0.3 },
      { label: 'Aggressive (10%)', data: ${JSON.stringify(d.projections.aggressive)}, borderColor: '#059669', backgroundColor: 'rgba(5,150,105,0.1)', fill: true, tension: 0.3 }
    ]
  },
  options: { plugins: { legend: { position: 'top' } }, scales: { y: { ticks: { callback: v => '$' + (v >= 1000000 ? (v/1000000).toFixed(1) + 'M' : (v/1000) + 'k') } } } }
});
</script>
</body>
</html>`;
}

function buildInteractiveReport(outputDir) {
  const html = generateHTML();
  const outputPath = path.join(outputDir, "financial-report.html");
  fs.writeFileSync(outputPath, html, "utf-8");
  return outputPath;
}

module.exports = { buildInteractiveReport };

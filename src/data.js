/**
 * Financial planning data module.
 * Contains sample portfolio, income, expenses, goals, and projections.
 */

const financialData = {
  profile: {
    name: "Alex & Jordan Mitchell",
    date: new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }),
    advisor: "Claude Financial Planning",
    planHorizon: "2026–2056 (30 years)",
  },

  summary: {
    totalAssets: 785000,
    totalLiabilities: 215000,
    netWorth: 570000,
    annualIncome: 185000,
    annualExpenses: 132000,
    savingsRate: 28.6,
    emergencyFundMonths: 6.2,
  },

  income: {
    labels: ["Salary (Alex)", "Salary (Jordan)", "Rental Income", "Dividends", "Side Business"],
    values: [105000, 62000, 9600, 4800, 3600],
  },

  expenses: {
    labels: ["Housing", "Transportation", "Food & Dining", "Insurance", "Healthcare", "Education", "Entertainment", "Savings & Investments", "Utilities", "Other"],
    values: [28800, 12000, 9600, 7200, 5400, 4800, 3600, 42000, 6000, 12600],
  },

  assets: [
    { category: "Retirement (401k/IRA)", value: 320000 },
    { category: "Taxable Investments", value: 145000 },
    { category: "Real Estate (Primary)", value: 185000 },
    { category: "Emergency Fund", value: 48000 },
    { category: "HSA", value: 22000 },
    { category: "Crypto & Alternative", value: 18000 },
    { category: "Cash & Checking", value: 15000 },
    { category: "529 Education", value: 32000 },
  ],

  liabilities: [
    { category: "Mortgage", value: 165000, rate: 3.75, monthlyPayment: 1540 },
    { category: "Student Loans", value: 28000, rate: 4.5, monthlyPayment: 380 },
    { category: "Auto Loan", value: 22000, rate: 5.2, monthlyPayment: 420 },
  ],

  portfolioAllocation: {
    labels: ["US Stocks", "International Stocks", "Bonds", "Real Estate (REITs)", "Cash & Equivalents", "Alternative"],
    values: [42, 18, 22, 8, 6, 4],
    colors: ["#2563eb", "#7c3aed", "#059669", "#d97706", "#6b7280", "#dc2626"],
  },

  goals: [
    { name: "Retirement at 60", target: 2500000, current: 465000, yearsLeft: 22, monthlyNeeded: 2800, onTrack: true },
    { name: "Children's College Fund", target: 200000, current: 32000, yearsLeft: 12, monthlyNeeded: 1050, onTrack: true },
    { name: "Pay Off Mortgage", target: 165000, current: 0, yearsLeft: 9, monthlyNeeded: 1540, onTrack: true },
    { name: "Vacation Home", target: 350000, current: 45000, yearsLeft: 15, monthlyNeeded: 1420, onTrack: false },
  ],

  projections: {
    years: [2026, 2028, 2030, 2032, 2034, 2036, 2038, 2040, 2042, 2044, 2046, 2048],
    conservative: [570000, 650000, 745000, 855000, 980000, 1125000, 1290000, 1480000, 1695000, 1945000, 2230000, 2555000],
    moderate: [570000, 680000, 810000, 965000, 1150000, 1370000, 1630000, 1940000, 2310000, 2750000, 3275000, 3900000],
    aggressive: [570000, 720000, 900000, 1125000, 1405000, 1755000, 2195000, 2745000, 3430000, 4285000, 5360000, 6700000],
  },

  monthlyBudget: {
    labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    income: [15400, 15400, 15400, 15900, 15400, 15400, 15400, 15400, 15400, 15400, 15400, 18900],
    expenses: [11200, 10800, 11500, 10900, 11800, 12200, 11000, 12500, 11100, 10700, 12800, 14500],
  },

  recommendations: [
    {
      title: "Increase 401(k) Contributions",
      description: "Maximize employer match by increasing contributions from 12% to 15% of salary. This adds ~$5,250/year in tax-advantaged growth.",
      impact: "High",
      timeline: "Immediate",
    },
    {
      title: "Refinance Auto Loan",
      description: "Current rate of 5.2% can likely be reduced to ~3.8% with your credit score, saving ~$840 over the remaining term.",
      impact: "Medium",
      timeline: "1-2 months",
    },
    {
      title: "Rebalance Portfolio",
      description: "International equity allocation is below target. Consider shifting 3-4% from US stocks to international index funds for better diversification.",
      impact: "Medium",
      timeline: "Next quarter",
    },
    {
      title: "Establish Roth Conversion Ladder",
      description: "Begin gradual Roth conversions to reduce future tax burden in retirement. Target $20,000-30,000/year in conversions.",
      impact: "High",
      timeline: "Before year-end",
    },
    {
      title: "Review Insurance Coverage",
      description: "Consider umbrella policy ($1M) and review term life coverage. Current coverage may be insufficient for dual-income household.",
      impact: "Medium",
      timeline: "3-6 months",
    },
  ],

  riskScore: {
    score: 68,
    label: "Moderate-Aggressive",
    description: "Suitable for investors with a long time horizon who can tolerate short-term market fluctuations.",
  },
};

function formatCurrency(value) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function formatPercent(value) {
  return `${value.toFixed(1)}%`;
}

module.exports = { financialData, formatCurrency, formatPercent };

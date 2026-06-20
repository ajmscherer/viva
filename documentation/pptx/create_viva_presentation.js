const pptxgen = require("pptxgenjs");

let pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';
pres.author = 'Grok for Alexandre Scherer';
pres.title = 'Viva: Cash Flow Examples';
pres.subject = 'Scaffolding presentation introducing Viva language examples';

// Color palette - Teal Trust (professional finance feel)
const colors = {
  primary: "028090",      // Teal
  secondary: "00A896",    // Seafoam
  accent: "02C39A",       // Mint
  dark: "003D4D",         // Deep teal/navy
  light: "F0FDFA",        // Very light teal
  white: "FFFFFF",
  text: "1E293B",         // Slate dark
  muted: "64748B"         // Slate gray
};

// Title Slide
let titleSlide = pres.addSlide();
titleSlide.background = { color: colors.dark };

titleSlide.addText("Viva", {
  x: 0.5, y: 1.5, w: 9, h: 1.2,
  fontSize: 60, fontFace: "Arial", bold: true,
  color: colors.white, align: "center"
});

titleSlide.addText("Cash Flow Modeling Examples", {
  x: 0.5, y: 2.7, w: 9, h: 0.8,
  fontSize: 28, fontFace: "Arial",
  color: colors.accent, align: "center"
});

titleSlide.addText("A scaffolding presentation for the Viva language project\nIntroducing four representative examples", {
  x: 0.5, y: 3.8, w: 9, h: 1,
  fontSize: 16, fontFace: "Arial",
  color: "B0E0E6", align: "center"
});

titleSlide.addText("Alexandre Scherer", {
  x: 0.5, y: 5.1, w: 9, h: 0.4,
  fontSize: 12, fontFace: "Arial",
  color: "A0C4C8", align: "center"
});

// Example data
const examples = [
  {
    id: "paul",
    title: "Paul's Life Planning",
    subtitle: "Core Example from Genesis",
    description: "A young man planning for potential child birth, ongoing savings, and life insurance protection. Demonstrates basic life declarations, probabilistic events, and triggered flows.",
    image: "images/paul.jpg",
    code: "life: Paul, man, born 2005\n\nevent: child_birth, in the next 10 years, uniform annual probability 80%\n\nflow: child_expense, -20k, upon child_birth, for 20 years\nflow: saving, 1k per month\nflow: insurance, 1m, upon Paul.death
// New: upon Paul\'s birth, from Baby\'s birth, 2 years after X.death, 3 million, from year 3 (relative), etc.
  },
  {
    id: "retirement",
    title: "Retirement Planning",
    subtitle: "Long-term Financial Security",
    description: "Models a person's career income, retirement savings contributions (401k + Roth IRA), and post-retirement income streams including Social Security and phased withdrawals, plus late-life healthcare costs.",
    image: "images/retirement.jpg",
    code: "life: Julian, person, born 1980\n\nflow: salary, 150k per year, until retirement\nflow: 401k_contribution, -20k per year, until retirement\n\n event: retirement, at age 65\n\nflow: social_security, 25k per year, upon retirement\nflow: 401k_withdrawal, 60k per year, upon retirement, for 30 years"
  },
  {
    id: "family",
    title: "Family & Education",
    subtitle: "Multi-Generational Planning",
    description: "A family of three planning for childbirth, K-12 education, college tuition, housing, childcare, and life insurance across multiple lives. Shows complex event timing and multi-life interactions.",
    image: "images/family.jpg",
    code: "life: Jordan, person, born 1990\nlife: Spouse, person, born 1992\nlife: Child, person, born 2028\n\nevent: child_birth, in 2028, probability 100%\nevent: child_college, at age 18   # MVP simplified (full 'for Child' deferred)\n\nflow: childcare, -25k per year, upon child_birth, for 5 years\nflow: college_tuition, -50k per year, upon child_college, for 4 years
// Supports birth refs (upon Child\'s birth), \'s possessive, relative years, trillion etc.
  },
  {
    id: "business",
    title: "Small Business Cash Flow",
    subtitle: "Entrepreneurial Finance",
    description: "Models a small business startup: revenue streams, operating expenses, loans, taxes, owner compensation, equipment purchases, and low-probability risk events (e.g. insurance payout on fire).",
    image: "images/business.jpg",
    code: "life: Owner, person, born 1975\n\nevent: business_start, year 2025\nevent: expansion, in 3 years after start, probability 60%\n\nflow: product_sales, 500k per year, upon business_start\nflow: salaries, -250k per year, upon business_start\nflow: startup_loan, 200k, upon business_start\nflow: loan_repayment, -25k per year, for 10 years"
  }
];

// Create one slide per example
examples.forEach((ex, index) => {
  let slide = pres.addSlide();
  slide.background = { color: colors.light };

  // Left accent bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.15, h: 5.625,
    fill: { color: colors.primary }
  });

  // Title
  slide.addText(ex.title, {
    x: 0.5, y: 0.3, w: 5.5, h: 0.6,
    fontSize: 28, fontFace: "Arial", bold: true,
    color: colors.dark
  });

  // Subtitle
  slide.addText(ex.subtitle, {
    x: 0.5, y: 0.85, w: 5.5, h: 0.35,
    fontSize: 14, fontFace: "Arial", italic: true,
    color: colors.primary
  });

  // Description
  slide.addText(ex.description, {
    x: 0.5, y: 1.35, w: 5.5, h: 1.2,
    fontSize: 12, fontFace: "Arial",
    color: colors.text, valign: "top"
  });

  // Code box
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.5, y: 2.7, w: 5.5, h: 2.5,
    fill: { color: "1E293B" },
    rectRadius: 0.08
  });

  slide.addText(ex.code, {
    x: 0.65, y: 2.85, w: 5.2, h: 2.2,
    fontSize: 9, fontFace: "Consolas",
    color: "E2E8F0", valign: "top"
  });

  // Image on right
  slide.addImage({
    path: ex.image,
    x: 6.2, y: 0.8, w: 3.5, h: 2.6,
    sizing: { type: 'cover', w: 3.5, h: 2.6 }
  });

  // Slide number
  slide.addText(`${index + 1} / ${examples.length}`, {
    x: 0.5, y: 5.35, w: 9, h: 0.25,
    fontSize: 10, fontFace: "Arial",
    color: colors.muted, align: "right"
  });
});

// Save
pres.writeFile({ fileName: "./viva_examples_presentation.pptx" })
  .then(() => console.log("Presentation created successfully: viva_examples_presentation.pptx"))
  .catch(err => console.error("Error:", err));

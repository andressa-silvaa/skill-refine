import { firstNameFromUserFullName, iconForInsightKey, monthLabel } from './dashboardFormatters';

describe('monthLabel', () => {
  it('formats valid YYYY-MM period', () => {
    const label = monthLabel('2024-03', 'en-US');
    expect(label).toMatch(/Mar/i);
  });

  it('returns raw period when invalid', () => {
    expect(monthLabel('not-a-period', 'en-US')).toBe('not-a-period');
  });
});

describe('iconForInsightKey', () => {
  it('maps known insight suffixes', () => {
    expect(iconForInsightKey('analysis.insights.improvements.ats_keywords')).toBe('fa-solid fa-key');
    expect(iconForInsightKey('analysis.insights.improvements.add_metrics')).toBe('fa-solid fa-chart-line');
    expect(iconForInsightKey('analysis.insights.improvements.executive_summary')).toBe('fa-solid fa-align-left');
    expect(iconForInsightKey('analysis.insights.improvements.use_action_verbs')).toBe('fa-solid fa-bolt');
    expect(iconForInsightKey('analysis.insights.improvements.relevant_links')).toBe('fa-solid fa-link');
  });

  it('returns default icon for unknown keys', () => {
    expect(iconForInsightKey('analysis.insights.strengths.other')).toBe('fa-solid fa-lightbulb');
  });
});

describe('firstNameFromUserFullName', () => {
  it('returns first token', () => {
    expect(firstNameFromUserFullName('Maria Silva', 'Guest')).toBe('Maria');
  });

  it('returns fallback for empty', () => {
    expect(firstNameFromUserFullName('', 'Guest')).toBe('Guest');
    expect(firstNameFromUserFullName(null, 'Guest')).toBe('Guest');
    expect(firstNameFromUserFullName('   ', 'Guest')).toBe('Guest');
  });

  it('returns fallback when split yields empty', () => {
    expect(firstNameFromUserFullName('\t\n', 'Guest')).toBe('Guest');
  });
});

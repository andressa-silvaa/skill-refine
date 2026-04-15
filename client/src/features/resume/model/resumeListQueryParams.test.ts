import { scoreFilterToRange, updatedFilterToRange } from './resumeListQueryParams';

describe('scoreFilterToRange', () => {
  it('returns include_no_score for none', () => {
    expect(scoreFilterToRange('none')).toEqual({ include_no_score: true });
  });

  it('returns score bands', () => {
    expect(scoreFilterToRange('0-50')).toEqual({ score_min: 0, score_max: 50 });
    expect(scoreFilterToRange('51-70')).toEqual({ score_min: 51, score_max: 70 });
    expect(scoreFilterToRange('71-85')).toEqual({ score_min: 71, score_max: 85 });
    expect(scoreFilterToRange('86-100')).toEqual({ score_min: 86, score_max: 100 });
  });

  it('returns empty object for all', () => {
    expect(scoreFilterToRange('all')).toEqual({});
  });
});

describe('updatedFilterToRange', () => {
  const fixed = new Date(Date.UTC(2024, 5, 15, 12, 0, 0));

  it('returns empty for all', () => {
    expect(updatedFilterToRange('all', fixed)).toEqual({});
  });

  it('returns updated_from 7 days before now (UTC date)', () => {
    expect(updatedFilterToRange('7d', fixed)).toEqual({ updated_from: '2024-06-08' });
  });

  it('returns updated_from 30 days before now (UTC date)', () => {
    expect(updatedFilterToRange('30d', fixed)).toEqual({ updated_from: '2024-05-16' });
  });
});

import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { getApiErrorMessage } from '@/shared/api';
import { Card, Modal } from '@/shared/ui';
import { notify } from '@/shared/lib/notify';

import type { AnalysisResult, ImprovementInsightItem } from '../model/types';
import { resolveExampleContent, resolveImprovementAction, tryAutoApplyImprovement } from '../model/improvementActionMap';
import { InsightListItem } from './InsightListItem';

import './InsightList.css';

type Props = {
  result: AnalysisResult;
  selectedResumeId: string;
};

export function InsightList(props: Props) {
  const { result, selectedResumeId } = props;
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [exampleItem, setExampleItem] = useState<ImprovementInsightItem | null>(null);
  const [applyingKey, setApplyingKey] = useState<string | null>(null);

  const handleSeeExample = (item: ImprovementInsightItem) => {
    setExampleItem(item);
  };

  const exampleContent = useMemo(
    () => (exampleItem ? resolveExampleContent(exampleItem, t) : null),
    [exampleItem, t]
  );

  const openGuidedEdit = (item: ImprovementInsightItem) => {
    const action = resolveImprovementAction(item);
    const params = new URLSearchParams({
      editResumeId: selectedResumeId,
      targetStep: action.targetStep,
      improvementKey: item.key,
    });
    if (action.targetField) {
      params.set('fieldTarget', action.targetField);
    }
    if (item.exampleText) {
      params.set('suggestedText', item.exampleText);
    }

    navigate(`/protected/resumes?${params.toString()}`);
  };

  const handleApply = async (item: ImprovementInsightItem) => {
    if (!selectedResumeId) {
      notify.error(t('analysis.applySelectResumeFirst'));
      return;
    }

    setApplyingKey(item.key);
    try {
      const wasAutoApplied = await tryAutoApplyImprovement(selectedResumeId, item);
      if (wasAutoApplied) {
        notify.success(t('analysis.applySuccessAuto'));
        return;
      }

      openGuidedEdit(item);
      notify.info(t('analysis.applyGuidedOpen'));
    } catch (err) {
      notify.error(getApiErrorMessage(err, t('analysis.applyFailed')));
    } finally {
      setApplyingKey(null);
    }
  };

  return (
    <div className="sr-insight-list" role="region" aria-label={t('analysis.listsAria')}>
      <section className="sr-insight-list__col" aria-label={t('analysis.strengths')}>
        <Card className="sr-insight-list__card">
          <h3 className="sr-insight-list__title">
            <i className="fa-solid fa-circle-check sr-insight-list__title-icon sr-insight-list__title-icon--success" aria-hidden />
            {t('analysis.strengths')}
          </h3>
          <ul className="sr-insight-list__items">
            {result.strengths.map((insight, idx) => (
              <li key={idx}>
                <InsightListItem variant="positive" insight={insight} />
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <section className="sr-insight-list__col" aria-label={t('analysis.improvements')}>
        <Card className="sr-insight-list__card">
          <h3 className="sr-insight-list__title">
            <i className="fa-solid fa-triangle-exclamation sr-insight-list__title-icon sr-insight-list__title-icon--warning" aria-hidden />
            {t('analysis.improvements')}
          </h3>
          <ul className="sr-insight-list__items">
            {result.improvements.map((item: ImprovementInsightItem, idx: number) => (
              <li key={idx}>
                <InsightListItem
                  variant="improvement"
                  insight={item}
                  onSeeExample={handleSeeExample}
                  onApply={handleApply}
                  applying={applyingKey === item.key}
                />
              </li>
            ))}
          </ul>
        </Card>
      </section>

      <Modal
        open={Boolean(exampleItem && exampleContent)}
        onClose={() => setExampleItem(null)}
        title={t('analysis.exampleModalTitle')}
        subtitle={exampleItem ? t(exampleItem.key, exampleItem.params) : undefined}
        width={620}
      >
        {exampleContent?.mode === 'before_after' ? (
          <div className="sr-insight-list__example-grid">
            <article className="sr-insight-list__example-card sr-insight-list__example-card--before">
              <h4 className="sr-insight-list__example-heading">{t('analysis.exampleBefore')}</h4>
              <p className="sr-insight-list__example-text">{exampleContent.before}</p>
            </article>
            <article className="sr-insight-list__example-card sr-insight-list__example-card--after">
              <h4 className="sr-insight-list__example-heading">{t('analysis.exampleAfter')}</h4>
              <p className="sr-insight-list__example-text">{exampleContent.after}</p>
            </article>
          </div>
        ) : (
          <article className="sr-insight-list__example-card sr-insight-list__example-card--single">
            <h4 className="sr-insight-list__example-heading">{t('analysis.exampleSuggestion')}</h4>
            <p className="sr-insight-list__example-text">{exampleContent?.text}</p>
          </article>
        )}
      </Modal>
    </div>
  );
}

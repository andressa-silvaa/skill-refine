import type { AiInsight } from '../model/useDashboardMock';

import './InsightItem.css';

type Props = {
  item: AiInsight;
};

export function InsightItem({ item }: Props) {
  return (
    <div className="sr-dash-insight-item">
      <div className="sr-dash-insight-item__icon">
        <i className={item.icon} aria-hidden />
      </div>
      <div className="sr-dash-insight-item__content">
        <span className="sr-dash-insight-item__title">{item.title}</span>
        <p className="sr-dash-insight-item__desc">{item.description}</p>
      </div>
    </div>
  );
}

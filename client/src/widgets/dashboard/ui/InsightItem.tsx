import type { AiInsight } from '../model/types';

import './InsightItem.css';

type Props = {
  item: AiInsight;
  onClick?: () => void;
};

export function InsightItem({ item, onClick }: Props) {
  return (
    <button type="button" className="sr-dash-insight-item" onClick={onClick}>
      <div className="sr-dash-insight-item__icon">
        <i className={item.icon} aria-hidden />
      </div>
      <div className="sr-dash-insight-item__content">
        <span className="sr-dash-insight-item__title">{item.title}</span>
        <p className="sr-dash-insight-item__desc">{item.description}</p>
      </div>
    </button>
  );
}

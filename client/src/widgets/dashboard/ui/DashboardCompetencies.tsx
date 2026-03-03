import type { Competency } from '../model/useDashboardMock';

import './DashboardCompetencies.css';

type Props = {
  data: Competency[];
};

function getBarColor(value: number): string {
  if (value >= 80) return 'var(--sr-accent)';
  if (value >= 60) return '#f59e0b';
  return '#f08040';
}

export function DashboardCompetencies({ data }: Props) {
  return (
    <div className="sr-dash-competencies">
      {data.map((item) => (
        <div key={item.label} className="sr-dash-competencies__row">
          <div className="sr-dash-competencies__row-header">
            <span className="sr-dash-competencies__label">{item.label}</span>
            <span className="sr-dash-competencies__value">{item.value}%</span>
          </div>
          <div className="sr-dash-competencies__track">
            <div
              className="sr-dash-competencies__bar"
              style={{
                width: `${item.value}%`,
                background: getBarColor(item.value),
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

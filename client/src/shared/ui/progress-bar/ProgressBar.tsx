import './ProgressBar.css';

type Props = {
  current: number;
  total: number;
  className?: string;
  rightContent?: React.ReactNode;
};

export function ProgressBar(props: Props) {
  const { current, total, className = '', rightContent } = props;
  const percentage = Math.min(100, Math.max(0, (current / total) * 100));

  return (
    <div className={`sr-progress-bar${className ? ` ${className}` : ''}`} role="progressbar" aria-valuenow={current} aria-valuemin={0} aria-valuemax={total}>
      <div className="sr-progress-bar__header">
        <span className="sr-progress-bar__label">
          {current} de {total}
        </span>
        {rightContent}
      </div>
      <div className="sr-progress-bar__track">
        <div className="sr-progress-bar__fill" style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

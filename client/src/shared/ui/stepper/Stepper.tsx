import './Stepper.css';

type Step = {
  id: string;
  label: string;
};

type Props = {
  steps: Step[];
  currentStep: number;
  className?: string;
  onStepClick?: (stepId: string, stepNum: number) => void;
  isStepClickable?: (stepId: string, stepNum: number) => boolean;
};

export function Stepper(props: Props) {
  const { steps, currentStep, className = '', onStepClick, isStepClickable } = props;

  return (
    <div className={`sr-stepper${className ? ` ${className}` : ''}`} role="progressbar" aria-valuenow={currentStep} aria-valuemin={1} aria-valuemax={steps.length}>
      {steps.map((step, index) => {
        const stepNum = index + 1;
        const isActive = stepNum === currentStep;
        const isDone = stepNum < currentStep;
        const isPending = stepNum > currentStep;
        const isClickable = isStepClickable ? isStepClickable(step.id, stepNum) : false;

        return (
          <div
            key={step.id}
            className={`sr-stepper__item${isActive ? ' is-active' : ''}${isDone ? ' is-done' : ''}${isPending ? ' is-pending' : ''}${isClickable ? ' is-clickable' : ''}`}
            onClick={isClickable && onStepClick ? () => onStepClick(step.id, stepNum) : undefined}
            role={isClickable ? 'button' : undefined}
            tabIndex={isClickable ? 0 : undefined}
            onKeyDown={isClickable && onStepClick ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onStepClick(step.id, stepNum);
              }
            } : undefined}
          >
            <div className="sr-stepper__circle">
              {isDone ? (
                <i className="fa-solid fa-check" aria-hidden />
              ) : (
                <span className="sr-stepper__number">{stepNum}</span>
              )}
            </div>
            <span className="sr-stepper__label">{step.label}</span>
          </div>
        );
      })}
    </div>
  );
}

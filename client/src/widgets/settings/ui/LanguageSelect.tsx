import { useId } from 'react';

import { useListbox } from '@/shared/lib/hooks/useListbox';

type Option = { value: string; label: string };

type Props = {
  value: string;
  options: Option[];
  disabled?: boolean;
  onChange: (value: string) => void;
  onOpenChange?: (open: boolean) => void;
};

export function LanguageSelect(props: Props) {
  const { value, options, disabled, onChange, onOpenChange } = props;

  const selectId = useId();
  const { wrapRef, open, setOpen, activeIndex, setActiveIndex, selectedLabel, onTriggerKeyDown } = useListbox({
    value,
    options,
    disabled,
    onOpenChange,
  });

  return (
    <div ref={wrapRef} className="sr-settings-general__select">
      <button
        type="button"
        className="sr-input sr-settings-general__select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={selectId}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        onKeyDown={onTriggerKeyDown}
      >
        <span className="sr-settings-general__select-value">{selectedLabel}</span>
        <span className="sr-settings-general__select-caret" aria-hidden />
      </button>

      {open ? (
        <div className="sr-settings-general__select-menu" role="listbox" id={selectId}>
          {options.map((opt, idx) => {
            const selected = opt.value === value;
            const active = idx === activeIndex;
            return (
              <button
                key={opt.value}
                type="button"
                role="option"
                aria-selected={selected}
                disabled={disabled}
                className={`sr-settings-general__select-option${selected ? ' is-selected' : ''}${active ? ' is-active' : ''}`}
                onMouseEnter={() => setActiveIndex(idx)}
                onClick={() => {
                  onChange(opt.value);
                  setOpen(false);
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

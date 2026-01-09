import './SettingsSwitch.css';

type Props = {
  checked: boolean;
  onToggle: () => void;
  ariaLabel: string;
};

export function SettingsSwitch(props: Props) {
  const { checked, onToggle, ariaLabel } = props;
  return (
    <button
      type="button"
      className={`sr-settings-switch${checked ? ' is-on' : ''}`}
      role="switch"
      aria-checked={checked}
      aria-label={ariaLabel}
      onClick={onToggle}
    >
      <span className="sr-settings-switch__thumb" aria-hidden />
    </button>
  );
}



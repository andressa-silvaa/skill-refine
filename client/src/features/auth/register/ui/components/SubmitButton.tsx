type Props = {
  disabled: boolean;
};

export function SubmitButton(props: Props) {
  const { disabled } = props;

  return (
    <button className="submit-btn" type="submit" disabled={disabled}>
      <span>CADASTRAR</span>
      <span className="arrow">→</span>
    </button>
  );
}



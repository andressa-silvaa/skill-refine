type Props = {
  onGoLogin?: () => void;
};

export function RegisterFooter(props: Props) {
  const { onGoLogin } = props;

  return (
    <footer className="footer">
      <span>Você já tem uma conta?</span>
      <button className="signup-link" type="button" onClick={onGoLogin}>
        Acesse aqui
      </button>
    </footer>
  );
}



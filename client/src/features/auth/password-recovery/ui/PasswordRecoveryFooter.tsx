import '@/features/auth/ui/AuthStyles.css';

type Props = {
  onGoLogin?: () => void;
};

export function PasswordRecoveryFooter(props: Props) {
  const { onGoLogin } = props;
  return (
    <span>
      Você já tem uma conta?{' '}
      <button className="recovery-small-action" type="button" onClick={onGoLogin}>
        Entrar
      </button>
    </span>
  );
}



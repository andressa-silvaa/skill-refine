import '@/shared/ui/auth/AuthStyles.css';

type Props = {
  onGoLogin?: () => void;
};

export function ResetSuccess(props: Props) {
  const { onGoLogin } = props;
  return (
    <>
      <div className="recovery-success">
        <div className="recovery-success-icon">✔</div>
        <p className="recovery-success-text">Sua senha foi atualizada.</p>
      </div>

      <button className="recovery-btn" type="button" onClick={onGoLogin}>
        Entrar
      </button>
    </>
  );
}



import RecoveryLayout from '../../components/RecoveryLayout';

export default function ResetSuccessPage({ onGoLogin }) {
  return (
    <RecoveryLayout
      title="Senha alterada com sucesso!"
      subtitle=""
      footer={
        <button className="recovery-btn" type="button" onClick={onGoLogin}>
          Entrar
        </button>
      }
    >
      <div className="recovery-success">
        <div className="recovery-success-icon">✔</div>
        <p className="recovery-success-text">Sua senha foi atualizada.</p>
      </div>
    </RecoveryLayout>
  );
}


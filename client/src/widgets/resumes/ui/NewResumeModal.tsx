import { useMemo, useState } from 'react';

import { Button, Modal } from '@/shared/ui';
import { ResumeThemePicker } from '@/features/resume-theme-select';
import { DEFAULT_RESUME_THEME_ID, resumeThemes, type ResumeThemeId } from '@/entities/resume';

import './NewResumeModal.css';

type Props = {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; themeId: ResumeThemeId }) => void;
};

export function NewResumeModal(props: Props) {
  const { open, onClose, onCreate } = props;

  const [step, setStep] = useState(1);
  const [themeId, setThemeId] = useState<ResumeThemeId>(resumeThemes[0]?.id ?? DEFAULT_RESUME_THEME_ID);
  const [name, setName] = useState('');

  const canNext = useMemo(() => {
    if (step === 1) return Boolean(themeId);
    if (step === 2) return name.trim().length >= 3;
    return true;
  }, [name, step, themeId]);

  const close = () => {
    onClose();
    window.setTimeout(() => {
      setStep(1);
      setThemeId(resumeThemes[0]?.id ?? DEFAULT_RESUME_THEME_ID);
      setName('');
    }, 0);
  };

  const next = () => {
    if (!canNext) return;
    setStep((s) => Math.min(3, s + 1));
  };

  const back = () => setStep((s) => Math.max(1, s - 1));

  const finish = () => {
    if (!canNext) return;
    onCreate({ name: name.trim(), themeId });
    close();
  };

  return (
    <Modal open={open} title="Novo Currículo" subtitle="Preencha as informações para criar seu currículo" onClose={close} width={760}>
      <div className="sr-new-resume">
        {/* Stepper (desktop/tablet) */}
        <div className="sr-new-resume__steps sr-new-resume__steps--desktop" aria-label="Etapas">
          {[1, 2, 3].map((n) => (
            <div key={n} className={`sr-new-resume__step${n === step ? ' is-active' : ''}${n < step ? ' is-done' : ''}`}>
              {n}
            </div>
          ))}
        </div>

        {/* Progresso compacto (mobile/tablet pequeno) */}
        <div className="sr-new-resume__progress sr-new-resume__progress--mobile" aria-label="Progresso">
          <span className="sr-new-resume__progress-text">Etapa {step} de 3</span>
          <div className="sr-new-resume__progress-bar" aria-hidden>
            <div className="sr-new-resume__progress-fill" style={{ width: `${(step / 3) * 100}%` }} />
          </div>
        </div>

        {/* Única área scrollável */}
        <div className="sr-new-resume__content">
          {step === 1 ? (
            <div className="sr-new-resume__panel">
              <h3 className="sr-new-resume__h3">Selecione um tema</h3>
              <p className="sr-new-resume__muted">Para começar, selecione um tema visual abaixo.</p>

              <ResumeThemePicker selectedId={themeId} onSelect={setThemeId} variant="carousel" cardSize="compact" />
            </div>
          ) : step === 2 ? (
            <div className="sr-new-resume__panel">
              <h3 className="sr-new-resume__h3">Nome do currículo</h3>
              <p className="sr-new-resume__muted">Ex.: Currículo Desenvolvedor 2026</p>
              <input
                className="sr-input"
                value={name}
                placeholder="Digite um nome para identificar este currículo"
                onChange={(e) => setName(e.target.value)}
              />
            </div>
          ) : (
            <div className="sr-new-resume__panel">
              <h3 className="sr-new-resume__h3">Próximas etapas</h3>
              <p className="sr-new-resume__muted">O builder completo entra aqui. Por enquanto, vamos criar seu rascunho.</p>

              <div className="sr-new-resume__placeholder">
                <div className="sr-new-resume__placeholder-row">
                  <div className="sr-new-resume__dot is-active" />
                  <div>
                    <div className="sr-new-resume__placeholder-title">Dados pessoais</div>
                    <div className="sr-new-resume__template-desc">Nome, e-mail, telefone, links…</div>
                  </div>
                </div>

                <div className="sr-new-resume__placeholder-row">
                  <div className="sr-new-resume__dot" />
                  <div>
                    <div className="sr-new-resume__placeholder-title">Experiência</div>
                    <div className="sr-new-resume__template-desc">Cargos, empresas, resultados…</div>
                  </div>
                </div>

                <div className="sr-new-resume__placeholder-row">
                  <div className="sr-new-resume__dot" />
                  <div>
                    <div className="sr-new-resume__placeholder-title">Habilidades</div>
                    <div className="sr-new-resume__template-desc">Tags, nível e destaque…</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer fixo */}
        <div className="sr-new-resume__footer">
          <Button variant="secondary" onClick={step === 1 ? close : back}>
            {step === 1 ? 'Cancelar' : 'Voltar'}
          </Button>

          {step < 3 ? (
            <Button variant="primary" onClick={next} disabled={!canNext}>
              Próximo
              <i className="fa-solid fa-arrow-right" aria-hidden />
            </Button>
          ) : (
            <Button variant="primary" onClick={finish}>
              Criar currículo
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
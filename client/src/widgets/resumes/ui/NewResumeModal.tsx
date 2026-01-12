import { useMemo, useState } from 'react';

import { Button, Card, Modal } from '@/shared/ui';

import './NewResumeModal.css';

type TemplateId = 'tech' | 'business' | 'minimal';

type Props = {
  open: boolean;
  onClose: () => void;
  onCreate: (data: { name: string; templateId: TemplateId }) => void;
};

export function NewResumeModal(props: Props) {
  const { open, onClose, onCreate } = props;
  const [step, setStep] = useState(1);
  const [templateId, setTemplateId] = useState<TemplateId>('tech');
  const [name, setName] = useState('');

  const canNext = useMemo(() => {
    if (step === 1) return Boolean(templateId);
    if (step === 2) return name.trim().length >= 3;
    return true;
  }, [name, step, templateId]);

  const close = () => {
    onClose();
    window.setTimeout(() => {
      setStep(1);
      setTemplateId('tech');
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
    onCreate({ name: name.trim(), templateId });
    close();
  };

  return (
    <Modal open={open} title="Novo Currículo" subtitle="Preencha as informações para criar seu currículo" onClose={close} width={760}>
      <div className="sr-new-resume">
        <div className="sr-new-resume__steps" aria-label="Etapas">
          {[1, 2, 3].map((n) => (
            <div key={n} className={`sr-new-resume__step${n === step ? ' is-active' : ''}${n < step ? ' is-done' : ''}`}>
              {n}
            </div>
          ))}
        </div>

        {step === 1 ? (
          <div className="sr-new-resume__panel">
            <h3 className="sr-new-resume__h3">Selecione seu modelo</h3>
            <p className="sr-new-resume__muted">Para começar, selecione um modelo de currículo abaixo.</p>

            <div className="sr-new-resume__carousel" role="list">
              {(
                [
                  { id: 'tech', title: 'Tech', desc: 'Ideal para devs e produto.' },
                  { id: 'business', title: 'Business', desc: 'Foco em resultados e gestão.' },
                  { id: 'minimal', title: 'Minimal', desc: 'Limpo e direto ao ponto.' },
                ] as const
              ).map((t) => (
                <Card key={t.id} className={`sr-new-resume__template${templateId === t.id ? ' is-selected' : ''}`} role="listitem">
                  <div className="sr-new-resume__preview" aria-hidden />
                  <div className="sr-new-resume__template-body">
                    <div>
                      <div className="sr-new-resume__template-title">{t.title}</div>
                      <div className="sr-new-resume__template-desc">{t.desc}</div>
                    </div>
                    <Button variant={templateId === t.id ? 'primary' : 'secondary'} onClick={() => setTemplateId(t.id)}>
                      Selecionar
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        ) : step === 2 ? (
          <div className="sr-new-resume__panel">
            <h3 className="sr-new-resume__h3">Nome do currículo</h3>
            <p className="sr-new-resume__muted">Ex.: Currículo Desenvolvedor 2026</p>
            <input className="sr-input" value={name} placeholder="Digite um nome para identificar este currículo" onChange={(e) => setName(e.target.value)} />
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

        <div className="sr-new-resume__actions">
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

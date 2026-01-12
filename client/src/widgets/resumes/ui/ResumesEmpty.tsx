import { Button, Card } from '@/shared/ui';

import './ResumesEmpty.css';

type Props = {
  onCreate: () => void;
};

export function ResumesEmpty(props: Props) {
  const { onCreate } = props;

  return (
    <Card className="sr-resumes-empty">
      <div className="sr-resumes-empty__icon" aria-hidden>
        <i className="fa-regular fa-file-lines" />
      </div>
      <h3 className="sr-resumes-empty__title">Nenhum currículo por aqui</h3>
      <p className="sr-resumes-empty__text">Crie, edite e aprimore com IA — tudo em um só lugar.</p>
      <Button variant="primary" onClick={onCreate}>
        <i className="fa-solid fa-plus" aria-hidden />
        Criar meu primeiro currículo
      </Button>
    </Card>
  );
}

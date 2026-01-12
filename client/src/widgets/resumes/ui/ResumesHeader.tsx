import { Button } from '@/shared/ui';

import './ResumesHeader.css';

type Props = {
  onCreate: () => void;
};

export function ResumesHeader(props: Props) {
  const { onCreate } = props;

  return (
    <header className="sr-resumes__header">
      <div>
        <h1 className="sr-resumes__h1">Meus Currículos</h1>
        <p className="sr-resumes__subtitle">Gerencie e edite todos os seus currículos</p>
      </div>
      <Button variant="primary" onClick={onCreate}>
        <i className="fa-solid fa-plus" aria-hidden />
        Novo currículo
      </Button>
    </header>
  );
}

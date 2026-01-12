import './ResumeThumb.css';

type Props = {
  variant?: 'doc' | 'spark';
};

export function ResumeThumb(props: Props) {
  const { variant = 'doc' } = props;
  return (
    <div className="sr-resume-thumb" aria-hidden>
      <i className={variant === 'spark' ? 'fa-solid fa-wand-magic-sparkles' : 'fa-regular fa-file-lines'} />
    </div>
  );
}

import './AuthStyles.css';

type Props = {
  message: string;
  variant?: 'error' | 'success';
};

export function AlertMessage(props: Props) {
  const { message, variant = 'error' } = props;
  return <p className={`auth-alert auth-alert--${variant}`}>{message}</p>;
}

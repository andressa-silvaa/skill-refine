import type { PropsWithChildren, ReactNode } from 'react';

import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

type Props = PropsWithChildren<{
  title: string;
  subtitle?: string;
  footer?: ReactNode;
  onBack?: () => void;
  className?: string;
}>;

export function AuthLayout(props: Props) {
  return <RecoveryLayout {...props} />;
}



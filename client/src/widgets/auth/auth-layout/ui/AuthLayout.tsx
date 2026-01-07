import type { PropsWithChildren, ReactNode } from 'react';

import { RecoveryLayout } from '@/widgets/auth/recovery-layout';

type Props = PropsWithChildren<{
  title: string;
  subtitle?: string;
  footer?: ReactNode;
  onBack?: () => void;
  className?: string;
}>;

/**
 * Generic auth layout used across auth flows (reset password, confirm email, verify email).
 * Implementation reuses the existing RecoveryLayout to keep visual consistency.
 */
export function AuthLayout(props: Props) {
  return <RecoveryLayout {...props} />;
}



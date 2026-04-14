import { useCallback, useRef } from 'react';

import { accountApi, type EmailConfirmationRequestResult } from '@/entities/session';
import { asApiError } from '@/shared/api';
import { useAsyncRequest } from '@/shared/lib/hooks/useAsyncRequest';
import { useCooldown } from '@/shared/lib/hooks/useCooldown';

type Options = {
  cooldownSeconds?: number;
};

export function useEmailConfirmationResend(options: Options = {}) {
  const { cooldownSeconds = 60 } = options;

  const cooldown = useCooldown({ seconds: cooldownSeconds });
  const req = useAsyncRequest(accountApi.requestEmailConfirmation);
  const inFlightRef = useRef(false);

  const resend = useCallback(
    async (email: string): Promise<EmailConfirmationRequestResult | undefined> => {
      if (!email) return;
      if (inFlightRef.current || req.isLoading || cooldown.isCoolingDown) return;

      inFlightRef.current = true;
      try {
        const data = await req.run({ email });
        if (!data?.already_verified) {
          cooldown.start(cooldownSeconds);
        }
        return data;
      } catch (e) {
        const apiErr = asApiError(e);
        if (apiErr?.status === 429) {
          cooldown.start(apiErr.retryAfterSeconds ?? cooldownSeconds);
          return undefined;
        }
        cooldown.stop();
        throw e;
      } finally {
        inFlightRef.current = false;
      }
    },
    [cooldown, cooldownSeconds, req]
  );

  return {
    resend,
    isLoading: req.isLoading,
    error: req.error,
    isCoolingDown: cooldown.isCoolingDown,
    cooldownLabel: cooldown.label,
    remainingSeconds: cooldown.remaining,
    startCooldown: cooldown.start,
  };
}



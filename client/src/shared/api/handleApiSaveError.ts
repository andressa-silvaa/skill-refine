import { getApiErrorMessage, getApiFieldErrors } from './error';
import { notify } from '@/shared/lib/notify';

export type ApiSaveErrorOptions = {
  fallbackMessage: string;
  fieldKey?: string;
  onFieldError?: (message: string) => void;
  onFieldErrors?: (fields: Record<string, string>) => void;
  notifyError?: (message: string) => void;
};

export function handleApiSaveError(error: unknown, options: ApiSaveErrorOptions): void {
  const {
    fallbackMessage,
    fieldKey,
    onFieldError,
    onFieldErrors,
    notifyError = notify.error,
  } = options;

  const fields = getApiFieldErrors(error);

  if (fieldKey && onFieldError) {
    const raw = fields?.[fieldKey];
    if (raw !== undefined && raw !== null && typeof raw === 'string') {
      onFieldError(raw);
      return;
    }
  }

  if (onFieldErrors && fields && Object.keys(fields).length > 0) {
    onFieldErrors(fields);
    return;
  }

  notifyError(getApiErrorMessage(error, fallbackMessage));
}

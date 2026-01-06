import type { FieldErrors, FieldValues, FormState } from 'react-hook-form';

export const GENERIC_FORM_ERROR_MESSAGE = 'Corrija os erros do formulário.';

export function hasFormErrors(errors: FieldErrors) {
  return Object.keys(errors).length > 0;
}

export function shouldShowGenericFormError<TFieldValues extends FieldValues>(
  formState: Pick<FormState<TFieldValues>, 'isSubmitted' | 'errors'>,
) {
  return formState.isSubmitted && hasFormErrors(formState.errors);
}



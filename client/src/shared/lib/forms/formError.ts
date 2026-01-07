import type { FieldErrors, FieldValues, FormState } from 'react-hook-form';

export function hasFormErrors(errors: FieldErrors) {
  return Object.keys(errors).length > 0;
}

export function shouldShowGenericFormError<TFieldValues extends FieldValues>(
  formState: Pick<FormState<TFieldValues>, 'isSubmitted' | 'errors'>,
) {
  return formState.isSubmitted && hasFormErrors(formState.errors);
}



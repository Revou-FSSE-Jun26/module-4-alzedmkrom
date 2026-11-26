import { useId, type ReactNode } from 'react';

export interface FormFieldControl {
  id: string;
  'aria-invalid': boolean;
  'aria-describedby'?: string;
}

export interface FormFieldProps {
  label: string;
  error?: string | null;
  hint?: string;
  children: (control: FormFieldControl) => ReactNode;
}

export function FormField({ label, error, hint, children }: FormFieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const hasError = Boolean(error);

  const control: FormFieldControl = hasError
    ? {
        id,
        'aria-invalid': true,
        'aria-describedby': hint ? `${hintId} ${errorId}` : errorId,
      }
    : { id, 'aria-invalid': false };

  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-base font-medium text-gray-800">
        {label}
      </label>
      {children(control)}
      {hint ? (
        <p id={hintId} className="text-base text-gray-600">
          {hint}
        </p>
      ) : null}
      {hasError ? (
        <p id={errorId} className="text-base text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}

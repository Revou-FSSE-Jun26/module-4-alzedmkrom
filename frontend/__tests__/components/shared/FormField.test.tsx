import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FormField } from '@/components/shared/FormField';

describe('FormField', () => {
  it('links the label to the control and sets no error wiring without an error', () => {
    render(
      <FormField label="Name">
        {(control) => <input {...control} />}
      </FormField>,
    );

    const input = screen.getByLabelText('Name');
    expect(input).toHaveAttribute('id');
    expect(input).toHaveAttribute('aria-invalid', 'false');
    expect(input).not.toHaveAttribute('aria-describedby');
    expect(document.querySelector('p')).toBeNull();
  });

  it('renders the error below the control and points aria-describedby at it', () => {
    render(
      <FormField label="Email" error="Email is already in use.">
        {(control) => <input {...control} />}
      </FormField>,
    );

    const input = screen.getByLabelText('Email');
    const describedBy = input.getAttribute('aria-describedby');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(describedBy).toBe(`${input.id}-error`);
    expect(document.getElementById(describedBy as string)).toHaveTextContent(
      'Email is already in use.',
    );
  });

  it('treats an empty error string as no error', () => {
    render(
      <FormField label="Title" error="">
        {(control) => <input {...control} />}
      </FormField>,
    );

    const input = screen.getByLabelText('Title');
    expect(input).toHaveAttribute('aria-invalid', 'false');
    expect(input).not.toHaveAttribute('aria-describedby');
  });

  it('lists the hint and the error in aria-describedby when both are present', () => {
    render(
      <FormField label="Password" hint="At least 8 characters." error="Password is required.">
        {(control) => <input type="password" {...control} />}
      </FormField>,
    );

    const input = screen.getByLabelText('Password');
    const ids = (input.getAttribute('aria-describedby') ?? '').split(' ');
    expect(ids).toEqual([`${input.id}-hint`, `${input.id}-error`]);
    expect(screen.getByText('At least 8 characters.')).toHaveAttribute('id', `${input.id}-hint`);
    expect(screen.getByText('Password is required.')).toHaveAttribute('id', `${input.id}-error`);
  });
});

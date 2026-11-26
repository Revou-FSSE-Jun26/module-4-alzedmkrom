'use client';

import { useEffect, useId, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

export type BaseModalSize = 'md' | 'lg';

export interface BaseModalProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  size?: BaseModalSize;
  /** True while a submit is pending. Escape and backdrop click do nothing then (FE-UI-03). */
  dismissDisabled?: boolean;
}

/**
 * Tokens of the open modals, in opening order. Only the last entry (the topmost
 * modal) handles keyboard input.
 */
const modalStack: symbol[] = [];

const FOCUSABLE_SELECTOR = 'button, input, select, textarea, a[href], [tabindex]';

const SIZE_CLASSES: Record<BaseModalSize, string> = {
  md: 'sm:max-w-md',
  lg: 'sm:max-w-3xl',
};

function isRendered(element: HTMLElement): boolean {
  for (let node: HTMLElement | null = element; node; node = node.parentElement) {
    if (node.hidden || window.getComputedStyle(node).display === 'none') {
      return false;
    }
  }
  return window.getComputedStyle(element).visibility !== 'hidden';
}

function isFocusable(element: HTMLElement): boolean {
  if (element.matches(':disabled') || element.tabIndex < 0) {
    return false;
  }
  if (element instanceof HTMLInputElement && element.type === 'hidden') {
    return false;
  }
  return isRendered(element);
}

function getFocusable(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    isFocusable,
  );
}

function trapTab(event: KeyboardEvent, dialog: HTMLElement): void {
  const focusable = getFocusable(dialog);
  if (focusable.length === 0) {
    event.preventDefault();
    dialog.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  const active = document.activeElement;
  // Focus on the container itself or outside the dialog counts as "before the first"
  // for Shift+Tab and "after the last" for Tab.
  const outside = !(active instanceof HTMLElement) || !dialog.contains(active) || active === dialog;

  if (event.shiftKey) {
    if (outside || active === first) {
      event.preventDefault();
      last.focus();
    }
  } else if (outside || active === last) {
    event.preventDefault();
    first.focus();
  }
}

function restoreFocus(previous: HTMLElement | null): void {
  if (previous?.isConnected) {
    previous.focus();
    return;
  }
  if (document.activeElement instanceof HTMLElement) {
    document.activeElement.blur();
  }
}

export function BaseModal({
  open,
  title,
  onClose,
  children,
  size = 'md',
  dismissDisabled = false,
}: BaseModalProps) {
  const headingId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  const dismissDisabledRef = useRef(dismissDisabled);
  const [token] = useState(() => Symbol('base-modal'));

  useEffect(() => {
    onCloseRef.current = onClose;
    dismissDisabledRef.current = dismissDisabled;
  }, [onClose, dismissDisabled]);

  const requestClose = () => {
    if (!dismissDisabledRef.current) {
      onCloseRef.current();
    }
  };

  useEffect(() => {
    if (!open) {
      return;
    }

    const previous =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    modalStack.push(token);

    const dialog = dialogRef.current;
    if (dialog) {
      (getFocusable(dialog)[0] ?? dialog).focus();
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (modalStack[modalStack.length - 1] !== token) {
        return;
      }
      if (event.key === 'Escape') {
        requestClose();
      } else if (event.key === 'Tab' && dialogRef.current) {
        trapTab(event, dialogRef.current);
      }
    };
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      const index = modalStack.lastIndexOf(token);
      if (index !== -1) {
        modalStack.splice(index, 1);
      }
      restoreFocus(previous);
    };
  }, [open, token]);

  if (!open || typeof document === 'undefined') {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div aria-hidden="true" className="absolute inset-0 bg-black/50" onClick={requestClose} />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        tabIndex={-1}
        className={`relative w-full max-w-full max-h-[100dvh] overflow-y-auto rounded-none bg-white p-4 shadow-xl sm:rounded-lg sm:p-6 ${SIZE_CLASSES[size]}`}
      >
        <h2 id={headingId} className="mb-4 text-lg font-semibold break-words text-gray-900">
          {title}
        </h2>
        {children}
      </div>
    </div>,
    document.body,
  );
}

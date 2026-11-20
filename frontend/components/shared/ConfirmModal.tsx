'use client';

import { BaseButton } from './BaseButton';
import { BaseModal } from './BaseModal';

export interface ConfirmModalProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  pending?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmModal({
  open,
  title,
  message,
  confirmLabel,
  pending = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  return (
    <BaseModal open={open} title={title} onClose={onCancel}>
      <p className="mb-6 text-sm text-gray-700">{message}</p>
      <div className="flex justify-end gap-2">
        <BaseButton variant="secondary" onClick={() => onCancel()}>
          Cancel
        </BaseButton>
        <BaseButton variant="destructive" disabled={pending} onClick={() => onConfirm()}>
          {confirmLabel}
        </BaseButton>
      </div>
    </BaseModal>
  );
}

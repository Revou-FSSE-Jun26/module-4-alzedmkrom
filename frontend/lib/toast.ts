import toast from 'react-hot-toast'

// The only file that imports react-hot-toast (FE-API-04).

/** Shown once per expiry: a fixed id makes repeated calls replace the same toast. */
const SESSION_EXPIRED_ID = 'session-expired'

export function success(message: string): string {
  return toast.success(message)
}

export function error(message: string): string {
  return toast.error(message)
}

export function loading(message: string): string {
  return toast.loading(message)
}

export function dismiss(id?: string): void {
  toast.dismiss(id)
}

export function showSessionExpiredToast(): string {
  return toast.error('Session expired', { id: SESSION_EXPIRED_ID })
}

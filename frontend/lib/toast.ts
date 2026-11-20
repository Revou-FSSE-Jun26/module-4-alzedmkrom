import toast from 'react-hot-toast'

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

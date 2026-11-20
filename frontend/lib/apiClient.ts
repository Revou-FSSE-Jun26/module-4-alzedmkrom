import { ApiError } from '@/lib/errors'

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export interface RequestOptions {
  token?: string | null
  body?: unknown
}

/**
 * Resolves the API origin without a trailing slash.
 * Next inlines `process.env.NAME` only for literal property access, so both
 * variables are referenced literally below.
 */
export function resolveBaseUrl(): string {
  const server = typeof window === 'undefined'
  let name: 'API_BASE_URL' | 'NEXT_PUBLIC_API_BASE_URL'
  let raw: string | undefined
  if (server) {
    if (process.env.API_BASE_URL !== undefined) {
      name = 'API_BASE_URL'
      raw = process.env.API_BASE_URL
    } else {
      name = 'NEXT_PUBLIC_API_BASE_URL'
      raw = process.env.NEXT_PUBLIC_API_BASE_URL
    }
  } else {
    name = 'NEXT_PUBLIC_API_BASE_URL'
    raw = process.env.NEXT_PUBLIC_API_BASE_URL
  }

  const trimmed = (raw ?? '').trim()
  if (trimmed === '') {
    throw new Error(`${name} is not set`)
  }
  return trimmed.replace(/\/+$/, '')
}

export async function apiRequest<T>(
  method: HttpMethod,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const server = typeof window === 'undefined'
  const url = `${resolveBaseUrl()}${path}`

  const headers: Record<string, string> = {}
  if (typeof options.token === 'string' && options.token !== '') {
    headers.Authorization = `Bearer ${options.token}`
  }
  let body: string | undefined
  if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  let res: Response
  try {
    res = await fetch(url, {
      method,
      headers,
      body,
      cache: server ? 'no-store' : undefined,
    })
  } catch {
    throw new ApiError(0, 'Network request failed')
  }

  const text = await res.text()
  let parsed: unknown = undefined
  try {
    parsed = JSON.parse(text)
  } catch {
    parsed = undefined
  }

  if (res.status >= 200 && res.status <= 299) {
    if (typeof parsed === 'object' && parsed !== null && 'data' in parsed) {
      return (parsed as { data: T }).data
    }
    throw new ApiError(res.status, 'Invalid response from server')
  }

  const envelopeError =
    typeof parsed === 'object' && parsed !== null && 'error' in parsed
      ? (parsed as { error: unknown }).error
      : undefined
  const message =
    typeof envelopeError === 'string' && envelopeError !== ''
      ? envelopeError
      : `Request failed with status ${res.status}`
  throw new ApiError(res.status, message)
}

export const apiClient = {
  get<T>(path: string, token?: string | null): Promise<T> {
    return apiRequest<T>('GET', path, { token })
  },
  post<T>(path: string, body?: unknown, token?: string | null): Promise<T> {
    return apiRequest<T>('POST', path, { token, body })
  },
  patch<T>(path: string, body: unknown, token?: string | null): Promise<T> {
    return apiRequest<T>('PATCH', path, { token, body })
  },
  delete<T>(path: string, token?: string | null): Promise<T> {
    return apiRequest<T>('DELETE', path, { token })
  },
}

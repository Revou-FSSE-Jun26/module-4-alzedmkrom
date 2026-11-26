import { ApiError } from '@/lib/errors'

// The only module that calls `fetch` for the backend (FE-API-01).

export type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'DELETE'

export interface RequestOptions {
  /** Bearer token. Sent only when it is a non-empty string. */
  token?: string | null
  body?: unknown
}

/**
 * Returns the API origin without a trailing slash (FE-SEC-02).
 * The server reads API_BASE_URL and the browser reads NEXT_PUBLIC_API_BASE_URL.
 * Next inlines `NEXT_PUBLIC_*` only for literal property access, so each name
 * is referenced literally.
 */
export function resolveBaseUrl(): string {
  const isServer = typeof window === 'undefined'
  const raw = isServer ? process.env.API_BASE_URL : process.env.NEXT_PUBLIC_API_BASE_URL
  const trimmed = (raw ?? '').trim()
  if (trimmed === '') {
    throw new Error(
      isServer
        ? 'API_BASE_URL is not set. Add it to frontend/.env.local.'
        : 'NEXT_PUBLIC_API_BASE_URL is not set. Add it to frontend/.env.local.',
    )
  }
  return trimmed.replace(/\/+$/, '')
}

function isDetails(value: unknown): value is Record<string, string[]> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    return false
  }
  return Object.values(value).every(
    (entry) => Array.isArray(entry) && entry.every((item) => typeof item === 'string'),
  )
}

/** Builds the ApiError for a non-2xx response from the BE-ERR-01 body. */
function errorFromResponse(status: number, text: string): ApiError {
  let parsed: unknown = undefined
  try {
    parsed = JSON.parse(text)
  } catch {
    return new ApiError(status, `Request failed with status ${status}.`, 'UNKNOWN')
  }
  const envelope =
    typeof parsed === 'object' && parsed !== null && 'error' in parsed
      ? (parsed as { error: unknown }).error
      : undefined
  if (typeof envelope !== 'object' || envelope === null) {
    return new ApiError(status, `Request failed with status ${status}.`, 'UNKNOWN')
  }
  const { code, message, details } = envelope as Record<string, unknown>
  return new ApiError(
    status,
    typeof message === 'string' ? message : `Request failed with status ${status}.`,
    typeof code === 'string' ? code : 'UNKNOWN',
    isDetails(details) ? details : null,
  )
}

export async function apiRequest<T>(
  method: HttpMethod,
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const isServer = typeof window === 'undefined'
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

  let response: Response
  try {
    response = await fetch(url, {
      method,
      headers,
      body,
      // FE-API-02: server-side calls are never cached.
      cache: isServer ? 'no-store' : undefined,
    })
  } catch {
    throw new ApiError(0, "Can't reach the server.", 'NETWORK_ERROR')
  }

  if (response.status === 204) {
    return undefined as T
  }
  const text = await response.text()
  if (response.status >= 200 && response.status <= 299) {
    try {
      return JSON.parse(text) as T
    } catch {
      throw new ApiError(response.status, 'Invalid response from server.', 'UNKNOWN')
    }
  }
  throw errorFromResponse(response.status, text)
}

export const apiClient = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return apiRequest<T>('GET', path, options)
  },
  post<T>(path: string, options?: RequestOptions): Promise<T> {
    return apiRequest<T>('POST', path, options)
  },
  patch<T>(path: string, options?: RequestOptions): Promise<T> {
    return apiRequest<T>('PATCH', path, options)
  },
  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return apiRequest<T>('DELETE', path, options)
  },
}

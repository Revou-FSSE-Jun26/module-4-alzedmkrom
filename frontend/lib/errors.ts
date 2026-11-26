/**
 * The error every backend call throws (FE-API-03). Fields come from the
 * BE-ERR-01 body `{"error": {"code", "message", "details"}}`.
 */
export class ApiError extends Error {
  readonly statusCode: number
  readonly code: string | null
  readonly details: Record<string, string[]> | null

  constructor(
    statusCode: number,
    message: string,
    code: string | null = null,
    details: Record<string, string[]> | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.code = code
    this.details = details
  }
}

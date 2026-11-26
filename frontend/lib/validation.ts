import type { Card, User } from '@/types/api'

// Pure client-side validation (FE-FRM-02). Limits mirror the column lengths in
// database.md DB-SCH-01, and the password rule mirrors backend.md BE-VAL-05. The API
// stays the final judge: a 422 `details` response is mapped onto these fields.
// Each validator returns `null` when valid, or the message to show.

export const LIMITS = {
  /** users.name (DB-SCH-01). */
  name: 100,
  /** boards.name and columns.name (DB-SCH-01). */
  boardName: 100,
  columnName: 100,
  /** cards.title (DB-SCH-01). */
  title: 200,
  /** cards.description (DB-SCH-01 CHECK). */
  description: 5000,
  /** comments.content (DB-SCH-01 CHECK). */
  comment: 2000,
  /** users.email (DB-SCH-01). */
  emailMin: 3,
  emailMax: 255,
  /** BE-VAL-05. */
  passwordMin: 8,
  passwordMax: 128,
  /** Search box length. Not a stored field. */
  search: 200,
} as const

export type FieldErrors<K extends string> = Partial<Record<K, string>>

export type CardField = 'title' | 'description' | 'assignee_id' | 'completed'
export type ProfileField = 'name' | 'email'

export interface CardFieldValues {
  title: string
  description: string
  assignee_id: string | null
  completed: boolean
}

export interface ProfileFieldValues {
  name: string
  email: string
}

/** Length in Unicode code points, matching Python `str` length on the API. */
export const codePointLength = (value: string): number => [...value].length

/**
 * Exactly one `@`, at least one character before it, and a domain with a `.` that is
 * neither its first nor its last character. No whitespace. Expects a trimmed value.
 */
export function isValidEmail(trimmed: string): boolean {
  if (/\s/.test(trimmed)) {
    return false
  }
  const at = trimmed.indexOf('@')
  if (at < 1) {
    return false
  }
  if (trimmed.indexOf('@', at + 1) !== -1) {
    return false
  }
  const domain = trimmed.slice(at + 1)
  return domain.slice(1, -1).includes('.')
}

/** Trims `raw`, then checks the length range and the format. */
export function validateEmail(raw: string): string | null {
  const trimmed = raw.trim()
  const length = codePointLength(trimmed)
  if (length < LIMITS.emailMin || length > LIMITS.emailMax) {
    return `Email must be ${LIMITS.emailMin} to ${LIMITS.emailMax} characters.`
  }
  if (!isValidEmail(trimmed)) {
    return 'Enter a valid email address.'
  }
  return null
}

/** Name and password are checked untrimmed. Email is trimmed. */
export function validateRegister(v: {
  name: string
  email: string
  password: string
}): FieldErrors<'name' | 'email' | 'password'> {
  const errors: FieldErrors<'name' | 'email' | 'password'> = {}
  const nameLength = codePointLength(v.name.trim())
  if (nameLength < 1 || nameLength > LIMITS.name) {
    errors.name = `Name must be 1 to ${LIMITS.name} characters.`
  }
  const emailError = validateEmail(v.email)
  if (emailError !== null) {
    errors.email = emailError
  }
  const passwordLength = codePointLength(v.password)
  if (passwordLength < LIMITS.passwordMin || passwordLength > LIMITS.passwordMax) {
    errors.password = `Password must be ${LIMITS.passwordMin} to ${LIMITS.passwordMax} characters.`
  }
  return errors
}

/** Email needs at least one non-whitespace character. Password needs at least one character. */
export function validateLogin(v: {
  email: string
  password: string
}): FieldErrors<'email' | 'password'> {
  const errors: FieldErrors<'email' | 'password'> = {}
  if (v.email.trim() === '') {
    errors.email = 'Email is required.'
  }
  if (v.password === '') {
    errors.password = 'Password is required.'
  }
  return errors
}

/** Name is trimmed and must be 1 to 100 characters. Email follows `validateEmail`. */
export function validateProfile(v: { name: string; email: string }): FieldErrors<'name' | 'email'> {
  const errors: FieldErrors<'name' | 'email'> = {}
  const nameError = validateRequiredText('Name', v.name, LIMITS.name)
  if (nameError !== null) {
    errors.name = nameError
  }
  const emailError = validateEmail(v.email)
  if (emailError !== null) {
    errors.email = emailError
  }
  return errors
}

/** Trims `raw`. Empty is invalid. Length is checked after trimming. */
export function validateRequiredText(label: string, raw: string, max: number): string | null {
  const trimmed = raw.trim()
  if (trimmed === '') {
    return `${label} is required.`
  }
  if (codePointLength(trimmed) > max) {
    return `${label} must be at most ${max} characters.`
  }
  return null
}

/** Empty is valid. The value is not trimmed, so the length is checked as typed. */
export function validateOptionalText(label: string, raw: string, max: number): string | null {
  if (codePointLength(raw) > max) {
    return `${label} must be at most ${max} characters.`
  }
  return null
}

/** Non-whitespace and at most 2000 characters after trimming (DB-SCH-01). */
export function validateComment(raw: string): string | null {
  return validateRequiredText('Comment', raw, LIMITS.comment)
}

/**
 * Returns the card fields whose value differs from the card. Callers pass trimmed `title`
 * values. `description` is compared with `card.description ?? ''`, and `completed` with
 * `card.completed_at !== null`.
 */
export function changedCardFields(card: Card, values: CardFieldValues): CardField[] {
  const changed: CardField[] = []
  if (values.title !== card.title) {
    changed.push('title')
  }
  if (values.description !== (card.description ?? '')) {
    changed.push('description')
  }
  if (values.assignee_id !== card.assignee_id) {
    changed.push('assignee_id')
  }
  if (values.completed !== (card.completed_at !== null)) {
    changed.push('completed')
  }
  return changed
}

/** Returns `name` when it differs, and `email` when its trimmed value differs. */
export function changedProfileFields(user: User, values: ProfileFieldValues): ProfileField[] {
  const changed: ProfileField[] = []
  if (values.name !== user.name) {
    changed.push('name')
  }
  if (values.email.trim() !== user.email) {
    changed.push('email')
  }
  return changed
}

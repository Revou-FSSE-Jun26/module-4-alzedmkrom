"use client";

import { useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/errors";
import { error as showErrorToast } from "@/lib/toast";

// FE-API-05 mapping. Components never build messages from statusCode themselves.
export const FORBIDDEN_MESSAGE = "You don't have permission to do that.";
export const NOT_FOUND_MESSAGE = "That item no longer exists.";
export const VALIDATION_MESSAGE = "Please check the highlighted fields.";
export const UNREACHABLE_MESSAGE = "Can't reach the server. Check your connection.";
export const GENERIC_MESSAGE = "Something went wrong. Please try again.";

export interface ErrorDescription {
  /** Text for the toast, or null when no toast should be shown. */
  message: string | null;
  /** True when the session ended and the expiry flow must run. */
  endsSession: boolean;
  /** True when the error has field details the form shows inline (FE-FRM-02). */
  hasFieldDetails: boolean;
}

/** Maps any thrown value to the toast text (FE-API-05). */
export function describeError(error: unknown): ErrorDescription {
  if (!(error instanceof ApiError)) {
    return { message: GENERIC_MESSAGE, endsSession: false, hasFieldDetails: false };
  }
  // Code overrides come first. The 409 messages are the server's own text.
  if (error.statusCode === 0 || error.code === "NETWORK_ERROR") {
    return { message: UNREACHABLE_MESSAGE, endsSession: false, hasFieldDetails: false };
  }
  switch (error.statusCode) {
    case 401:
      return { message: null, endsSession: true, hasFieldDetails: false };
    case 403:
      return { message: FORBIDDEN_MESSAGE, endsSession: false, hasFieldDetails: false };
    case 404:
      return { message: NOT_FOUND_MESSAGE, endsSession: false, hasFieldDetails: false };
    case 409:
      return { message: error.message, endsSession: false, hasFieldDetails: false };
    case 422: {
      const hasFieldDetails = error.details !== null && Object.keys(error.details).length > 0;
      return {
        message: hasFieldDetails ? null : VALIDATION_MESSAGE,
        endsSession: false,
        hasFieldDetails,
      };
    }
    default:
      return { message: GENERIC_MESSAGE, endsSession: false, hasFieldDetails: false };
  }
}

// Returns a handler that shows one toast, or runs the expiry flow on 401 (FE-AUTH-04).
export function useErrorHandler(): (error: unknown) => void {
  const { expireSession } = useAuth();
  return useCallback(
    (error: unknown) => {
      const { message, endsSession } = describeError(error);
      if (endsSession) {
        void expireSession();
        return;
      }
      if (message !== null) {
        showErrorToast(message);
      }
    },
    [expireSession],
  );
}

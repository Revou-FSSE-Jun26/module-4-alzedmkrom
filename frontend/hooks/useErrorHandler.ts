"use client";

import { useCallback } from "react";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/errors";
import { error as showErrorToast } from "@/lib/toast";

const SESSION_EXPIRED_MESSAGE = "Your session has expired. Please log in again.";
const FORBIDDEN_MESSAGE = "You do not have permission to do this.";
const NOT_FOUND_MESSAGE = "The requested item was not found.";
const UNREACHABLE_MESSAGE = "Cannot reach the server. Check your connection.";
const GENERIC_MESSAGE = "Something went wrong. Please try again.";

export interface ErrorDescription {
  message: string;
  endsSession: boolean;
}

// Maps any thrown value to the toast text and to whether the session ends.
export function describeError(error: unknown): ErrorDescription {
  if (!(error instanceof ApiError)) {
    return { message: GENERIC_MESSAGE, endsSession: false };
  }

  switch (error.statusCode) {
    case 0:
      return { message: UNREACHABLE_MESSAGE, endsSession: false };
    case 400:
    case 409:
      return { message: error.message, endsSession: false };
    case 401:
      return { message: SESSION_EXPIRED_MESSAGE, endsSession: true };
    case 403:
      return { message: FORBIDDEN_MESSAGE, endsSession: false };
    case 404:
      return { message: NOT_FOUND_MESSAGE, endsSession: false };
    default:
      return { message: GENERIC_MESSAGE, endsSession: false };
  }
}

// Returns a handler that shows one error toast, then calls logout once
// when the error means the session has ended.
export function useErrorHandler(): (error: unknown) => void {
  const { logout } = useAuth();

  return useCallback(
    (error: unknown) => {
      const { message, endsSession } = describeError(error);
      showErrorToast(message);
      if (endsSession) {
        logout();
      }
    },
    [logout],
  );
}

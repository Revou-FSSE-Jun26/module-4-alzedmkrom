"use client";

import { useEffect, useState, type FormEvent } from "react";
import { BaseButton } from "@/components/shared/BaseButton";
import { ConfirmModal } from "@/components/shared/ConfirmModal";
import { FormField } from "@/components/shared/FormField";
import { useAuth } from "@/context/AuthContext";
import { useApi } from "@/hooks/useApi";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { sortByCreatedAt } from "@/lib/collections";
import { formatDateTime } from "@/lib/format";
import type { Comment, DeletedId } from "@/lib/types";
import { validateComment } from "@/lib/validation";

export interface CommentListProps {
  cardId: string;
}

const TEXTAREA_CLASSES =
  "rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 aria-[invalid=true]:border-red-600";

// Comments of one card, with a create form, and edit and delete for the
// current user's own comments (Requirements 14.1 to 14.13).
export function CommentList({ cardId }: CommentListProps) {
  const api = useApi();
  const handleError = useErrorHandler();
  const { user } = useAuth();

  // null until the first GET succeeds, so a failed load never shows "No comments yet".
  const [comments, setComments] = useState<Comment[] | null>(null);

  const [draft, setDraft] = useState("");
  const [draftError, setDraftError] = useState<string | null>(null);
  const [createPending, setCreatePending] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState("");
  const [editError, setEditError] = useState<string | null>(null);
  const [editPending, setEditPending] = useState(false);

  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deletePending, setDeletePending] = useState(false);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const response = await api.get<Comment[]>("/api/cards/" + cardId + "/comments");
        if (active) {
          setComments(sortByCreatedAt(response, "asc"));
        }
      } catch (caught) {
        if (active) {
          handleError(caught);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [api, cardId, handleError]);

  function isOwnComment(comment: Comment): boolean {
    return user !== null && comment.author.id === user.id;
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (createPending) {
      return;
    }
    const validationError = validateComment(draft);
    setDraftError(validationError);
    if (validationError !== null) {
      return;
    }
    setCreatePending(true);
    try {
      const created = await api.post<Comment>(
        "/api/cards/" + cardId + "/comments",
        { content: draft.trim() },
      );
      setCreatePending(false);
      setComments((previous) => (previous === null ? previous : [...previous, created]));
      setDraft("");
    } catch (caught) {
      setCreatePending(false);
      handleError(caught);
    }
  }

  function startEdit(comment: Comment) {
    setEditingId(comment.id);
    setEditDraft(comment.content);
    setEditError(null);
  }

  function cancelEdit() {
    setEditingId(null);
    setEditDraft("");
    setEditError(null);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>, commentId: string) {
    event.preventDefault();
    if (editPending) {
      return;
    }
    const validationError = validateComment(editDraft);
    setEditError(validationError);
    if (validationError !== null) {
      return;
    }
    setEditPending(true);
    try {
      const updated = await api.patch<Comment>("/api/comments/" + commentId, {
        content: editDraft.trim(),
      });
      setEditPending(false);
      setComments((previous) =>
        previous === null
          ? previous
          : previous.map((comment) => (comment.id === updated.id ? updated : comment)),
      );
      cancelEdit();
    } catch (caught) {
      setEditPending(false);
      handleError(caught);
    }
  }

  async function handleDelete() {
    if (deletingId === null || deletePending) {
      return;
    }
    const commentId = deletingId;
    setDeletePending(true);
    try {
      await api.delete<DeletedId>("/api/comments/" + commentId);
      setDeletePending(false);
      setComments((previous) =>
        previous === null ? previous : previous.filter((comment) => comment.id !== commentId),
      );
      if (editingId === commentId) {
        cancelEdit();
      }
      setDeletingId(null);
    } catch (caught) {
      setDeletePending(false);
      handleError(caught);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <h3 className="text-base font-semibold text-gray-900">Comments</h3>

      {comments !== null && comments.length === 0 ? (
        <p className="text-sm text-gray-600">No comments yet</p>
      ) : null}

      {comments !== null && comments.length > 0 ? (
        <ul className="flex flex-col gap-3">
          {comments.map((comment) => (
            <li key={comment.id} className="rounded-md border border-gray-200 p-3">
              <div className="flex flex-wrap items-baseline gap-2 text-sm">
                <span className="font-medium text-gray-900">{comment.author.name}</span>
                <time dateTime={comment.created_at} className="text-gray-600">
                  {formatDateTime(comment.created_at)}
                </time>
              </div>

              {editingId === comment.id ? (
                <form
                  noValidate
                  className="mt-2 flex flex-col gap-2"
                  onSubmit={(event) => void handleSave(event, comment.id)}
                >
                  <FormField label="Edit comment" error={editError}>
                    {(control) => (
                      <textarea
                        {...control}
                        name="content"
                        rows={3}
                        value={editDraft}
                        onChange={(event) => {
                          setEditDraft(event.target.value);
                          setEditError(null);
                        }}
                        className={TEXTAREA_CLASSES}
                      />
                    )}
                  </FormField>
                  <div className="flex justify-end gap-2">
                    <BaseButton variant="secondary" onClick={cancelEdit}>
                      Cancel
                    </BaseButton>
                    <BaseButton type="submit" loading={editPending}>
                      Save
                    </BaseButton>
                  </div>
                </form>
              ) : (
                <>
                  <p className="mt-1 whitespace-pre-wrap break-words text-sm text-gray-800">
                    {comment.content}
                  </p>
                  {isOwnComment(comment) ? (
                    <div className="mt-2 flex gap-2">
                      <BaseButton variant="secondary" onClick={() => startEdit(comment)}>
                        Edit
                      </BaseButton>
                      <BaseButton variant="destructive" onClick={() => setDeletingId(comment.id)}>
                        Delete
                      </BaseButton>
                    </div>
                  ) : null}
                </>
              )}
            </li>
          ))}
        </ul>
      ) : null}

      <form noValidate className="flex flex-col gap-2" onSubmit={handleCreate}>
        <FormField label="Add a comment" error={draftError}>
          {(control) => (
            <textarea
              {...control}
              name="content"
              rows={3}
              value={draft}
              onChange={(event) => {
                setDraft(event.target.value);
                setDraftError(null);
              }}
              className={TEXTAREA_CLASSES}
            />
          )}
        </FormField>
        <div className="flex justify-end">
          <BaseButton type="submit" loading={createPending}>
            Post comment
          </BaseButton>
        </div>
      </form>

      <ConfirmModal
        open={deletingId !== null}
        title="Delete comment"
        message="Delete this comment? This cannot be undone."
        confirmLabel="Delete"
        pending={deletePending}
        onConfirm={() => void handleDelete()}
        onCancel={() => setDeletingId(null)}
      />
    </section>
  );
}

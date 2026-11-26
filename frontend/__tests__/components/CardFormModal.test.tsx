import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CardFormModal } from '@/components/board/CardFormModal';
import { renderWithAuth } from '../helpers/renderWithAuth';
import type { Card, Member } from '@/types/api';

const members: Member[] = [
  { user_id: 'u-2', name: 'Bea', email: 'bea@example.com', role: 'member', created_at: '2026-01-01T00:00:00Z' },
  { user_id: 'u-3', name: 'Cal', email: 'cal@example.com', role: 'admin', created_at: '2026-01-01T00:00:00Z' },
];

const createdCard: Card = {
  id: 'card-1',
  board_id: 'board-1',
  column_id: 'col-7',
  title: 'Write docs',
  description: null,
  assignee_id: 'u-3',
  assignee: { id: 'u-3', name: 'Cal' },
  due_date: null,
  order: 1,
  completed_at: null,
  created_by: 'user-1',
  created_at: '2026-01-01T00:00:00Z',
};

function renderModal(overrides: Partial<React.ComponentProps<typeof CardFormModal>> = {}) {
  const props = {
    open: true,
    columnId: 'col-7',
    members,
    onClose: vi.fn(),
    onCreated: vi.fn(),
    ...overrides,
  };
  const result = renderWithAuth(<CardFormModal {...props} />);
  return { ...result, props };
}

describe('CardFormModal', () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', 'http://api.test');
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });

  it('lists an empty option selected by default, then one option per member in API order', () => {
    renderModal();

    const select = screen.getByLabelText('Assignee') as HTMLSelectElement;
    expect(select.value).toBe('');
    const options = Array.from(select.options).map((option) => option.textContent);
    expect(options).toEqual(['Unassigned', 'Bea', 'Cal']);
  });

  it('shows a title error and sends no request when the title is blank', async () => {
    const user = userEvent.setup();
    renderModal();

    await user.type(screen.getByLabelText('Title'), '   ');
    await user.click(screen.getByRole('button', { name: 'Create' }));

    expect(screen.getByLabelText('Title')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByText('Title is required.')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects a description longer than 5,000 characters without sending a request', async () => {
    renderModal();

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Task' } });
    fireEvent.change(screen.getByLabelText('Description'), {
      target: { value: 'x'.repeat(5_001) },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(screen.getByText('Description must be at most 5000 characters.')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('posts the trimmed title with a null assignee, then reports the card and closes', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(createdCard), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const { props } = renderModal();

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: '  Write docs  ' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(props.onCreated).toHaveBeenCalledWith(createdCard));
    expect(props.onClose).toHaveBeenCalledTimes(1);

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe('http://api.test/api/columns/col-7/cards');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body as string)).toEqual({
      title: 'Write docs',
      description: '',
      assignee_id: null,
    });
  });

  it('sends the selected member id as assignee_id', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify(createdCard), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    renderModal();

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Task' } });
    fireEvent.change(screen.getByLabelText('Assignee'), { target: { value: 'u-3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(1));
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(JSON.parse(init.body as string).assignee_id).toBe('u-3');
  });

  it('keeps the modal open with the entered values and re-enables submit after a failure', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ error: { code: 'NOT_FOUND', message: 'Column not found.', details: null } }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const { props } = renderModal();

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Keep me' } });
    fireEvent.change(screen.getByLabelText('Description'), { target: { value: 'Details' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Create' })).toBeEnabled());
    expect(props.onCreated).not.toHaveBeenCalled();
    expect(props.onClose).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Title')).toHaveValue('Keep me');
    expect(screen.getByLabelText('Description')).toHaveValue('Details');
  });
});

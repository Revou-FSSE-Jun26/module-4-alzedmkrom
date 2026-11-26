import { http, HttpResponse } from 'msw';
import { setupServer } from 'msw/node';
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { apiClient, resolveBaseUrl } from '@/lib/apiClient';
import { ApiError } from '@/lib/errors';

const BASE = 'http://api.test';
const server = setupServer();

beforeAll(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', BASE);
  server.listen({ onUnhandledRequest: 'error' });
});
afterEach(() => {
  server.resetHandlers();
});
afterAll(() => {
  server.close();
  vi.unstubAllEnvs();
});

describe('apiClient (browser environment)', () => {
  it('attaches the Bearer header when a token is given', async () => {
    let auth: string | null = null;
    server.use(
      http.get(`${BASE}/api/users/me`, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.json({ id: 'u1' });
      }),
    );
    await apiClient.get('/api/users/me', { token: 'tok-1' });
    expect(auth).toBe('Bearer tok-1');
  });

  it('sends no Authorization header without a token', async () => {
    let auth: string | null = 'unset';
    server.use(
      http.get(`${BASE}/api/boards`, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.json({ items: [] });
      }),
    );
    await apiClient.get('/api/boards');
    expect(auth).toBeNull();
  });

  it('returns the bare JSON body of a success response (BE-ERR-05)', async () => {
    server.use(http.get(`${BASE}/api/boards/1`, () => HttpResponse.json({ id: '1', name: 'Roadmap' })));
    await expect(apiClient.get<{ id: string; name: string }>('/api/boards/1')).resolves.toEqual({
      id: '1',
      name: 'Roadmap',
    });
  });

  it('returns undefined for a 204 response', async () => {
    server.use(http.delete(`${BASE}/api/cards/c1`, () => new HttpResponse(null, { status: 204 })));
    await expect(apiClient.delete('/api/cards/c1')).resolves.toBeUndefined();
  });

  it('throws ApiError with code and details from the BE-ERR-01 body on 422', async () => {
    server.use(
      http.patch(`${BASE}/api/cards/c1/position`, () =>
        HttpResponse.json(
          {
            error: {
              code: 'VALIDATION_ERROR',
              message: 'Invalid request data.',
              details: { order: ['Must be greater than 0.'] },
            },
          },
          { status: 422 },
        ),
      ),
    );
    const caught = await apiClient
      .patch('/api/cards/c1/position', { body: { column_id: 'x', order: 0 } })
      .catch((error: unknown) => error);
    expect(caught).toBeInstanceOf(ApiError);
    expect(caught).toMatchObject({
      statusCode: 422,
      code: 'VALIDATION_ERROR',
      details: { order: ['Must be greater than 0.'] },
    });
  });

  it('throws ApiError on 401 with the server code', async () => {
    server.use(
      http.get(`${BASE}/api/users/me`, () =>
        HttpResponse.json(
          { error: { code: 'UNAUTHENTICATED', message: 'Log in again.', details: null } },
          { status: 401 },
        ),
      ),
    );
    await expect(apiClient.get('/api/users/me', { token: 'old' })).rejects.toMatchObject({
      statusCode: 401,
      code: 'UNAUTHENTICATED',
    });
  });

  it('throws ApiError on 5xx', async () => {
    server.use(
      http.get(`${BASE}/api/boards`, () =>
        HttpResponse.json(
          { error: { code: 'INTERNAL_ERROR', message: 'Something went wrong.', details: null } },
          { status: 500 },
        ),
      ),
    );
    await expect(apiClient.get('/api/boards')).rejects.toMatchObject({
      statusCode: 500,
      code: 'INTERNAL_ERROR',
    });
  });

  it('throws ApiError with code UNKNOWN for a non-JSON error body', async () => {
    server.use(
      http.get(`${BASE}/api/boards`, () =>
        new HttpResponse('<html>Bad gateway</html>', {
          status: 502,
          headers: { 'Content-Type': 'text/html' },
        }),
      ),
    );
    await expect(apiClient.get('/api/boards')).rejects.toMatchObject({
      statusCode: 502,
      code: 'UNKNOWN',
    });
  });

  it('throws ApiError with statusCode 0 and NETWORK_ERROR when the request fails', async () => {
    server.use(http.get(`${BASE}/api/boards`, () => HttpResponse.error()));
    await expect(apiClient.get('/api/boards')).rejects.toMatchObject({
      statusCode: 0,
      code: 'NETWORK_ERROR',
    });
  });

  it('uses NEXT_PUBLIC_API_BASE_URL in the browser and throws when it is missing', () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '  http://api.test///  ');
    expect(resolveBaseUrl()).toBe('http://api.test');
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '');
    expect(() => resolveBaseUrl()).toThrow('NEXT_PUBLIC_API_BASE_URL is not set');
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', BASE);
  });
});

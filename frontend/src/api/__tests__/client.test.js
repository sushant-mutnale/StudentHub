import { AxiosError } from 'axios';
import { describe, expect, it } from 'vitest';

import { api } from '../client';

describe('api error interceptor', () => {
  it('preserves the response on a 409 so callers can handle conflicts', async () => {
    const detail = { code: 'session_exists', session_id: 's1' };

    await expect(
      api.post(
        '/agent-interview/start',
        {},
        {
          adapter: async (config) => {
            throw new AxiosError(
              'conflict',
              'ERR_BAD_REQUEST',
              config,
              {},
              {
                status: 409,
                statusText: 'Conflict',
                headers: {},
                config,
                data: { detail },
              }
            );
          },
        }
      )
    ).rejects.toMatchObject({
      response: { status: 409, data: { detail } },
    });
  });
});

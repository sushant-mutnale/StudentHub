import { describe, expect, it } from 'vitest'

import { API_BASE_URL } from '../env'

describe('API_BASE_URL', () => {
  it('defaults to same-origin when VITE_API_URL is unset', () => {
    expect(API_BASE_URL).toBe('')
  })
})

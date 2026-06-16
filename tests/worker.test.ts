// tests/worker.test.ts
import { describe, expect, it } from 'vitest'
import worker, { TelegramContainer, pickContainerEnv } from '../src/worker'

// Minimal in-memory KV that matches the Env.KV shape (arrayBuffer get/put/delete).
function makeKv() {
  const store = new Map<string, ArrayBuffer>()
  return {
    store,
    async get(k: string, type?: string) {
      const v = store.get(k)
      if (v === undefined) return null
      return type === 'arrayBuffer' ? v : new TextDecoder().decode(v)
    },
    async put(k: string, v: string | ArrayBuffer) {
      store.set(k, typeof v === 'string' ? new TextEncoder().encode(v).buffer : v)
    },
    async delete(k: string) { store.delete(k) },
  }
}

describe('kvOutbound (via TelegramContainer.outboundByHost)', () => {
  const handler = TelegramContainer.outboundByHost['kv.internal']

  it('returns 404 for a missing key', async () => {
    const env = { KV: makeKv() } as any
    const res = await handler(new Request('http://kv.internal/telegram%2Fsubs%2Fu1%2Fsession'), env)
    expect(res.status).toBe(404)
  })

  it('round-trips a binary blob via arrayBuffer (PUT then GET)', async () => {
    const env = { KV: makeKv() } as any
    const blob = new Uint8Array([0, 1, 2, 250, 251, 255]).buffer  // non-UTF8 bytes
    await handler(new Request('http://kv.internal/telegram%2Fconfig', { method: 'PUT', body: blob }), env)
    const res = await handler(new Request('http://kv.internal/telegram%2Fconfig'), env)
    expect(res.status).toBe(200)
    expect(new Uint8Array(await res.arrayBuffer())).toEqual(new Uint8Array(blob))
  })

  it('DELETE removes the key', async () => {
    const env = { KV: makeKv() } as any
    await handler(new Request('http://kv.internal/k', { method: 'PUT', body: new ArrayBuffer(1) }), env)
    await handler(new Request('http://kv.internal/k', { method: 'DELETE' }), env)
    const res = await handler(new Request('http://kv.internal/k'), env)
    expect(res.status).toBe(404)
  })
})

describe('pickContainerEnv forwards security-critical secrets into the container', () => {
  it('forwards MCP_RELAY_PASSWORD (Gate A) so /authorize is gated, not open', () => {
    const env = {
      MCP_RELAY_PASSWORD: 'shared-pw',
      MCP_DCR_SERVER_SECRET: 'dcr',
      CREDENTIAL_SECRET: 'cred',
      MCP_STORAGE_BACKEND: 'cf-kv',
    } as any
    const out = pickContainerEnv(env)
    // Regression guard: dropping MCP_RELAY_PASSWORD here turns the deployed server
    // into an open self-service relay (the human front door vanishes).
    expect(out.MCP_RELAY_PASSWORD).toBe('shared-pw')
    expect(out.MCP_DCR_SERVER_SECRET).toBe('dcr')
    expect(out.CREDENTIAL_SECRET).toBe('cred')
  })

  it('drops empty/unset values so a blank secret never injects', () => {
    const env = { MCP_RELAY_PASSWORD: '', MCP_STORAGE_BACKEND: 'cf-kv' } as any
    const out = pickContainerEnv(env)
    expect('MCP_RELAY_PASSWORD' in out).toBe(false)
    expect(out.MCP_STORAGE_BACKEND).toBe('cf-kv')
  })
})

describe('fetch routes to per-user DO by JWT sub', () => {
  it('uses sub from the Bearer token as the DO name', async () => {
    let namedWith = ''
    const env = {
      TELEGRAM: {
        idFromName(n: string) { namedWith = n; return { n } },
        get() { return { fetch: async () => new Response('ok') } },
      },
    } as any
    // JWT with payload {"sub":"user-xyz"} (header.payload.sig; only payload is read)
    const payload = btoa(JSON.stringify({ sub: 'user-xyz' }))
    const req = new Request('https://telegram.n24q02m.com/mcp', {
      headers: { authorization: `Bearer h.${payload}.s` },
    })
    const res = await worker.fetch(req, env)
    expect(await res.text()).toBe('ok')
    expect(namedWith).toBe('user-xyz')
  })
})

// tests/worker.test.ts
import { describe, expect, it } from 'vitest'
import worker, { TelegramContainer, pickContainerEnv } from '../src/worker'

// Minimal in-memory KV that matches the Env.KV shape (arrayBuffer get/put/delete).
// ArrayBufferLike (not ArrayBuffer): TypeScript's Uint8Array is generic since
// TS 5.7, so `TextEncoder#encode(...).buffer` is typed ArrayBufferLike (the
// ArrayBuffer | SharedArrayBuffer union), even though a real TextEncoder never
// backs its output with a SharedArrayBuffer.
function makeKv() {
  const store = new Map<string, ArrayBufferLike>()
  return {
    store,
    async get(k: string, type?: string) {
      const v = store.get(k)
      if (v === undefined) return null
      return type === 'arrayBuffer' ? v : new TextDecoder().decode(v as ArrayBuffer)
    },
    async put(k: string, v: string | ArrayBuffer) {
      store.set(k, typeof v === 'string' ? new TextEncoder().encode(v).buffer : v)
    },
    async delete(k: string) { store.delete(k) },
  }
}

// OutboundHandlerContext<unknown> (the kvOutbound handler's ctx type): only
// containerId/className are required, `params` stays optional -- see
// @cloudflare/containers dist/lib/container.d.ts OutboundHandlerContext.
const outboundCtx = { containerId: 'test-container', className: 'TelegramContainer' }

describe('kvOutbound (via TelegramContainer.outboundByHost)', () => {
  // outboundByHost is typed possibly-undefined by the library (it's only set
  // once ../src/worker's module-level `TelegramContainer.outboundByHost = {...}`
  // assignment runs) -- assert the invariant explicitly instead of `!`, so a
  // future refactor that drops the assignment fails loudly here, not silently.
  const outboundByHost = TelegramContainer.outboundByHost
  if (!outboundByHost) throw new Error('TelegramContainer.outboundByHost not registered by ../src/worker import')
  const handler = outboundByHost['kv.internal']

  it('returns 404 for a missing key', async () => {
    const env = { KV: makeKv() } as any
    const res = await handler(new Request('http://kv.internal/telegram%2Fsubs%2Fu1%2Fsession'), env, outboundCtx)
    expect(res.status).toBe(404)
  })

  it('round-trips a binary blob via arrayBuffer (PUT then GET)', async () => {
    const env = { KV: makeKv() } as any
    const blob = new Uint8Array([0, 1, 2, 250, 251, 255]).buffer  // non-UTF8 bytes
    await handler(new Request('http://kv.internal/telegram%2Fconfig', { method: 'PUT', body: blob }), env, outboundCtx)
    const res = await handler(new Request('http://kv.internal/telegram%2Fconfig'), env, outboundCtx)
    expect(res.status).toBe(200)
    expect(new Uint8Array(await res.arrayBuffer())).toEqual(new Uint8Array(blob))
  })

  it('DELETE removes the key', async () => {
    const env = { KV: makeKv() } as any
    await handler(new Request('http://kv.internal/k', { method: 'PUT', body: new ArrayBuffer(1) }), env, outboundCtx)
    await handler(new Request('http://kv.internal/k', { method: 'DELETE' }), env, outboundCtx)
    const res = await handler(new Request('http://kv.internal/k'), env, outboundCtx)
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

describe('fetch routes to the single reserved container DO', () => {
  it('names the DO "default" regardless of the Bearer token sub (SINGLE-DO COLLAPSE, see extractUserId)', async () => {
    let namedWith = ''
    const env = {
      TELEGRAM: {
        idFromName(n: string) { namedWith = n; return { n } },
        get() { return { fetch: async () => new Response('ok') } },
      },
    } as any
    // JWT with payload {"sub":"user-xyz"} (header.payload.sig; only payload is read)
    const payload = btoa(JSON.stringify({ sub: 'user-xyz' }))
    // POST, not GET: the edge now declines the standing GET /mcp SSE stream
    // with 405 (see "edge declines the standing GET /mcp SSE stream" below),
    // so DO-routing is exercised via POST here.
    const req = new Request('https://telegram.n24q02m.com/mcp', {
      method: 'POST',
      headers: { authorization: `Bearer h.${payload}.s` },
    })
    const res = await worker.fetch(req, env)
    expect(await res.text()).toBe('ok')
    expect(namedWith).toBe('default')
  })
})

describe('edge auth gate rejects anonymous /mcp before touching the container DO', () => {
  function makeEnv() {
    let stubCalls = 0
    const env = {
      TELEGRAM: {
        idFromName(n: string) { return { n } },
        get() { return { fetch: async () => { stubCalls++; return new Response('ok') } } },
      },
    } as any
    return { env, calls: () => stubCalls }
  }

  it('POST /mcp with no Authorization -> 401, stub never called', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/mcp', { method: 'POST' })
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(401)
    expect(res.headers.get('WWW-Authenticate')).toMatch(
      /^Bearer resource_metadata="https:\/\/[^"]+\/\.well-known\/oauth-protected-resource"$/,
    )
    expect(await res.text()).toBe('')
    expect(calls()).toBe(0)
  })

  it('OPTIONS /mcp with no Authorization -> 401, stub never called', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/mcp', { method: 'OPTIONS' })
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(401)
    expect(calls()).toBe(0)
  })

  it('POST /mcp with Authorization: Bearer anything -> stub called exactly once', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/mcp', {
      method: 'POST',
      headers: { authorization: 'Bearer anything' },
    })
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(200)
    expect(calls()).toBe(1)
  })

  it('GET /authorize with no Authorization -> non-/mcp path passes through to the DO', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/authorize?foo=1')
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(200)
    expect(calls()).toBe(1)
  })
})

describe('edge declines the standing GET /mcp SSE stream (container never pinned awake by an idle stream)', () => {
  function makeEnv() {
    let stubCalls = 0
    const env = {
      TELEGRAM: {
        idFromName(n: string) { return { n } },
        get() { return { fetch: async () => { stubCalls++; return new Response('ok') } } },
      },
    } as any
    return { env, calls: () => stubCalls }
  }

  it('GET /mcp with Authorization -> 405, Allow: POST, DELETE, stub never called', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/mcp', {
      method: 'GET',
      headers: { authorization: 'Bearer x' },
    })
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(405)
    expect(res.headers.get('Allow')).toBe('POST, DELETE')
    expect(calls()).toBe(0)
  })

  it('GET /mcp/sub with Authorization -> 405', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/mcp/sub', {
      method: 'GET',
      headers: { authorization: 'Bearer x' },
    })
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(405)
    expect(calls()).toBe(0)
  })

  it('GET /mcp with no Authorization -> still 401 (bearer gate runs first)', async () => {
    const { env, calls } = makeEnv()
    const req = new Request('https://telegram.n24q02m.com/mcp', { method: 'GET' })
    const res = await worker.fetch(req, env)
    expect(res.status).toBe(401)
    expect(calls()).toBe(0)
  })
})

describe('tombstone contract (W4 dehost preparation & drill)', () => {
  function makeEnv(flags: Record<string, string> = {}) {
    let stubCalls = 0
    const env = {
      TELEGRAM: {
        idFromName(n: string) { return { n } },
        get() { return { fetch: async () => { stubCalls++; return new Response('ok') } } },
      },
      ...flags,
    }
    return { env: env as never, calls: () => stubCalls }
  }

  it('returns 410 Gone with non-sensitive successor message and headers before edge auth when DEHOSTED is true', async () => {
    const { env, calls } = makeEnv({ DEHOSTED: 'true' })
    const res = await worker.fetch(
      new Request('https://telegram.n24q02m.com/mcp', {
        method: 'POST',
      }),
      env
    )

    expect(res.status).toBe(410)
    expect(res.headers.get('Content-Type')).toBe('application/json')
    expect(res.headers.get('X-Dehosted-Successor')).toBe('https://mcp.n24q02m.com/servers/better-telegram-mcp/')

    const body = (await res.json()) as Record<string, unknown>
    expect(body).toMatchObject({
      error: 'hosted_runtime_dehosted',
      status: 410,
      successor: 'https://mcp.n24q02m.com/servers/better-telegram-mcp/',
    })
    expect(body.message).toContain('retired')
    expect(body.message).toContain('stdio')

    // CRITICAL: 0 requests reach the Container DO
    expect(calls()).toBe(0)
  })

  it('returns 410 Gone on all routes before auth/DO for DEHOSTED and the existing TOMBSTONE drill alias', async () => {
    for (const flag of ['DEHOSTED', 'TOMBSTONE'] as const) {
      const { env, calls } = makeEnv({ [flag]: 'true' })

      for (const path of ['/authorize', '/health', '/.well-known/jwks.json', '/mcp/v1']) {
        const res = await worker.fetch(
          new Request(`https://telegram.n24q02m.com${path}`, { method: 'GET' }),
          env
        )
        expect(res.status).toBe(410)
        expect(res.headers.get('X-Dehosted-Successor')).toBe('https://mcp.n24q02m.com/servers/better-telegram-mcp/')
      }

      expect(calls()).toBe(0)
    }
  })
})

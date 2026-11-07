import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { retryMessage, streamMessage } from './conversations'

beforeEach(() => vi.stubGlobal('localStorage', { getItem: () => null }))
afterEach(() => vi.unstubAllGlobals())

function responseFor(text: string): Response {
  const bytes = new TextEncoder().encode(text)
  return new Response(new ReadableStream<Uint8Array>({
    start(controller) {
      // Split UTF-8 characters and CRLF delimiters across arbitrary network chunks.
      for (let i = 0; i < bytes.length; i += 7) controller.enqueue(bytes.slice(i, i + 7))
      controller.close()
    }
  }))
}

describe('conversation streams', () => {
  it('decodes chunked Chinese SSE events on the retry endpoint', async () => {
    const response = responseFor('event: text_delta\r\ndata: {"content":"推荐依据"}\r\n\r\nevent: message_end\r\ndata: {"message_id":"saved"}\r\n\r\n')
    const fetch = vi.fn().mockResolvedValue(response)
    vi.stubGlobal('fetch', fetch)
    const emit = vi.fn()
    await retryMessage('conversation', 'turn', { stage: 'generating' }, emit)
    expect(fetch.mock.calls[0][0]).toContain('/messages/turn/retry')
    expect(JSON.parse(fetch.mock.calls[0][1].body)).toEqual({ stage: 'generating' })
    expect(emit.mock.calls.map(call => call[0])).toEqual([
      { event: 'text_delta', data: { content: '推荐依据' } },
      { event: 'message_end', data: { message_id: 'saved' } }
    ])
    expect(response.body?.locked).toBe(false)
  })

  it('preserves a useful rejection message from the backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { message: '请对最新一轮推荐进行操作。' }
    }), { status: 409 })))
    await expect(retryMessage('conversation', 'turn', { stage: 'comparing' }, vi.fn()))
      .rejects.toMatchObject({ name: 'ConversationStreamError', message: '请对最新一轮推荐进行操作。' })
  })

  it('closes the response reader if processing an event fails', async () => {
    const response = responseFor('event: error\ndata: {"message":"失败"}\n\n')
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    await expect(streamMessage('conversation', { content: '找书' }, () => { throw new Error('失败') }))
      .rejects.toThrow('失败')
    expect(response.body?.locked).toBe(false)
  })
})

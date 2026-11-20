import assert from 'node:assert/strict';
import test from 'node:test';
import { readAIResponse } from '../src/assets/frontend/aiResponse.js';

test('successful replies keep paragraphs and markdown', async () => {
  const text = 'Hello\n\n**World**';
  assert.equal(await readAIResponse(Response.json({ response: text })), text);
});
test('rate-limit details reach the frontend instead of becoming an assistant reply', async () => {
  await assert.rejects(readAIResponse(Response.json({ error: 'This model is rate-limited.' }, { status: 429 })), /rate-limited/);
});
test('HTTP 200 with an error body is treated as a failure', async () => {
  await assert.rejects(readAIResponse(Response.json({ error: { message: 'Provider unavailable' } })), /Provider unavailable/);
});
test('missing or empty response content is rejected', async () => {
  for (const data of [{}, { response: null }, { response: '  ' }]) {
    await assert.rejects(readAIResponse(Response.json(data)), /empty answer/);
  }
});
test('non-JSON upstream errors get a readable fallback', async () => {
  await assert.rejects(readAIResponse(new Response('<h1>Bad Gateway</h1>', { status: 502 })), /HTTP 502/);
});

// Run against npm run dev. Uses installed Chrome/Edge and Node 22, no browser packages.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, resolve } from 'node:path';
import { createServer } from 'node:net';

const models = JSON.parse(readFileSync(new URL('./fixtures/model-capabilities.json', import.meta.url)));
const [flint, xingchen] = models;
const chrome = process.env.CHROME_PATH || [
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(existsSync);
assert.ok(chrome, 'Set CHROME_PATH to an installed Chrome or Edge executable');
const port = await new Promise((done) => {
  const server = createServer().listen(0, '127.0.0.1', () => {
    const chosen = server.address().port;
    server.close(() => done(chosen));
  });
});
const profile = mkdtempSync(join(tmpdir(), 'promptly-parameters-'));
const browser = spawn(chrome, [...(process.env.CI ? ['--no-sandbox'] : []), '--headless=new', '--disable-gpu', '--no-first-run',
  '--no-default-browser-check', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
  'about:blank'], { windowsHide: true, stdio: 'ignore' });
const delay = (ms) => new Promise((done) => setTimeout(done, ms));
let socket;
try {
  let targets;
  for (let attempt = 0; attempt < 100; attempt++) {
    try { targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json(); break; }
    catch { await delay(100); }
  }
  assert.ok(targets, 'Browser debugging endpoint did not start');
  socket = new WebSocket(targets.find((target) => target.type === 'page').webSocketDebuggerUrl);
  await new Promise((done, reject) => { socket.onopen = done; socket.onerror = reject; });
  let nextId = 0;
  const pending = new Map();
  const errors = [];
  const requests = [];
  const alerts = [];
  const authRequests = [];
  let failNextResponse = false;
  let capturing = false;
  const detailsLoaded = new Set();
  function cdp(method, params = {}) {
    return new Promise((done, reject) => {
      const id = ++nextId;
      const timeout = setTimeout(() => { pending.delete(id); reject(new Error(`CDP timeout: ${method}`)); }, 15000);
      pending.set(id, { done, reject, timeout });
      socket.send(JSON.stringify({ id, method, params }));
    });
  }
  socket.onmessage = ({ data }) => {
    const event = JSON.parse(data);
    if (event.id) {
      const task = pending.get(event.id);
      if (!task) return;
      pending.delete(event.id);
      clearTimeout(task.timeout);
      if (event.error) task.reject(new Error(event.error.message)); else task.done(event.result);
    } else if (event.method === 'Page.javascriptDialogOpening') {
      alerts.push(event.params.message);
      cdp('Page.handleJavaScriptDialog', { accept: true }).catch((error) => errors.push(String(error)));
    } else if (event.method === 'Runtime.exceptionThrown') {
      errors.push(event.params.exceptionDetails.exception?.description || event.params.exceptionDetails.text);
    } else if (event.method === 'Fetch.requestPaused') {
      fulfill(event.params).catch((error) => errors.push(String(error)));
    }
  };
  async function fulfill({ requestId, request }) {
    const path = new URL(request.url).pathname;
    let result = {};
    let responseCode = 200;
    if (request.method === 'OPTIONS') result = {};
    else if (path.startsWith('/api/Load_chats_name/')) result = [{ title: 'Ideas & questions', chatId: '000000000000000000000002' }];
    else if (path.startsWith('/api/Load_chat_messages/')) result = capturing ? [
      { role: 'user', message: 'How can I break a large project into manageable steps?' },
      { role: 'AI', message: 'Start with a clear outcome, then work backward.\n\n1. **Define what done means.** Write down the result someone should be able to see or use.\n2. **Find the smallest useful version.** Choose one complete flow you can finish first.\n3. **Make the next task concrete.** A small task should have a clear input, an action, and a way to check it.\n\nBuild one piece, get feedback, and adjust your plan as you learn.' }
    ] : [];
    else if (path === '/api/Load_models') result = models;
    else if (path === '/api/Load_model_details') {
      const id = JSON.parse(request.postData).model_id;
      result = models.find((model) => model.id === id);
      detailsLoaded.add(id);
    } else if (path === '/api/save_message_ai/') result = { message: 'Message saved successfully' };
    else if (path === '/api/save_voice_message') result = { transcript: 'Voice parameter test' };
    else if (path === '/api/get_ai_response') {
      requests.push(JSON.parse(request.postData));
      if (failNextResponse) {
        failNextResponse = false;
        responseCode = 429;
        result = { error: 'This model is rate-limited. Try again shortly or select another model.', code: 'rate_limit_exceeded' };
      } else result = { response: 'Test answer' };
    } else if (['/api/sign_in', '/api/send_code', '/api/sign_up'].includes(path)) {
      authRequests.push({ path, body: JSON.parse(request.postData) });
      if (path === '/api/sign_in') { responseCode = 401; result = { error: 'Invalid email or password' }; }
      else result = path === '/api/sign_up' ? { confirmed: true } : { message: 'Code sent!' };
    } else throw new Error(`Unexpected API call: ${path}`);
    await cdp('Fetch.fulfillRequest', { requestId, responseCode,
      responseHeaders: [
        { name: 'Content-Type', value: 'application/json' },
        { name: 'Access-Control-Allow-Origin', value: 'http://localhost:5173' },
        { name: 'Access-Control-Allow-Headers', value: 'authorization,content-type' },
        { name: 'Access-Control-Allow-Methods', value: 'GET,POST,OPTIONS' },
      ], body: Buffer.from(JSON.stringify(result)).toString('base64') });
  }
  async function evaluate(expression) {
    const result = await cdp('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description);
    return result.result.value;
  }
  async function until(expression) {
    for (let attempt = 0; attempt < 100; attempt++) {
      if (await evaluate(expression)) return;
      await delay(50);
    }
    throw new Error(`Browser assertion timed out: ${expression}`);
  }
  async function setValue(selector, value, kind = 'input') {
    await evaluate(`(() => {
      const element = document.querySelector(${JSON.stringify(selector)});
      const prototype = ${kind === 'select' ? 'HTMLSelectElement' : kind === 'textarea' ? 'HTMLTextAreaElement' : 'HTMLInputElement'}.prototype;
      Object.getOwnPropertyDescriptor(prototype, 'value').set.call(element, ${JSON.stringify(String(value))});
      element.dispatchEvent(new Event(${JSON.stringify(kind === 'select' ? 'change' : 'input')}, { bubbles: true }));
    })()`);
    await delay(30);
  }
  const click = (selector) => evaluate(`document.querySelector(${JSON.stringify(selector)}).click()`);
  const temperature = '.models-nav input[aria-label="Temperature"]';
  async function select(model) {
    await setValue('#model-select', model.id, 'select');
    await until(`document.querySelector('.models-nav')?.textContent.includes(${JSON.stringify(model.name)})`);
  }
  async function sendText() {
    const count = requests.length;
    await setValue('.chat-textarea', 'Parameter test', 'textarea');
    await click('.chat-container > .send-button');
    for (let attempt = 0; attempt < 100 && requests.length === count; attempt++) await delay(50);
    assert.equal(requests.length, count + 1);
    return requests.at(-1);
  }
  await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await cdp('Runtime.enable');
  await cdp('Fetch.enable', { patterns: [{ urlPattern: '*://*/api/*' }] });
  const token = `test.${Buffer.from(JSON.stringify({ user_id: '000000000000000000000001', user_email: 'test@example.invalid', exp: Math.floor(Date.now() / 1000) + 3600 })).toString('base64url')}.test`;
  await cdp('Page.addScriptToEvaluateOnNewDocument', { source: `
    localStorage.setItem('authToken', ${JSON.stringify(token)});
    Object.defineProperty(navigator, 'mediaDevices', { configurable: true, value: {
      getUserMedia: async () => ({ getTracks: () => [] })
    }});
    window.MediaRecorder = class {
      start() { this.ondataavailable({ data: new Blob(['test'], { type: 'audio/webm' }) }); }
      stop() { this.onstop(); }
    };
  ` });
  await cdp('Page.navigate', { url: 'http://localhost:5173/app' });
  await until(`!!document.querySelector('.chat-button')`);
  await click('.chat-button');
  await until(`!!document.querySelector('.chat-textarea')`);
  await click('.chat-container > .tools-button');
  await until(`document.querySelector('#model-select')?.options.length === 3`);

  // Capabilities load even when the parameter panel has never been opened.
  await setValue('#model-select', flint.id, 'select');
  for (let attempt = 0; attempt < 100 && !detailsLoaded.has(flint.id); attempt++) await delay(50);
  await delay(100);
  const unopened = await sendText();
  assert.deepEqual(unopened.parameters, { max_tokens: 8192, temperature: 0.7, top_p: 1 });
  await click('header .header-right button');
  await until(`document.querySelector('.models-nav')?.textContent.includes(${JSON.stringify(flint.name)})`);
  assert.equal(await evaluate(`document.querySelector('[aria-label="Max Tokens"]').max`), '32768');
  await setValue('[aria-label="Max Tokens"]', 16384);
  await click('.apply-btn');
  assert.equal((await sendText()).parameters.max_tokens, 16384);
  assert.deepEqual(await evaluate(`[...document.querySelectorAll('.model-param input')].map(e => e.getAttribute('aria-label'))`),
    ['Max Tokens', 'Temperature', 'Top P', 'Seed']);
  await setValue(temperature, 0.3);
  await click('.apply-btn');
  assert.equal((await sendText()).parameters.temperature, 0.3);

  await select(xingchen);
  assert.equal(await evaluate(`Number(document.querySelector(${JSON.stringify(temperature)}).value)`), 1);
  assert.equal(await evaluate(`Number(document.querySelector('[aria-label="Top P"]').value)`), 0.95);
  assert.equal(await evaluate(`Number(document.querySelector('[aria-label="Repetition Penalty"]').value)`), 1.05);
  for (const label of ['Frequency Penalty', 'Presence Penalty', 'Top K', 'Min P']) {
    assert.equal(await evaluate(`!!document.querySelector(${JSON.stringify(`[aria-label="${label}"]`)})`), true);
  }
  await setValue(temperature, 1.2);
  assert.equal((await sendText()).parameters.temperature, 1); // Draft is not yet applied.
  await click('.apply-btn');
  assert.equal((await sendText()).parameters.temperature, 1.2);
  await select(flint);
  assert.equal(await evaluate(`Number(document.querySelector(${JSON.stringify(temperature)}).value)`), 0.3);
  await select(xingchen);
  assert.equal(await evaluate(`Number(document.querySelector(${JSON.stringify(temperature)}).value)`), 1.2);
  await select(flint);
  await click('header .header-right button');
  await until(`!document.querySelector('.models-nav')`);
  await click('header .header-right button');
  await until(`!!document.querySelector('.models-nav')`);
  assert.equal(await evaluate(`Number(document.querySelector(${JSON.stringify(temperature)}).value)`), 0.3);

  // Exercise the existing voice transcript -> get_ai_response flow too.
  const previousCount = requests.length;
  await click('.voice-button');
  await until(`!!document.querySelector('.voice-buttons')`);
  await click('.voice-buttons .tools-button');
  await delay(100);
  await evaluate(`document.querySelectorAll('.voice-buttons .tools-button')[1].click()`);
  await delay(100);
  await click('.voice-buttons .send-button');
  for (let attempt = 0; attempt < 100 && requests.length === previousCount; attempt++) await delay(50);
  assert.equal(requests.length, previousCount + 1);
  assert.equal(requests.at(-1).parameters.temperature, 0.3);
  for (const request of requests) {
    const model = models.find((item) => item.id === request.model);
    for (const parameter of Object.keys(request.parameters)) assert.ok(model.supported_parameters.includes(parameter));
    assert.equal('seed' in request.parameters, false);
  }
  await click('.voice-buttons .cancel-button');
  await until(`!!document.querySelector('.chat-textarea')`);
  failNextResponse = true;
  await sendText();
  for (let attempt = 0; attempt < 100 && alerts.length === 0; attempt++) await delay(50);
  assert.match(alerts.at(-1), /rate-limited/);
  await until(`!document.querySelector('.message.assistant.loading')`);
  assert.equal(await evaluate(`document.body.textContent.includes('Failed to generate AI response')`), false);
  assert.deepEqual(errors, []);
  // Verify the code is submitted with the final account creation request.
  await cdp('Page.navigate', { url: 'http://localhost:5173/' });
  await until(`!!document.querySelector('.auth-form')`);
  await setValue('[name=email]', 'reader@example.com');
  await setValue('[name=password]', 'test-password-long');
  await click('.auth-button');
  await until(`!!document.querySelector('[role=alert]')`);
  assert.match(await evaluate(`document.querySelector('[role=alert]').textContent`), /Invalid email or password/);
  await click('.toggle-link');
  await setValue('[name=email]', 'reader@example.com');
  await setValue('[name=password]', 'test-password-long');
  await setValue('[name=confirmPassword]', 'test-password-long');
  await click('.auth-button');
  await until(`!!document.querySelector('[name=code]')`);
  await setValue('[name=code]', '123456');
  await click('.auth-button');
  await until(`document.querySelector('[role=status]')?.textContent.includes('Your account is ready')`);
  const registration = authRequests.find(request => request.path === '/api/sign_up');
  assert.equal(registration.body.code, '123456');
  assert.equal(registration.body.password, 'test-password-long');
  await cdp('Page.navigate', { url: 'http://localhost:5173/app' });
  await until(`!!document.querySelector('.chat-button')`);
  await click('.chat-button');
  await until(`!!document.querySelector('.chat-textarea')`);
  // Exercise mobile geometry after the model-settings integration flow.
  await cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
  await delay(350);
  assert.equal(await evaluate(`document.querySelector('.chat-container').getBoundingClientRect().right <= innerWidth`), true);
  assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), true);
  if (process.env.SCREENSHOT_DIR) {
    capturing = true;
    const output = resolve(process.env.SCREENSHOT_DIR);
    mkdirSync(output, { recursive: true });
    async function snapshot(name) {
      const result = await cdp('Page.captureScreenshot', { format: 'png' });
      writeFileSync(join(output, name), Buffer.from(result.data, 'base64'));
    }
    await cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
    await cdp('Page.navigate', { url: 'http://localhost:5173/app' });
    await until(`!!document.querySelector('.welcome-state')`);
    await delay(400);
    await snapshot('workspace.png');
    await click('.chat-button');
    await until(`!!document.querySelector('.chat-textarea')`);
    await until(`document.querySelectorAll('.message').length === 2`);
    await click('.chat-container > .tools-button');
    await until(`document.querySelector('#model-select')?.options.length === 3`);
    await setValue('#model-select', flint.id, 'select');
    await click('header .header-right button');
    await until(`document.querySelector('.models-nav')?.textContent.includes(${JSON.stringify(flint.name)})`);
    await delay(400);
    await snapshot('model-controls.png');
    await cdp('Page.navigate', { url: 'http://localhost:5173/' });
    await until(`!!document.querySelector('.auth-form')`);
    await delay(400);
    await snapshot('sign-in.png');
    await cdp('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await delay(300);
    assert.equal(await evaluate(`document.documentElement.scrollWidth <= innerWidth`), true);
    await snapshot('mobile.png');
  }
  console.log('Browser checks passed: model settings, text/voice payloads, rate-limit alert and loading cleanup.');
} finally {
  socket?.close();
  browser.kill();
  await delay(300);
  // Only remove the exact temporary browser profile created by this test.
  if (dirname(resolve(profile)) === resolve(tmpdir()) && basename(profile).startsWith('promptly-parameters-')) {
    try { rmSync(profile, { recursive: true, force: true, maxRetries: 3 }); } catch { /* Chrome may still be closing. */ }
  }
}

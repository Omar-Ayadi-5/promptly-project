import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { PARAMETER_CONFIG, filterParameters, initialParameters, sliderSettings, supportsParameter }
  from '../src/assets/frontend/modelParameters.js';
const [flint, xingchen] = JSON.parse(readFileSync(new URL('./fixtures/model-capabilities.json', import.meta.url)));

test('Flint uses only its stored capabilities and does not invent a seed', () => {
  assert.deepEqual(initialParameters(flint), { max_tokens: 8192, temperature: 0.7, top_p: 1 });
  assert.equal(supportsParameter(flint, 'frequency_penalty'), false);
  assert.equal(supportsParameter(flint, 'seed'), true);
});
test('XingChen defaults and additional controls match MongoDB', () => {
  const initial = initialParameters(xingchen);
  assert.equal(initial.temperature, 1);
  assert.equal(initial.top_p, 0.95);
  assert.equal(initial.repetition_penalty, 1.05);
  for (const name of ['frequency_penalty', 'presence_penalty', 'top_k', 'min_p', 'max_tokens']) {
    assert.equal(supportsParameter(xingchen, name), true);
    assert.equal(typeof initial[name], 'number');
  }
});
test('per-model saved values override defaults without crossing capabilities', () => {
  const saved = { [flint.id]: { temperature: 0.3 }, [xingchen.id]: { temperature: 1.2 } };
  assert.equal(initialParameters(flint, saved[flint.id]).temperature, 0.3);
  assert.equal(initialParameters(xingchen, saved[xingchen.id]).temperature, 1.2);
  assert.equal(initialParameters(flint, { frequency_penalty: 1 }).frequency_penalty, undefined);
});
test('unsupported, invalid and UI-only fields are excluded', () => {
  assert.deepEqual(filterParameters(flint, {
    temperature: 0.3, frequency_penalty: 1, seed: 0, top_p: NaN, max_tokens: '100',
    model: 'other', supported_parameters: [], default_parameters: {}, messages: [],
    provider: {}, extra_body: {},
  }), { temperature: 0.3, seed: 0 });
});
test('typed capabilities pass through without slider controls', () => {
  const typed = { stop: ['END'], reasoning: { effort: 'low' }, include_reasoning: false,
    response_format: { type: 'json_object' }, tools: [], tool_choice: 'none', structured_outputs: true };
  assert.deepEqual(filterParameters(xingchen, typed), typed);
  for (const name of Object.keys(typed)) assert.notEqual(PARAMETER_CONFIG[name].control, 'slider');
  assert.deepEqual(filterParameters(xingchen, { stop: [1], reasoning: true, tools: {} }), {});
});
test('legacy, empty, invalid and null metadata are safe', () => {
  assert.deepEqual(Object.keys(initialParameters({ id: 'old', default_parameters: null })),
    ['max_tokens', 'temperature', 'top_p', 'presence_penalty', 'frequency_penalty']);
  assert.deepEqual(initialParameters({ id: 'none', supported_parameters: [] }), {});
  assert.deepEqual(initialParameters({ id: 'invalid', supported_parameters: 'temperature' }), {});
  assert.deepEqual(initialParameters(null), {});
});
test('slider bounds and precision preserve provider defaults', () => {
  assert.equal(sliderSettings(PARAMETER_CONFIG.max_tokens, 4096).max, 32768);
  assert.equal(sliderSettings(PARAMETER_CONFIG.temperature, 1.8).max, 1.8);
  assert.equal(sliderSettings(PARAMETER_CONFIG.temperature, 0.75).step, 0.01);
  assert.equal(sliderSettings(PARAMETER_CONFIG.top_p, 0).min, 0);
});

test('larger output budget respects model limits and existing preferences', () => {
  const model = { ...flint, max_completion_tokens: 4096 };
  assert.equal(initialParameters(model).max_tokens, 4096);
  assert.equal(initialParameters(model, { max_tokens: 1024 }).max_tokens, 1024);
  assert.equal(filterParameters(model, { max_tokens: 32768 }).max_tokens, 4096);
  assert.equal(sliderSettings(PARAMETER_CONFIG.max_tokens, 4096, model).max, 4096);
  assert.equal(initialParameters({ ...flint, default_parameters: { max_tokens: 16384 } }).max_tokens, 16384);
  assert.equal(initialParameters({ ...flint, context: 2048 }).max_tokens, 2048);
});

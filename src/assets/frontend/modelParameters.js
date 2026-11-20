import parameterConfig from '../model_parameters.json' with { type: 'json' };

export const PARAMETER_CONFIG = parameterConfig;
const isObject = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

export function supportedParameters(model) {
  if (!model || !model.id || model.id === 'no_model') return [];
  // Missing/null metadata denotes an older catalog entry; [] explicitly means none.
  const names = model.supported_parameters == null
    ? Object.keys(PARAMETER_CONFIG).filter((key) => PARAMETER_CONFIG[key].legacy)
    : model.supported_parameters;
  return Array.isArray(names)
    ? names.filter((key) => typeof key === 'string' && Object.hasOwn(PARAMETER_CONFIG, key))
    : [];
}

export function supportsParameter(model, name) {
  return supportedParameters(model).includes(name);
}

export function validParameter(name, value) {
  const config = PARAMETER_CONFIG[name];
  if (!Object.hasOwn(PARAMETER_CONFIG, name) || value == null) return false;
  switch (config.type) {
    case 'number':
    case 'integer':
      return typeof value === 'number' && Number.isFinite(value)
        && (config.type !== 'integer' || Number.isSafeInteger(value))
        && (config.min === undefined || value >= config.min)
        && (config.max === undefined || value <= config.max);
    case 'boolean': return typeof value === 'boolean';
    case 'string': return typeof value === 'string';
    case 'object': return isObject(value);
    case 'array': return Array.isArray(value);
    case 'stop': return typeof value === 'string'
      || (Array.isArray(value) && value.every((item) => typeof item === 'string'));
    case 'choice': return typeof value === 'string' || isObject(value);
    default: return false;
  }
}

export function maxTokensLimit(model) {
  const limits = [model?.max_completion_tokens, model?.top_provider?.max_completion_tokens, Number(model?.context)]
    .filter((value) => Number.isSafeInteger(value) && value > 0);
  return Math.min(...limits);
}

export function filterParameters(model, parameters) {
  const supported = new Set(supportedParameters(model));
  return Object.fromEntries(Object.entries(isObject(parameters) ? parameters : {})
    .filter(([key, value]) => supported.has(key) && validParameter(key, value))
    .map(([key, value]) => [key, key === 'max_tokens' ? Math.min(value, maxTokensLimit(model)) : value]));
}

export function initialParameters(model, saved = {}) {
  const defaults = isObject(model?.default_parameters) ? model.default_parameters : {};
  const initial = {};
  for (const key of supportedParameters(model)) {
    const fallback = PARAMETER_CONFIG[key].default;
    if (validParameter(key, fallback)) initial[key] = fallback;
    if (validParameter(key, defaults[key])) initial[key] = defaults[key];
  }
  return filterParameters(model, { ...initial, ...filterParameters(model, saved) });
}

export function sliderSettings(config, value, model) {
  const limit = config.limit === 'output_tokens' ? maxTokensLimit(model) : Infinity;
  const current = Math.min(Number.isFinite(value) ? value : 0, limit);
  // Keep database defaults visible even outside the original slider's range/step.
  const decimals = String(current).split('.')[1]?.length || 0;
  return {
    min: Math.min(config.sliderMin, current),
    max: Math.min(limit, Math.max(config.sliderMax, current)),
    step: Math.min(config.step, 10 ** -decimals),
    value: current,
  };
}

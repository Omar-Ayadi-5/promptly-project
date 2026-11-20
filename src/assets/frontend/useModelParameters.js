import { useEffect, useState } from 'react';
import { API_BASE_URL } from './api';
import { filterParameters, initialParameters } from './modelParameters';

export default function useModelParameters(modelId, token) {
  const [modelsById, setModelsById] = useState({});
  const [parametersByModel, setParametersByModel] = useState({});
  const [draftsByModel, setDraftsByModel] = useState({});
  const model = modelsById[modelId] || null;

  useEffect(() => {
    if (modelId === 'no_model' || !token || modelsById[modelId]) return;
    const controller = new AbortController();
    let cancelled = false;
    async function loadModel() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/Load_model_details`, {
          method: 'POST',
          headers: { authorization: `bearer ${token}`, 'content-type': 'application/json' },
          body: JSON.stringify({ model_id: modelId }),
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('Failed to load model details');
        const details = await response.json();
        if (!cancelled) setModelsById((previous) => ({
          ...previous, [modelId]: { ...details, id: modelId },
        }));
      } catch (error) {
        if (!cancelled) console.error('Failed to get model details:', error);
      }
    }
    loadModel();
    return () => { cancelled = true; controller.abort(); };
  }, [modelId, token, modelsById]);

  const generationParams = initialParameters(model, parametersByModel[modelId]);
  const draftParams = initialParameters(model, draftsByModel[modelId] || parametersByModel[modelId]);

  function changeDraft(name, value) {
    if (!model) return;
    const change = filterParameters(model, { [name]: value });
    setDraftsByModel((previous) => ({
      ...previous,
      [modelId]: { ...initialParameters(model, previous[modelId] || parametersByModel[modelId]), ...change },
    }));
  }

  function applyParameters() {
    if (!model) return;
    setParametersByModel((previous) => ({
      ...previous, [modelId]: filterParameters(model, draftParams),
    }));
  }

  return { model, generationParams, draftParams, changeDraft, applyParameters };
}

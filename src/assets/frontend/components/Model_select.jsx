// ModelSelector.jsx
import { API_BASE_URL } from '../api';
import { useCallback, useEffect, useState } from 'react';
import '../FullStyle.css';
import { useAuth } from '../authContext';


function ModelSelector({ selectedModel, onModelChange }) {
  const [Models, setModals] = useState([])
  const {token} = useAuth();

  const Load_models = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/Load_models`,
        {
          method:"GET",
          headers:{
            "authorization" : `bearer ${token}`,
            "content-type" : "application/json"
          }
        }
      );
      if (!response.ok) throw new Error("Erreur lors du chargement des modèles");
        const data = await response.json();
        setModals(data);
    } catch (error) {
      console.error("Erreur lors du chargement des données:", error);
      setModals([])
    }
  }, [token]);
  useEffect(() => {
    Load_models();
  }, [Load_models])
  return (
    <div className="model-selector">
      <label htmlFor="model-select">Choose a model:</label>
      <select
        id="model-select"
        value={selectedModel}
        onChange={(e) => onModelChange(e.target.value)}
      >
        <option value={"no_model"}>Select a model</option>
        {Models.map((model) => (
          <option value={model.id} key={model.id}>{model.name}</option>

        ))}

      </select>
    </div>
  );
}

export default ModelSelector;

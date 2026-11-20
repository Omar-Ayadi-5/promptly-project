import "../FullStyle.css";
import { useEffect, useRef, useState } from "react";
import { PARAMETER_CONFIG, sliderSettings, supportsParameter } from '../modelParameters';


const ModelsNav = ({ isVisible, selectedModel, parameters, onDraftChange, onParamsChange }) => {
    const [confirmationModel, setConfirmationModel] = useState(null);
    const confirmationTimer = useRef(null);
    const Model_details = selectedModel || {
        name: "No Model Selected", context: "Na", description: "Na",
    };
    const confirmation = selectedModel && confirmationModel === selectedModel.id;
    useEffect(() => () => clearTimeout(confirmationTimer.current), []);

    const handleUpdate = () => {
        if (selectedModel && onParamsChange) {
            onParamsChange();
            setConfirmationModel(selectedModel.id);
            clearTimeout(confirmationTimer.current);
            confirmationTimer.current = setTimeout(() => setConfirmationModel(null), 2000);
        }
    };


    return (
        <nav className={`models-nav ${isVisible ? "models-slide-in" : "models-slide-out"}`}>

            <h3>Selected Model Description & Parameters</h3>

            <p><strong>Model Name   :   </strong> {Model_details.name}</p>
            <p><strong>Context-length   :   </strong> {Model_details.context}</p>

            <p><strong>Description   :  </strong> {Model_details.description || 'No description provided by this model.'}</p>

            <hr />
            <p><strong>Edit Model Parameters : </strong></p>
            {Object.entries(PARAMETER_CONFIG)
                .filter(([name, config]) => config.control === 'slider' && supportsParameter(selectedModel, name))
                .map(([name, config]) => (
                    <div className="model-param" key={name}>
                        <label>{config.label}: {parameters[name] ?? 'Provider default'}</label>
                        <input
                            type="range"
                            {...sliderSettings(config, parameters[name], selectedModel)}
                            aria-label={config.label}
                            onChange={(e) => onDraftChange(name, Number(e.target.value))}
                        />
                    </div>
                ))}
            {confirmation && <p className="confirmation-msg">✅ Settings applied</p>}
            <button className="apply-btn" onClick={handleUpdate}>Apply Settings</button>

        </nav>
    );
};

export default ModelsNav;

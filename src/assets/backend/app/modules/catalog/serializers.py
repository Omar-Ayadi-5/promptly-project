def model_summaries(models):
    return [{"id": model.get("id"), "name": model.get("name")} for model in models]


def model_details(model_id, model):
    return {
        "id": model_id,
        "name": model.get("name", "Unknown Model"),
        "description": model.get("description", "No description available"),
        "context": model.get("context", "N/A"),
        "max_completion_tokens": model.get("max_completion_tokens") or (model.get("top_provider") or {}).get("max_completion_tokens"),
        "default_parameters": model.get("default_parameters") or {},
        **({"supported_parameters": model["supported_parameters"]}
           if "supported_parameters" in model else {}),
    }

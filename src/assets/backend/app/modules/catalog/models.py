def catalog_document(data):
    return {
        "id": data["id"],
        "name": data["name"].replace("(free)", "").strip(),
        "description": data.get("description", ""),
        "provider": data["id"].split("/")[0],
        "context": data.get("context_length", 0),
        "max_completion_tokens": (data.get("top_provider") or {}).get("max_completion_tokens"),
        "supported_parameters": data.get("supported_parameters", []),
        "default_parameters": data.get("default_parameters"),
    }

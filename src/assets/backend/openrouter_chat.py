"""Build Chat Completions messages and handle OpenRouter's response variants."""


class OpenRouterResponseError(Exception):
    def __init__(self, message, code="provider_error", status=502):
        super().__init__(message)
        self.code = code
        self.status = status


def provider_error(error, status=None):
    error = error if isinstance(error, dict) else {}
    raw_code = error.get("code")
    if status is None:
        status = raw_code if isinstance(raw_code, int) and 400 <= raw_code <= 599 else 502
    messages = {
        401: ("OpenRouter rejected the backend API key. Check the server configuration.", "upstream_authentication"),
        402: ("OpenRouter requires credits for this request. Check the account balance or select a free model.", "upstream_payment_required"),
        429: ("This model is rate-limited by OpenRouter or its provider. Try again shortly or select another model.", "rate_limit_exceeded"),
        404: ("OpenRouter has no available endpoint for this model and its selected parameters. Try another model.", "model_unavailable"),
        503: ("The model provider is temporarily unavailable. Try again shortly or select another model.", "provider_unavailable"),
    }
    message, code = messages.get(status, (
        error.get("message") or "OpenRouter could not generate a response. Try again or select another model.",
        "provider_error",
    ))
    # An upstream credential failure is not a failure of the user's Promptly login.
    return OpenRouterResponseError(message, code, 502 if status == 401 else status)


def build_messages(history, message):
    messages = [{
        "role": "system",
        "content": "You are a helpful assistant. The following is a short conversation history. "
                   "Use it only to understand context. Respond only to the user's final message at the end.",
    }]
    previous_failures = {
        "Failed to generate AI response",
        "No response generated due to Problems in parameters or the Model",
    }
    for item in history:
        role = "assistant" if item.get("role") == "AI" else item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str) or not content.strip():
            continue
        if role == "assistant" and content in previous_failures:
            continue
        messages.append({"role": role, "content": content})
    # Both text and voice flows save the user's message before requesting a reply.
    if messages[-1] == {"role": "user", "content": message}:
        messages.pop()
    messages.append({"role": "user", "content": message})
    return messages


def completion_text(completion):
    error = getattr(completion, "error", None)
    if error:
        raise provider_error(error)
    choices = getattr(completion, "choices", None)
    if not choices:
        raise OpenRouterResponseError("OpenRouter returned no completion. Try again or select another model.", "empty_response")
    choice = choices[0]
    error = getattr(choice, "error", None)
    if error:
        raise provider_error(error)
    if choice.finish_reason == "error":
        raise OpenRouterResponseError("The model provider failed while generating the response.")
    content = getattr(choice.message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    if choice.finish_reason == "length":
        raise OpenRouterResponseError(
            "The model reached Max Tokens before producing an answer. Increase Max Tokens and try again.",
            "max_tokens_exhausted",
        )
    if choice.finish_reason == "content_filter":
        raise OpenRouterResponseError("The provider declined to generate this response.", "content_filtered")
    if getattr(choice.message, "tool_calls", None):
        raise OpenRouterResponseError("The model requested a tool call, but this chat does not execute tools.", "tool_call_without_text")
    raise OpenRouterResponseError("OpenRouter returned an empty answer. Try again or select another model.", "empty_response")

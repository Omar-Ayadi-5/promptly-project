"""Keep OpenRouter transport and SDK response handling behind one adapter."""
import requests
from openai import OpenAI, APIStatusError, APIConnectionError, APITimeoutError

from openrouter_chat import completion_text, provider_error, OpenRouterResponseError


def create_client(config):
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=config["OPENROUTER_KEY"])


class OpenRouterRequestError(OpenRouterResponseError):
    def __init__(self, failure, upstream_status, retry_after):
        super().__init__(str(failure), failure.code, failure.status)
        self.upstream_status = upstream_status
        self.retry_after = retry_after


class OpenRouterAdapter:
    def __init__(self, client):
        self.client = client

    def generate(self, model, parameters, messages):
        try:
            completion = self.client.with_options(max_retries=0, timeout=60).chat.completions.create(
                model=model,
                extra_body=parameters,
                messages=messages,
            )
        except APIStatusError as error:
            body = error.body if isinstance(error.body, dict) else {}
            failure = provider_error(body.get("error", body), error.status_code)
            raise OpenRouterRequestError(
                failure, error.status_code, error.response.headers.get("retry-after")
            ) from error
        except APITimeoutError as error:
            raise OpenRouterResponseError(
                "OpenRouter timed out. Try again or select another model.", "upstream_timeout", 504
            ) from error
        except APIConnectionError as error:
            raise OpenRouterResponseError(
                "Could not connect to OpenRouter. Try again shortly.", "upstream_connection_error", 502
            ) from error
        return completion_text(completion)


class OpenRouterCatalogAdapter:
    def fetch_models(self):
        response = requests.get("https://openrouter.ai/api/v1/models", timeout=30)
        response.raise_for_status()
        return response.json().get("data", [])

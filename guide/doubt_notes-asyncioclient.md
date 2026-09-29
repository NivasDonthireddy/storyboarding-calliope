# Learning notes: Calling LLM APIs with HTTPX

## 1. What this code does

Your `LLMClient._live_chat()` makes an asynchronous HTTP request to a chat-completions endpoint:

```python
async with httpx.AsyncClient(
    timeout=self.settings.request_timeout_sec,
    trust_env=False,
) as client:
    response = await client.post(trace["url"], json=payload)
```

- `httpx.AsyncClient` is an HTTP client that works with Python’s `async`/`await`.
- `async with` opens the client and reliably closes it afterward, including if an error occurs.
- `client.post(...)` sends an HTTP `POST` request.
- `json=payload` serializes the Python dictionary to JSON and sends it as the request body.
- `await` lets the program wait for the network response without blocking other async work.

The code then checks the HTTP status, parses the JSON response, looks for `choices[0].message`, and returns the assistant message fields it needs.

## 2. The three settings that determine where a request goes

These are separate concepts:

| Setting | Purpose |
|---|---|
| `llm_base_url` | Which provider or server receives the request |
| `llm_model` | Which model that provider should run |
| API key | Whether you are authorized to use the provider |

The current code uses `llm_model` in the payload and builds the endpoint by appending `/chat/completions` to `llm_base_url`. It does not currently add an API key to the request.

For a provider that uses Bearer-token authentication, a request might include:

```python
headers={"Authorization": f"Bearer {api_key}"}
```

The required header depends on the provider. Keep API keys in environment-based configuration or a secret store—not in source code, logs, or trace files.

## 3. Can you use different models without the OpenAI SDK?

**Yes.** HTTPX can send requests directly, so you do not need the OpenAI SDK. Many hosted providers, including providers offering closed-source frontier models, support an OpenAI-compatible chat-completions API.

Changing only `llm_model` is enough when the new model is available through the same provider and endpoint. For a different provider, you may need to change the base URL, authentication, request fields, or response parsing.

“OpenAI-compatible” means the provider follows much of the same API shape; it does **not** guarantee every feature behaves identically. In this code, features that may vary include:

- Tool calling (`tools` and `tool_choice`)
- Token-limit fields such as `max_tokens`
- JSON or schema-constrained output
- Provider-specific `chat_template_kwargs`
- The response structure expected at `choices[0].message`

Check the chosen provider’s documentation, especially for supported parameters and authentication.

## 4. Create a new client each time or reuse one?

Your current approach creates and closes a client for every request. That is simple and safe, and it can be reasonable for occasional requests.

For a service that makes repeated requests, it is usually better to reuse one `AsyncClient`. It maintains a **connection pool**—reusable network connections—which can reduce the overhead of repeatedly setting up connections.

The application should create the shared client at startup, pass it to the LLM client, and close it at shutdown. Don’t leave a shared client open indefinitely. The OpenAI SDK also manages HTTP requests and connections, but it is an optional convenience; HTTPX is a valid choice when you want direct control.

## 5. What the other request options mean

- `timeout=...` limits how long the request can take before HTTPX raises an error.
- `trust_env=False` tells HTTPX not to read proxy settings from environment variables. This is appropriate if you deliberately do not want environment-configured proxies; otherwise, a required proxy could be ignored.
- `"stream": False` asks for the response as a complete result rather than streamed pieces.
- `"temperature": 0.3` influences response variability; lower values generally make answers less varied.
- `"messages"` contains the conversation or instructions sent to the model.

## 6. Important note about traces and structured output

This code writes the request and response to trace files. Those traces may include prompts, user data, or model output, so treat them as potentially sensitive: limit access and retention, and avoid putting credentials in them.

`generate_structured()` asks the model to return JSON, then parses it and validates it with Pydantic. The validation is a useful safety check, but the prompt alone does not guarantee valid JSON—the code correctly handles parsing or validation failures by raising `ModelOutputError`.
import os
import json
import re
from typing import Literal
from pydantic import BaseModel, Field
from . import store

def secret(name):
    if os.getenv(name):
        return os.environ[name]
    try:
        # pyrefly: ignore [missing-import]
        import keyring
        return keyring.get_password('local-job-agent', name) or ''
    except Exception:
        return ''

def save_secret(name, value):
    # pyrefly: ignore [missing-import]
    import keyring
    if value:
        keyring.set_password('local-job-agent', name, value)
    else:
        try:
            keyring.delete_password('local-job-agent', name)
        except keyring.errors.PasswordDeleteError:
            pass

DEFAULT_MODELS = {
    'openrouter': 'minimax/minimax-m3:free',
    'tokenrouter': 'z-ai/glm-5.3-free',
    'opencode': 'opencode/free',
    'openai': 'gpt-4o-mini',
    'custom': 'minimax/minimax-m3:free',
}

DEFAULT_BASE_URLS = {
    'openrouter': 'https://openrouter.ai/api/v1',
    'tokenrouter': 'https://api.tokenrouter.io/v1',
    'opencode': 'https://api.opencode.ai/v1',
    'openai': 'https://api.openai.com/v1',
    'custom': 'http://localhost:11434/v1',
}

PROVIDER_SECRET_NAMES = {
    'openrouter': 'OPENROUTER_API_KEY',
    'tokenrouter': 'TOKENROUTER_API_KEY',
    'opencode': 'OPENCODE_API_KEY',
    'openai': 'OPENAI_API_KEY',
    'custom': 'CUSTOM_API_KEY',
}

PROVIDER_DISPLAY_NAMES = {
    'openrouter': 'OpenRouter',
    'tokenrouter': 'TokenRouter',
    'opencode': 'OpenCode',
    'openai': 'OpenAI',
    'custom': 'Custom',
}

def get_provider_config():
    provider = store.setting('provider', 'openrouter')
    if provider not in DEFAULT_MODELS:
        provider = 'openrouter'

    secret_name = PROVIDER_SECRET_NAMES.get(provider, 'OPENROUTER_API_KEY')
    key = secret(secret_name)
    # If using openai or fallback key
    if not key and provider == 'openai':
        key = secret('OPENAI_API_KEY')
    elif not key and provider == 'openrouter':
        # check if OPENROUTER_API_KEY or OPENAI_API_KEY is available
        key = secret('OPENROUTER_API_KEY') or secret('OPENAI_API_KEY')

    if provider == 'custom':
        base_url = store.setting('custom_base_url') or store.setting('base_url') or DEFAULT_BASE_URLS['custom']
    else:
        base_url = DEFAULT_BASE_URLS.get(provider, 'https://openrouter.ai/api/v1')
    base_url = base_url.rstrip('/')

    default_model = DEFAULT_MODELS.get(provider, 'meta-llama/llama-3.3-70b-instruct:free')
    model = store.setting('model', default_model)
    if not model:
        model = default_model

    # Custom provider may not strictly require an API key (e.g. local Ollama)
    connected = bool(key) if provider != 'custom' else True

    return {
        'provider': provider,
        'key': key,
        'base_url': base_url,
        'model': model,
        'connected': connected,
        'secret_name': secret_name,
    }

class Requirement(BaseModel):
    text: str
    priority: Literal['required', 'preferred']
    source_quote: str

class Requirements(BaseModel):
    requirements: list[Requirement]

class Rewrite(BaseModel):
    evidence_id: str
    text: str

class Rewrites(BaseModel):
    changes: list[Rewrite]

class Check(BaseModel):
    evidence_id: str
    supported: bool
    reason: str

class Checks(BaseModel):
    checks: list[Check]

class Coverage(BaseModel):
    requirement_index: int
    support: Literal['full', 'partial', 'missing']
    evidence_ids: list[str]
    explanation: str

class Coverages(BaseModel):
    coverage: list[Coverage]

class Letter(BaseModel):
    text: str

class StructuredSection(BaseModel):
    title: str
    items: list[str]

class StructuredProfile(BaseModel):
    name: str
    headline: str
    email: str
    phone: str
    location: str
    links: list[str]
    sections: list[StructuredSection]

def _clean_json_markdown(text: str) -> str:
    if not text:
        return ''
    text = text.strip()
    # Strip <think>...</think> blocks from reasoning models
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
    # Strip common safety/system headers prepended by proxies (e.g. "User Safety: safe")
    text = re.sub(r'^(?:User Safety|Safety Status|Safety Rating|Safety)\s*:\s*[a-zA-Z0-9_ -]+\s*', '', text, flags=re.IGNORECASE | re.MULTILINE).strip()
    # Strip markdown code fences if present
    if '```' in text:
        fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        if fence_match:
            text = fence_match.group(1).strip()
    # Extract the outermost JSON object {...} or array [...]
    match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
    if match:
        return match.group(1).strip()
    return ''

def ask(schema, instruction, payload):
    from openai import OpenAI
    import openai

    cfg = get_provider_config()
    provider = cfg['provider']
    key = cfg['key']
    base_url = cfg['base_url']
    model = cfg['model']

    if not key and provider != 'custom':
        provider_name = PROVIDER_DISPLAY_NAMES.get(provider, provider.capitalize())
        raise ValueError(f'Connect an API key for {provider_name} in Settings to use AI tailoring.')

    default_headers = {}
    if provider == 'openrouter':
        default_headers = {
            'HTTP-Referer': 'http://127.0.0.1:8765',
            'X-Title': 'Jobfolio Local Agent',
        }

    client = OpenAI(
        api_key=key or 'not-needed-for-local',
        base_url=base_url,
        default_headers=default_headers,
        timeout=90,
        max_retries=1
    )

    schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
    system_prompt = (
        'You are an expert ATS resume and career advisor. '
        + instruction
        + '\n\nCRITICAL: Respond ONLY with a valid JSON object matching this schema. '
        'Do NOT include any preamble, safety header, commentary, or text outside the JSON:\n'
        + schema_json
    )

    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]

    try:
        kwargs = {'temperature': 0.1}
        if provider == 'openai':
            kwargs['response_format'] = {'type': 'json_object'}

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs
        )
        content = response.choices[0].message.content or ''
        clean_text = _clean_json_markdown(content)

        # Retry once with strict JSON prompt if response did not contain JSON
        if not clean_text:
            retry_messages = [
                {'role': 'system', 'content': 'You are a factual JSON generator. Output ONLY a valid JSON object starting with { and ending with }. No safety labels or text outside JSON.'},
                {'role': 'user', 'content': f"Instruction: {instruction}\n\nSchema:\n{schema_json}\n\nInput Data:\n{json.dumps(payload, ensure_ascii=False)}\n\nOutput ONLY valid JSON now:"}
            ]
            response = client.chat.completions.create(
                model=model,
                messages=retry_messages,
                temperature=0.1
            )
            content = response.choices[0].message.content or ''
            clean_text = _clean_json_markdown(content)

        # If openrouter model hits an unresponsive router endpoint or safety classifier, try reliable free model fallbacks
        if not clean_text and provider == 'openrouter':
            for fb_model in ['minimax/minimax-m3:free', 'z-ai/glm-5.2:free', 'google/gemma-4-31b-it:free']:
                try:
                    fb_resp = client.chat.completions.create(
                        model=fb_model,
                        messages=messages,
                        temperature=0.1
                    )
                    clean_text = _clean_json_markdown(fb_resp.choices[0].message.content or '')
                    if clean_text:
                        break
                except Exception:
                    continue

        if not clean_text:
            raise ValueError('The AI model did not return a valid JSON response. Please try again or switch model in Connections.')

        try:
            return schema.model_validate_json(clean_text)
        except Exception:
            # Fix common trailing comma issues and try once more
            fixed = re.sub(r',\s*([}\]])', r'\1', clean_text)
            return schema.model_validate_json(fixed)

    except openai.RateLimitError as e:
        raise ValueError('Free model quota or rate limit reached (HTTP 429). Please wait a moment, switch to another free model in Connections, or use local preparation.') from e
    except openai.APIError as e:
        msg = str(e)
        if getattr(e, 'status_code', None) == 401:
            provider_name = PROVIDER_DISPLAY_NAMES.get(provider, provider.capitalize())
            raise ValueError(f'{provider_name} rejected the saved API key (401). Replace it in Connections, or use local CV preparation.') from e
        if '429' in msg or 'rate limit' in msg.lower() or 'quota' in msg.lower():
            raise ValueError('Free model quota or rate limit reached. Please wait a moment, switch to another free model in Connections, or use local preparation.') from e
        # If response_format json_object wasn't supported by the model, retry without response_format
        if 'response_format' in msg.lower() or 'json_object' in msg.lower():
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.1,
                )
                content = response.choices[0].message.content or ''
                clean_text = _clean_json_markdown(content)
                return schema.model_validate_json(clean_text)
            except Exception as retry_err:
                raise ValueError(f'AI model response could not be parsed as required schema: {retry_err}') from retry_err
        raise ValueError(f'AI provider error ({provider}): {msg}') from e
    except Exception as e:
        msg = str(e)
        if '429' in msg or 'rate limit' in msg.lower() or 'quota' in msg.lower():
            raise ValueError('Free model quota or rate limit reached. Please wait a moment, switch to another free model in Connections, or use local preparation.') from e
        raise ValueError(f'AI tailoring failed: {msg}') from e

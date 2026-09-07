"""OpenAI / Anthropic / Gemini 공용 클라이언트.

지금은 '연결 테스트'와 향후 필드 재작성 기능에서 재사용할 generate() 만 제공한다.
실제 "특정 필드를 사용자 요구에 맞게 고쳐쓰기" 기능은 대상 필드가 아직 정의되지 않아
이번 범위에서 구현하지 않는다 — 이 클라이언트만 미리 준비해둔다.
"""

PROVIDERS = ["openai", "anthropic", "gemini"]

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-5",
    "gemini": "gemini-2.5-flash",
}

PROVIDER_LABELS = {
    "openai": "ChatGPT (OpenAI)",
    "anthropic": "Claude (Anthropic)",
    "gemini": "Gemini (Google)",
}


def generate(provider: str, api_key: str, model: str, prompt: str, system: str = None) -> str:
    if provider == "openai":
        return _generate_openai(api_key, model, prompt, system)
    if provider == "anthropic":
        return _generate_anthropic(api_key, model, prompt, system)
    if provider == "gemini":
        return _generate_gemini(api_key, model, prompt, system)
    raise ValueError(f"알 수 없는 provider: {provider}")


def test_connection(provider: str, api_key: str, model: str) -> tuple[bool, str]:
    """(성공여부, 메시지) 를 반환한다. 실제 최소 호출로 키/모델이 유효한지 확인한다."""
    try:
        text = generate(provider, api_key, model, "ping", system="Reply with just 'pong'.")
        return True, f"연결 성공: {text.strip()[:80]}"
    except Exception as exc:
        return False, f"연결 실패: {exc}"


def _generate_openai(api_key, model, prompt, system):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages, max_tokens=20)
    return resp.choices[0].message.content or ""


def _generate_anthropic(api_key, model, prompt, system):
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    kwargs = {"model": model, "max_tokens": 20, "messages": [{"role": "user", "content": prompt}]}
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return "".join(block.text for block in resp.content if hasattr(block, "text"))


def _generate_gemini(api_key, model, prompt, system):
    from google import genai
    client = genai.Client(api_key=api_key)
    contents = prompt if not system else f"{system}\n\n{prompt}"
    resp = client.models.generate_content(model=model, contents=contents)
    return resp.text or ""

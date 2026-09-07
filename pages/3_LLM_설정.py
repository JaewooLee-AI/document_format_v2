import streamlit as st

from db import models
from llm.client import DEFAULT_MODELS, PROVIDER_LABELS, PROVIDERS, test_connection

st.set_page_config(page_title="LLM 설정", page_icon="🔑", layout="wide")
models.init_db()

st.title("🔑 LLM 설정")
st.caption(
    "ChatGPT(OpenAI) · Claude(Anthropic) · Gemini(Google) 3종의 API 키/모델을 등록하고 "
    "연결 테스트를 통과한 provider 중 하나를 기본값으로 지정합니다. "
    "(필드별 LLM 재작성 기능은 대상 필드가 정의되면 추가될 예정입니다.)"
)

default_setting = models.get_default_provider()

for provider in PROVIDERS:
    setting = models.get_llm_setting(provider) or {}
    with st.container(border=True):
        st.markdown(f"### {PROVIDER_LABELS[provider]}")
        c1, c2 = st.columns(2)
        api_key = c1.text_input(
            "API Key", value=setting.get("api_key", "") or "", type="password", key=f"{provider}_key",
        )
        model = c2.text_input(
            "모델명", value=setting.get("model") or DEFAULT_MODELS[provider], key=f"{provider}_model",
        )

        b1, b2, b3 = st.columns(3)
        if b1.button("저장", key=f"{provider}_save"):
            models.upsert_llm_setting(provider, api_key, model)
            st.success("저장되었습니다.")

        if b2.button("연결 테스트", key=f"{provider}_test"):
            models.upsert_llm_setting(provider, api_key, model)
            with st.spinner("연결 테스트 중..."):
                ok, msg = test_connection(provider, api_key, model)
            models.set_test_result(provider, ok)
            (st.success if ok else st.error)(msg)

        setting = models.get_llm_setting(provider) or {}
        is_default = bool(default_setting and default_setting["provider"] == provider)
        if setting.get("last_test_ok"):
            st.caption(f"✅ 마지막 테스트 성공 ({setting.get('last_tested_at')})")
            if is_default:
                b3.button("✓ 기본값", key=f"{provider}_default", disabled=True)
            elif b3.button("기본값으로 지정", key=f"{provider}_default"):
                models.set_default_provider(provider)
                st.rerun()
        elif setting.get("last_tested_at"):
            st.caption(f"❌ 마지막 테스트 실패 ({setting.get('last_tested_at')})")
        else:
            st.caption("아직 연결 테스트를 하지 않았습니다. 테스트를 통과해야 기본값으로 지정할 수 있습니다.")

st.divider()
if default_setting:
    st.info(f"현재 기본 provider: **{PROVIDER_LABELS[default_setting['provider']]}**")
else:
    st.warning("아직 기본 provider가 지정되지 않았습니다. 연결 테스트를 통과한 provider를 기본값으로 지정하세요.")

import json
import requests
import streamlit as st
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.1:8b"
KB_PATH = Path(__file__).parent.parent / "data" / "conditions.json"

# ── Carrega base de conhecimento ──────────────────────────────────────────────

@st.cache_resource
def load_knowledge_base() -> dict:
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def kb_as_text(kb: dict) -> str:
    """Serializa a KB em texto compacto para injetar no system prompt."""
    lines = ["## Base de Conhecimento — Condições Documentadas\n"]
    for c in kb["conditions"]:
        lines.append(f"### {c['nome']}")
        lines.append(f"- Sintomas-chave: {', '.join(c['sintomas_chave'])}")
        lines.append(f"- Sintomas de alerta: {', '.join(c['sintomas_alerta'])}")
        lines.append(f"- Urgência: {c['urgencia']}")
        lines.append(f"- Orientação: {c['orientacao']}")
        lines.append("")
    legenda = kb["urgencia_legenda"]
    lines.append("## Legenda de Urgência")
    for k, v in legenda.items():
        lines.append(f"- {v['label']}: {v['descricao']}")
    return "\n".join(lines)

# ── System prompt ─────────────────────────────────────────────────────────────

def build_system_prompt(kb: dict) -> str:
    kb_text = kb_as_text(kb)
    return f"""Você é o VitaCheck, um assistente de triagem de sintomas empático e direto.

Seu objetivo é conduzir uma triagem progressiva em até 5 turnos, acumular contexto e chegar a uma orientação clara.

### REGRAS DE COMPORTAMENTO

1. Faça ao menos 2 perguntas de triagem antes de dar qualquer orientação.
2. Acumule o contexto da conversa. Se a pessoa já mencionou um sintoma, referencie: "Você mencionou febre há pouco..."
3. Foque em um problema por vez. Se houver muitos sintomas, priorize o mais preocupante.
4. Baseie suas orientações EXCLUSIVAMENTE na base de conhecimento abaixo.
5. Se os sintomas estiverem fora da base, diga claramente que não tem informação suficiente e recomende atendimento médico.
6. NUNCA prescreva posologia específica (ex: "tome 500mg a cada 8h"). Mencione o medicamento apenas como referência geral.
7. Nunca seja alarmista desnecessariamente, mas sinalize urgência com clareza quando necessário.

### FORMATO DA ORIENTAÇÃO FINAL

Quando tiver informações suficientes, responda assim:

**Com base no que você me contou:**
[breve descrição do que os sintomas podem indicar]

**Orientação:**
[orientação prática baseada na KB]

[nível de urgência em destaque: 🟢 / 🟡 / 🔴]

*Lembre-se: essa é uma triagem de apoio, não um diagnóstico médico. Em caso de dúvida, consulte um profissional de saúde.*

### QUANDO OS SINTOMAS SÃO DESCONHECIDOS

Responda: "Esses sintomas estão fora do escopo que consigo avaliar com segurança. Por precaução, recomendo buscar atendimento médico."

---

{kb_text}
"""

# ── Chamada ao Ollama ─────────────────────────────────────────────────────────

def chat_with_ollama(messages: list[dict]) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "messages": messages, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
    except requests.exceptions.ConnectionError:
        return "⚠️ Não consegui conectar ao Ollama. Verifique se ele está rodando com `ollama serve`."
    except requests.exceptions.Timeout:
        return "⚠️ O modelo demorou demais para responder. Tente novamente."
    except Exception as e:
        return f"⚠️ Erro inesperado: {str(e)}"

# ── UI ────────────────────────────────────────────────────────────────────────

def render_urgency_card(text: str):
    """Detecta nível de urgência na resposta e renderiza card colorido."""
    if "🔴" in text:
        st.error("🔴 **Emergência** — Busque atendimento imediato: SAMU 192 ou UPA")
    elif "🟡" in text:
        st.warning("🟡 **Atenção** — Recomendável ir a uma farmácia ou clínica")
    elif "🟢" in text:
        st.success("🟢 **Leve** — Cuidados em casa devem ser suficientes")

def init_session():
    kb = load_knowledge_base()
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": build_system_prompt(kb)}
        ]
    if "chat_display" not in st.session_state:
        st.session_state.chat_display = []
    if "triagem_iniciada" not in st.session_state:
        st.session_state.triagem_iniciada = False

def reset_session():
    for key in ["messages", "chat_display", "triagem_iniciada"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="VitaCheck",
        page_icon="🩺",
        layout="centered",
    )

    # Header
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("🩺 VitaCheck")
        st.caption("Assistente de triagem de sintomas • Powered by llama3.1:8b (local)")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Reiniciar", help="Iniciar nova triagem"):
            reset_session()

    st.divider()

    # Aviso legal
    st.info(
        "⚠️ **VitaCheck não é um serviço médico.** "
        "As orientações aqui são de triagem inicial e não substituem consulta profissional. "
        "Em emergências, ligue **192 (SAMU)**.",
        icon=None,
    )

    init_session()

    # Mensagem de boas-vindas (apenas uma vez)
    if not st.session_state.triagem_iniciada:
        with st.chat_message("assistant", avatar="🩺"):
            welcome = (
                "Olá! Sou o **VitaCheck**, seu assistente de triagem de sintomas. 👋\n\n"
                "Estou aqui para te ajudar a entender melhor o que você está sentindo "
                "e orientar qual o próximo passo mais adequado.\n\n"
                "**Me conta: o que você está sentindo?**"
            )
            st.markdown(welcome)

    # Histórico de mensagens
    for msg in st.session_state.chat_display:
        avatar = "🩺" if msg["role"] == "assistant" else "🧑"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                render_urgency_card(msg["content"])

    # Input do usuário
    user_input = st.chat_input("Descreva seus sintomas...")

    if user_input:
        st.session_state.triagem_iniciada = True

        # Exibe mensagem do usuário
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)
        st.session_state.chat_display.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Gera resposta
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("Analisando..."):
                response = chat_with_ollama(st.session_state.messages)
            st.markdown(response)
            render_urgency_card(response)

        st.session_state.chat_display.append({"role": "assistant", "content": response})
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Footer
    st.divider()
    st.caption("VitaCheck • Projeto de portfólio • Rodando 100% local com Ollama")

if __name__ == "__main__":
    main()

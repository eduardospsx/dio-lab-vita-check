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
        if c.get("urgencia_explicita"):
            lines.append(f"- Regra de urgência: {c['urgencia_explicita']}")
        lines.append(f"- Orientação: {c['orientacao']}")
        perguntas = c.get("perguntas_triagem", [])
        if perguntas:
            lines.append(f"- Perguntas de triagem sugeridas: {' | '.join(perguntas)}")
        lines.append("")
    legenda = kb["urgencia_legenda"]
    lines.append("## Legenda de Urgência")
    for k, v in legenda.items():
        lines.append(f"- {v['label']}: {v['descricao']}")
    return "\n".join(lines)

# ── System prompt ─────────────────────────────────────────────────────────────

def build_system_prompt(kb: dict) -> str:
    kb_text = kb_as_text(kb)
    return f"""Você é o VitaCheck, um assistente de triagem de sintomas.

== REGRA ABSOLUTA — LEIA ANTES DE QUALQUER COISA ==

VOCÊ NUNCA PODE DAR ORIENTAÇÃO MÉDICA NA PRIMEIRA RESPOSTA.
VOCÊ NUNCA PODE DAR ORIENTAÇÃO MÉDICA NA SEGUNDA RESPOSTA.

A orientação final SÓ pode aparecer a partir da TERCEIRA mensagem sua, e apenas se já tiver feito ao menos 2 perguntas de triagem e recebido as respostas.

Se você der orientação antes de fazer 2 perguntas, está quebrando sua função principal.

== FLUXO OBRIGATÓRIO ==

MENSAGEM 1 do usuário → Você DEVE fazer 1 pergunta de triagem. Nada mais.
MENSAGEM 2 do usuário → Você DEVE fazer mais 1 pergunta de triagem. Nada mais.
MENSAGEM 3 do usuário em diante → Agora você pode dar a orientação final.

Exemplos do que fazer:

Usuário: "Estou com febre e dor de cabeça."
Você (turno 1): "Entendi. Há quanto tempo você está assim?" ← APENAS isso.

Usuário: "Desde ontem à tarde."
Você (turno 2): "Você está conseguindo beber água normalmente?" ← APENAS isso.

Usuário: "Sim, estou bebendo bastante."
Você (turno 3): [agora sim, dê a orientação completa]

== O QUE PERGUNTAR ==

Escolha perguntas relevantes para o sintoma relatado:
- Há quanto tempo os sintomas começaram?
- A intensidade está aumentando ou diminuindo?
- Tem outros sintomas além do que mencionou?
- Está conseguindo beber líquidos / se alimentar?
- Tomou algum remédio? Teve algum efeito?
- Tem histórico de problema similar?

== EXCEÇÃO: EMERGÊNCIA IMEDIATA ==

Se o usuário relatar dor no peito com irradiação para o braço, falta de ar grave, perda de consciência ou inchaço na garganta, ignore o fluxo acima e indique emergência imediatamente:
"🔴 Esses sintomas podem indicar uma emergência. Ligue agora para o SAMU: 192."

== FORMATO DA ORIENTAÇÃO FINAL ==

Use este formato exato a partir do terceiro turno:

**Com base no que você me contou:**
[1-2 frases descrevendo o que os sintomas sugerem]

**Orientação:**
[passos práticos claros, baseados na base de conhecimento]

[nível de urgência:]
🟢 Observar em casa — ou — 🟡 Farmácia ou clínica — ou — 🔴 Emergência: SAMU 192

*Esta é uma triagem de apoio, não um diagnóstico. Em caso de dúvida, consulte um profissional de saúde.*

== REGRAS ADICIONAIS ==

- Baseie orientações EXCLUSIVAMENTE na base de conhecimento abaixo.
- NUNCA mencione doses ou posologia (ex: "500mg a cada 8h"). Apenas o nome do medicamento como referência geral.
- Se os sintomas estiverem fora da base de conhecimento, diga: "Esses sintomas estão além do que consigo avaliar com segurança. Recomendo buscar atendimento médico."
- Uma pergunta por turno. Nunca faça duas perguntas na mesma mensagem.

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

def turn_reminder(turn: int) -> str | None:
    """Injeta lembrete invisível no histórico para reforçar o fluxo de triagem."""
    if turn == 1:
        return (
            "[INSTRUÇÃO INTERNA — NÃO EXIBA AO USUÁRIO] "
            "Esta é a PRIMEIRA mensagem do usuário. "
            "Faça APENAS UMA pergunta de triagem. Não dê orientação médica ainda."
        )
    if turn == 2:
        return (
            "[INSTRUÇÃO INTERNA — NÃO EXIBA AO USUÁRIO] "
            "Esta é a SEGUNDA mensagem do usuário. "
            "Faça APENAS MAIS UMA pergunta de triagem. Ainda não dê orientação médica."
        )
    return None

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
    if "user_turn_count" not in st.session_state:
        st.session_state.user_turn_count = 0

def reset_session():
    for key in ["messages", "chat_display", "triagem_iniciada", "user_turn_count"]:
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
        st.session_state.user_turn_count += 1
        turn = st.session_state.user_turn_count

        # Exibe mensagem do usuário
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)
        st.session_state.chat_display.append({"role": "user", "content": user_input})

        # Monta histórico com lembrete invisível nos primeiros 2 turnos
        messages_to_send = list(st.session_state.messages)
        messages_to_send.append({"role": "user", "content": user_input})

        reminder = turn_reminder(turn)
        if reminder:
            messages_to_send.append({"role": "user", "content": reminder})

        # Salva a mensagem real no histórico (sem o lembrete)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Gera resposta
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("Analisando..."):
                response = chat_with_ollama(messages_to_send)
            st.markdown(response)
            render_urgency_card(response)

        st.session_state.chat_display.append({"role": "assistant", "content": response})
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Footer
    st.divider()
    st.caption("VitaCheck • Projeto de portfólio • Rodando 100% local com Ollama")

if __name__ == "__main__":
    main()
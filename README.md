# 🩺 VitaCheck — Assistente de Triagem de Sintomas com IA Local

> Triagem inteligente de sintomas com contexto acumulado, base de conhecimento estruturada e classificação de urgência — rodando 100% local, sem API key, sem custo.

---

## O Problema

Quando alguém sente um sintoma, a primeira reação costuma ser pesquisar no Google — e o resultado quase sempre é uma lista de possibilidades que vai do banal ao catastrófico, sem nenhuma orientação sobre o que realmente fazer.

O que falta não é informação. É **triagem**: alguém que faça as perguntas certas, no ordem certa, e diga com clareza qual é o próximo passo.

---

## A Solução

O VitaCheck é um assistente de triagem de sintomas que conduz uma conversa progressiva com o usuário — fazendo perguntas de contexto antes de concluir — e ao final indica:

- O que os sintomas podem indicar
- A orientação prática baseada em uma base de conhecimento curada
- O nível de urgência: 🟢 Observar em casa / 🟡 Farmácia ou clínica / 🔴 Emergência

**Não é um diagnóstico. É triagem** — a diferença entre tomar a decisão certa e ignorar algo que não devia ignorar.

---

## Diferenciais Técnicos

| Feature | Como foi implementado |
|---|---|
| **Roda 100% local** | Ollama com llama3.1:8b — zero custo, zero dependência de nuvem |
| **Multi-turn com contexto real** | Histórico completo da sessão enviado a cada chamada à API |
| **Base de conhecimento estruturada** | `conditions.json` com 10 condições, sintomas de alerta e orientações seguras |
| **KB injetada no system prompt** | O modelo vê as condições documentadas a cada turno — sem alucinação |
| **Classificação de urgência visual** | Cards coloridos (🟢🟡🔴) renderizados automaticamente na UI |
| **Recusa segura** | Prompt treinado para admitir limite do escopo em vez de inventar |

---

## Stack

- **LLM:** [Ollama](https://ollama.com/) + `llama3.1:8b` (local)
- **Frontend:** [Streamlit](https://streamlit.io/)
- **Linguagem:** Python 3.10+
- **Dependências:** `streamlit`, `requests` — sem SDK de IA, sem chave de API

---

## Estrutura do Projeto

```
vitacheck/
├── README.md
├── requirements.txt
├── data/
│   └── conditions.json        # Base de conhecimento com 10 condições
├── docs/
│   ├── prompts.md             # System prompt, prompts de abertura e fallback
│   └── avaliacao.md          # Cenários de teste e métricas de qualidade
└── src/
    └── app.py                 # Aplicação Streamlit
```

---

## Como Rodar

### Pré-requisitos

- Python 3.10+
- [Ollama instalado](https://ollama.com/download)

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/eduardospsx/dio-lab-vita-check.git
cd vitacheck

# 2. Instale as dependências Python
pip install -r requirements.txt

# 3. Baixe o modelo (só na primeira vez, ~5GB)
ollama pull llama3.1:8b

# 4. Suba o Ollama em background
ollama serve

# 5. Rode o app
streamlit run src/app.py
```

Acesse em `http://localhost:8501`

---

## Como Funciona

```
Usuário descreve sintoma
        │
        ▼
VitaCheck faz perguntas de triagem (até 5 turnos)
        │
        ▼
Contexto acumulado + KB injetada no prompt
        │
        ▼
Modelo gera orientação baseada nas condições documentadas
        │
        ▼
UI exibe orientação + card de urgência (🟢 / 🟡 / 🔴)
```

A cada turno, o histórico completo da conversa é enviado ao Ollama — o modelo nunca perde o contexto do que foi dito antes.

---

## Base de Conhecimento

O arquivo `data/conditions.json` cobre 10 condições comuns:

| Condição | Urgência padrão |
|---|---|
| Resfriado comum | 🟢 |
| Dor lombar | 🟢 |
| Conjuntivite | 🟢 |
| Gripe / Influenza | 🟡 |
| Desidratação | 🟡 |
| Gastroenterite | 🟡 |
| Enxaqueca | 🟡 |
| Crise de ansiedade | 🟡 |
| Reação alérgica | ⚠️ Variável |
| Dor no peito | 🔴 |

Cada condição tem: sintomas-chave, sintomas de alerta, orientação prática e perguntas de triagem sugeridas.

---

## Avaliação

O projeto inclui um protocolo de avaliação com 6 cenários de teste documentados em `docs/avaliacao.md`, cobrindo:

- Triagem de sintomas leves e graves
- Comportamento em cenários de emergência
- Teste de contexto acumulado (multi-turn)
- Recusa segura para sintomas fora do escopo
- Resistência a indução de posologia

---

## Limitações

- O VitaCheck **não substitui atendimento médico**
- A base de conhecimento cobre condições comuns — sintomas raros ou complexos ativam o fallback
- A qualidade das respostas depende do modelo local; o llama3.1:8b tem bom desempenho para triagem em português, mas pode variar
- Não há persistência entre sessões — cada conversa começa do zero

---

## Próximos Passos

- [ ] Expandir a base de conhecimento para 25+ condições
- [ ] Adicionar suporte a voz (input por microfone via `speech_recognition`)
- [ ] Integrar observabilidade com LangFuse (compatível com a API local do Ollama)
- [ ] Adicionar histórico de sessões salvo localmente em SQLite

---

## Aviso Legal

> ⚠️ O VitaCheck é um projeto de portfólio educacional. As orientações fornecidas são de triagem geral e **não substituem consulta médica profissional**. Em caso de emergência, ligue **192 (SAMU)**.

---

*Desenvolvido como projeto de portfólio para o Lab "Construa Seu Assistente Virtual Com Inteligência Artificial" — DIO*

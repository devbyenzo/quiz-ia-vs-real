import io
import random
import sqlite3
from contextlib import closing
from datetime import datetime

import streamlit as st
from PIL import Image

DB_PATH = "quiz.db"
TOTAL_PERGUNTAS = 20

st.set_page_config(page_title="IA ou Real?", page_icon="🕵️", layout="wide")

SESSION_DEFAULTS = {
    "nome": "",
    "perguntas": [],
    "indice": 0,
    "acertos": 0,
    "respondida": False,
    "ultimo_acerto": False,
    "salvo": False,
}
for chave, valor in SESSION_DEFAULTS.items():
    st.session_state.setdefault(chave, valor)


def aplicar_estilos():
    st.markdown(
        """
        <style>
        :root {
            --ink: #20322d;
            --muted: #6c7771;
            --accent: #c65f43;
            --accent-hover: #a94b34;
            --forest: #203d35;
            --surface: #fffefa;
            --line: #e5dfd4;
            --paper: #f4f0e8;
        }
        .stApp { background: var(--paper); color: var(--ink); }
        [data-testid="stHeader"] { background: transparent; }
        [data-testid="stToolbar"] { right: 1rem; }
        .block-container {
            max-width: 1120px;
            padding: 2.6rem 2.2rem 4rem;
        }
        h1, h2, h3 { color: var(--ink); letter-spacing: -.035em; }
        .hero {
            position: relative;
            overflow: hidden;
            padding: clamp(1.8rem, 4vw, 2.8rem);
            margin: .35rem 0 1.5rem;
            border-radius: 22px;
            background: var(--forest);
            color: #fffefa;
        }
        .hero:after {
            content: "";
            position: absolute;
            width: 19rem;
            height: 19rem;
            right: -5rem;
            top: -10rem;
            border: 1px solid rgba(255, 254, 250, .15);
            border-radius: 50%;
            box-shadow: 0 0 0 2.2rem rgba(255, 254, 250, .035),
                        0 0 0 4.5rem rgba(255, 254, 250, .025);
        }
        .hero-kicker {
            margin: 0 0 .8rem;
            color: #edb29b;
            font-size: .72rem;
            font-weight: 750;
            letter-spacing: .16em;
            text-transform: uppercase;
        }
        .hero h1 {
            position: relative;
            z-index: 1;
            margin: 0;
            color: #fffefa;
            font-size: clamp(2.7rem, 6vw, 4.3rem);
            font-weight: 720;
            letter-spacing: -.065em;
            line-height: 1;
        }
        .hero p {
            position: relative;
            z-index: 1;
            max-width: 34rem;
            margin: 1rem 0 0;
            color: #d4dfd8 !important;
            font-size: 1rem;
            line-height: 1.6;
        }
        [data-testid="stTabs"] [role="tablist"] {
            gap: 1.6rem;
            border-bottom: 1px solid #ded7cb;
        }
        [data-testid="stTabs"] button[role="tab"] {
            padding: .8rem .15rem;
            color: var(--muted);
            font-weight: 600;
        }
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: var(--forest);
            border-bottom: 2px solid var(--accent);
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--line) !important;
            border-radius: 16px !important;
            background: var(--surface);
        }
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button {
            min-height: 3rem;
            border: 1px solid #d8d1c5;
            border-radius: 9px;
            background: var(--surface);
            color: var(--ink) !important;
            font-weight: 650;
            transition: border-color .15s ease, background .15s ease, transform .15s ease;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover {
            border-color: var(--forest);
            background: #f2f4ef;
            transform: translateY(-1px);
        }
        [data-testid="stButton"] button[kind="primary"],
        [data-testid="stFormSubmitButton"] button[kind="primary"] {
            background: var(--accent);
            border-color: var(--accent);
            color: #fffefa !important;
        }
        [data-testid="stButton"] button[kind="primary"]:hover,
        [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
            background: var(--accent-hover);
            border-color: var(--accent-hover);
            color: #fffefa !important;
        }
        [data-testid="stTextInput"] input {
            min-height: 3rem;
            border: 1px solid #d8d1c5;
            border-radius: 9px;
            background: var(--surface);
            color: var(--ink) !important;
        }
        [data-testid="stTextInput"] input::placeholder {
            color: #89918b !important;
            opacity: 1;
        }
        [data-testid="stCaptionContainer"] p { color: var(--muted); }
        [data-testid="stMarkdownContainer"] p { color: var(--muted); }
        [data-testid="stProgressBar"] > div > div { background: var(--accent); }
        [data-testid="stImage"] img { border-radius: 12px; }
        [data-testid="stMetric"] {
            padding: 1.3rem 1.5rem;
            border: 1px solid var(--line);
            border-radius: 14px;
            background: var(--surface);
        }
        [data-testid="stMetricValue"] { color: var(--forest); }
        [data-testid="stAlert"] { border-radius: 10px; }
        @media (max-width: 700px) {
            .block-container { padding: 1.2rem 1rem 2.5rem; }
            .hero { padding: 1.8rem 1.4rem; border-radius: 16px; }
            .hero:after { right: -13rem; }
            [data-testid="stTabs"] [role="tablist"] { gap: .9rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- Banco de dados
def get_conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with closing(get_conn()) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS pares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descricao TEXT,
                img_real BLOB NOT NULL,
                img_ia BLOB NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS resultados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                acertos INTEGER NOT NULL,
                total INTEGER NOT NULL,
                data TEXT NOT NULL
            )"""
        )
        conn.commit()


def preparar_imagem(arquivo) -> bytes:
    """Redimensiona (máx. 900px) e converte para JPEG antes de salvar no banco."""
    img = Image.open(arquivo).convert("RGB")
    img.thumbnail((900, 900))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def salvar_par(descricao, arq_real, arq_ia):
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO pares (descricao, img_real, img_ia) VALUES (?, ?, ?)",
            (descricao, preparar_imagem(arq_real), preparar_imagem(arq_ia)),
        )
        conn.commit()


def contar_pares() -> int:
    with closing(get_conn()) as conn:
        return conn.execute("SELECT COUNT(*) FROM pares").fetchone()[0]


def ids_pares():
    with closing(get_conn()) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM pares")]


def buscar_par(par_id):
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT img_real, img_ia FROM pares WHERE id = ?", (par_id,)
        ).fetchone()


def salvar_resultado(nome, acertos, total):
    with closing(get_conn()) as conn:
        conn.execute(
            "INSERT INTO resultados (nome, acertos, total, data) VALUES (?, ?, ?, ?)",
            (nome, acertos, total, datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()


def ranking(limite=10):
    """Melhor pontuação de cada usuário."""
    with closing(get_conn()) as conn:
        return conn.execute(
            """SELECT nome, MAX(acertos) AS melhor, total
               FROM resultados
               GROUP BY nome
               ORDER BY melhor DESC, MIN(data) ASC
               LIMIT ?""",
            (limite,),
        ).fetchall()


# ---------------------------------------------------------------- Estado
def resetar():
    for chave, valor in SESSION_DEFAULTS.items():
        st.session_state[chave] = valor


def iniciar_quiz(nome):
    ids = ids_pares()
    sorteados = random.sample(ids, min(TOTAL_PERGUNTAS, len(ids)))
    st.session_state.nome = nome
    st.session_state.perguntas = [
        {"id": i, "ia_na_esquerda": random.choice([True, False])} for i in sorteados
    ]
    st.session_state.indice = 0
    st.session_state.acertos = 0
    st.session_state.respondida = False
    st.session_state.ultimo_acerto = False
    st.session_state.salvo = False


def responder(escolha_esquerda: bool):
    q = st.session_state.perguntas[st.session_state.indice]
    acertou = escolha_esquerda == q["ia_na_esquerda"]
    st.session_state.acertos += int(acertou)
    st.session_state.ultimo_acerto = acertou
    st.session_state.respondida = True


def proxima():
    st.session_state.indice += 1
    st.session_state.respondida = False


# ---------------------------------------------------------------- Interface
def mostrar_ranking():
    st.subheader("Placar")
    st.caption("Melhor resultado de cada jogador")
    dados = ranking()
    if not dados:
        st.info("Ainda não há resultados. Seja o primeiro a jogar.")
        return
    with st.container(border=True):
        for pos, (nome, melhor, total) in enumerate(dados, start=1):
            pos_col, player_col = st.columns([.55, 2.4])
            pos_col.markdown(f"**{pos:02d}**")
            player_col.markdown(f"**{nome}**")
            player_col.caption(f"{melhor} / {total} acertos")


def tela_login():
    if contar_pares() == 0:
        st.warning("O quiz ainda não tem imagens. Cadastre alguns pares para começar.")
        return
    if contar_pares() < TOTAL_PERGUNTAS:
        st.warning(
            f"Só há {contar_pares()} pares cadastrados; o quiz terá "
            f"{contar_pares()} perguntas em vez de {TOTAL_PERGUNTAS}."
        )
    with st.container(border=True):
        st.markdown("### Seu olho, contra o algoritmo.")
        st.write("Veja dois exemplos. Só um deles foi criado por inteligência artificial.")
        nome = st.text_input("Seu nome", max_chars=30, placeholder="Como podemos chamar você?")
        if st.button("Começar desafio", type="primary", use_container_width=True):
            if nome.strip():
                iniciar_quiz(nome.strip())
                st.rerun()
            else:
                st.error("Informe seu nome.")


def tela_pergunta():
    perguntas = st.session_state.perguntas
    idx = st.session_state.indice
    q = perguntas[idx]

    st.caption(f"JOGADOR  /  {st.session_state.nome}")
    st.progress((idx + 1) / len(perguntas), text=f"Pergunta {idx + 1} de {len(perguntas)}")
    st.markdown("### Qual imagem foi gerada por IA?")

    img_real, img_ia = buscar_par(q["id"])
    esquerda, direita = (img_ia, img_real) if q["ia_na_esquerda"] else (img_real, img_ia)

    c1, c2 = st.columns(2)
    c1.image(esquerda, caption="A", use_container_width=True)
    c2.image(direita, caption="B", use_container_width=True)

    if not st.session_state.respondida:
        b1, b2 = st.columns(2)
        b1.button("A foi criada por IA", on_click=responder, args=(True,), use_container_width=True)
        b2.button("B foi criada por IA", on_click=responder, args=(False,), use_container_width=True)
    else:
        lado = "A" if q["ia_na_esquerda"] else "B"
        if st.session_state.ultimo_acerto:
            st.success(f"Correto. A imagem {lado} foi gerada por IA.")
        else:
            st.error(f"Não foi dessa vez. A imagem {lado} foi gerada por IA.")
        ultimo = idx == len(perguntas) - 1
        st.button(
            "Ver resultado" if ultimo else "Próximo par",
            on_click=proxima,
            type="primary",
        )


def tela_final():
    total = len(st.session_state.perguntas)
    acertos = st.session_state.acertos
    if not st.session_state.salvo:
        salvar_resultado(st.session_state.nome, acertos, total)
        st.session_state.salvo = True

    st.subheader(f"Desafio concluído, {st.session_state.nome}.")
    st.metric("Acertos", f"{acertos} / {total}", f"{acertos / total:.0%} de precisão")
    if st.button("Jogar novamente", type="primary"):
        resetar()
        st.rerun()


def aba_quiz():
    col_quiz, col_rank = st.columns([2, 1], gap="large")
    with col_quiz:
        if not st.session_state.perguntas:
            tela_login()
        elif st.session_state.indice < len(st.session_state.perguntas):
            tela_pergunta()
        else:
            tela_final()
    with col_rank:
        mostrar_ranking()


def aba_cadastro():
    st.subheader("Adicionar imagens ao quiz")
    st.caption(
        f"Cada par tem uma foto **real** e uma imagem **gerada por IA** "
        f"(ideal: assuntos parecidos). Pares cadastrados: **{contar_pares()}** "
        f"(recomendado: pelo menos {TOTAL_PERGUNTAS})."
    )
    with st.form("cadastro", clear_on_submit=True):
        descricao = st.text_input("Assunto do par (opcional)", placeholder="Ex.: paisagem de montanha")
        c1, c2 = st.columns(2)
        arq_real = c1.file_uploader("Fotografia ou arte real", type=["jpg", "jpeg", "png", "webp"])
        arq_ia = c2.file_uploader("Imagem gerada por IA", type=["jpg", "jpeg", "png", "webp"])
        enviado = st.form_submit_button("Adicionar par", type="primary")
    if enviado:
        if arq_real and arq_ia:
            salvar_par(descricao, arq_real, arq_ia)
            st.success("Par adicionado ao quiz.")
        else:
            st.error("Envie as duas imagens.")


# ---------------------------------------------------------------- Main
init_db()
aplicar_estilos()
st.markdown(
    """
    <header class="hero">
        <div class="hero-kicker">Desafio visual · 01</div>
        <h1>IA ou real?</h1>
        <p>Seu olho ainda sabe diferenciar? Compare as imagens e descubra o que foi criado por inteligência artificial.</p>
    </header>
    """,
    unsafe_allow_html=True,
)
tab_quiz, tab_cad = st.tabs(["Jogar", "Cadastrar imagens"])
with tab_quiz:
    aba_quiz()
with tab_cad:
    aba_cadastro()

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
    for chave in ("nome", "perguntas", "indice", "acertos", "respondida", "ultimo_acerto", "salvo"):
        st.session_state.pop(chave, None)


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
    st.subheader("🏆 Ranking")
    dados = ranking()
    if not dados:
        st.info("Ninguém jogou ainda. Seja o primeiro!")
        return
    medalhas = ["🥇", "🥈", "🥉"]
    for pos, (nome, melhor, total) in enumerate(dados):
        marca = medalhas[pos] if pos < 3 else f"{pos + 1}º"
        st.markdown(f"**{marca} {nome}** — {melhor}/{total} acertos")


def tela_login():
    st.subheader("👤 Entrar")
    if contar_pares() == 0:
        st.warning("Nenhuma imagem cadastrada. Use a aba **Cadastrar imagens** primeiro.")
        return
    if contar_pares() < TOTAL_PERGUNTAS:
        st.warning(
            f"Só há {contar_pares()} pares cadastrados; o quiz terá "
            f"{contar_pares()} perguntas em vez de {TOTAL_PERGUNTAS}."
        )
    nome = st.text_input("Digite seu nome para começar", max_chars=30)
    if st.button("Começar quiz", type="primary"):
        if nome.strip():
            iniciar_quiz(nome.strip())
            st.rerun()
        else:
            st.error("Informe seu nome.")


def tela_pergunta():
    perguntas = st.session_state.perguntas
    idx = st.session_state.indice
    q = perguntas[idx]

    st.markdown(f"Jogador: **{st.session_state.nome}**")
    st.progress(idx / len(perguntas), text=f"Pergunta {idx + 1} de {len(perguntas)}")
    st.markdown("### Qual destas imagens foi gerada por IA?")

    img_real, img_ia = buscar_par(q["id"])
    esquerda, direita = (img_ia, img_real) if q["ia_na_esquerda"] else (img_real, img_ia)

    c1, c2 = st.columns(2)
    c1.image(esquerda, caption="Imagem A", use_container_width=True)
    c2.image(direita, caption="Imagem B", use_container_width=True)

    if not st.session_state.respondida:
        b1, b2 = st.columns(2)
        b1.button("A é gerada por IA", on_click=responder, args=(True,), use_container_width=True)
        b2.button("B é gerada por IA", on_click=responder, args=(False,), use_container_width=True)
    else:
        lado = "A" if q["ia_na_esquerda"] else "B"
        if st.session_state.ultimo_acerto:
            st.success(f"✅ Acertou! A imagem {lado} era a gerada por IA.")
        else:
            st.error(f"❌ Errou! A imagem gerada por IA era a {lado}.")
        ultimo = idx == len(perguntas) - 1
        st.button(
            "Ver resultado" if ultimo else "Próxima ➡️",
            on_click=proxima,
            type="primary",
        )


def tela_final():
    total = len(st.session_state.perguntas)
    acertos = st.session_state.acertos
    if not st.session_state.salvo:
        salvar_resultado(st.session_state.nome, acertos, total)
        st.session_state.salvo = True

    st.subheader(f"🎉 Fim, {st.session_state.nome}!")
    st.metric("Seu resultado", f"{acertos} / {total}", f"{acertos / total:.0%} de acerto")
    if st.button("Jogar novamente", type="primary"):
        resetar()
        st.rerun()


def aba_quiz():
    col_quiz, col_rank = st.columns([2, 1], gap="large")
    with col_quiz:
        if "perguntas" not in st.session_state:
            tela_login()
        elif st.session_state.indice < len(st.session_state.perguntas):
            tela_pergunta()
        else:
            tela_final()
    with col_rank:
        mostrar_ranking()


def aba_cadastro():
    st.subheader("Cadastrar par de imagens")
    st.caption(
        f"Cada par tem uma foto **real** e uma imagem **gerada por IA** "
        f"(ideal: assuntos parecidos). Pares cadastrados: **{contar_pares()}** "
        f"(recomendado: pelo menos {TOTAL_PERGUNTAS})."
    )
    with st.form("cadastro", clear_on_submit=True):
        descricao = st.text_input("Descrição (opcional)")
        c1, c2 = st.columns(2)
        arq_real = c1.file_uploader("Imagem REAL", type=["jpg", "jpeg", "png", "webp"])
        arq_ia = c2.file_uploader("Imagem gerada por IA", type=["jpg", "jpeg", "png", "webp"])
        enviado = st.form_submit_button("Salvar par", type="primary")
    if enviado:
        if arq_real and arq_ia:
            salvar_par(descricao, arq_real, arq_ia)
            st.success("Par salvo no banco de dados!")
        else:
            st.error("Envie as duas imagens.")


# ---------------------------------------------------------------- Main
init_db()
st.title("🕵️ IA ou Real?")
tab_quiz, tab_cad = st.tabs(["🎮 Quiz", "🖼️ Cadastrar imagens"])
with tab_quiz:
    aba_quiz()
with tab_cad:
    aba_cadastro()

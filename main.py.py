from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import pandas as pd
import datetime
import pyodbc
import matplotlib
matplotlib.use("Agg")  # backend sem janela (evita travar)
import matplotlib.pyplot as plt
import io
import logging
import sys

# Logging básico
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Caminho do banco Access
CAMINHO_RECEBIMENTO = r"\\lctbrfsr01\Corporativo_SPO\Logistica\USUÁRIOS\Banco_Dados\Banco_Dados_Recebimento.accdb"

# Função para aplicar cor ao status
def cor_status(status):
    status = str(status).strip().lower()
    if status == "realizado":
        return "🟢 Realizado"
    elif status == "pendente":
        return "🟡 Pendente"
    else:
        return status.capitalize()

# Função auxiliar para carregar dados via cursor (sem warnings)
def carregar_dados(query, caminho=CAMINHO_RECEBIMENTO):
    conn_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        fr"DBQ={caminho};"
    )
    conn = pyodbc.connect(conn_str)
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame.from_records(rows, columns=columns)
        return df
    finally:
        conn.close()

# ---------------- OPÇÃO 1 ----------------
def consultar_analise_patio():
    try:
        df = carregar_dados("SELECT * FROM tbl_Recebimento")
        # Garantir colunas essenciais
        for col in ["Data", "Processo", "Status_Entrada", "Transportes", "Transportadora", "Etapas_Gerais"]:
            if col not in df.columns:
                return f"Coluna ausente no banco: {col}"

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
        hoje = datetime.date.today()

        df_hoje = df[df["Data"] == hoje]
        if df_hoje.empty:
            return "Nenhum processo encontrado com data atual (hoje)."

        # KPIs resumidos
        total = df_hoje["Processo"].nunique()
        realizados = df_hoje[df_hoje["Status_Entrada"].astype(str).str.upper() == "REALIZADO"]["Processo"].nunique()
        pendentes = df_hoje[df_hoje["Status_Entrada"].astype(str).str.upper() == "PENDENTE"]["Processo"].nunique()

        linhas = ["📋 *Análise de Pátio (Hoje)*\n"]
        linhas.append(f"📊 Indicadores do dia:\n- Total: {total}\n- Realizados: {realizados}\n- Pendentes: {pendentes}\n")

        # Listagem detalhada
        for _, row in df_hoje.iterrows():
            processo = str(row.get("Processo", "")).strip()
            transportes = str(row.get("Transportes", "")).strip()
            transportadora = str(row.get("Transportadora", "")).strip()
            status = cor_status(row.get("Status_Entrada", ""))
            etapa = str(row.get("Etapas_Gerais", "")).strip()

            linhas.append(
                f"🚚*{processo}*\n"
                f"- Transportes: {transportes}\n"
                f"- Transportadora: {transportadora}\n"
                f"- Estoque: {status}\n"
                f"- Etapa: {etapa}\n"
            )

        return "\n".join(linhas)

    except Exception as e:
        logging.exception("Erro ao acessar banco Access")
        return "Erro ao acessar os dados de recebimento."

# ---------------- OPÇÃO 2 ----------------
def consultar_carregamentos():
    try:
        df = carregar_dados("SELECT * FROM tbl_Carregamento")

        # Garantir colunas
        for col in ["Processo", "Data_Programada", "CD-TSPF_Destino", "Perfil_Veiculo", "Etapas_Gerais"]:
            if col not in df.columns:
                return f"Coluna ausente no banco: {col}"

        if df.empty:
            return "Sem Dados.."

        linhas = ["📦 *Carregamentos*\n"]
        for _, row in df.iterrows():
            processo = str(row.get("Processo", "")).strip()
            data_prog = str(row.get("Data_Programada", "")).strip()
            destino = str(row.get("CD-TSPF_Destino", "")).strip()
            perfil = str(row.get("Perfil_Veiculo", "")).strip()
            etapa = cor_status(row.get("Etapas_Gerais", ""))

            linhas.append(
                f"🚛*{processo}*\n"
                f"- Data Programada: {data_prog}\n"
                f"- Destino: {destino}\n"
                f"- Perfil Veículo: {perfil}\n"
                f"- Etapa: {etapa}\n"
            )

        return "\n".join(linhas)

    except Exception as e:
        logging.exception("Erro ao acessar banco Access")
        return "Erro ao acessar os dados de carregamento."

# ---------------- OPÇÃO 3 ----------------
def consultar_fila():
    try:
        df = carregar_dados("SELECT * FROM tbl_Recebimento")
        if "Etapas_Gerais" not in df.columns:
            return "Coluna ausente no banco: Etapas_Gerais"

        df["Etapas_Gerais"] = df["Etapas_Gerais"].astype(str)
        df_fila = df[df["Etapas_Gerais"].str.strip().str.upper() == "NA FILA"]

        if df_fila.empty:
            return "Sem Dados.."

        linhas = ["⏳ *Fila de Recebimentos*\n"]
        for _, row in df_fila.iterrows():
            processo = str(row.get("Processo", "")).strip()
            transportes = str(row.get("Transportes", "")).strip()
            transportadora = str(row.get("Transportadora", "")).strip()

            linhas.append(
                f"📌*{processo}*\n"
                f"- Transportes: {transportes}\n"
                f"- Transportadora: {transportadora}\n"
            )

        return "\n".join(linhas)

    except Exception as e:
        logging.exception("Erro ao acessar banco Access")
        return "Erro ao acessar os dados da fila."

# ---------------- OPÇÃO 4 (Gráficos da Semana) ----------------
def gerar_grafico_status_semana():
    try:
        df = carregar_dados("SELECT * FROM tbl_Recebimento")
        # Verifica colunas antes de usar
        required_cols = ["Data", "Entrada_Cenario", "Transportadora", "CD_Origem", "Ocorrência"]
        for col in required_cols:
            if col not in df.columns:
                logging.warning(f"Coluna ausente no banco: {col}")

        # Conversões seguras
        if "Data" in df.columns:
            df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
        else:
            df["Data"] = pd.NaT

        if "Entrada_Cenario" in df.columns:
            df["Entrada_Cenario"] = df["Entrada_Cenario"].astype(str).str.strip().str.upper().replace({"NAO":"NÃO"})
        else:
            df["Entrada_Cenario"] = ""

        if "Ocorrência" in df.columns:
            df["Ocorrência"] = df["Ocorrência"].astype(str).str.strip().str.upper().replace({"NAO":"NÃO"})
        else:
            df["Ocorrência"] = ""

        hoje = datetime.date.today()
        inicio_semana = hoje - datetime.timedelta(days=7)
        inicio_mes = hoje.replace(day=1)

        df_semana = df[(df["Data"] >= inicio_semana) & (df["Data"] <= hoje)]
        df_mes = df[(df["Data"] >= inicio_mes) & (df["Data"] <= hoje)]
        df_dia = df[df["Data"] == hoje]

        # ---------------- Percentuais gerais Entrada_Cenario ----------------
        def calc_percent(df_local):
            if df_local.empty:
                return 0.0
            total = len(df_local)
            sim = (df_local["Entrada_Cenario"] == "SIM").sum()
            return round(sim / total * 100, 1) if total > 0 else 0.0

        pct_dia = calc_percent(df_dia)
        pct_semana = calc_percent(df_semana)
        pct_mes = calc_percent(df_mes)

        resumo_percentuais = (
            f"📊 *Percentual Entrada em Cenário*\n"
            f"- Dia: {pct_dia}% SIM\n"
            f"- Semana: {pct_semana}% SIM\n"
            f"- Mês: {pct_mes}% SIM\n"
        )

        # ---------------- Gráfico 1: Recebimentos por dia (SIM/NÃO) ----------------
        buf1 = io.BytesIO()
        if not df_semana.empty:
            resumo = (
                df_semana.groupby(["Data", "Entrada_Cenario"])
                .size()
                .unstack(fill_value=0)
            )
            # Garante colunas SIM/NÃO mesmo que falte uma
            for k in ["SIM", "NÃO"]:
                if k not in resumo.columns:
                    resumo[k] = 0

            resumo[["SIM", "NÃO"]].plot(kind="bar", stacked=True, figsize=(8,5), color={"SIM":"green","NÃO":"orange"})
            plt.title("Recebimentos da Semana - Entrada em Cenário (SIM/NÃO)")
            plt.xlabel("Data")
            plt.ylabel("Quantidade")
        else:
            plt.figure(figsize=(8,5))
            plt.title("Recebimentos da Semana - Sem dados")
            plt.xlabel("Data")
            plt.ylabel("Quantidade")
            plt.text(0.5, 0.5, "Sem dados na semana", ha="center", va="center")

        plt.tight_layout()
        plt.savefig(buf1, format="png")
        plt.close()
        buf1.seek(0)

        # ---------------- Gráfico 2: Top 10 Transportadoras (total processos) ----------------
        buf2 = None
        df_top10 = pd.DataFrame()
        if "Transportadora" in df.columns and not df_semana.empty:
            top_transportadoras = df_semana.groupby("Transportadora").size().nlargest(10)
            df_top10 = top_transportadoras.to_frame(name="Total Processos")

            buf2 = io.BytesIO()
            df_top10.plot(kind="bar", figsize=(10,6), color="blue")
            plt.title("Top 10 Transportadoras - Total de Processos (Semana)")
            plt.xlabel("Transportadora")
            plt.ylabel("Quantidade")
            plt.tight_layout()
            plt.savefig(buf2, format="png")
            plt.close()
            buf2.seek(0)

        # ---------------- Gráfico 3: Ocorrência por CD_Origem ----------------
        buf3 = None
        if "CD_Origem" in df.columns and "Ocorrência" in df.columns and not df_semana.empty:
            df_ocorrencia = df_semana.dropna(subset=["CD_Origem", "Ocorrência"])
            # Remove vazios
            df_ocorrencia = df_ocorrencia[(df_ocorrencia["CD_Origem"].astype(str).str.strip() != "") &
                                          (df_ocorrencia["Ocorrência"].astype(str).str.strip() != "")]

            if not df_ocorrencia.empty:
                resumo_ocorrencia = (
                    df_ocorrencia.groupby(["CD_Origem", "Ocorrência"])
                    .size()
                    .unstack(fill_value=0)
                )
                # Garante colunas SIM/NÃO
                for k in ["SIM", "NÃO"]:
                    if k not in resumo_ocorrencia.columns:
                        resumo_ocorrencia[k] = 0

                buf3 = io.BytesIO()
                resumo_ocorrencia[["SIM", "NÃO"]].plot(kind="bar", stacked=True, figsize=(10,6), color={"SIM":"red","NÃO":"green"})
                plt.title("Ocorrência por CD_Origem - Semana Atual")
                plt.xlabel("CD Origem")
                plt.ylabel("Quantidade")
                plt.tight_layout()
                plt.savefig(buf3, format="png")
                plt.close()
                buf3.seek(0)

        return buf1, buf2, buf3, df_top10, resumo_percentuais

    except Exception as e:
        logging.exception("Erro ao gerar gráficos")
        return None, None, None, None, None

# ---------------- BOT ----------------
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        texto = (update.message.text or "").strip().lower()

        if texto == "1":
            resposta = consultar_analise_patio()
            await update.message.reply_text(resposta)
        elif texto == "2":
            resposta = consultar_carregamentos()
            await update.message.reply_text(resposta)
        elif texto == "3":
            resposta = consultar_fila()
            await update.message.reply_text(resposta)
        elif texto == "4":
            buf1, buf2, buf3, df_top10, resumo_percentuais = gerar_grafico_status_semana()

            # Percentuais gerais
            if resumo_percentuais:
                await update.message.reply_text(resumo_percentuais)

            # Gráfico da semana
            if buf1:
                await update.message.reply_photo(photo=buf1)

            # Gráfico transportadoras + resumo
            if buf2 and df_top10 is not None and not df_top10.empty:
                await update.message.reply_photo(photo=buf2)

                linhas = ["📦 *Top 10 Transportadoras - Total Processos*\n"]
                for idx, row in df_top10.iterrows():
                    linhas.append(f"- {idx}: {row['Total Processos']} processos")
                await update.message.reply_text("\n".join(linhas))

            # Gráfico Ocorrência por CD_Origem
            if buf3:
                await update.message.reply_photo(photo=buf3)
        else:
            resposta = (
                "Olá! Selecione uma das opções abaixo:\n\n"
                "1️⃣ Recebimentos (KPIs + detalhes)\n"
                "2️⃣ Carregamentos\n"
                "3️⃣ Fila\n"
                "4️⃣ Gráficos da Semana (Status + Transportadoras + Ocorrência)"
            )
            await update.message.reply_text(resposta)

    except Exception:
        logging.exception("Erro no handler do bot")
        await update.message.reply_text("Ocorreu um erro ao processar sua solicitação. Tente novamente.")

def main():
    try:
        app = ApplicationBuilder().token("7636125896:AAGu0N9ayf0hDEF_sYAOik5_otsYomaPjzU").build()
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
        logging.info("Bot iniciando polling...")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception:
        logging.exception("Falha ao iniciar o bot")

if __name__ == "__main__":
    main()

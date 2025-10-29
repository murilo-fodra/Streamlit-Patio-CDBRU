from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import pandas as pd
import datetime
import pyodbc

# Caminho do banco Access
CAMINHO_RECEBIMENTO = r"\\lctbrfsr01\Corporativo_SPO\Logistica\USUÁRIOS\Banco_Dados\Banco_Dados_Recebimento.accdb"

# Função para aplicar cor ao status
def cor_status(status):
    status = status.strip().lower()
    if status == "realizado":
        return "🟢 Realizado"
    elif status == "pendente":
        return "🟡 Pendente"
    else:
        return status.capitalize()

# Função para consultar a análise de pátio
def consultar_analise_patio():
    try:
        conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            fr"DBQ={CAMINHO_RECEBIMENTO};"
        )
        conn = pyodbc.connect(conn_str)
        df = pd.read_sql_query("SELECT * FROM tbl_Recebimento", conn)
        conn.close()

        df["Data"] = pd.to_datetime(df["Data"], errors="coerce").dt.date
        hoje = datetime.date.today()

        # Verifica se há registros com data de hoje
        df_hoje = df[df["Data"] == hoje]
        if df_hoje.empty:
            return "Nenhum processo encontrado com data atual (hoje)."

        # Identifica o dia anterior mais próximo dentro dos dados
        datas_anteriores = df[df["Data"] < hoje]["Data"].dropna().unique()
        if len(datas_anteriores) == 0:
            datas_validas = [hoje]
        else:
            dia_anterior = max(datas_anteriores)
            datas_validas = [hoje, dia_anterior]

        df_filtrado = df[df["Data"].isin(datas_validas)]
        df_ordenado = df_filtrado.sort_values(by="Data", ascending=False)

        linhas = ["📋 *Análise de Pátio (Hoje e Dia Anterior)*\n"]
        data_atual = None

        for _, row in df_ordenado.iterrows():
            data = row.get("Data", "")
            if data != data_atual:
                linhas.append(f"\n--- 📅 Dia: {data.strftime('%d/%m/%Y')} ---\n")
                data_atual = data

            processo = str(row.get("Processo", "")).strip()
            transportes = str(row.get("Transportes", "")).strip()
            transportadora = str(row.get("Transportadora", "")).strip()
            status = cor_status(str(row.get("Status_Entrada", "")).strip())
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
        print(f"Erro ao acessar banco Access: {e}")
        return "Erro ao acessar os dados de recebimento."

# Função principal de resposta
async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip().lower()

    if texto == "1":
        resposta = consultar_analise_patio()
    elif texto in ["2", "3", "4", "5"]:
        resposta = "Essa análise ainda está em desenvolvimento. Em breve estará disponível!"
    else:
        resposta = (
            "Olá! Selecione uma das opções abaixo:\n\n"
            "1️⃣ Análise Pátio\n"
            "2️⃣ Pendências de Estoque\n"
            "3️⃣ Ocupação\n"
            "4️⃣ Doca\n"
            "5️⃣ Prioridades Atendidas"
        )

    await update.message.reply_text(resposta)

# Inicia o bot
app = ApplicationBuilder().token("7636125896:AAGu0N9ayf0hDEF_sYAOik5_otsYomaPjzU").build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder))
app.run_polling()

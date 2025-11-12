import streamlit as st
import pandas as pd
import plotly.express as px
import pyodbc

# ==============================
# Função para carregar base com cache
# ==============================
@st.cache_data
def carregar_base():
    caminho_db = r"\\******************************\Banco_Dados\Banco_Dados_Recebimento.accdb"
    conn_str = (
        r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
        fr"DBQ={caminho_db};"
    )
    conn = pyodbc.connect(conn_str)
    query = "SELECT * FROM tbl_Recebimento"
    df = pd.read_sql(query, conn)
    conn.close()

    # Ajustar tipos
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["Mes"] = df["Data"].dt.to_period("M").astype(str)
    return df

# ==============================
# Carregar base
# ==============================
df = carregar_base()

# ==============================
# Título
# ==============================
st.title("🚛 Dashboard - Controle de Pátio")

# Botão de atualizar
if st.button("🔄 Atualizar dados"):
    st.cache_data.clear()   # limpa cache
    df = carregar_base()    # recarrega base
    st.success("Dados atualizados com sucesso!")

# ==============================
# Filtros
# ==============================
meses = sorted(df["Mes"].dropna().unique())
mes_selecionado = st.selectbox("Selecione o mês:", meses)
df_filtrado = df[df["Mes"] == mes_selecionado]

# ==============================
# Indicadores principais
# ==============================
st.subheader("📈 Indicadores")
col1, col2, col3 = st.columns(3)

total = df_filtrado["ID"].nunique()
realizados = df_filtrado[df_filtrado["Status_Entrada"] == "REALIZADO"]["ID"].nunique()
pendentes = df_filtrado[df_filtrado["Status_Entrada"] == "PENDENTE"]["ID"].nunique()

col1.metric("Total de Recebimentos", total)
col2.metric("Realizados", realizados)
col3.metric("Pendentes", pendentes)

# ==============================
# Gráfico Status Entrada
# ==============================
st.subheader("📦 Status de Entrada")
status_count = df_filtrado["Status_Entrada"].value_counts().reset_index()
status_count.columns = ["Status", "Quantidade"]

fig1 = px.bar(status_count, x="Status", y="Quantidade", color="Status", text="Quantidade")
fig1.update_layout(xaxis_title="Status", yaxis_title="Quantidade")
st.plotly_chart(fig1, use_container_width=True)

# ==============================
# Indicadores Entrada Cenário
# ==============================
st.subheader("🎯 Entrada Cenário (Sim/Não)")

if "Entrada_Cenario" in df_filtrado.columns:  # ajuste o nome conforme está na tabela
    total_cenario = df_filtrado["Entrada_Cenario"].count()
    sim = df_filtrado[df_filtrado["Entrada_Cenario"].str.upper() == "SIM"]["Entrada_Cenario"].count()
    nao = df_filtrado[df_filtrado["Entrada_Cenario"].str.upper() == "NAO"]["Entrada_Cenario"].count()

    perc_sim = round((sim / total_cenario) * 100, 1) if total_cenario > 0 else 0
    perc_nao = round((nao / total_cenario) * 100, 1) if total_cenario > 0 else 0

    col1, col2 = st.columns(2)
    col1.metric("Cenário SIM (%)", f"{perc_sim}%")
    col2.metric("Cenário NÃO (%)", f"{perc_nao}%")
else:
    st.warning("⚠️ Coluna 'Entrada_Cenario' não encontrada na base. Verifique o nome exato no Access.")


# ==============================
# Transportadoras
# ==============================
st.subheader("🚚 Top 10 Transportadoras")
top_transportadoras = df_filtrado["Transportadora"].value_counts().nlargest(10).reset_index()
top_transportadoras.columns = ["Transportadora", "Quantidade"]

fig3 = px.bar(top_transportadoras, x="Transportadora", y="Quantidade", text="Quantidade", color="Transportadora")
fig3.update_layout(xaxis_title="Transportadora", yaxis_title="Quantidade")
st.plotly_chart(fig3, use_container_width=True)

# ==============================
# Etapas Gerais
# ==============================
st.subheader("🛠️ Etapas Gerais do Processo")
etapas_count = df_filtrado["Etapas_Gerais"].value_counts().reset_index()
etapas_count.columns = ["Etapa", "Quantidade"]

fig4 = px.bar(etapas_count, x="Etapa", y="Quantidade", text="Quantidade", color="Etapa")
fig4.update_layout(xaxis_title="Etapas", yaxis_title="Quantidade")
st.plotly_chart(fig4, use_container_width=True)

# ==============================
# Evolução mensal (linha)
# ==============================
st.subheader("📅 Evolução Mensal de Recebimentos")
evolucao = df.groupby("Mes")["ID"].nunique().reset_index()
evolucao.columns = ["Mes", "Quantidade"]

fig5 = px.line(evolucao, x="Mes", y="Quantidade", markers=True)
fig5.update_layout(xaxis_title="Mês", yaxis_title="Qtd Recebimentos")
st.plotly_chart(fig5, use_container_width=True)

# ==============================
# Exibir tabela filtrada
# ==============================
st.subheader("📋 Dados filtrados")
st.dataframe(df_filtrado)

import pyodbc
import pandas as pd
import ctypes

caminho_banco = r'\\lctbrfsr01\Corporativo_SPO\Logistica\USUÁRIOS\Banco_Dados\Banco_Dados_Recebimento.accdb'

conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
    f'DBQ={caminho_banco};'
)
conn = pyodbc.connect(conn_str)

query = """
SELECT Processo, Hora_Entrada_Doca, Hora_Saida_Doca
FROM tbl_Recebimento
WHERE Hora_Entrada_Doca IS NOT NULL AND Hora_Saida_Doca IS NOT NULL
"""

df = pd.read_sql(query, conn)
conn.close()

df['Hora_Entrada_Doca'] = pd.to_datetime(df['Hora_Entrada_Doca'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
df['Hora_Saida_Doca'] = pd.to_datetime(df['Hora_Saida_Doca'], format='%d/%m/%Y %H:%M:%S', errors='coerce')

df['Tempo_Doca'] = df['Hora_Saida_Doca'] - df['Hora_Entrada_Doca']
df = df[df['Tempo_Doca'] >= pd.Timedelta(0)]

top3 = df.sort_values(by='Tempo_Doca', ascending=False).head(3)

mensagem = "📦 Top 3 Processos Mais Demorados:\n\n"
for i, row in top3.iterrows():
    processo = row['Processo']
    tempo = row['Tempo_Doca']
    minutos = round(tempo.total_seconds() / 60, 2)
    mensagem += f"🟥 Processo {processo}: {minutos} min\n"

# Exibir popup
ctypes.windll.user32.MessageBoxW(0, mensagem, "Alerta de Tempo na Doca", 1)

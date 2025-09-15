import streamlit as st
import pandas as pd
import plotly_express as px

# Título da página
st.set_page_config(layout="wide")
st.title("Dashboard Bela Vista Agropecuaria")

# Caminho do arquivo
file_path = "data/yeardate.csv"

try:
    # ---------------------------------------------
    # Leitura e Pré-processamento dos dados
    # ---------------------------------------------
    
    # Lê o arquivo, pulando as primeiras linhas e usando os delimitadores corretos
    df = pd.read_csv(file_path, sep=';', encoding='latin-1', on_bad_lines='skip', usecols=[0,1,2])  # pode remover skiprows=2 se não houver cabeçalhos extras

    # Lê o CSV pegando só as 3 primeiras colunas
    df = pd.read_csv(file_path, sep=';', encoding='latin-1', on_bad_lines='skip', usecols=[0,1,2])

    # Remove espaços nos nomes das colunas
    df.columns = [c.strip() for c in df.columns]

    # Renomeia para nomes consistentes
    df.columns = ["Conta", "Valor", "Mês"]

    # Normaliza a coluna "Conta"
    df['Conta'] = df['Conta'].astype(str).str.strip().str.lower()

    # Remove linhas onde a coluna 'Conta' está vazia
    df = df.dropna(subset=['Conta'])

    # Converte a coluna 'Valor' para número
    df['Valor'] = df['Valor'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')

    # Remove valores nulos após a conversão
    df = df.dropna(subset=['Valor'])

    st.header("Prévia dos Dados ")
    st.dataframe(df.head(200))
    
    st.write("---")

    # ---------------------------------------------
    # Cálculos dos Indicadores
    # ---------------------------------------------
    
    # Lista para armazenar os indicadores de cada mês
    indicadores = []
    
    for mes in df["Mês"].unique():
        dados_mes = df[df["Mês"] == mes]
    
        # Encontra as contas usando palavras-chave, o que é mais robusto
        ativo_circ = dados_mes.loc[dados_mes['Conta'].str.contains('ativo circulante', na=False), 'Valor'].sum()
        passivo_circ = dados_mes.loc[dados_mes['Conta'].str.contains('passivo circulante', na=False), 'Valor'].sum()
        passivo_nc = dados_mes.loc[dados_mes['Conta'].str.contains('passivo não circulante', na=False), 'Valor'].sum()
        patrimonio_liquido = dados_mes.loc[dados_mes['Conta'].str.contains('patrimonio liquido', na=False), 'Valor'].sum()
        estoque = dados_mes.loc[dados_mes['Conta'].str.contains('estoque para venda', na=False), 'Valor'].sum()
        imobilizado = dados_mes.loc[dados_mes['Conta'].str.lower().str.strip() == 'imobilizado', 'Valor'].sum()
     
        
    
        # Cálculos dos indicadores, verificando divisões por zero
        liquidez_corrente = ativo_circ / passivo_circ if passivo_circ > 0 else 0
        liquidez_seca = (ativo_circ - estoque) / passivo_circ if passivo_circ > 0 else 0
        liquidez_geral = ativo_circ  / (passivo_circ + passivo_nc) if (passivo_circ + passivo_nc) > 0 else 0
        endividamento = passivo_circ / (passivo_circ + passivo_nc) if (passivo_circ + passivo_nc) > 0 else 0
        imobilizado = imobilizado / patrimonio_liquido if patrimonio_liquido > 0 else 0
    
        indicadores.append({
            "Mês": mes,
            "Liquidez Corrente": liquidez_corrente,
            "Liquidez Seca": liquidez_seca,
            "Liquidez Geral": liquidez_geral,
            "Endividamento": endividamento,
            "Imobilização do PL": imobilizado
        })

    
    df_indicadores = pd.DataFrame(indicadores)

    # Cria uma lista com os meses na ordem correta
    mes_order = ['JULHO', 'AGOSTO']
    df_indicadores['Mês'] = pd.Categorical(df_indicadores['Mês'], categories=mes_order, ordered=True)
    df_indicadores = df_indicadores.sort_values('Mês')

    df_melted = pd.melt(
        df_indicadores,
        id_vars=["Mês"],
        value_vars=["Liquidez Corrente", "Liquidez Seca", "Liquidez Geral", "Endividamento", "Imobilização do PL"],
        var_name="Indicador",
        value_name="Valor"
    )

    
    
    # ---------------------------------------------
    # Visualização dos Gráficos e Tabelas
    # ---------------------------------------------
    
    st.subheader("Tabela de Indicadores Financeiros")
    st.dataframe(df_indicadores)
    
    st.write("---")
    
    st.subheader("Análise de Liquidez ao Longo do Tempo")
    fig_liquidez = px.line(
        df_indicadores, 
        x="Mês", 
        y=["Liquidez Corrente", "Liquidez Seca", "Liquidez Geral"],
        markers=True, 
        title="Indicadores de Liquidez por Mês"
    )
    st.plotly_chart(fig_liquidez, use_container_width=True)

    #Gráfico de Barras Agrupadas por Mês
    fig = px.bar(
        df_melted,
        x="Mês",
        y="Valor",
        color="Indicador",  # cada indicador recebe uma cor
        barmode="group",    # barras lado a lado
        title="Comparação de Indicadores por Mês"
    )

    #Mostra no ST
    st.plotly_chart(fig, use_container_width=True)

    # Cria um único gráfico de linha para todos os indicadores
    st.subheader("Evolução dos Indicadores Financeiros")
    fig = px.line(
        df_melted,
        x="Mês",
        y="Valor",
        color="Indicador",
        markers=True,
        title="Evolução Mensal de Todos os Indicadores"
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gráfico de barras para Endividamento vs. Imobilização
    st.write("---")
    st.subheader("Endividamento vs. Imobilização do Patrimônio Líquido")
    fig_comparativo = px.bar(
        df_indicadores,
        x="Mês",
        y=["Endividamento", "Imobilização do PL"],
        barmode="group",
        title="Comparativo de Endividamento e Imobilização por Mês",
        text_auto=True
    )
    st.plotly_chart(fig_comparativo, use_container_width=True)

    # Novo Gráfico de Barras para Liquidez
    # Cria um DataFrame apenas com os indicadores de liquidez
    df_liquidez = df_indicadores[['Mês', 'Liquidez Corrente', 'Liquidez Seca', 'Liquidez Geral']]
    
    # Derrete (melt) o DataFrame para agrupar os indicadores
    df_liquidez_melted = pd.melt(
        df_liquidez,
        id_vars=["Mês"],
        value_vars=["Liquidez Corrente", "Liquidez Seca", "Liquidez Geral"],
        var_name="Tipo de Liquidez",
        value_name="Valor"
    )

    # Cria o gráfico de barras agrupadas para comparar Julho e Agosto
    st.subheader("Comparativo de Liquidez: Julho vs. Agosto")
    fig_liquidez = px.bar(
        df_liquidez_melted,
        x="Mês",
        y="Valor",
        color="Tipo de Liquidez",
        barmode="group",
        title="Liquidez Corrente, Seca e Geral por Mês",
        text_auto=True
    )
    st.plotly_chart(fig_liquidez, use_container_width=True, key="liquidez_chart")

    # Filtra os dados apenas para o Ativo Circulante no mês de AGOSTO
    ativo_circulante_agosto = df[
        (df['Mês'] == 'AGOSTO') & 
        (df['Conta'].str.contains('caixa|banco|aplicação financeira|contas a receber|estoque para venda', na=False))
    ]
    
    # Cria o gráfico de pizza (donut) para o Ativo Circulante
    fig_pizza = px.pie(
        ativo_circulante_agosto, 
        values='Valor', 
        names='Conta', 
        title='Composição do Ativo Circulante - Agosto',
        hole=0.4
    )
    st.plotly_chart(fig_pizza, use_container_width=True, key="pizza_chart")



    

except FileNotFoundError:
    st.error(f"O arquivo {file_path} não foi encontrado. Certifique-se de que ele está na pasta 'data' dentro do seu projeto.")
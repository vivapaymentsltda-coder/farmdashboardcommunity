import pandas as pd
import streamlit as st
import plotly_express as px
from supabase import create_client, Client
import io

# --- Configurações Iniciais e Layout ---
st.set_page_config(layout="wide")

col1, col2 = st.columns([0.2, 0.9])

with col1:
    # Substitua o URL abaixo pelo link da sua logo
    st.image("data/logobelavista.png", width=500)

with col2:
    st.markdown("<div style='margin-top: 90px;'></div>", unsafe_allow_html=True)
    st.title("Fazenda Bela Vista Agropecuária")

st.write("---")

# --- Lógica de Conexão com o Supabase ---
@st.cache_resource
def init_supabase_client():
    """Inicializa e retorna o cliente Supabase."""
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except KeyError as e:
        st.error(f"Erro: Credenciais do Supabase não encontradas. Verifique seu arquivo .streamlit/secrets.toml. Detalhe: {e}")
        return None

supabase: Client = init_supabase_client()

# --- Lógica Principal: Leitura, Limpeza e Visualização dos Dados ---
@st.cache_data
def load_data_from_supabase():
    """Carrega os dados do balanço patrimonial do Supabase."""
    response = supabase.table("balancodre").select("*").execute()
    df = pd.DataFrame(response.data)
    if not df.empty and 'Valor' in df.columns:
        # Garante que a coluna 'Valor' seja numérica para evitar erros
        df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    return df

def save_data_to_supabase(data_to_save):
    """Salva os dados limpos no Supabase."""
    data_to_save_list = data_to_save.to_dict(orient='records')
    supabase.table("balancodre").insert(data_to_save_list).execute()
    
def delete_all_data():
    """Deleta todos os dados da tabela no Supabase."""
    supabase.table("balancodre").delete().neq("Mês", "INVALID").execute()
    st.cache_data.clear() # Limpa o cache do Streamlit
    st.rerun()

# --- Upload e Processamento de Dados ---
st.header("Upload e Processamento de Dados")
uploaded_file = st.file_uploader("Escolha um arquivo CSV...", type="csv")
mes_selecionado = st.selectbox("Selecione o mês do arquivo:", ("JULHO", "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"))

def processar_e_adicionar_dados():
    """Lê, limpa e adiciona os dados do arquivo CSV no Supabase."""
    if uploaded_file is not None:
        try:
            # Tenta ler o arquivo usando a codificação 'utf-8' (mais comum e moderna)
            df = pd.read_csv(io.StringIO(uploaded_file.getvalue().decode('utf-8')), sep=';', skiprows=3, header=None)
        except UnicodeDecodeError:
            # Se der erro, tenta ler o arquivo com 'latin-1' (usada em arquivos mais antigos)
            df = pd.read_csv(io.StringIO(uploaded_file.getvalue().decode('latin-1')), sep=';', skiprows=3, header=None)
        
        if df.shape[1] >= 3:
            # Pega as 2 colunas corretas (índices 1 e 2) e as renomeia
            df = df.iloc[:, [1, 2]]
            df.columns = ["Conta", "Valor"]

            # Limpeza e normalização da coluna 'Conta'
            df['Conta'] = df['Conta'].astype(str).str.strip().str.lower()
            df = df.dropna(subset=['Conta'])
            
            # Limpeza e conversão da coluna 'Valor'
            df['Valor'] = df['Valor'].astype(str).str.strip().str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
            df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
            df = df.dropna(subset=['Valor'])
            
            # Adiciona a coluna 'Mês' com o valor selecionado
            df['Mês'] = mes_selecionado
            
            # ** DEBUG: Exibe o DataFrame processado antes de enviar **
            st.write("Dados processados (antes do upload):")
            st.dataframe(df)

            # Checa se o DataFrame não está vazio antes de salvar
            if not df.empty:
                # Adiciona os novos dados ao Supabase
                save_data_to_supabase(df[['Conta', 'Valor', 'Mês']])
                st.success("Dados processados e adicionados ao Supabase com sucesso!")
                st.cache_data.clear() # Limpa o cache para recarregar os dados
                st.rerun()
            else:
                st.warning("Nenhum dado válido encontrado após o processamento. O arquivo pode estar vazio ou com formato incorreto.")

        else:
            st.error("Erro: O arquivo não tem as 3 colunas esperadas. Verifique a estrutura do CSV.")
    else:
        st.error("Por favor, envie um arquivo para processar.")

# Adiciona o botão que chama a função de processamento
if st.button("Processar e Adicionar Dados"):
    processar_e_adicionar_dados()

st.markdown("---")

# Botão para limpar todos os dados do banco de dados
if st.button("Limpar Dados Salvos"):
    delete_all_data()

try:
    if supabase is None:
        st.stop()

    df = load_data_from_supabase()

    if df.empty:
        st.warning("Nenhum dado encontrado no Supabase. Por favor, faça o upload de dados para visualizá-los.")
        st.stop()
    
    # Exibe o DataFrame carregado do Supabase
    st.header("Dados Salvos no Supabase")
    st.dataframe(df.drop_duplicates())

    # Normaliza a coluna "Conta"
    df['Conta'] = df['Conta'].astype(str).str.strip().str.lower()
    df = df.dropna(subset=['Conta'])

    # Converte a coluna 'Valor' para número
    df['Valor'] = pd.to_numeric(df['Valor'], errors='coerce')
    df = df.dropna(subset=['Valor'])

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
        imobilizado_calc = dados_mes.loc[dados_mes['Conta'].str.lower().str.strip() == 'imobilizado', 'Valor'].sum()
    
        # Cálculos dos indicadores, verificando divisões por zero
        liquidez_corrente = ativo_circ / passivo_circ if passivo_circ > 0 else 0
        liquidez_seca = (ativo_circ - estoque) / passivo_circ if passivo_circ > 0 else 0
        liquidez_geral = ativo_circ / (passivo_circ + passivo_nc) if (passivo_circ + passivo_nc) > 0 else 0
        endividamento = passivo_circ / (passivo_circ + passivo_nc) if (passivo_circ + passivo_nc) > 0 else 0
        imobilizacao = imobilizado_calc / patrimonio_liquido if patrimonio_liquido > 0 else 0
    
        indicadores.append({
            "Mês": mes,
            "Liquidez Corrente": liquidez_corrente,
            "Liquidez Seca": liquidez_seca,
            "Liquidez Geral": liquidez_geral,
            "Endividamento": endividamento,
            "Imobilização do PL": imobilizacao
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

    # Gráfico de Barras Agrupadas por Mês
    fig = px.bar(
        df_melted,
        x="Mês",
        y="Valor",
        color="Indicador",
        barmode="group",
        title="Comparação de Indicadores por Mês"
    )
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
    df_liquidez = df_indicadores[['Mês', 'Liquidez Corrente', 'Liquidez Seca', 'Liquidez Geral']]
    
    df_liquidez_melted = pd.melt(
        df_liquidez,
        id_vars=["Mês"],
        value_vars=["Liquidez Corrente", "Liquidez Seca", "Liquidez Geral"],
        var_name="Tipo de Liquidez",
        value_name="Valor"
    )

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

except Exception as e:
    st.error(f"Ocorreu um erro ao processar os dados: {e}. Verifique se a sua tabela 'balancodre' está configurada corretamente no Supabase e se o arquivo secrets.toml está no lugar certo.")

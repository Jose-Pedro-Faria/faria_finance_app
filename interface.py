import streamlit as st
import pandas as pd
import sqlite3
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Faria Finance Dashboard", layout="wide")

# Caminho dentro do contentor Docker
DB_PATH = '/app/finance_db.sqlite'

def carregar_dados():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    try:
        conn = sqlite3.connect(DB_PATH)
        query = "SELECT * FROM historico_financeiro"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao ler a base de dados: {e}")
        return pd.DataFrame()

# --- INTERFACE ---
st.title("📊 Faria Finance: Análise de Ativos")

df = carregar_dados()

if df.empty:
    st.warning("⚠️ A base de dados está vazia ou não foi encontrada. Corre o Coletor primeiro!")
else:
    # Sidebar - Filtros e Inputs
    st.sidebar.header("Configurações de Análise")
    tickers = sorted(df['ticker'].unique())
    ticker_selecionado = st.sidebar.selectbox("Escolha a Empresa", tickers)
    
    # Inputs para simulação
    st.sidebar.markdown("---")
    preco_atual = st.sidebar.number_input(f"Preço Atual de {ticker_selecionado}", min_value=0.01, value=10.0, step=0.01)
    yield_10y = st.sidebar.number_input("Taxa Sem Risco (Yield 10 anos %)", value=4.0) / 100

    # Filtrar a última leitura da empresa selecionada
    dados_recentes = df[df['ticker'] == ticker_selecionado].sort_values(by='data_extracao', ascending=False)
    
    if not dados_recentes.empty:
        dados = dados_recentes.iloc[0]

        # --- CÁLCULOS FINANCEIROS (TRATAMENTO DE ERROS) ---
        try:
            def to_f(val): # Função auxiliar para converter para float com segurança
                try: return float(val) if val is not None else 0.0
                except: return 0.0

            patrimonio = to_f(dados['patrimonio_liquido'])
            num_acoes = to_f(dados['num_acoes'])
            lucro = to_f(dados['lucro_liquido'])
            receita = to_f(dados['receita_total'])
            divida_total = to_f(dados['divida_total'])
            caixa = to_f(dados['caixa_equivalentes'])
            ebitda = to_f(dados['ebitda'])
            
            # Indicadores
            vpa = patrimonio / num_acoes if num_acoes > 0 else 0
            p_b = preco_atual / vpa if vpa > 0 else 0
            divida_liquida = divida_total - caixa
            ratio_divida = divida_liquida / ebitda if ebitda > 0 else 0
            roe = (lucro / patrimonio) * 100 if patrimonio > 0 else 0
            margem = (lucro / receita) * 100 if receita > 0 else 0
            lpa = lucro / num_acoes if num_acoes > 0 else 0
            
            # --- DASHBOARD METRICS ---
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("P/B (Preço/V.Patrimonial)", f"{p_b:.2f}")
                if 0 < p_b < 1: st.success("Abaixo do Valor Contabilístico")
                elif p_b > 3: st.warning("Pode estar sobrevalorizada")

            with col2:
                st.metric("Dívida Líquida / EBITDA", f"{ratio_divida:.2f}x")
                if ratio_divida < 2 and ratio_divida != 0: st.success("Dívida Saudável")
                elif ratio_divida > 4: st.error("Risco de Endividamento")

            with col3:
                st.metric("ROE (Retorno Cap. Próprio)", f"{roe:.2f}%")
                if roe > 15: st.success("Excelente Rentabilidade")

            with col4:
                st.metric("Margem Líquida", f"{margem:.2f}%")

            # --- ANÁLISE DE VALOR JUSTO (GRAHAM) ---
            st.markdown("---")
            st.subheader("💡 Avaliação por Graham (Valor Justo)")
            
            # Fórmula de Graham: Raiz de (22.5 * LPA * VPA)
            if lpa > 0 and vpa > 0:
                valor_justo = (22.5 * lpa * vpa) ** 0.5
                upside = ((valor_justo / preco_atual) - 1) * 100
                
                c1, c2 = st.columns(2)
                c1.write(f"**Valor Justo Estimado:** {valor_justo:.2f}")
                c1.write(f"**Preço Atual:** {preco_atual:.2f}")
                
                if valor_justo > preco_atual:
                    c2.metric("Potencial de Valorização", f"{upside:.2f}%", delta=f"{upside:.2f}%")
                    st.info("A ação apresenta uma margem de segurança segundo os critérios de Graham.")
                else:
                    c2.metric("Potencial de Valorização", f"{upside:.2f}%", delta=f"{upside:.2f}%", delta_color="inverse")
                    st.warning("A ação está a ser negociada acima do valor justo de Graham.")
            else:
                st.write("Dados insuficientes (LPA ou VPA negativos) para calcular o Valor Justo.")

            # --- TABELA DE HISTÓRICO ---
            st.markdown("---")
            st.subheader(f"📜 Histórico de Recolhas: {ticker_selecionado}")
            st.dataframe(dados_recentes[['data_extracao', 'ticker', 'lucro_liquido', 'patrimonio_liquido', 'divida_total']], use_container_width=True)

        except Exception as e:
            st.error(f"Erro nos cálculos: {e}")

# Rodapé informando o estado do sistema
st.sidebar.markdown("---")
st.sidebar.caption(f"Base de Dados: {DB_PATH}")
if st.sidebar.button("Atualizar Dados"):
    st.rerun()
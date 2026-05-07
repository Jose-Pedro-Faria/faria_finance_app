import yfinance as yf
import pandas as pd
import sqlite3
from datetime import datetime
import os
import time

# --- CONFIGURAÇÃO DE CAMINHOS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'finance_db.sqlite')
PASTA_LISTAS = os.path.join(BASE_DIR, 'listas')

# Deteta o dia da semana atual (ex: Monday, Tuesday...)
DIA_ATUAL = datetime.now().strftime('%A')
LISTA_HOJE = os.path.join(PASTA_LISTAS, f'{DIA_ATUAL}.txt')

def obter_dados(ticker):
    """Faz a extração bruta de dados do yfinance para um ticker específico"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] A recolher: {ticker}...")
    try:
        acao = yf.Ticker(ticker)
        
        # Extração dos Relatórios (DataFrames do Pandas)
        is_stmt = acao.financials      # Income Statement
        bs = acao.balance_sheet        # Balance Sheet
        cf = acao.cashflow             # Cash Flow
        info = acao.info               # Metadados e rácios prontos

# Função robusta para tentar vários nomes possíveis para o mesmo indicador
        def get_val(df, labels):
            if df is None or df.empty:
                return None
            # Se passarmos apenas uma string, convertemos para lista
            if isinstance(labels, str):
                labels = [labels]
            
            for label in labels:
                if label in df.index:
                    val = df.loc[label].iloc[0]
                    # Verifica se o valor é um número válido e não NaN
                    if pd.notnull(val):
                        return val
            return None

        dados = {
            'data_extracao': datetime.now().strftime('%Y-%m-%d'),
            'ticker': ticker,
            'dia_semana': DIA_ATUAL,
            
            # Dados de Mercado
            'num_acoes': info.get('sharesOutstanding'),
            'beta': info.get('beta'),
            
            # Income Statement
            'lucro_liquido': get_val(is_stmt, ['Net Income', 'Net Income Common Stockholders']),
            'lucro_operacional': get_val(is_stmt, ['Operating Income', 'Operating Profit']),
            'ebit': get_val(is_stmt, 'EBIT'),
            'ebt': get_val(is_stmt, ['Pretax Income', 'Income Before Tax']),
            'receita_total': info.get('totalRevenue') or get_val(is_stmt, ['Total Revenue', 'Operating Revenue']),
            'custo_receita': get_val(is_stmt, ['Cost Of Revenue', 'Total Expenses']),
            'juros_liquidos': get_val(is_stmt, ['Interest Expense', 'Net Interest Income']),
            'imposto_renda': get_val(is_stmt, ['Tax Provision', 'Income Tax Expense']),
            
            # Balance Sheet
            'patrimonio_liquido': get_val(bs, ['Stockholders Equity', 'Total Equity Gross Minority Interest']),
            'ativo_total': get_val(bs, 'Total Assets'),
            'ativo_circulante': get_val(bs, ['Total Current Assets', 'Current Assets']),
            'passivo_circulante': get_val(bs, ['Total Current Liabilities', 'Current Liabilities']),
            'divida_total': info.get('totalDebt') or get_val(bs, ['Total Debt', 'Long Term Debt']),
            'caixa_equivalentes': info.get('totalCash') or get_val(bs, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']),
            'inventory': get_val(bs, ['Inventory', 'Total Inventory']),
            'retained_earnings': get_val(bs, 'Retained Earnings'),
            
            # Cash Flow
            'fluxo_caixa_op': get_val(cf, ['Operating Cash Flow', 'Cash Flow From Continuing Operating Activities']),
            'capex': abs(get_val(cf, ['Capital Expenditure', 'Investing Cash Flow'])) if get_val(cf, ['Capital Expenditure', 'Investing Cash Flow']) else None,
            'dividendos_pagos': abs(get_val(cf, ['Cash Dividends Paid', 'Common Stock Dividend Paid'])) if get_val(cf, ['Cash Dividends Paid', 'Common Stock Dividend Paid']) else 0,
            'free_cash_flow': info.get('freeCashflow') or get_val(cf, 'Free Cash Flow')
        }

        # Cálculo de EBITDA (se não vier no info, somamos EBIT + Depreciação)
        ebitda = info.get('ebitda')
        if not ebitda:
            deprec = get_val(cf, 'Depreciation And Amortization')
            if dados['ebit'] is not None and deprec is not None:
                ebitda = dados['ebit'] + deprec
        dados['ebitda'] = ebitda

        return dados

    except Exception as e:
        print(f"   [!] Erro crítico em {ticker}: {e}")
        return None

def salvar_no_sqlite(lista_resultados):
    """Guarda a lista de dicionários na base de dados SQLite"""
    if not lista_resultados:
        print("\n[!] Sem dados válidos para guardar.")
        return
    
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.DataFrame(lista_resultados)
        # Grava na tabela 'historico_financeiro'. Se não existir, cria.
        df.to_sql('historico_financeiro', conn, if_exists='append', index=False)
        conn.close()
        print(f"\n[v] SUCESSO: {len(lista_resultados)} registos guardados em {DB_PATH}")
    except Exception as e:
        print(f"\n[!] Erro ao aceder à Base de Dados: {e}")

if __name__ == "__main__":
    # ... (código anterior)
    
    if not os.path.exists(LISTA_HOJE):
        print(f"Ficheiro {DIA_ATUAL}.txt não encontrado.")
    else:
        with open(LISTA_HOJE, 'r') as f:
            # Lemos o conteúdo todo do ficheiro
            conteudo = f.read()
            
            # 1. Substituímos vírgulas por quebras de linha
            # 2. Partimos o texto por linhas
            # 3. Limpamos espaços em branco
            tickers = [t.strip().upper() for t in conteudo.replace(',', '\n').split('\n') if t.strip()]
        
        if not tickers:
            print(f"Nenhum ticker encontrado em {DIA_ATUAL}.txt")
        else:
            print(f"Empresas detetadas: {tickers}") # Para confirmares no terminal
            resultados = []
            for t in tickers:
                res = obter_dados(t)
                if res:
                    resultados.append(res)
                time.sleep(2)
            
            salvar_no_sqlite(resultados)
    
    print(f"\nTerminado às {datetime.now().strftime('%H:%M:%S')}.\n")
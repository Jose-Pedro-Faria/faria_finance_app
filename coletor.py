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

        # Função auxiliar para extrair o valor mais recente (coluna 0) com segurança
        def get_val(df, label):
            if df is not None and not df.empty and label in df.index:
                return df.loc[label].iloc[0]
            return None

        # Dicionário com os campos das tuas imagens (Dados Brutos)
        dados = {
            'data_extracao': datetime.now().strftime('%Y-%m-%d'),
            'ticker': ticker,
            'dia_semana': DIA_ATUAL,
            
            # Dados de Mercado e Gerais
            'num_acoes': info.get('sharesOutstanding'),
            'beta': info.get('beta'),
            
            # Income Statement (Demonstração de Resultados)
            'lucro_liquido': get_val(is_stmt, 'Net Income'),
            'lucro_operacional': get_val(is_stmt, 'Operating Income'),
            'ebit': get_val(is_stmt, 'EBIT'),
            'ebt': get_val(is_stmt, 'Pretax Income'),
            'receita_total': info.get('totalRevenue') or get_val(is_stmt, 'Total Revenue'),
            'custo_receita': get_val(is_stmt, 'Cost Of Revenue'),
            'juros_liquidos': get_val(is_stmt, 'Interest Expense'),
            'imposto_renda': get_val(is_stmt, 'Tax Provision'),
            
            # Balance Sheet (Balanço Patrimonial)
            'patrimonio_liquido': get_val(bs, 'Stockholders Equity'),
            'ativo_total': get_val(bs, 'Total Assets'),
            'ativo_circulante': get_val(bs, 'Total Current Assets'),
            'passivo_circulante': get_val(bs, 'Total Current Liabilities'),
            'divida_total': info.get('totalDebt') or (get_val(bs, 'Total Debt') if 'Total Debt' in bs.index else None),
            'caixa_equivalentes': info.get('totalCash') or get_val(bs, 'Cash And Cash Equivalents'),
            'inventory': get_val(bs, 'Inventory'),
            'retained_earnings': get_val(bs, 'Retained Earnings'),
            
            # Cash Flow (Fluxo de Caixa)
            'fluxo_caixa_op': get_val(cf, 'Operating Cash Flow'),
            'capex': abs(get_val(cf, 'Capital Expenditure')) if get_val(cf, 'Capital Expenditure') else None,
            'dividendos_pagos': abs(get_val(cf, 'Cash Dividends Paid')) if get_val(cf, 'Cash Dividends Paid') else 0,
            'free_cash_flow': info.get('freeCashflow')
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
    print(f"{'='*40}")
    print(f"FARIA FINANCE APP - Execução de {DIA_ATUAL}")
    print(f"{'='*40}")
    
    if not os.path.exists(LISTA_HOJE):
        print(f"Aviso: O ficheiro '{DIA_ATUAL}.txt' não existe na pasta 'listas/'.")
        print("Crie o ficheiro para processar empresas hoje.")
    else:
        with open(LISTA_HOJE, 'r') as f:
            tickers = [line.strip().upper() for line in f if line.strip()]
        
        if not tickers:
            print(f"A lista '{DIA_ATUAL}.txt' está vazia.")
        else:
            resultados = []
            for t in tickers:
                res = obter_dados(t)
                if res:
                    resultados.append(res)
                
                # Pausa de 2 segundos para respeitar os servidores do Yahoo
                time.sleep(2)
            
            salvar_no_sqlite(resultados)
    
    print(f"\nTerminado às {datetime.now().strftime('%H:%M:%S')}.\n")
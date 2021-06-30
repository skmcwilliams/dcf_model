#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Mar  6 08:15:10 2021

@author: skm
"""
#import sys  
#sys.path.append('/Users/skm/Documents/Code/Python/Investing')
from utils import DCF, FinViz, get_10_year, get_historical_data,make_ohlc,make_comp_chart
from yahooquery import Ticker
import pandas as pd
from functools import reduce
import numpy as np
#from yahoofinancials import YahooFinancials as 
import plotly.express as px
import plotly.io as pio

"""
import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
"""


"""TRYING TO FIGURE OUT HOW TO SAVE INPUT AS VARIABLE FOR VALUATION AND PLOTTING

    
def generate_table(dataframe, max_rows=10):
    return html.Table([
        html.Thead(
            html.Tr([html.Th(col) for col in dataframe.columns])
        ),
        html.Tbody([
            html.Tr([
                html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))
        ])
    ])


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
server = app.server
"""

finviz=FinViz()
dcf = DCF()
fv = FinViz() 
q_bs_df = pd.DataFrame()
a_cf_df=pd.DataFrame()
pio.renderers.default = "browser"
done = False

while done is False:
    ticker = input("Ticker to perform DCF valuation:").upper()
    
    if ticker == 'XX':
        done=True
        break
        
    if ticker=='AAPL':
        key='demo'
    else:
        keys= ['3da65237f17cee96481b2251702509d1','3a1649ceeafc5888ec99181c59cb5f8b']
        key= np.random.choice(keys)
    
    
    # List of data we want to extract from Finviz Table
    finviz_df = fv.fundamentals(ticker)
    yf = Ticker(ticker)
    #gather historical data for ticker and indices data
    ticker_hist = get_historical_data(ticker,'5Y','1d',True)
    spy_df = get_historical_data('SPY','5Y','1d',True)
    dia_df = get_historical_data('DIA','5Y','1d',True)
    qqq_df = get_historical_data('QQQ','5Y','1d',True)
    data_frames = [ticker_hist,spy_df,dia_df,qqq_df]
    
    # marge indices df on ticker df
    joint_df = reduce(lambda  left,right: pd.merge(left,right,on=['date'],
                                            how='inner'), data_frames)  # pd.merge(hist[['date',f'{ticker}_close']],spy_df[['date','SPY_close'],],how='inner',on='date')
    joint_df[f'{ticker}_pct_change'] = joint_df[f'{ticker}_close'].pct_change().cumsum()
    joint_df['QQQ_pct_change'] = joint_df['QQQ_close'].pct_change().cumsum()
    joint_df['DIA_pct_change'] = joint_df['DIA_close'].pct_change().cumsum()
    joint_df['SPY_pct_change'] = joint_df['SPY_close'].pct_change().cumsum()
    
    
    #,plot ohlc and historical figs
    make_ohlc(ticker,ticker_hist)
    make_comp_chart(ticker,joint_df)
    
    
    #GET QUARTERLY BALANCE SHEET, CASH FLOW
    balance_sheet= yf.balance_sheet('q',False)
    cash_flow_df = yf.cash_flow('a',True).reset_index()
    cash_flow_df = cash_flow_df.drop_duplicates(subset='asOfDate')
    cash_flow_df['asOfDate'] = list(map(str,cash_flow_df['asOfDate']))
    cash_flow_df['year'] = cash_flow_df['asOfDate'].apply(lambda x: x.split('-')[0])
    cash_flow_df.insert(0,'Period',cash_flow_df['year']+'-'+cash_flow_df['periodType'])
    
    
    # PLOT HISTORICAL CASH FLOWS
    cf_fig = px.bar(data_frame=cash_flow_df,x='Period',y='FreeCashFlow',orientation='v',title=f'{ticker} Historical Free Cash Flows')
    cf_fig.show()
    
    # CREATE VARIABLES TO PRINT AT BEGINNING
    try:
        total_debt = balance_sheet.iloc[-1]['TotalDebt']
    except KeyError:
        total_debt=0
    
    try:
        debt_payment = np.nan_to_num(cash_flow_df.iloc[-1]['RepaymentOfDebt']*-1)
    except KeyError:
        debt_payment = 0
    
        
    try:
        cash_and_ST_investments = balance_sheet.iloc[-1]['CashAndCashEquivalents']
    except KeyError:
        cash_and_ST_investments = balance_sheet.iloc[-1]['CashCashEquivalentsAndShortTermInvestments']
    
    cash_flow = cash_flow_df.iloc[-1]['FreeCashFlow']
   
    try:
        quick_ratio = balance_sheet.iloc[-1]['CurrentAssets']/balance_sheet.iloc[-1]['CurrentLiabilities']
    except KeyError:
       quick_ratio = 0
       
    print(f'{ticker.upper()} Financial Overview')
    print(f"Free Cash Flow: {cash_flow}")
    print(f"Total Debt:{total_debt} ")
    print(f"Cash and ST Investments: {cash_and_ST_investments}")
    print(f"Quick Ratio: {round(quick_ratio,3)}")
    
    # SET DCF VARIABLES
    total_equity = yf.summary_detail[ticker]['marketCap']
    try:
        beta = yf.summary_detail[ticker]['beta']
    except KeyError:
        beta=2.0
    current_price = float(finviz_df['Price'])
    shares_outstanding = total_equity/current_price
    tax_rate = dcf.get_tax_rate(ticker,key)
    treasury = get_10_year()
    wacc = dcf.get_wacc(total_debt,total_equity,debt_payment,tax_rate,beta,treasury,ticker)
    
    # CALL STRATEGISK DCF VALUATION
    intrinsic_value = dcf.calculate_intrinsic_value(ticker,
                                                cash_flow_df, total_debt, 
                                                cash_and_ST_investments, 
                                                finviz_df, wacc,shares_outstanding)
       
    
    # CALL FINANCIAL MODEL PREP DCF VALUATION
    fmp_dcf = dcf.get_fmp_dcf(ticker,key)
    print(f"Estimated {ticker} Valuation Results:\Calculated Discounted Cash Flow Value: {round(intrinsic_value,2)}")
    print(f"Current Price: {round(current_price,2)}")
    print(f"Margin: {round((1-current_price/intrinsic_value)*100,2)}%")
    
    try:
        print(f"\nFinancial Modeling Prep {ticker} DCF Target Price: {round(fmp_dcf[0]['dcf'],2)}")
    except IndexError:
        print(f"\nNo {ticker} valuation by Financial Modeling Prep")
    
    try:
        print(f"\nFinViz {ticker} Target Price: {float(finviz_df['Target Price'])}\n")
    except ValueError:
        print('No FinViz Valuation Available')
    
    corr_5 = joint_df.corr().at['SPY_close',f'{ticker}_close']
    corr_1 = joint_df[-365:].corr().at['SPY_close',f'{ticker}_close']
    corr_90 = joint_df[-90:].corr().at['SPY_close',f'{ticker}_close']
    corr_30 = joint_df[-30:].corr().at['SPY_close',f'{ticker}_close']
    corrs = [corr_5,corr_1,corr_90,corr_30]
    periods = ['5Y','1Y','90Day','30Day']
    zipped = zip(periods,corrs)
    print(f'Correlation to S&P500 Over Time: {[i for i in zipped]}')
    
    
    yahoo_ratings = yf.recommendation_trend.reset_index()
    yahoo_ratings.rename(columns={'period':'Period'},inplace=True)
    yahoo_ratings.at[0,'Period'] = 'Current'
    yahoo_ratings.at[1,'Period'] = '1 Month Back' 
    yahoo_ratings.at[2,'Period'] = '2 Months Back'
    yahoo_ratings.at[3,'Period'] = '3 Months Back' 
    ratings_fig = px.bar(yahoo_ratings,x='Period',y=['strongBuy','buy','hold','sell','strongSell'],
                         title=f'{ticker} Yahoo Recommendation Trends')
    ratings_fig.show()
    
    finviz_ratings = fv.get_ratings(ticker)
    finviz_ratings = finviz_ratings.drop_duplicates(subset='firm') #ensure latest rating by each firm
    finviz_ratings = finviz_ratings[finviz_ratings['date'].str.endswith('21')] #only recent ratings
    fv_fig = px.histogram(finviz_ratings, x="rating",title=f'{ticker} 2021 Ratings per FinViz')
    fv_fig.show()
    #print(f'Recent IB Ratings:\n{finviz_ratings}')


#if __name__=='__main__':
 #   app.run_server(debug=True)

    
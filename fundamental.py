import streamlit as st
import requests
import config
import json
import pandas as pd
from iex import stocks
from datetime import datetime, timedelta
from alpha_vantage.fundamentaldata import FundamentalData
from alpha_vantage.timeseries import TimeSeries
from fbprophet import Prophet
from fbprophet.plot import plot_plotly
import yfinance as yf
from plotly import graph_objs as go




def main():

    st.title("Fundamental Dashboard")
    symbol=st.sidebar.text_input("TICKER")
    if symbol=="":
        st.write(symbol)
        st.info("You have not selected any ticker please input a ticker")
        st.stop()

    screen=st.sidebar.selectbox("MENU",["Forecasting","intraday-price","overview","News",])#Ownership","Technicals","Balance sheet","Income statement","fundamental",
    st.title(screen)

    stock=stocks(config.key,symbol)

    stock1=stocks(config.alpha_key,symbol)


    if screen=="intraday-price":
        
        data=stock1.get_intraday()
        # st.write(pd.DataFrame(data['Time Series (5min)']).T.columns)
        st.table(pd.DataFrame(data['Time Series (5min)']).T)
        st.line_chart(pd.DataFrame(data['Time Series (5min)']).T.iloc[ : ,3])

    if screen=="Income statement":
        data=stock1.get_income_statement()
        data1=pd.DataFrame(data['annualReports'])
        # data1.reset_index(inplace=True)
        # data1.columns()
        st.table(data1.T)

    if screen=="Forecasting":
        stock=symbol
        n_years=st.slider("Years of prediction:",1,4)
        period=n_years*365
        start="2015-01-01"
        to=datetime.today().strftime("%Y-%m-%d")

        def load_ticker(symbol):
            data=yf.download(symbol,start,to)
            data.reset_index(inplace=True)
            return data

        def plot_data():
            fig=go.Figure()
            fig.add_trace(go.Scatter(x=data['Date'],y=data['Open'],name="stock_open"))
            fig.add_trace(go.Scatter(x=data['Date'],y=data['Close'],name="stock_close"))
            fig.layout.update(title_text="Time Series data",xaxis_rangeslider_visible=True)
            st.plotly_chart(fig)
        
        st.subheader("Time series data")
        data=load_ticker(symbol)
        st.write(data.tail())

        plot_data()
        #forecasting
        df_train=data[['Date','Close']]
        df_train.Date=df_train.Date.dt.strftime('%m/%d/%Y')
        df_train=df_train.rename(columns={'Date':'ds','Close':'y'})
        m=Prophet()
        m.fit(df_train)
        future=m.make_future_dataframe(periods=period)
        forecast=m.predict(future)

        st.subheader("forecast data")
        st.write(forecast.tail())

        fig1=plot_plotly(m,forecast)
        st.plotly_chart(fig1)

        st.write("forecast componenets")
        fig2=m.plot_components(forecast)
        st.write(fig2)


    if screen=="overview":
        logo=stock.get_logo()
        info=stock.get_company_info()
        

        # url= f"https://cloud.iexapis.com/stable/stock/{symbol}/company?token={config.key}"
        # r=requests.get(url)
        # response=r.json()
        # st.write()

        col1,col2=st.columns([1,3])
        with col1:
            st.image(logo["url"])
        
        with col2:
        
            st.title(info["companyName"])

            st.subheader("Description")
            st.write(info["description"])

            st.subheader("exchange")
            st.write(info["exchange"])
            
            st.subheader("industry")
            st.write(info["industry"])
            
            st.subheader("website")
            st.write(info["website"])
            
            st.subheader("securityName")
            st.write(info["securityName"])
            
            st.subheader("employees")
            st.write(info["employees"])
            
            st.subheader("address")
            st.write(info["address"])
            
            st.subheader("phone")
            st.write(info["phone"])
            
            st.subheader("country")
            st.write(info["country"])

            st.subheader("zip")
            st.write(info["zip"])




    elif screen=="fundamental":

        get_stats=stock.get_stats()
        stats=json.loads(get_stats)
        st.header('Ratios')

        col1, col2 = st.columns(2)
        with col1:
            st.subheader('P/E')
            st.write(stats['peRatio'])
            st.subheader('Forward P/E')
            st.write(stats['forwardPERatio'])
            st.subheader('PEG Ratio')
            st.write(stats['pegRatio'])
            st.subheader('Price to Sales')
            st.write(stats['priceToSales'])
            st.subheader('Price to Book')
            st.write(stats['priceToBook'])
        with col2:
            st.subheader('Revenue')
            st.write(stats['revenue'])
            st.subheader('Cash')
            st.write(stats['totalCash'])
            st.subheader('Debt')
            st.write(stats['currentDebt'])
            st.subheader('200 Day Moving Average')
            st.write(stats['day200MovingAvg'])
            st.subheader('50 Day Moving Average')
            st.write(stats['day50MovingAvg'])


    elif screen=="News":

        news=stock.get_news()
        for article in news:
            st.subheader(article['headline'])
            dt = datetime.utcfromtimestamp(article['datetime']/1000).isoformat()
            st.write(f"Posted by {article['source']} at {dt}")
            st.write(article['url'])
            st.write(article['summary'])
            st.image(article['image'])

    elif screen=="Balance sheet":
        data=stock.get_balance_sheet()
        data1=pd.DataFrame(data['annualReports'])
        st.table(data1.T)

if __name__ == '__main__':
    main()





















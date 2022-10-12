import requests

class stocks:

    def __init__(self,token,symbol):
        self.base_url="https://cloud.iexapis.com/stable/"
        self.base_url2="https://www.alphavantage.co/query"
        self.base_url3="sam"
        self.symbol=symbol
        self.token=token
    
    def get_logo(self):
        url=f"{self.base_url}/stock/{self.symbol}/logo?token={self.token}"
        r=requests.get(url)
        response=r.json()
        return response

    def get_company_info(self):
        url=f"{self.base_url}/stock/{self.symbol}/company?token={self.token}"
        r=requests.get(url)
        response=r.json()
        return response

    def get_stats(self):
        url = f"{self.base_url}/stock/{self.symbol}/advanced-stats?token={self.token}"
        r = requests.get(url)
        response=r.json()
        return response

    # def get_balance_sheet(self):
    #     url=f"{self.base_url2}?function=BALANCE_SHEET&symbol={self.symbol}&apikey={self.token}"
    #     r=requests.get(url)
    #     response=r.json()
    #     return response
    
    def get_balance_sheet(self):
        url=f"{self.base_url}stock/{self.symbol}/balance-sheet?token={self.token}"
        r=requests.get(url)
        response=r.json()
        return response
    
    def get_news(self,last=10):
        url=f"{self.base_url}/stock/{self.symbol}/news/last/{last}?token={self.token}"
        r=requests.get(url)
        response=r.json()
        return response

    def get_intraday(self):
        url=f"{self.base_url2}?function=TIME_SERIES_INTRADAY&symbol={self.symbol}&interval=5min&apikey={self.token}"
        r=requests.get(url)
        response=r.json()
        return response

    def get_income_statement(self):
        url=f'{self.base_url2}?function=INCOME_STATEMENT&symbol={self.symbol}&apikey={self.token}'
        r=requests.get(url)
        response=r.json()
        return response
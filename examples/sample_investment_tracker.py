from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from investment_tracker.models import Base, Stock, User

engine = create_engine("sqlite:///:memory:")
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()
# creates all tables
Base.metadata.create_all(engine)

"""Sample code on how to use the investment_tracker framework"""
# Creates at stock with a the 'BRK.A' ticker symbol
BRK = Stock(ticker="BRK.A")

# sets the price of BRK stock to 20 units
BRK.set_price(20, day=date.today())
session.add(BRK)

# Creating a user with the username "buffett" with an initial available funds value of 100
buffett = User(username="buffett", available_funds=100)

# Creates a stock transaction for two BRK.A stocks. The stock parameter can be a Stock object or the ticker string
buffett.order(BRK, quantity=2, session=session)
session.add(buffett)
session.commit()

# Creates a stock transaction to sell a 'BRK.A' stock
buffett.order(stock="BRK.A", quantity=-1, session=session)
session.add(buffett)
session.commit()

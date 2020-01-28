"""Main module."""
import logging
import logging.handlers
import os
from datetime import date
from sqlalchemy import func
from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Float,
    Date,
    # Numeric,
    # ForeignKeyConstraint,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import NoInspectionAvailable

# creates logs file if not exists
try:
    os.makedirs("logs")
except OSError:
    pass

LOG_FILE_PATH = "logs/investment_tracker.log"
investment_tracker_logger = logging.getLogger(__name__)
investment_tracker_logger.setLevel(logging.INFO)
handler = logging.FileHandler(LOG_FILE_PATH, mode="w")
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(filename)s:%(lineno)s] %(message)s")
handler.setFormatter(formatter)
investment_tracker_logger.addHandler(handler)

Base = declarative_base()

# Creates an in memory database using sqlite3
engine = create_engine("sqlite:///:memory:", echo=True)

Session = sessionmaker()

Session.configure(bind=engine)

session = Session()


class ModelReprMixin(object):
    """Automatic __repr__ overload for each class"""

    def __repr__(self):
        model = type(self)
        try:
            table = inspect(model)
            # Builds comma separated list of existing properties of the class instance
            repr_properties = ", ".join(
                [f"{column.name}={getattr(self, column.name)}" for column in table.c if getattr(self, column.name)]
            )
            return f"<{model.__name__}({repr_properties})>"
        except (NoInspectionAvailable, AttributeError, TypeError) as e:
            investment_tracker_logger.warning(e)
            return super().__repr__()


class ModelLoggingMixin(object):
    """Logs creation of each object"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        investment_tracker_logger.debug(f"{self} created")


class User(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores user information, such as username and available funds. Users can perform certain actions with stocks.
    Table name: users

    Keyword arguments:
    id -- primary key of the user table
    username -- unique name used in place of User.id to identify a user
    available_funds -- amount of money available to buy stocks in cents (sqlite does not support decimal natively)

    Methods:
    order -- initiates an order given a ticker symbol, type of order, and number of shares
    buy -- initiates an order with type='buy' as a parameter
    sell -- initiates an order with type='sell' as a parameter
    """

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(250), unique=True, nullable=False)
    available_funds = Column(Integer, nullable=False, default=0)
    # All transactions made by the user
    transactions = relationship("Transaction", back_populates="user")

    def stock_quantity(self, ticker):
        stock = session.query(Stock).filter(Stock.ticker == ticker).one()
        stocks_bought = (
            session.query(func.sum(Transaction.quantity))
            .filter(Transaction.user_id == self.id, Transaction.stock_id == stock.id, Transaction.kind == "buy")
            .scalar()
            or 0
        )
        stocks_sold = (
            session.query(func.sum(Transaction.quantity))
            .filter(Transaction.user_id == self.id, Transaction.stock_id == stock.id, Transaction.kind == "sell")
            .scalar()
            or 0
        )

        return stocks_bought - stocks_sold

    def order(self, ticker, kind, quantity, price=None, day=date.today()):
        """User initiates an order of a stock"""
        # TODO add api call if ticker does not exist in db
        order_modifier = {"buy": 1, "sell": -1}
        if kind not in order_modifier:
            raise ValueError(f"{kind} order type not recognized.")
        # searches database for a stock if exists
        stock = session.query(Stock).filter(Stock.ticker == ticker).one()
        if price is None:
            price = session.query(Price).filter(Price.stock_id == stock.id, Price.day == day).one()
        investment_tracker_logger.debug(f"Price fetched for buy order: {price}")
        # change sign of quantity based on order type
        try:
            # Reduce available funds by price
            final_price = self.available_funds - order_modifier[kind] * price.price
            if final_price < 0:
                raise ValueError("Available price cannot become negative.")
            self.available_funds = final_price
        except ValueError as e:
            investment_tracker_logger.error(e, exc_info=True)
            session.rollback()
            return
        finally:
            investment_tracker_logger.debug(f"User final state: {self}")
        try:
            self.transactions.append(Transaction(stock_id=stock.id, quantity=quantity, kind=kind, stock_price=price))
            investment_tracker_logger.info(f"{self.transactions[-1]} order created.")
        except IndexError:
            logging.error(
                f"{self} cannot find most recently appended entry for transaction relationship", exc_info=True
            )

    def buy(self, ticker, quantity, price=None, day=date.today()):
        """buy order"""
        self.order(ticker, "buy", quantity, price=price, day=day)

    def sell(self, ticker, quantity, price=None, day=date.today()):
        """sell order"""
        stock_quantity_held = self.stock_quantity(ticker)
        if stock_quantity_held - quantity >= 0:
            self.order(ticker, "sell", quantity, price=price, day=day)
        else:
            raise ValueError(f"{quantity} of {ticker} to be sold, but only {stock_quantity_held} of {ticker} available")


class Stock(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores stock information, such as its ticker symbol

    Keyword arguments:
    id -- primary key of the stock table
    ticker -- stock symbol ie AAPL, MSFT

    Methods:
    set_price -- sets the price of a stock for a given day in the prices table
    get_price -- gets price of stock from the price table
    """

    __tablename__ = "stocks"
    id = Column(Integer, primary_key=True)
    ticker = Column(String(8), unique=True, nullable=False)

    # List of prices of the stock
    price = relationship(
        "Price",
        back_populates="ticker",
        collection_class=attribute_mapped_collection("day"),  # dictionary mapped by day
    )

    # def __repr__(self):
    #     return f"<Stock(ticker={self.ticker})>"

    def set_price(self, price, day=date.today()):
        """
        sets price of stock in cents on a given day

        Parameters
        ----------
        price
        day

        Returns
        -------

        """
        self.price[day] = Price(stock_id=self.id, day=day, price=price)

    def get_price(self, query_date=date.today()):
        # TODO api call if price does not exist
        return self.price[query_date]


class Price(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores the price information of a stock for one day

    Keyword arguments:
    stock_id -- id of the stock, compound primary key with day
    day -- day of the price of the stock, compound primary key with stock_id
    price -- price of the stock on the given day in cents (sqlite does not support decimal)
    """

    __tablename__ = "prices"
    stock_id = Column(Integer, ForeignKey("stocks.id"), primary_key=True)
    day = Column(Date, primary_key=True)
    price = Column(Integer, nullable=False)

    # all transactions in a certain day
    transactions = relationship("Transaction", back_populates="stock_price")

    # Ticker of the stock
    ticker = relationship("Stock", back_populates="price", uselist=False)


class Transaction(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores transaction information. Transactions can be created with the order method on the User class.

    Keyword arguments:
    id -- Primary key of the transactions table
    user_id -- id of the user who is executing a transaction
    stock_id -- id of the stock in the order
    day -- date of the transaction
    quantity -- amount of stock being bought or sold
    kind -- type of transaction. Either buy, sell, or transfer (of funds)
    transfer_amt -- amount of money transferred when funds are being transferred
    total_price -- total transaction cost in cents (sqlite does not support decimal)
    """

    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    stock_id = Column(Integer, ForeignKey("stocks.id"))
    day = Column(Date, ForeignKey("prices.day"), default=date.today())
    quantity = Column(Float)
    kind = Column(String(8), nullable=False)  # Buy, sell, or transfer
    transfer_amt = Column(Integer)

    # The price of the stock on the transaction day
    stock_price = relationship(
        Price,
        primaryjoin="and_(Transaction.stock_id==Price.stock_id, Transaction.day==Price.day)",
        back_populates="transactions",
        uselist=False,
    )

    # user who initiated the transaction
    user = relationship(User, back_populates="transactions", uselist=False)

    @property
    def total_price(self):
        # SELECT t.quantity * p.price from transactions t join price p on (t.stock_id = p.stock_id AND t.day = d.day)
        q = self.quantity
        return int(q * self.stock_price.price) if q else self.transfer_amt


# creates all tables
Base.metadata.create_all(engine)

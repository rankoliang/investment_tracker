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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
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
handler = logging.FileHandler(LOG_FILE_PATH, mode="a")
formatter = logging.Formatter("%(asctime)s %(levelname)s [%(filename)s:%(lineno)s] %(message)s")
handler.setFormatter(formatter)
investment_tracker_logger.addHandler(handler)

Base = declarative_base()


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


class InsufficientQuantity(ValueError):
    pass


class InsufficientFunds(ValueError):
    pass


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

    def stock_quantity(self, ticker, session=None):
        stock = session.query(Stock).filter(Stock.ticker == ticker).one()
        stocks_available = (
            session.query(func.sum(TransactionStock.quantity))
            .join(Transaction, TransactionStock.transaction_id == Transaction.id)
            .filter(Transaction.user_id == self.id, TransactionStock.stock_id == stock.id, Transaction.kind == "stock")
            .scalar()
        ) or 0

        return stocks_available

    def order(self, ticker, quantity, price=None, day=date.today(), session=None):
        """User initiates an order of a stock"""
        # TODO add api call if ticker does not exist in db
        # searches database for a stock if exists
        stock_quantity_held = self.stock_quantity(ticker, session=session)
        if stock_quantity_held + quantity < 0:
            raise InsufficientQuantity(
                f"{-1 * quantity} of {ticker} to be sold, but only {stock_quantity_held} of {ticker} available"
            )

        stock = session.query(Stock).filter(Stock.ticker == ticker).one()
        if price is None:
            price = session.query(Price).filter(Price.stock_id == stock.id, Price.day == day).one()
        investment_tracker_logger.debug(f"Price fetched for buy order: {price}")
        # change sign of quantity based on order type
        try:
            # Reduce available funds by price
            final_price = self.available_funds - quantity * price.price
            if final_price < 0:
                raise InsufficientFunds("Available price cannot become negative.")
            self.available_funds = final_price
        except ValueError as e:
            investment_tracker_logger.error(e, exc_info=True)
            session.rollback()
            raise e
        finally:
            investment_tracker_logger.debug(f"User final state: {self}")
        try:
            self.transactions.append(Transaction(day=day).stock_order(stock_id=stock.id, quantity=quantity))
            investment_tracker_logger.info(f"{self.transactions[-1]} order created.")
        except IndexError:
            logging.error(
                f"{self} cannot find most recently appended entry for transaction relationship", exc_info=True,
            )


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
        """
        returns the price value of the stock on a given day
        """
        # TODO api call if price does not exist
        return self.price[query_date].price


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
    day = Column(Date, primary_key=True, default=date.today())
    price = Column(Integer, nullable=False)

    # Ticker of the stock
    ticker = relationship("Stock", back_populates="price", uselist=False)

    transaction_details = relationship(
        "TransactionStock",
        secondary="transactions",
        primaryjoin="TransactionStock.transaction_id==Transaction.id",
        secondaryjoin="and_(TransactionStock.stock_id==Price.stock_id, Price.day==Transaction.day)",
        back_populates="stock_price",
        uselist=False,
    )


class Transaction(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores transaction information. Transactions can be created with the order method on the User class.

    Keyword arguments:
    id -- Primary key of the transactions table
    user_id -- id of the user who is executing a transaction
    day -- date of the transaction
    kind -- type of transaction. Either stock or transfer (of funds)
    """

    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    day = Column(Date, ForeignKey("prices.day"), default=date.today())
    kind = Column(String(8), nullable=False)  # stock or transfer

    # user who initiated the transaction
    user = relationship(User, back_populates="transactions", uselist=False)

    stock_order_info = relationship("TransactionStock", back_populates="transaction", uselist=False)

    transfer_info = relationship("TransactionTransfer", back_populates="transaction", uselist=False)

    def stock_order(self, stock_id, quantity):
        self.stock_order_info = TransactionStock(stock_id=stock_id, quantity=quantity)
        self.kind = "stock"
        return self

    def fund_transfer(self, transfer_amount):
        self.transfer_info = TransactionTransfer(transfer_amount=transfer_amount)
        self.kind = "transfer"
        return self


class TransactionStock(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores stock information associated with transactions

    Keyword arguments:
    transaction_id -- id of the associated transaction
    stock_id -- id of the transaction being stocks_sold
    quantity -- amount of stock being bought or sold; positive = buy, negative = sell
    """

    __tablename__ = "transaction_stock"
    transaction_id = Column(Integer, ForeignKey("transactions.id"), primary_key=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), primary_key=True)
    quantity = Column(Float)

    transaction = relationship("Transaction", back_populates="stock_order_info", uselist=False)

    # The price of the stock on the transaction day
    stock_price = relationship(
        Price,
        secondary="transactions",
        primaryjoin="TransactionStock.transaction_id==Transaction.id",
        secondaryjoin="and_(TransactionStock.stock_id==Price.stock_id, Price.day==Transaction.day)",
        back_populates="transaction_details",
        uselist=False,
    )

    stock = relationship("Stock")


class TransactionTransfer(ModelLoggingMixin, ModelReprMixin, Base):
    """
    Stores information about transfer of funds to and from accounts

    Keyword arguments:
    transaction_id -- id of the associated transactions
    transfer_amount -- amount of money transferred to or from an account; positive = deposit; negative = withdrawal
    """

    __tablename__ = "transaction_transfer"
    transaction_id = Column(Integer, ForeignKey("transactions.id"), primary_key=True)
    transfer_amount = Column(Integer)

    transaction = relationship("Transaction", back_populates="transfer_info", uselist=False)

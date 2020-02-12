#!/usr/bin/env python

"""Tests for `investment_tracker` package."""

import pytest
from logging import getLogger, DEBUG
from click.testing import CliRunner
from investment_tracker import cli
from investment_tracker.models import Stock, User, Price, Transaction, Base, ModelReprMixin
from investment_tracker.exceptions import InsufficientFunds, InsufficientQuantity
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import NoInspectionAvailable


# Creates an in memory database using sqlite3
engine = create_engine("sqlite:///:memory:")
Session = sessionmaker()
Session.configure(bind=engine)


@pytest.fixture(scope="function")
def session():
    session = Session()
    # creates all tables
    Base.metadata.create_all(engine)
    try:
        yield session
    finally:
        session.close()
        # drops tables when each test is finished
        Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def sample_user():
    return User(id=31, username="sample_user", available_funds=1000)


@pytest.fixture(scope="function")
def sample_stock():
    return Stock(id=41, ticker="sample_stock")


@pytest.fixture(scope="function")
def sample_price():
    return Price(stock_id=41, price=10, day=date.today())


@pytest.fixture(scope="function")
def sample_transaction():
    return Transaction(id=59, day=date.today())


@pytest.fixture(scope="function")
def sample_stock_purchase():
    return Transaction(id=26, user_id=31, day=date.today()).stock_order(stock_id=41, quantity=1)


@pytest.fixture(scope="function")
def sample_transfer():
    return Transaction(id=53, day=date.today()).fund_transfer(transfer_amount=20)


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "investment_tracker.cli.main" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help  Show this message and exit." in help_result.output


def test_investment_tracker(session):
    """Sample code on how to use the investment_tracker framework"""
    test_investment_tracker_logger = getLogger("investment_tracker.investment_tracker")
    test_investment_tracker_logger.setLevel(DEBUG)

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

    assert buffett.stock_quantity(BRK, session=session) == 2
    assert buffett.available_funds == 100 - BRK.price * 2

    # Creates a stock transaction to sell a 'BRK.A' stock
    buffett.order(stock="BRK.A", quantity=-1, session=session)
    session.add(buffett)
    session.commit()
    assert buffett.stock_quantity(stock="BRK.A", session=session) == 1
    assert buffett.available_funds == 100 - BRK.price
    queried_user = session.query(User).first()
    assert queried_user is buffett
    qu_transaction = queried_user.transactions[0]
    assert qu_transaction.stock_order_info.stock.price == 20


class TestUser:
    @pytest.fixture(scope="function")
    def order_session(self, sample_user, sample_stock, sample_price, session):
        session.add(sample_stock)
        session.add(sample_price)
        session.add(sample_user)
        session.commit()
        return session

    def test_username(self, sample_user):
        assert sample_user.username == "sample_user"

    def test_available_funds(self, sample_user):
        assert sample_user.available_funds == 1000

    @pytest.mark.parametrize("available_funds,order_quantity", [(1000, 3), (1000, -3), (1000, 0)])
    def test_orders(self, order_session, order_quantity, available_funds):
        sample_customer = order_session.query(User).one()
        sample_customer.available_funds = available_funds
        try:
            sample_customer.order("sample_stock", order_quantity, session=order_session)
        except ValueError:
            assert sample_customer.stock_quantity("sample_stock", session=order_session) >= 0
            return
        ordered_stock = order_session.query(Stock).one()
        order_session.commit()
        order_transaction = sample_customer.transactions[0]
        assert len(sample_customer.transactions) == 1
        assert order_transaction.kind == "stock"
        assert order_transaction.stock_order_info.quantity == order_quantity
        assert order_transaction.stock_order_info.stock_id == ordered_stock.id
        assert sample_customer.stock_quantity("sample_stock", session=order_session) == order_quantity
        assert sample_customer.available_funds == 1000 - order_quantity * ordered_stock.price

    @pytest.mark.parametrize(
        "available_funds,order_quantities",
        [
            (1000, [5, -3]),
            (500, [7, 2]),
            (600, [4, 0, 6, -10]),
            (1000, [-4, 0]),
            (1000, [5, -7]),
            (40, [5]),
            (600, [4, 0, 6, -11]),
        ],
    )
    def test_multiple_orders(self, order_session, order_quantities, available_funds):
        sample_customer = order_session.query(User).one()
        sample_customer.available_funds = available_funds
        ordered_stock = order_session.query(Stock).one()
        transaction_count = 0
        for quantity in order_quantities:
            try:
                sample_customer.order("sample_stock", quantity, session=order_session)
                order_session.commit()
                order_transaction = sample_customer.transactions[transaction_count]
                transaction_count += 1
                assert len(sample_customer.transactions) == transaction_count
                assert order_transaction.stock_order_info.stock_id == ordered_stock.id
                # expected_available_funds
                available_funds -= quantity * ordered_stock.price
                assert sample_customer.available_funds == available_funds
            except InsufficientQuantity:
                assert sample_customer.stock_quantity("sample_stock", session=order_session) >= 0
                expected_quantity = 0
                for q in order_quantities:
                    if expected_quantity + q >= 0:
                        expected_quantity += q
                    else:
                        break
                assert sample_customer.stock_quantity("sample_stock", session=order_session) == expected_quantity
                return
            except InsufficientFunds:
                assert sample_customer.available_funds >= 0
                return
        assert sum(order_quantities) == sample_customer.stock_quantity(ordered_stock.ticker, session=order_session)


class TestStock:
    def test_ticker(self, sample_stock):
        assert sample_stock.ticker == "sample_stock"


class TestPrice:
    def test_price(self, sample_price):
        assert sample_price.price == 10

    def test_day(self, sample_price):
        assert sample_price.day == date.today()

    def test_default_day(self, session):
        sample_price_default = Price(stock_id=41, price=10)
        session.add(sample_price_default)
        session.commit()
        assert sample_price_default.day == date.today()


class TestTransaction:
    def test_day(self, sample_transaction):
        assert sample_transaction.day == date.today()

    def test_stock_purchase(self, sample_stock_purchase):
        assert sample_stock_purchase.id == 26
        assert sample_stock_purchase.id != 0
        assert sample_stock_purchase.stock_order_info.quantity == 1
        assert sample_stock_purchase.stock_order_info.stock_id == 41
        assert sample_stock_purchase.kind == "stock"

    def test_fund_transfer(self, sample_transfer):
        assert sample_transfer.id == 53
        assert sample_transfer.id != 0
        assert sample_transfer.transfer_info.transfer_amount == 20
        assert sample_transfer.kind == "transfer"

    # @pytest.mark.skip
    def test_stock_purchase_backref(self, sample_stock_purchase, sample_stock, sample_price, sample_user, session):
        session.add(sample_stock_purchase)
        session.add(sample_stock)
        session.add(sample_price)
        session.add(sample_user)
        session.commit()
        sample_stock_info = sample_stock_purchase.stock_order_info
        assert sample_stock_info.transaction.id == 26
        assert sample_stock.id == 41
        assert sample_stock_info.stock.ticker == "sample_stock"


class TestModelReprMixin:
    class CannotBeInspected(ModelReprMixin):
        def __init__(self):
            pass

    def test_catch_error(self):
        tbrc = self.CannotBeInspected()
        try:
            inspect(tbrc)
        except (NoInspectionAvailable, AttributeError, TypeError):
            assert repr(tbrc)
            return
        assert False

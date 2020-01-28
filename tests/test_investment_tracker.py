#!/usr/bin/env python

"""Tests for `investment_tracker` package."""

import pytest
from logging import getLogger, DEBUG, WARNING, INFO, ERROR, CRITICAL
from click.testing import CliRunner
from investment_tracker.investment_tracker import session, Stock, User, Price, Transaction
from investment_tracker import cli
from datetime import date


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


def test_content(response):
    """Sample pytest test function with the pytest fixture as an argument."""
    # from bs4 import BeautifulSoup
    # assert 'GitHub' in BeautifulSoup(response.content).title.string


def test_command_line_interface():
    """Test the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli.main)
    assert result.exit_code == 0
    assert "investment_tracker.cli.main" in result.output
    help_result = runner.invoke(cli.main, ["--help"])
    assert help_result.exit_code == 0
    assert "--help  Show this message and exit." in help_result.output


def test_investment_tracker():
    """Sample code on how to use the investment_tracker framework"""
    test_investment_tracker_logger = getLogger("investment_tracker.investment_tracker")
    test_investment_tracker_logger.setLevel(DEBUG)
    BRK = Stock(ticker="BRK.A")
    # sets the price of BRK stock to $20
    BRK.set_price(20, day=date.today())
    session.add(BRK)
    test_investment_tracker_logger.info(f"{BRK} added to session")

    buffett = User(username="buffett", available_funds=100)
    buffett.buy("BRK.A", quantity=2)
    session.add(buffett)
    test_investment_tracker_logger.debug(
        f"{buffett.stock_quantity('BRK.A')} stocks available to sell"
    )
    test_investment_tracker_logger.info(f"{buffett} added to session")
    buffett.sell("BRK.A", quantity=1)
    session.add(buffett)
    test_investment_tracker_logger.debug(
        f"{buffett.stock_quantity('BRK.A')} stocks available to sell"
    )

    users = session.query(User).first()
    test_investment_tracker_logger.info(users.transactions[0].stock_price)
    test_investment_tracker_logger.info(
        f"{users.transactions[0]} total price: {users.transactions[0].total_price}"
    )
    test_investment_tracker_logger.info(f"{users.transactions[0].stock_price}")


@pytest.fixture(scope='class')
def sample_user():
    return User(username='sample_user', available_funds=1000)


@pytest.fixture(scope='module')
def sample_stock():
    return Stock(ticker='sample_stock')


@pytest.fixture(scope='module')
def sample_price():
    return Price(price=10, day=date.today())


@pytest.fixture(scope='module')
def sample_transaction():
    return Transaction(day=date.today(), quantity=0)


@pytest.fixture(scope='module')
def sample_stock_purchase():
    return Transaction(day=date.today(), quantity=1, kind='buy')


@pytest.fixture(scope='module')
def sample_transfer():
    return Transaction(day=date.today(), kind='transfer', transfer_amt=50)


class TestUser():

    def test_username(self, sample_user):
        assert sample_user.username == 'sample_user'

    def test_available_funds(self, sample_user):
        assert sample_user.available_funds == 1000


class TestStock():

    def test_ticker(self, sample_stock):
        assert sample_stock.ticker == 'sample_stock'


class TestPrice():

    def test_price(self, sample_price):
        assert sample_price.price == 10

    def test_day(self, sample_price):
        assert sample_price.day == date.today()

    # TODO figure out how to test default values
    @pytest.mark.skip
    def test_default_day(self, sample_price):
        assert Price(price=10).day == date.today()


class TestTransaction():

    def test_day(self, sample_transaction):
        assert sample_transaction.day == date.today()

    def test_quantity(self, sample_transaction):
        assert sample_transaction.quantity == 0

    def test_kind(self, sample_stock_purchase):
        assert sample_stock_purchase.kind == 'buy'

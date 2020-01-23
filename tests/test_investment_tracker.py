#!/usr/bin/env python

"""Tests for `investment_tracker` package."""

import pytest
from logging import getLogger, DEBUG, WARNING, INFO, ERROR, CRITICAL
from click.testing import CliRunner
from investment_tracker.investment_tracker import session, Stock, User
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

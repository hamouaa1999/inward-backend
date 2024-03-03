""" import pytest
from flask import Flask
from main import create_app


@pytest.fixture()
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })

    # other setup can go here

    yield app

    # clean up / reset resources here

def test_request_example(client):
    response = client.get("/")
    assert b"Hello, Hamou. You`re the best, believe me!" in response.data

@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def runner(app):
    return app.test_cli_runner() """
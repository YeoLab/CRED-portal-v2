import pytest


def pytest_addoption(parser):
    parser.addoption("--driver_path", action="store", help="input useranme")
    parser.addoption("--username", action="store", help="input useranme")
    parser.addoption("--password", action="store", help="input password")


@pytest.fixture
def params(request):
    params = {'driver_path': request.config.getoption('--driver_path'),
              'username': request.config.getoption('--username'),
              'password': request.config.getoption('--password')}
    if params['username'] is None or params['password'] is None:
        pytest.skip()
    return params

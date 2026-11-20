from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from streamlit.testing.v1 import AppTest


APP = str(Path(__file__).with_name("app.py"))
PASSWORD = "only-for-automated-tests"


def test_neon_refuses_to_connect_without_password():
    app = AppTest.from_file(APP)
    app.secrets["VEICULOS_NEON_DATABASE_URL"] = "test"
    with patch("vehicle_db_neon.NeonVehicles") as connection:
        app.run()
    assert not app.exception
    assert any("ainda não foi configurado" in text.value for text in app.error)
    connection.assert_not_called()


@pytest.mark.parametrize("route", ["vehicles", "out", "return", "panel", "admin"])
def test_direct_routes_require_password_before_opening_neon(route):
    app = AppTest.from_file(APP)
    app.secrets.update(VEICULOS_NEON_DATABASE_URL="test", VEICULOS_ACCESS_PASSWORD=PASSWORD)
    app.query_params["view"] = route
    with patch("vehicle_db_neon.NeonVehicles") as connection:
        app.run()
    assert not app.exception
    assert app.text_input[0].label == "Senha de acesso"
    connection.assert_not_called()


def test_logout_relocks_the_vehicle_app():
    app = AppTest.from_file(APP)
    app.secrets.update(VEICULOS_NEON_DATABASE_URL="test", VEICULOS_ACCESS_PASSWORD=PASSWORD)
    with patch("vehicle_db_neon.NeonVehicles") as connection:
        connection.return_value = MagicMock()
        connection.return_value.table.return_value.select.return_value.order.return_value.execute.return_value.data = []
        connection.return_value.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        app.run()
        app.text_input[0].set_value(PASSWORD)
        app.button[0].click().run()
        assert not app.exception
        assert any(button.label == "Sair" for button in app.button)
        assert connection.called
        app.button(key="veiculos_access_logout").click().run()
        assert app.text_input[0].label == "Senha de acesso"

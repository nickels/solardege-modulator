from unittest.mock import MagicMock, patch

from modbus import InverterClient, ACTIVE_POWER_LIMIT


def test_write_power_limit():
    client = InverterClient("192.168.1.10", 1502, device_id=1)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.write_power_limit(75)

    mock_modbus.write_register.assert_called_once_with(
        ACTIVE_POWER_LIMIT, 75, device_id=1
    )


def test_write_power_limit_clamps_range():
    client = InverterClient("192.168.1.10", 1502, device_id=1)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.write_power_limit(150)
    mock_modbus.write_register.assert_called_with(ACTIVE_POWER_LIMIT, 100, device_id=1)

    client.write_power_limit(-10)
    mock_modbus.write_register.assert_called_with(ACTIVE_POWER_LIMIT, 0, device_id=1)


def test_write_power_limit_custom_device_id():
    client = InverterClient("192.168.1.10", 1502, device_id=3)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.write_power_limit(50)

    mock_modbus.write_register.assert_called_once_with(
        ACTIVE_POWER_LIMIT, 50, device_id=3
    )


def test_connect_creates_client():
    with patch("modbus.ModbusTcpClient") as MockClient:
        mock_instance = MagicMock()
        MockClient.return_value = mock_instance

        client = InverterClient("192.168.1.10", 1502, device_id=1)
        client.connect()

        MockClient.assert_called_once_with("192.168.1.10", port=1502)
        mock_instance.connect.assert_called_once()


def test_close_writes_100_and_disconnects():
    client = InverterClient("192.168.1.10", 1502, device_id=1)
    mock_modbus = MagicMock()
    client._client = mock_modbus

    client.close()

    mock_modbus.write_register.assert_called_once_with(
        ACTIVE_POWER_LIMIT, 100, device_id=1
    )
    mock_modbus.close.assert_called_once()

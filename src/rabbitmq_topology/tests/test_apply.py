from unittest.mock import AsyncMock, patch

import pytest
from rabbitmq_topology.apply import apply_topology
from rabbitmq_topology.entities import DEAD_LETTER_QUEUES, EXCHANGES, QUEUES

_AMQP_URL = "amqp://guest:guest@localhost:5672/"


@pytest.mark.asyncio(loop_scope="session")
async def test_apply_topology_declares_all_exchanges() -> None:
    mock_broker = AsyncMock()

    with patch("rabbitmq_topology.apply.RabbitBroker", return_value=mock_broker):
        await apply_topology(amqp_url=_AMQP_URL)

    assert mock_broker.declare_exchange.call_count == len(EXCHANGES)
    for exchange in EXCHANGES:
        mock_broker.declare_exchange.assert_any_call(exchange)


@pytest.mark.asyncio(loop_scope="session")
async def test_apply_topology_declares_all_queues() -> None:
    mock_broker = AsyncMock()

    with patch("rabbitmq_topology.apply.RabbitBroker", return_value=mock_broker):
        await apply_topology(amqp_url=_AMQP_URL)

    expected_queues = [*DEAD_LETTER_QUEUES, *QUEUES]
    assert mock_broker.declare_queue.call_count == len(expected_queues)
    for queue in expected_queues:
        mock_broker.declare_queue.assert_any_call(queue)


@pytest.mark.asyncio(loop_scope="session")
async def test_apply_topology_stops_broker_on_exception() -> None:
    mock_broker = AsyncMock()
    mock_broker.declare_exchange.side_effect = RuntimeError("connection lost")

    with patch("rabbitmq_topology.apply.RabbitBroker", return_value=mock_broker):
        with pytest.raises(RuntimeError, match="connection lost"):
            await apply_topology(amqp_url=_AMQP_URL)

    mock_broker.stop.assert_called_once()

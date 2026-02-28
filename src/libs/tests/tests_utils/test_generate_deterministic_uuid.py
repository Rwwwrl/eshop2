from uuid import UUID

from libs.utils import generate_deterministic_uuid


def test_generate_deterministic_uuid_when_same_key() -> None:
    result_1 = generate_deterministic_uuid(key=(123,))
    result_2 = generate_deterministic_uuid(key=(123,))

    assert result_1 == result_2
    assert isinstance(result_1, UUID)


def test_generate_deterministic_uuid_when_different_keys() -> None:
    result_1 = generate_deterministic_uuid(key=(123,))
    result_2 = generate_deterministic_uuid(key=(456,))

    assert result_1 != result_2


def test_generate_deterministic_uuid_when_ambiguous_tuple_vs_single() -> None:
    result_single = generate_deterministic_uuid(key=(21,))
    result_tuple = generate_deterministic_uuid(key=(2, 1))

    assert result_single != result_tuple


def test_generate_deterministic_uuid_when_composite_key() -> None:
    result_1 = generate_deterministic_uuid(key=("client_42", 123))
    result_2 = generate_deterministic_uuid(key=("client_42", 123))
    result_3 = generate_deterministic_uuid(key=("client_42", 456))

    assert result_1 == result_2
    assert result_1 != result_3

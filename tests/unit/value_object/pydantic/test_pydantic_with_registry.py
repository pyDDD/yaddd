import datetime
from typing import Annotated

import pytest
from annotated_types import Interval
from pydantic import StringConstraints

from yaddd.domain.value_object import (
    BytesValueObject,
    DatetimeValueObject,
    DateValueObject,
    IntValueObject,
    NumericValueObject,
    StringValueObject,
    ValueObject,
)
from yaddd.domain.value_object.pydantic import PydanticVO


@pytest.mark.parametrize(
    "str_pyd_type, int_pyd_type, date_pyd_type, datetime_pyd_type",
    (
        (
            Annotated[str, StringConstraints(pattern="^test$")],
            Annotated[int, Interval(ge=0, lt=4)],
            Annotated[datetime.date, "placeholder"],
            Annotated[datetime.datetime, "placeholder"],
        ),
        (str, int, datetime.date, datetime.datetime),
    ),
    ids=("Annotated", "Basic"),
)
def test_bases(str_pyd_type, int_pyd_type, date_pyd_type, datetime_pyd_type):
    class CorrectVO(PydanticVO, ValueObject):
        pydantic_type = str_pyd_type

    with pytest.raises(TypeError, match="pydantic_type should be type: IncorrectlyTypedVO"):

        class IncorrectlyTypedVO(PydanticVO, ValueObject):
            pydantic_type = "jaja"

    class CorrectIntVO(PydanticVO, IntValueObject):
        pydantic_type = int_pyd_type

    with pytest.raises(TypeError, match="Types mismatch for IncorrectIntVO"):

        class IncorrectIntVO(PydanticVO, IntValueObject):
            pydantic_type = str_pyd_type

    class CorrectStringVO(PydanticVO, StringValueObject):
        pydantic_type = str_pyd_type

    with pytest.raises(TypeError, match="Types mismatch for IncorrectStringVO"):

        class IncorrectStringVO(PydanticVO, StringValueObject):
            pydantic_type = int_pyd_type

    class CorrectDateVO(PydanticVO, DateValueObject):
        pydantic_type = date_pyd_type

    class CorrectDateVOWithDatetime(PydanticVO, DateValueObject):
        pydantic_type = datetime_pyd_type

    with pytest.raises(TypeError, match="Types mismatch for IncorrectDateVO"):

        class IncorrectDateVO(PydanticVO, DateValueObject):
            pydantic_type = int_pyd_type

    class CorrectDatetimeVO(PydanticVO, DatetimeValueObject):
        pydantic_type = datetime_pyd_type

    with pytest.raises(TypeError, match="Types mismatch for IncorrectDatetimeVO"):

        class IncorrectDatetimeVO(PydanticVO, DatetimeValueObject):
            pydantic_type = int_pyd_type


def test_far_relative():
    class SecretKey(PydanticVO, BytesValueObject):
        """Секретный ключ для расшифровки данных."""

        sensitive = True
        pydantic_type = bytes

    class ConcreteSecretKey(SecretKey):
        pydantic_type = Annotated[bytes, "placeholder"]

    assert ConcreteSecretKey(b"12323")


def test_unregstered_relative():
    class ComplexNum(PydanticVO, NumericValueObject[complex]):
        pydantic_type = Annotated[complex, "placeholder"]

        def __float__(self):
            return float(self._validated_value)

        def __int__(self):
            return int(self._validated_value)

        def __round__(self, n=None):
            return round(self._validated_value, n)

    assert ComplexNum(complex(1, 1))  # PyCharm highlights due to incompatibility complex to _ValidatedValueProtocol


def test_union():
    with pytest.raises(NotImplementedError, match="pydantic_type doesn't support unions: "):

        class UnionVO(PydanticVO, ValueObject):
            """Секретный ключ для расшифровки данных."""

            pydantic_type = bytes | str | int

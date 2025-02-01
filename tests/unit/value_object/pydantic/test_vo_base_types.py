import datetime
import math
from typing import Annotated

import pytest
from annotated_types import Ge, Gt, Interval, Le, Len, Lt
from pydantic import (
    AfterValidator,
    BaseModel,
    SecretStr,
    StringConstraints,
    ValidationError,
)

from yaddd.domain.value_object import StringValueObject, IntValueObject, FloatValueObject, DateValueObject, \
    DatetimeValueObject
from yaddd.domain.value_object.base import SensitiveValueAccessError, ValueObject
from yaddd.domain.value_object.pydantic import PydanticVO


def test_str():
    class _TestType(PydanticVO, StringValueObject):
        pydantic_type = Annotated[str, StringConstraints(min_length=3)]

    operation_result = _TestType("lim") + _TestType("popo")
    assert type(operation_result) == _TestType
    assert operation_result == _TestType("limpopo")

    class Model(BaseModel):
        a: _TestType

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "a": {"title": "_TestType", "minLength": 3, "type": "string"},
        },
        "required": ["a"],
    }


def test_pydantic_vo_str_changes_value_during_validation():
    class _UpperString(PydanticVO, StringValueObject):
        @staticmethod
        def _upper_for_test(value: str):
            return value.upper()

        pydantic_type = Annotated[str, AfterValidator(_upper_for_test)]

    operation_result = _UpperString("lim") + _UpperString("popo")
    assert type(operation_result) == _UpperString
    assert operation_result == _UpperString("LIMPOPO")
    assert operation_result.value == "LIMPOPO"

    class Model(BaseModel):
        a: _UpperString

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {"a": {"title": "_UpperString", "type": "string"}},
        "required": ["a"],
    }


def test_int():
    class _TestType(PydanticVO, IntValueObject):
        pydantic_type = Annotated[int, Interval(ge=3)]

    operation_result = _TestType(3) + _TestType(4)
    assert type(operation_result) == _TestType
    assert operation_result == _TestType(7)

    class Model(BaseModel):
        a: _TestType

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "a": {"title": "_TestType", "type": "integer", "minimum": 3},
        },
        "required": ["a"],
    }


def test_float():
    class _TestType(PydanticVO, FloatValueObject):
        pydantic_type = Annotated[float, Ge(3)]

    operation_result = _TestType(3.3) + _TestType(6.6)
    assert type(operation_result) == _TestType
    assert math.isclose(operation_result.value, 9.9)

    class Model(BaseModel):
        a: _TestType

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "a": {"title": "test_type", "type": "number", "minimum": 3},
        },
        "required": ["a"],
    }


def test_secret_str():
    class UserPassword(PydanticVO, StringValueObject):
        pydantic_type = Annotated[SecretStr, StringConstraints(min_length=8)]
        _validated_value: SecretStr

        def get_secret_value(self):
            return self._validated_value.get_secret_value()

    with pytest.raises(ValidationError):
        UserPassword("testerr")
    password = UserPassword("testtest")
    assert password.get_secret_value() == password.value.get_secret_value() == "testtest"

    class Model(BaseModel):
        password: UserPassword

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "password": {
                "title": "UserPassword",
                "type": "string",
                "minLength": 8,
                "writeOnly": True,
                "format": "password",
            },
        },
        "required": ["password"],
    }


def test_date_pydantic_vo():
    today = datetime.date.today()

    class TomorrowOrLaterVo(PydanticVO, DateValueObject):
        pydantic_type = Annotated[datetime.date, Gt(today)]

    class YesterdayOrEarlierVo(PydanticVO, DateValueObject):
        pydantic_type = Annotated[datetime.date, Lt(today)]

    first_date = TomorrowOrLaterVo(today + datetime.timedelta(days=3))
    second_date = YesterdayOrEarlierVo(today - datetime.timedelta(days=3))

    with pytest.raises(ValidationError, match="Input should be greater than"):
        first_date - datetime.timedelta(days=6)

    assert first_date - second_date
    assert first_date + datetime.timedelta(days=3) == TomorrowOrLaterVo(today + datetime.timedelta(days=6))
    assert first_date.timetuple() == first_date.value.timetuple()
    assert first_date.toordinal() == first_date.value.toordinal()
    assert first_date.weekday() == first_date.value.weekday()
    assert first_date.isoweekday() == first_date.value.isoweekday()
    assert first_date.isocalendar() == first_date.value.isocalendar()
    assert first_date.isoformat() == first_date.value.isoformat()
    assert first_date.ctime() == first_date.value.ctime()
    assert first_date.strftime("H") == first_date.value.strftime("H")
    assert first_date.year == first_date.value.year
    assert first_date.month == first_date.value.month
    assert first_date.day == first_date.value.day

    class Model(BaseModel):
        a: TomorrowOrLaterVo
        b: YesterdayOrEarlierVo

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "a": {"format": "date", "title": "TomorrowOrLaterVo", "type": "string"},
            "b": {"format": "date", "title": "YesterdayOrEarlierVo", "type": "string"},
        },
        "required": ["a", "b"],
    }


def test_datetime_pydantic_vo():
    now = datetime.datetime.now()

    class NowOrLaterVo(PydanticVO, DatetimeValueObject):
        pydantic_type = Annotated[datetime.datetime, Ge(now)]

    class NowOrEarlierVo(PydanticVO, DatetimeValueObject):
        pydantic_type = Annotated[datetime.datetime, Le(now)]

    first_datetime = NowOrLaterVo(now + datetime.timedelta(days=3))
    second_datetime = NowOrEarlierVo(now - datetime.timedelta(days=3))

    with pytest.raises(ValidationError, match="Input should be greater than or equal"):
        first_datetime -= datetime.timedelta(days=6)

    assert first_datetime - second_datetime
    assert first_datetime + datetime.timedelta(days=3) == NowOrLaterVo(now + datetime.timedelta(days=6))
    assert first_datetime.timetuple() == first_datetime.value.timetuple()
    assert first_datetime.toordinal() == first_datetime.value.toordinal()
    assert first_datetime.weekday() == first_datetime.value.weekday()
    assert first_datetime.isoweekday() == first_datetime.value.isoweekday()
    assert first_datetime.isocalendar() == first_datetime.value.isocalendar()
    assert first_datetime.isoformat() == first_datetime.value.isoformat()
    assert first_datetime.ctime() == first_datetime.value.ctime()
    assert first_datetime.strftime("H") == first_datetime.value.strftime("H")
    assert first_datetime.year == first_datetime.value.year
    assert first_datetime.month == first_datetime.value.month
    assert first_datetime.day == first_datetime.value.day

    assert first_datetime.utcoffset() == first_datetime.value.utcoffset()
    assert first_datetime.tzname() == first_datetime.value.tzname()
    assert first_datetime.dst() == first_datetime.value.dst()
    assert first_datetime.hour == first_datetime.value.hour
    assert first_datetime.minute == first_datetime.value.minute
    assert first_datetime.second == first_datetime.value.second
    assert first_datetime.microsecond == first_datetime.value.microsecond
    assert first_datetime.tzinfo == first_datetime.value.tzinfo
    assert first_datetime.fold == first_datetime.value.fold

    class Model(BaseModel):
        a: NowOrLaterVo
        b: NowOrEarlierVo

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "a": {"format": "date-time", "title": "NowOrLaterVo", "type": "string"},
            "b": {"format": "date-time", "title": "NowOrEarlierVo", "type": "string"},
        },
        "required": ["a", "b"],
    }


def test_list():  # works same for tuples
    class _TestType(PydanticVO, ValueObject):
        pydantic_type = Annotated[list[int], Len(min_length=2)]

    class _TestType2(PydanticVO, ValueObject):
        pydantic_type = Annotated[list[int], Len(min_length=7)]

    with pytest.raises(TypeError, match="unsupported operand type"):
        _TestType([1, 2]) + _TestType2([2, 3, 4, 5])  # Pycharm highlights operator

    class Model(BaseModel):
        a: _TestType
        b: _TestType2

    assert Model.model_json_schema() == {
        "title": "Model",
        "type": "object",
        "properties": {
            "a": {
                "items": {"type": "integer"},
                "minItems": 2,
                "title": "test_type",
                "type": "array",
            },
            "b": {
                "items": {"type": "integer"},
                "maxItems": 7,
                "title": "test_type2",
                "type": "array",
            },
        },
        "required": ["a", "b"],
    }


def test_ioperations():
    class _TestType(PydanticVO, IntValueObject):
        pydantic_type = Annotated[int, Gt(2)]

    test_val = _TestType(3)
    with pytest.raises(TypeError, match="unsupported operand type"):
        test_val += 4
    test_val += _TestType(4)
    assert test_val == _TestType(7)
    assert type(test_val) == _TestType

    with pytest.raises(ValidationError):
        test_val -= _TestType(10)


def test_sensitive_vo():
    class SensitiveVO(PydanticVO, IntValueObject):
        pydantic_type = Annotated[int, Gt(2)]
        sensitive = True

    sensitive_vo = SensitiveVO(3)

    def _with_raises(callback):
        with pytest.raises(SensitiveValueAccessError):
            callback(sensitive_vo)

    _with_raises(print)
    _with_raises(str)
    _with_raises("Some string {}".format)

    assert repr(sensitive_vo) == "SensitiveVO([MASKED])"

    class ModelWithSensitiveData(BaseModel):
        sensitive: SensitiveVO

    model = ModelWithSensitiveData(sensitive=3)
    print(model)  #  -> sensitive=SensitiveVO([MASKED])
    assert str(model) == "sensitive=SensitiveVO([MASKED])"
    assert "Some string {!s}".format(model) == "Some string sensitive=SensitiveVO([MASKED])"
    assert "Some string {!r}".format(model) == "Some string ModelWithSensitiveData(sensitive=SensitiveVO([MASKED]))"

    assert repr(model) == "ModelWithSensitiveData(sensitive=SensitiveVO([MASKED]))"

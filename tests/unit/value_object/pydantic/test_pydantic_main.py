import json
from typing import Annotated

import pytest
from annotated_types import Interval
from pydantic import BaseModel, PlainSerializer, StringConstraints, TypeAdapter, ValidationError

from yaddd.domain.value_object import StringValueObject, ValueObject
from yaddd.domain.value_object.pydantic import PydanticVO


def test_pydantic_vo_v2():
    pyd_type, valid_value, invalid_value, pyd_error = (
        Annotated[str, StringConstraints(pattern="^test$")],
        "test",
        "tessst123",
        ValidationError,
    )

    class TestVo(PydanticVO, ValueObject):
        pydantic_type = pyd_type

    test_vo = TestVo(valid_value)

    with pytest.raises(pyd_error):
        TestVo(invalid_value)

    class TestModel(BaseModel):
        test_attr: TestVo

    test_model = TestModel(test_attr=valid_value)
    assert isinstance(test_model.test_attr, TestVo)
    assert test_model.test_attr == test_vo

    with pytest.raises(ValidationError):
        TestModel(test_attr=invalid_value)


def test_openapi_schema_v2():
    class OpenAPITestVO(PydanticVO, StringValueObject):
        pydantic_type = Annotated[str, StringConstraints(pattern="test")]

    class OpenAPITestSchema(BaseModel):
        test_attr: OpenAPITestVO

    openapi_schema = OpenAPITestSchema.model_json_schema()
    expected_result = {"title": "OpenAPITestVO", "pattern": "test", "type": "string"}

    generation_result = openapi_schema["properties"]["test_attr"]
    assert generation_result == expected_result, generation_result
    assert openapi_schema["required"] == ["test_attr"]


@pytest.mark.parametrize(
    "test_annotation, test_value, json_schema",
    (
        (
            Annotated[str, StringConstraints(pattern="^test$")],
            "test",
            {"type": "string", "pattern": "^test$"},
        ),
        (
            Annotated[int, Interval(gt=10, lt=20)],
            15,
            {"exclusiveMaximum": 20, "exclusiveMinimum": 10, "type": "integer"},
        ),
    ),
)
def test_pydantic_vo_v2_serialization(test_annotation, test_value, json_schema):
    class _TestType(PydanticVO, ValueObject):
        pydantic_type = test_annotation

    test_vo = _TestType(test_value)

    for adapter in (
        TypeAdapter(test_vo),  # In pydantic.BaseModel with PydanticVO these will be used
        test_vo._pydantic_adapter,  # Proof, that prev adapter works as original
        #                        (PydanticVO usage equals Annotated usage for pydantic.BaseModel)
        TypeAdapter(test_annotation),
    ):
        assert adapter.dump_python(test_vo) == test_vo  # warning!
        assert adapter.dump_json(test_vo) == json.dumps(test_value).encode()

    assert TypeAdapter(test_vo).json_schema() == json_schema | {"title": "_TestType"}


def test_vo_for_vo():
    class _TestType(PydanticVO, StringValueObject):
        pydantic_type = Annotated[str, StringConstraints(pattern="^test$")]

    with pytest.raises(ValidationError) as exc_context:
        _TestType(_TestType("test"))  # Pycharm highlights


def test_vo_with_json_serializer():
    class _TestType(PydanticVO, ValueObject):
        pydantic_type = int

    adapter = TypeAdapter(_TestType)
    assert adapter.dump_json(adapter._type(3)) == b"3"

    class _TestTypeWithSerialization(PydanticVO, ValueObject):
        pydantic_type = Annotated[int, PlainSerializer(lambda x: f"{x}!", return_type=str)]

    adapter = TypeAdapter(_TestTypeWithSerialization)
    assert adapter.dump_json(adapter._type(3)) == b'"3!"'


def test_vo_with_python_serializer():
    # on application level we want to use VO

    class _TestType(PydanticVO, ValueObject):
        pydantic_type = int

    adapter = TypeAdapter(_TestType)
    assert adapter.dump_python(adapter._type(3)) == _TestType(3)

    class _TestTypeWithSerialization(PydanticVO, ValueObject):
        pydantic_type = Annotated[int, PlainSerializer(lambda x: f"{x}!", return_type=str)]

    adapter = TypeAdapter(_TestTypeWithSerialization)
    assert adapter.dump_python(adapter._type(3)) == _TestTypeWithSerialization(3)

"""Value objects, powered with pydantic v2."""

from abc import ABCMeta
from types import UnionType
from typing import Annotated, Any, TypeAlias, final, get_args, get_origin

from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler, TypeAdapter
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, SchemaSerializer, core_schema
from pydantic_core.core_schema import (
    JsonSchema,
    SerializationInfo,
    SerializerFunctionWrapHandler,
)
from typing_extensions import Self, assert_never

from ..base import ValidatedValue, ValueObject, _ValueObjectMeta
from ..registry import VOBaseTypesRegistry

_PydanticType: TypeAlias = type[ValidatedValue] | Annotated  # type: ignore[valid-type]


class PydanticVOMeta(_ValueObjectMeta):
    def __new__(
        mcls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        skip_meta_validation: bool = False,
        **kwargs: Any,
    ) -> type["PydanticVO"]:
        pydantic_type: _PydanticType | None = namespace.get("pydantic_type")
        if not skip_meta_validation:
            mcls._validate_pydantic_type(pydantic_type, bases, name)
        namespace["_pydantic_adapter"] = TypeAdapter(pydantic_type)
        return super().__new__(mcls, name, bases, namespace, **kwargs)  # type: ignore[return-value]

    @classmethod
    def _validate_pydantic_type(mcls, pydantic_type: _PydanticType | None, bases: tuple[type, ...], name: str) -> None:
        if not pydantic_type:
            raise TypeError(f"pydantic_type must be set for {name}")

        if get_origin(pydantic_type) is Annotated:  # Annotated support
            return mcls._validate_pydantic_type(get_args(pydantic_type)[0], bases, name)

        if isinstance(pydantic_type, UnionType):
            raise NotImplementedError(f"pydantic_type doesn't support unions: {name}")

        if not isinstance(get_origin(pydantic_type) or pydantic_type, type):
            raise TypeError(f"pydantic_type should be type: {name}")

        if not mcls._pydantic_type_matches_with_parent(bases, pydantic_type, name):
            raise TypeError(f"Types mismatch for {name}")

    @classmethod
    def _pydantic_type_matches_with_parent(
        cls, bases: tuple[type, ...], pydantic_type: _PydanticType, name: str
    ) -> bool:
        """Check to avoid pydantic_type + ValueObject cls mismatch.

        Positive:
        class PositiveCaseVO(PydanticVO, IntValueObject):
            pydantic_type = int

        Negative:
        class NegativeCaseVO(PydanticVO, StringValueObject):
            pydantic_type = int
        """
        # Looking for latest ValueObject subclass in bases
        cls_based_on_value_object = next((base_cls for base_cls in bases if issubclass(base_cls, ValueObject)), None)
        if cls_based_on_value_object is None:
            raise TypeError(f"PydanticVO's children should be based on ValueObject: {name}")

        # Looking for the latest registered in VOBaseTypesRegistry class
        ddd_vo_cls = next(
            (
                ddd_cls
                for ddd_cls in cls_based_on_value_object.__mro__
                if ddd_cls in VOBaseTypesRegistry.registered_vo_classes
            ),
            None,
        )

        return ddd_vo_cls is None or ddd_vo_cls in VOBaseTypesRegistry.select_matching_vo_classes(pydantic_type)


class PydanticVO(metaclass=PydanticVOMeta, skip_meta_validation=True):
    """Value Object with power of pydantic.

    The core idea is still the same as for ValueObject.
    Pydantic provides powerful and well-known tools for validation and this subclass of VO
        is created to use them!
    How methods are executed:
        1) During BaseModel initialization:
            a) if PydanticVO is not provided:
                - '__get_pydantic_core_schema__' targets method 'cast'
                - 'cast' method is called on provided value
                - 'cast' returns PydanticVO instance, that runs 'validate' on initialization
                - 'validate' executes chain of pydantic validators
                    and returns trusted value or raises ValidationError
                As result: PydanticVO instance is a value of BaseModel attribute,
                    that contains trusted data and shown in OpenAPI schema as  '_validated_value' attribute
            b) if PydanticVO is provided:
                All steps are the same, but 'cast' returns PydanticVO without initialization,
                because it is already initialized.

        2) Domain model requires VO instance, so we trust data, that VO contains
            (because of validation during initialization)
    """

    _pydantic_adapter: TypeAdapter[_PydanticType]
    pydantic_type: _PydanticType

    __pydantic_serializer__: SchemaSerializer

    # ValueObject interface
    _validated_value: ValidatedValue

    @classmethod
    @final
    def validate(cls, value: ValidatedValue | Any) -> ValidatedValue:
        """Validate value, using pydantic validators."""
        return cls._pydantic_adapter.validate_python(value)

    @classmethod
    @final
    def __get_pydantic_core_schema__(cls, _source_type: Any, _handler: GetCoreSchemaHandler) -> CoreSchema:
        """Validators to be called during initializing pydantic base model."""
        schema = core_schema.no_info_plain_validator_function(
            function=cls._cast,
            serialization=core_schema.wrap_serializer_function_ser_schema(
                cls._serialize, schema=cls._pydantic_adapter.core_schema, info_arg=True
            ),
        )
        # Followed by issue: https://github.com/pydantic/pydantic/issues/7779
        cls.__pydantic_serializer__ = SchemaSerializer(schema)
        return schema

    @classmethod
    @final
    def __get_pydantic_json_schema__(cls, _schema: JsonSchema, _handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        """VO representation in json schema."""
        json_schema: dict[str, Any] = cls._pydantic_adapter.json_schema()
        json_schema["title"] = cls.__name__
        return json_schema

    @classmethod
    @final
    def _cast(cls, value: ValidatedValue | Self) -> Self:
        """Cast VO type.

        We want either initialize VO and execute all validators or skip validation,
            if VO instance is provided.
        """
        if isinstance(value, cls):
            return value
        return cls(value)  # type: ignore[call-arg]

    def _serialize(self, handler: SerializerFunctionWrapHandler, info: SerializationInfo) -> Any:
        """Serialize value.

        Expected to be used within WrapSerializerFunction

        :param handler: partially serializes value by cls.pydantic_type logic
        :param info: serialization context
        """
        match info.mode:
            case "json":
                # use all annotated serializers instructions
                return handler(self._validated_value)

            case "python":
                # on application level we want to use VO
                return self

            case unexpected_mode:
                assert_never(unexpected_mode)

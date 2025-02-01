"""SQLAlchemy integration."""

from typing import Protocol, overload, TypeVar, Any

from sqlalchemy import String, TypeDecorator, Dialect
from sqlalchemy.sql.type_api import TypeEngine

from ..base import ValueObject


_PythonValueT = TypeVar("_PythonValueT")
_DatabaseStorableValueT = TypeVar("_DatabaseStorableValueT")


class _TypeDecoratorFunctionProtocol(Protocol):
    @overload
    def __call__(self, value: _PythonValueT, dialect: Dialect) -> _DatabaseStorableValueT:
        """Serialize value before storage in database."""

    @overload
    def __call__(self, value: _DatabaseStorableValueT, dialect: Dialect) -> _PythonValueT:
        """Deserialize value after fetching from database."""

    def __call__(self, value: Any, dialect: Dialect) -> Any:
        """Instruction to convert values on database communication."""


def create_type_decorator(
    python_type: ValueObject | type | None,
    sqla_impl: TypeEngine = String,
    serialize_func: _TypeDecoratorFunctionProtocol | None = None,
    deserialize_func: _TypeDecoratorFunctionProtocol | None = None,
    to_cache=True,
    name: str | None = None,
) -> type[TypeDecorator]:
    """Fabric to create type decorator to provide power of VO into SQLAlchemy."""
    if python_type is None and (deserialize_func is None or name is None):
        raise ValueError("You should provide `python_type` or both `name` and `deserialize_func`")

    class _TypeDecorator(TypeDecorator):
        impl = sqla_impl
        cache_ok = to_cache

        if serialize_func:
            process_bind_param = serialize_func
        else:

            def process_bind_param(self, value, dialect):
                return None if value is None else str(value)

        if deserialize_func:
            process_result_value = deserialize_func
        else:

            def process_result_value(self, value, dialect):
                return None if value is None else python_type(value)

    type_decorator_cls = _TypeDecorator
    class_name = name or python_type.__name__
    _TypeDecorator.__name__ = _TypeDecorator.__qualname__ = f"{class_name}TypeDecorator"
    return type_decorator_cls

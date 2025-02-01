from types import UnionType
from typing import Any, Iterable, Annotated, get_origin, cast, get_args, Final, Generic

from yaddd.domain.value_object import ValueObject


class _VOBaseTypesRegistry:
    def __init__(self) -> None:
        self._cls2basic_types_map: dict[type[ValueObject[Any]], tuple[type, ...]] = {}
        self.basic_type2cls_map: dict[type, type[ValueObject[Any]]] = {}

    @property
    def registered_vo_classes(self) -> Iterable[type[ValueObject[Any]]]:
        return self._cls2basic_types_map.keys()

    def register(self, cls: type[ValueObject[Any]]) -> type[ValueObject[Any]]:
        if not issubclass(cls, ValueObject):
            raise TypeError("VOBaseTypesRegistry only registers ValueObject subclasses.")
        self._on_cls_registration(cls)
        return cls

    def select_matching_vo_classes(
        self,
        type_: Annotated | type,  # type: ignore[valid-type]
    ) -> list[type[ValueObject[Any]]]:
        """Select all VO classes matching for inheritance to use with provided type."""
        type_ = self._prepare_type(type_)

        result: list[type[ValueObject[Any]]] = [ValueObject]  # type: ignore[type-abstract]
        for vo_cls, basic_types in self._cls2basic_types_map.items():
            if issubclass(type_, basic_types):
                result.append(vo_cls)
        return result

    def select_most_matching_vo_class(
        self,
        type_: Annotated | type,  # type: ignore[valid-type]
    ) -> type[ValueObject[Any]]:
        """Select the most matching for inheritance VO class for provided type."""
        type_ = self._prepare_type(type_)
        matching_vo_classes: list[type[ValueObject[Any]]] = self.select_matching_vo_classes(type_)
        if len(matching_vo_classes) == 1:
            return matching_vo_classes[0]

        def _key_most_matching_vo_class(
            matching_vo_class: type[ValueObject[Any]],
        ) -> int:
            """For each matching_vo_class:

            1) Find basic types (or default)
            2) Collect MROs of each basic type, relative to <type_>
            3) Return length of the richest (MRO-wise) basic type's MRO
            """
            default = (object,)
            matching_vo_class_basic_types: tuple[type, ...] = self._cls2basic_types_map.get(matching_vo_class, default)
            mros = [basic_type.__mro__ for basic_type in matching_vo_class_basic_types if issubclass(type_, basic_type)]
            return len(max(mros))

        # Among each matching VO class find the most matching by key
        return max(matching_vo_classes, key=_key_most_matching_vo_class)

    def _on_cls_registration(self, cls: type[ValueObject[Any]]) -> None:
        basic_types_from_generic = self._get_basic_types_from_generic(cls)

        self._cls2basic_types_map[cls] = basic_types_from_generic
        for basic_type in basic_types_from_generic:
            if registered_by_cls := self.basic_type2cls_map.get(basic_type):
                raise ValueError(
                    f"Basic type {basic_type} is already registered by cls {registered_by_cls}. Triggered by: {cls}"
                )
            self.basic_type2cls_map[basic_type] = cls

    @staticmethod
    def _prepare_type(type_: type) -> type:
        if get_origin(type_) is Annotated:  # Annotated support
            return cast(type, get_args(type_)[0])
        return get_origin(type_) or type_  # Generic types support (ex. dict[k, v])

    @staticmethod
    def _get_basic_types_from_generic(cls: type[ValueObject[Any]]) -> tuple[type, ...]:
        """Get typevar from generic."""
        # Select ValueObject classes, parametrized with typevar
        value_object_classes_with_type_var = [
            base_cls
            for base_cls in cls.__orig_bases__  # type: ignore[attr-defined]
            if issubclass(get_origin(base_cls) or base_cls, ValueObject)
            and len(get_args(base_cls)) == _VO_TYPEVARS_COUNT
        ]
        if not value_object_classes_with_type_var:
            raise TypeError(f"TypeVar is not defined in registered class: {cls}.")

        if len(value_object_classes_with_type_var) > 1:
            raise TypeError(f"Several generic value_object bases: {cls}.")

        # Get the first typevar, as it should represent type of value, stored after validation
        type_var_type = get_args(value_object_classes_with_type_var[0])[0]

        # Return tuple of types to map with cls in registry
        if isinstance(type_var_type, UnionType):
            return get_args(type_var_type)
        return (get_origin(type_var_type) or type_var_type,)  # for generic typevars (ex: dict[k, v])


VOBaseTypesRegistry = _VOBaseTypesRegistry()
del _VOBaseTypesRegistry

_VO_TYPEVARS_COUNT: Final[int] = len(
    get_args(
        next(
            _base
            for _base in ValueObject.__orig_bases__  # type: ignore[attr-defined]
            if (get_origin(_base) or _base) == Generic
        )
    )
)

from __future__ import annotations

from types import UnionType
from typing import Annotated, Any, Final, Generic, Iterable, Type, cast, get_args, get_origin

from yaddd.domain.value_object import ValueObject


class _VOBaseTypesRegistry:
    def __init__(self) -> None:
        self._cls_to_basic_types: dict[Type[ValueObject[Any]], tuple[Type, ...]] = {}
        self._basic_type_to_cls: dict[Type, Type[ValueObject[Any]]] = {}

    @property
    def registered_vo_classes(self) -> Iterable[Type[ValueObject[Any]]]:
        return self._cls_to_basic_types.keys()

    def register(self, vo_cls: Type[ValueObject[Any]]) -> Type[ValueObject[Any]]:
        if not issubclass(vo_cls, ValueObject):
            raise TypeError(f"{vo_cls.__name__} must be a ValueObject subclass")

        self._process_class_registration(vo_cls)
        return vo_cls

    def select_matching_vo_classes(self, target_type: Annotated | Type) -> list[Type[ValueObject[Any]]]:
        processed_type = self._normalize_type(target_type)
        matches = [ValueObject]  # Default base class

        for vo_cls, basic_types in self._cls_to_basic_types.items():
            if issubclass(processed_type, basic_types):
                matches.append(vo_cls)

        return matches

    def select_most_matching_vo_class(self, target_type: Annotated | Type) -> Type[ValueObject[Any]]:
        candidates = self.select_matching_vo_classes(target_type)
        if len(candidates) == 1:
            return candidates[0]

        def mro_complexity(cls: Type[ValueObject[Any]]) -> int:
            basic_types = self._cls_to_basic_types.get(cls, (object,))
            relevant_mros = [bt.__mro__ for bt in basic_types if issubclass(processed_type, bt)]
            return max(len(mro) for mro in relevant_mros) if relevant_mros else 0

        processed_type = self._normalize_type(target_type)
        return max(candidates, key=mro_complexity)

    def _process_class_registration(self, vo_cls: Type[ValueObject[Any]]) -> None:
        basic_types = self._extract_basic_types(vo_cls)

        self._cls_to_basic_types[vo_cls] = basic_types

        for bt in basic_types:
            if existing := self._basic_type_to_cls.get(bt):
                raise ValueError(f"Type conflict: {bt} already registered by {existing.__name__}")
            self._basic_type_to_cls[bt] = vo_cls

    @staticmethod
    def _normalize_type(t: Type | Annotated) -> Type:
        if get_origin(t) is Annotated:
            return cast(Type, get_args(t)[0])
        return get_origin(t) or t

    @staticmethod
    def _extract_basic_types(vo_cls: Type[ValueObject[Any]]) -> tuple[Type, ...]:
        generic_bases = [
            base
            for base in getattr(vo_cls, "__orig_bases__", [])
            if issubclass(get_origin(base) or base, ValueObject) and len(get_args(base)) == _VO_TYPEVARS_COUNT
        ]

        if not generic_bases:
            raise TypeError(f"Missing type parameters in {vo_cls.__name__}")
        if len(generic_bases) > 1:
            raise TypeError(f"Multiple generic bases in {vo_cls.__name__}")

        type_var = get_args(generic_bases[0])[0]

        if isinstance(type_var, UnionType):
            return get_args(type_var)
        return (get_origin(type_var) or type_var,)


VOBaseTypesRegistry = _VOBaseTypesRegistry()
del _VOBaseTypesRegistry

_VO_TYPEVARS_COUNT: Final[int] = len(
    get_args(
        next(
            base
            for base in ValueObject.__orig_bases__  # type: ignore[attr-defined]
            if (get_origin(base) or base) == Generic
        )
    )
)

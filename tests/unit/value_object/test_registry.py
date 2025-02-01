import datetime
from abc import ABC
from typing import Generic, TypeVar

import pytest

from yaddd.domain.value_object import (
    ValueObject,
    VOBaseTypesRegistry,
    DatetimeValueObject,
    DateValueObject,
    DictValueObject,
)


def _unregister(cls: type, registry=VOBaseTypesRegistry):
    del registry._cls_to_basic_types[cls]
    for _type in registry._extract_basic_types(cls):
        del registry._basic_type_to_cls[_type]


def test_vo_register():
    class _TestBaseVO(ValueObject[bool]): ...

    VOBaseTypesRegistry.register(_TestBaseVO)
    assert _TestBaseVO in VOBaseTypesRegistry.registered_vo_classes
    assert bool in VOBaseTypesRegistry._basic_type_to_cls
    _unregister(_TestBaseVO)


def test_vo_register_not_vo():
    with pytest.raises(TypeError, match="int must be a ValueObject subclass"):
        VOBaseTypesRegistry.register(int)


def test_vo_register_union():
    class SuperInt(int): ...

    class SuperStr(str): ...

    class _TestBaseVO(ValueObject[SuperStr | SuperInt]): ...

    VOBaseTypesRegistry.register(_TestBaseVO)
    assert _TestBaseVO in VOBaseTypesRegistry.registered_vo_classes
    assert SuperInt in VOBaseTypesRegistry._basic_type_to_cls
    assert SuperStr in VOBaseTypesRegistry._basic_type_to_cls
    _unregister(_TestBaseVO)


def test_most_matching_vo_for_date():
    matching_vo_classes = VOBaseTypesRegistry.select_matching_vo_classes(datetime.date)
    # [ValueObject, DateValueObject]
    assert DateValueObject in matching_vo_classes

    assert VOBaseTypesRegistry.select_most_matching_vo_class(datetime.date) == DateValueObject


def test_most_matching_vo_for_datetime():
    matching_vo_classes = VOBaseTypesRegistry.select_matching_vo_classes(datetime.datetime)
    # [ValueObject, DateValueObject, DatetimeValueObject]
    assert DatetimeValueObject in matching_vo_classes

    assert VOBaseTypesRegistry.select_most_matching_vo_class(datetime.datetime) == DatetimeValueObject


def test_many_bases_vo_registration():
    class SimpleTestBaseVO(ValueObject[complex], ABC): ...

    class SomeMixin: ...

    class MixedTestBaseVO1(SomeMixin, ValueObject[complex], ABC): ...

    class NewVO(ValueObject):
        def fancy_method(self): ...

    class MixedTestBaseVO2(NewVO, ValueObject[complex], SomeMixin, object): ...

    _T = TypeVar("_T")

    class GenericMixin(Generic[_T]): ...

    class MixedTestBaseVO3(NewVO, GenericMixin[str], ValueObject[complex], SomeMixin, object): ...

    for _TestBaseVO in (SimpleTestBaseVO, MixedTestBaseVO1, MixedTestBaseVO2, MixedTestBaseVO3):
        VOBaseTypesRegistry.register(_TestBaseVO)
        assert _TestBaseVO in VOBaseTypesRegistry.registered_vo_classes
        assert complex in VOBaseTypesRegistry._basic_type_to_cls
        _unregister(_TestBaseVO)

    ChildTypeVar = TypeVar("ChildTypeVar", bound=str)

    class ChildVO(ValueObject[ChildTypeVar]): ...

    class SeveralGenericValueObjectsCase(NewVO, ChildVO[str], ValueObject[complex], SomeMixin, object): ...

    with pytest.raises(TypeError, match="Multiple generic bases."):
        VOBaseTypesRegistry.register(SeveralGenericValueObjectsCase)


@pytest.mark.parametrize(
    "type_",
    (
        dict,
        dict[str, str],
    ),
)
def test_dict_vo_matching(type_):
    matching_vo_classes = VOBaseTypesRegistry.select_matching_vo_classes(type_)
    # [ValueObject, DictValueObject]
    assert DictValueObject in matching_vo_classes

    assert VOBaseTypesRegistry.select_most_matching_vo_class(type_) == DictValueObject

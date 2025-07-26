"""Realisation of commonly used ValueObjects via pydantic."""

from typing import Annotated

from annotated_types import Interval

from ..base_types import IntValueObject
from .main import PydanticVO


class PositiveInt32(PydanticVO, IntValueObject):
    pydantic_type = Annotated[int, Interval(gt=0, le=2147483647)]

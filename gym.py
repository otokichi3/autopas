import dataclasses
from typing import List

# TODO これらのクラスを opas.py で使用する
@dataclasses.dataclass
class Court:
    """コート"""
    name: str = 'undefined'
    vacant_table: list[list[bool]] = dataclasses.field(default_factory=list)

@dataclasses.dataclass
class Gym:
    """体育館"""
    name: str = 'undefined'
    courts: list[Court] = dataclasses.field(default_factory=list)

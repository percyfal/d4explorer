"""d4explorer data module."""

import dataclasses
from enum import Enum
from pathlib import Path

import daiquiri
from pyd4 import D4File

logger = daiquiri.getLogger("d4explorer")


class DataTypes(Enum):
    """Enum for getter method data types."""

    LIST = "list"
    DATAFRAME = "df"
    BED = "bed"
    D4 = "d4"


@dataclasses.dataclass
class D4Data:
    name: Path


@dataclasses.dataclass
class D4Hist:
    d4file: D4File

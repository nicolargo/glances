from typing import Optional

from pydantic import BaseModel


class GlancesStatsModel(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    time_since_update: Optional[int] = None


# from pydantic import conlist


# class Foo(BaseModel):
#     # these were named min_length and max_length in Pydantic v1.10
#     fixed_size_list_parameter: conlist(float, min_length=4, max_length=4)

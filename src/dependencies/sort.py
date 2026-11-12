from enum import StrEnum
from typing import Optional

from fastapi import Query

from src.database.models.movies import MovieModel


class MovieSortEnum(StrEnum):
    PRICE_ASC = "price_asc"
    PRICE_DESC = "price_desc"
    YEAR_ASC = "year_asc"
    YEAR_DESC = "year_desc"
    META_SCORE_ASC = "meta_score_asc"
    META_SCORE_DESC = "meta_score_desc"



class MovieSortParams:
    def __init__(self,
                 sort_by: Optional[MovieSortEnum] = Query(None, description="Movie to sort by price, date, meta_score"),
                 ):
        self.sort_by = sort_by

    def sort(self, stmt):
        if self.sort_by == MovieSortEnum.PRICE_ASC:
            stmt = stmt.order_by(MovieModel.price.asc())
        elif self.sort_by == MovieSortEnum.PRICE_DESC:
            stmt = stmt.order_by(MovieModel.price.desc())
        elif self.sort_by == MovieSortEnum.YEAR_ASC:
            stmt = stmt.order_by(MovieModel.year.asc())
        elif self.sort_by == MovieSortEnum.YEAR_DESC:
            stmt = stmt.order_by(MovieModel.year.desc())
        elif self.sort_by == MovieSortEnum.META_SCORE_ASC:
            stmt = stmt.order_by(MovieModel.meta_score.asc())
        elif self.sort_by == MovieSortEnum.META_SCORE_DESC:
            stmt = stmt.order_by(MovieModel.meta_score.desc())
        return stmt


import os

from src.database.models.base import Base
from src.database.models.accounts import (
    UserModel,
    UserGroupModel,
    UserGroupEnum,
    ActivationTokenModel,
    PasswordResetTokenModel,
    RefreshTokenModel,
    UserProfileModel
)
from src.database.models.movies import (
    MovieModel,
    StarModel,
    GenreModel,
    DirectorModel,
    MovieGenresModel,
    MovieStarsModel,
    MovieDirectorModel,
    MovieRatingModel,
    CertificationModel,
    MovieLikeModel,

)
from src.database.session_sqlite import reset_sqlite_database as reset_database
from src.validation import accounts as accounts_validators

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from src.database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db
    )
else:
    from src.database.session_postgres import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )

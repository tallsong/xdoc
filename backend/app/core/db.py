from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

# Create engine conditionally: prefer Postgres when configured, otherwise
# fall back to an in-memory SQLite database so tests can run without a
# running Postgres instance.
if settings.POSTGRES_SERVER and settings.POSTGRES_USER and settings.POSTGRES_DB:
    engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
else:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel
    # For test environments using an in-memory SQLite DB we create tables
    # automatically so tests can run without applying Alembic migrations.
    try:
        from sqlmodel import SQLModel

        # Import application models so SQLModel metadata is populated
        import app.models  # noqa: F401

        if engine.url.scheme.startswith("sqlite"):
            SQLModel.metadata.create_all(engine)
    except Exception:
        # If anything goes wrong creating tables automatically, continue
        # and let the subsequent DB operations raise informative errors.
        pass

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

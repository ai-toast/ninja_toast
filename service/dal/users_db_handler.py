from abc import ABC, ABCMeta, abstractmethod

from service.dal.schemas.users_db import UserBase, UserEntry


class _SingletonMeta(ABCMeta):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class UsersDalHandler(ABC, metaclass=_SingletonMeta):

    @abstractmethod
    def create_user_in_db(self, user_name: str, email: str) -> UserEntry:
        ...  # pragma: no cover

    @abstractmethod
    def delete_user_in_db(self, user_id: str) -> UserBase:
        ...  # pragma: no cover

    @abstractmethod
    def get_user_in_db(self, user_id: str) -> UserEntry:
        ...  # pragma: no cover

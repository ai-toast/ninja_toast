from abc import ABC, ABCMeta, abstractmethod

from service.dal.schemas.orders_db import OrderBase, OrderEntry


class _SingletonMeta(ABCMeta):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(_SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class OrdersDalHandler(ABC, metaclass=_SingletonMeta):

    @abstractmethod
    def create_order_in_db(self, customer_name: str, order_item_count: int) -> OrderEntry:
        ...  # pragma: no cover

    @abstractmethod
    def delete_order_in_db(self, order_id: str) -> OrderBase:
        ...  # pragma: no cover

    @abstractmethod
    def get_order_in_db(self, order_id: str) -> OrderEntry:
        ...  # pragma: no cover

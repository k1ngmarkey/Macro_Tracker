"""Domain errors. Raised by services, translated to HTTP in main.py."""


class DomainError(Exception):
    """Base class for every error a service raises on purpose."""


class NotFound(DomainError):
    """The thing doesn't exist, or it exists but isn't visible to this user."""


class FoodNotFound(NotFound):
    def __init__(self, food_id: int | str):
        super().__init__(f"Food {food_id} not found")


class EntryNotFound(NotFound):
    def __init__(self, entry_id: int):
        super().__init__(f"Entry {entry_id} not found")


class InvalidInput(DomainError):
    """Input that passed schema validation but breaks a business rule."""


class InvalidQuantity(InvalidInput):
    pass


class DateRangeTooLarge(InvalidInput):
    pass
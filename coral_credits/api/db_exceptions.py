class ResourceRequestFormatError(Exception):
    """Raised when the resource request format is incorrect"""

    pass


class InsufficientCredits(Exception):
    """Raised when an account has insufficient credits for a request"""

    pass


class NoCreditAllocation(Exception):
    """Raised when an account has no credit allocated for a given resource"""

    pass


class NoResourceClass(Exception):
    """Raised when there is no resource class matching the query"""

    pass

class ActiveConsumersInAllocation(Exception):
    """Raised when trying to delete an allocation with active consumers"""

    pass

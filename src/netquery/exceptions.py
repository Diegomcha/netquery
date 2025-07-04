class NetqueryException(Exception): ...


class NetqueryTimeoutException(NetqueryException):
    def __str__(self) -> str:
        return "exception"  # TODO: Change this


class NetqueryUnknownDeviceTypeException(NetqueryException):
    def __str__(self) -> str:
        return "exception"  # TODO: Change this


class NetqueryUnauthorizedException(NetqueryException):
    def __str__(self) -> str:
        return "exception"  # TODO: Change this


class NetqueryNoMatchesException(NetqueryException):
    def __str__(self) -> str:
        return "exception"  # TODO: Change this

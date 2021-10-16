from . import CondaError


class InvalidSpec(CondaError, ValueError):

    def __init__(self, message, **kwargs):
        super(InvalidSpec, self).__init__(message, **kwargs)


class InvalidVersionSpec(InvalidSpec):
    def __init__(self, invalid_spec, details):
        message = "Invalid version '%(invalid_spec)s': %(details)s"
        super(InvalidVersionSpec, self).__init__(message, invalid_spec=invalid_spec,
                                                 details=details)

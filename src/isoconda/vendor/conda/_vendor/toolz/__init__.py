# Importing from toolz.functoolz is slow since it imports inspect.
# Copy the relevant part of excepts' implementation instead:
class excepts(object):
    def __init__(self, exc, func, handler=lambda exc: None):
        self.exc = exc
        self.func = func
        self.handler = handler

    def __call__(self, *args, **kwargs):
        try:
            return self.func(*args, **kwargs)
        except self.exc as e:
            return self.handler(e)

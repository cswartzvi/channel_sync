from itertools import zip_longest  # noqa

string_types = str
zip = zip
zip_longest = zip_longest
text_type = str


def iteritems(d, **kw):
    return iter(d.items(**kw))


def with_metaclass(Type, skip_attrs=set(('__dict__', '__weakref__'))):
    """Class decorator to set metaclass.
    Works with both Python 2 and Python 3 and it does not add
    an extra class in the lookup order like ``six.with_metaclass`` does
    (that is -- it copies the original class instead of using inheritance).
    """

    def _clone_with_metaclass(Class):
        attrs = dict((key, value) for key, value in iteritems(vars(Class))
                     if key not in skip_attrs)
        return Type(Class.__name__, Class.__bases__, attrs)

    return _clone_with_metaclass

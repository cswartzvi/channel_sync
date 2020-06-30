
def urljoin(*parts):
    """Concatenate url parts."""
    return '/'.join([part.strip('/') for part in parts])
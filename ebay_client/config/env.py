import os


def get_env(name, default=None, environ=None):
    environ = environ or os.environ
    return environ.get(name, default)

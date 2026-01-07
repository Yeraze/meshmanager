"""MeshManager backend application."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("meshmanager")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

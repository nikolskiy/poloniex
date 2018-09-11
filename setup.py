from setuptools import setup
import sys


MIN_PYTHON = (3, 6)
if sys.version_info < MIN_PYTHON:
    sys.exit("Python %s.%s or later is required.\n" % MIN_PYTHON)


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    python_requires='>=3.6',
    name='poloniex',
    version='0.0.1',
    description='Poloniex API client',
    url='http://github.com/nikolskiy/poloniex',
    author='Denis Nikolskiy',
    license='GNU GPLv3',
    packages=['poloniex'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=['requests', 'websockets'],
    keywords='poloniex api',
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
)

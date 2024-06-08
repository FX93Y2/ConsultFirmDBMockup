from setuptools import setup, find_packages

setup(
    name="consultant_dbmock",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "numpy",
        "faker",
        "random-address"
    ],
)
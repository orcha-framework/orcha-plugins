import os

from setuptools import find_packages

for dir in os.listdir():
    if find_packages(dir):
        print(dir)

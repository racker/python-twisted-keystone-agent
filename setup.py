import os
import sys

from distutils.core import Command
from setuptools import setup
from subprocess import call


class Pep8Command(Command):
    description = "run pep8 script"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            import pep8
            pep8
        except ImportError:
            print ('Missing "pep8" library. You can install it using pip: '
                   'pip install pep8')
            sys.exit(1)

        cwd = os.getcwd()
        retcode = call(('pep8 %s/txKeystone/' % (cwd)).split(' '))
        sys.exit(retcode)


setup(
    name='txKeystone',
    version='0.1',
    description='A Twisted Agent implementation which authenticates' +
                ' to Keystone and uses the Keystone auth credentials' +
                ' to authenticate against requested urls.',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Framework :: Twisted'
    ],
    license='Apache License (2.0)',
    url='https://github.com/racker/python-twisted-keystone-agent',
    cmdclass={
        'pep8': Pep8Command
    },
    packages=['txKeystone'],
    install_requires=['Twisted'],
)

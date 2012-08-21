import os
import sys

from distutils.core import Command
from setuptools import setup
from subprocess import call

try:
    import epydoc
    has_epydoc = True
except ImportError:
    has_epydoc = False


class Pep8Command(Command):
    description = "Run pep8 script"
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


class ApiDocsCommand(Command):
    description = "generate API documentation"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        if not has_epydoc:
            raise RuntimeError('Missing "epydoc" package!')

        os.system(
            'pydoctor'
            ' --add-package=txKeystone'
            ' --project-name=txKeystone'
        )


class TestCommand(Command):
    description = "Run tests"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system('trial txKeystone/test/')


setup(
    name='txKeystone',
    version='0.1',
    description='A Twisted Agent implementation which authenticates' +
                ' to Keystone and uses the Keystone auth credentials' +
                ' to authenticate against requested urls.',
    author='Rackspace Hosting, Inc.',
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
        'pep8': Pep8Command,
        'apidocs': ApiDocsCommand,
        'test': TestCommand
    },
    packages=['txKeystone'],
    install_requires=['Twisted'],
)

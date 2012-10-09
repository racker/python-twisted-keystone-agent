# Copyright 2012 Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

from distutils.core import Command
from setuptools import setup
from subprocess import call

from utils.dist import get_packages, get_data_files

try:
    import epydoc
    has_epydoc = True
except ImportError:
    has_epydoc = False

# Commands based on Libcloud setup.py:
# https://github.com/apache/libcloud/blob/trunk/setup.py

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
        cwd = os.getcwd()
        retcode = call(('trial %s/txKeystone/test/' % (cwd)).split(' '))
        sys.exit(retcode)

pre_python26 = (sys.version_info[0] == 2 and sys.version_info[1] < 6)

setup(
    name='txKeystone',
    version='0.1.1',
    description='A Twisted Agent implementation which authenticates' +
                ' to Keystone and uses the Keystone auth credentials' +
                ' to authenticate against requested urls.',
    author='Rackspace Hosting, Inc.',
    author_email='shawn.smith@rackspace.com',
    requires=([], ['simplejson'],)[pre_python26],
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Framework :: Twisted'
    ],
    license='Apache License (2.0)',
    url='https://github.com/racker/python-twisted-keystone-agent',
    cmdclass={
        'pep8': Pep8Command,
        'apidocs': ApiDocsCommand,
        'test': TestCommand
    },
    packages=get_packages('txKeystone'),
    package_dir={
        'txKeystone': 'txKeystone',
    },
    package_data={'txKeystone': get_data_files('txKeystone',
                                               parent='txKeystone')},
    install_requires=['Twisted >= 9.0.0'],
)

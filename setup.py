from setuptools import setup

setup(
    name='txKeystone',
    version='0.1',
    description='A Twisted Agent implementation which authenticates to Keystone and uses the keystone auth credentials to authenticate against requested urls.',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2.7',
        'Framework :: Twisted'
    ],
    license='APL2',
    url='https://github.com/racker/python-twisted-keystone-agent',
    packages=['txKeystone'],
    install_requires=['Twisted'],
)

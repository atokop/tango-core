"""Tango mobile web optimization framework."""

import sys

from setuptools import setup, find_packages

# Avoid importing tango here, to get accurate test coverage reports.
# Test tango sites reside in the tests/ directory.
sys.path.append('tests')
sys.path.append('tests/errors')


setup(
    name='Tango',
    version='0.2.5',
    url='http://www.willowtreeapps.com',
    license='BSD',
    maintainer='WillowTree Apps DevOps Team',
    maintainer_email='devops@willowtreeapps.com',
    description=__doc__,
    long_description=open('README.rst').read(),
    packages=find_packages(),
    platforms=['POSIX'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'distribute',
        'BeautifulSoup==3.2.0',
        'Flask>=0.9',
        'Flask-Script==0.3.2',
        'lxml',
        'oauth2',
        'pytest',
        'pyyaml',
        'cssselect',
        ],
    entry_points={
        'console_scripts': [
            'tango = tango.manage:run'
            ],
        },
    tests_require=[
        # Update Makefile and tox.ini on changes to this block.
        'nose',
        'minimock>1.2.6',
        'Flask-Testing',
        ],
    test_suite='nose.collector',
)

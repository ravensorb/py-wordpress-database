"""
wpdatabase package setup.
"""

from setuptools import setup

with open('README.md', 'r') as stream:
    LONG_DESCRIPTION = stream.read()

setup(
    author='Shawn Anderson',
    author_email='sanderson@eye-catcher.com',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP :: Site Management'
    ],
    description='A Python package that checks and/or sets up a WordPress database.',
    extras_require={
        'dev': [
            'autopep8',
            'coverage',
            'pylint'
        ]
    },
    install_requires=[
        'boto3~=1.9.0',
        'mysql-connector~=2.1.0',
        'wpconfigr~=1.0.0'
    ],
    name='wpdatabase2',
    license='MIT',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    packages=[
        'wpdatabase2',
        'wpdatabase2.classes',
        'wpdatabase2.exceptions'
    ],
    url='https://github.com/ravensorb/py-wordpress-database',
    version='0.0.1')

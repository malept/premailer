from distutils.core import setup
import os


def fullsplit(path, result=None):
    """
    Split a pathname into components (the opposite of os.path.join) in a
    platform-neutral way.

    """
    if result is None:
        result = []
    head, tail = os.path.split(path)
    if head == '':
        return [tail] + result
    if head == path:
        return result
    return fullsplit(head, [tail] + result)

packages = []
root_dir = os.path.dirname(__file__).join('premailer')

for dirpath, dirname, filename in os.walk(root_dir):
    if '__init__.py' in filename:
        packages.append('.'.join(fullsplit(dirpath)))

setup(
    name = 'premailer',
    version = '2.0',
    url = 'http://github.com/rcoyner/python-premailer',
    author = 'Ryan Coyner',
    author_email = 'rcoyner@gmail.com',
    description = 'Converts standard HTML into a format for e-mail delivery.',
    packages = packages,
    package_data = {
        'premailer': ['data/*.yaml'],
    },
    scripts = ['bin/premailer'],
    classifiers = ['Development Status :: 5 - Production/Stable',
                   'Environment :: X11 Applications',
                   'Environment :: Other Environment',
                   'Environment :: Web Environment',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: Python Software Foundation License',
                   'Operating System :: OS Independent',
                   'Programming Language :: Python',
                   'Topic :: Communications',
                   'Topic :: Internet :: WWW/HTTP',
                   'Topic :: Software Development :: Libraries :: Python Modules',
                  ],
)

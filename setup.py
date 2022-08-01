# coding=utf-8
"""Setup file for lazy-hippo utility"""

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='lazy-hippo',
      version='0.2.0',
      author='Jesse Almanrode',
      author_email='jesse@almanrode.com',
      description='Utility splitting video files by timestamp',
      long_description=long_description,
      long_description_content_type="text/markdown",
      py_modules=['lazy_hippo'],
      python_requires='>=3.10',
      install_requires=['click>=8.1.3',
                        'colorama>=0.4.5'
                        ],
      entry_points={
          'console_scripts': [
              'lazy-hippo = lazy_hippo:cli',
          ]
      },
      platforms=['Linux', 'Darwin'],
      classifiers=[
          'Programming Language :: Python',
          'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
          'Development Status :: 5 - Production/Stable',
          'Programming Language :: Python :: 3.10',
      ],
      )

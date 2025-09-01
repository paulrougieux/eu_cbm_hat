#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Written by Lucas Sinclair and Paul Rougieux.

JRC Biomass Project.
Unit D1 Bioeconomy.
"""

# Imports #
from setuptools import setup, find_namespace_packages
from os import path

# Load the contents of the README file #
this_dir = path.abspath(path.dirname(__file__))
readme_path = path.join(this_dir, 'README.md')
with open(readme_path, encoding='utf-8') as handle: readme = handle.read()

# Call setup #
setup(
    name             = 'eu_cbm_hat',
    version          = '2.1.0',
    description      = 'eu_cbm_hat is a python package for running carbon'
                       ' budget simulations.',
    license          = 'EUPL',
    url              = 'https://gitlab.com/bioeconomy/eu_cbm/eu_cbm_hat',
    author           = 'Lucas Sinclair',
    author_email     = 'lucas.sinclair@me.com',
    maintainer       = 'Paul Rougieux',
    packages         = find_namespace_packages(),
    install_requires = ['autopaths>=1.6.0', 'plumbing>=2.11.1',
                        'pymarktex>=1.4.6', 'pandas', 'simplejson', 'pyyaml',
                        'tqdm', 'p_tqdm', 'pyarrow'],
    extras_require   = {'extras': ['pystache', 'matplotlib', 'numexpr']},
    python_requires  = ">=3.8",
    scripts=['scripts/running/run_zz_in_temp_dir_without_eu_cbm_data.py'],
    long_description = readme,
    long_description_content_type = 'text/markdown',
    include_package_data = True,
)

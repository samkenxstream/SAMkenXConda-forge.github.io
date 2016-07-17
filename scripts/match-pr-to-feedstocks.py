#!/usr/bin/env conda-execute

# conda execute
# env:
#  - python
#  - click
#  - jinja2
#  - requests
#  - ruamel.yaml
#  - conda-smithy
#  - pygithub
#  - fuzzywuzzy
# channels:
#  - conda-forge
# run_with: python

import click
import conda_smithy.feedstocks as feedstocks
import jinja2
import json
import requests
import ruamel.yaml
import os

from github import Github
import conda_smithy.github as smithy_github
from fuzzywuzzy import process


# patch over differences between PY2 and PY3
try:
    text_type = unicode
except NameError:
    text_type = str


class NullUndefined(jinja2.Undefined):
    def __unicode__(self):
        return text_type(self._undefined_name)

    def __getattr__(self, name):
        return text_type('{}.{}'.format(self, name))

    def __getitem__(self, name):
        return '{}["{}"]'.format(self, name)


env = jinja2.Environment(undefined=NullUndefined)


@click.group()
def cli():
    """Match package names in pr against existing feedstocks.

    Tools to match package names in from all the recipes in a pr against
    the existing conda-forge feedstocks.
    """
    pass


@cli.command('build-feedstock-index', help='create json index of feedstocks.')
@click.argument('filename')
@click.option('--gh-org', default='conda-forge', help='Set Github organization name.')
def build_feedstock_index(filename, gh_org='conda-forge'):
    "Iterate over feedstocks and return dict of pkg-name:feedstock"
    pkg_index = {}
    for repo in feedstocks.feedstock_repos(gh_org):
        try:
            meta = repo.get_file_contents(path='recipe/meta.yaml').decoded_content
            pkg_name = _extract_package_name(meta)
        except (AttributeError, KeyError):
            # unable to parse the bob.io.image-feedstock
            print('Unable to parse meta.yaml for {}'.format(repo.url))
            print('guessing pkg name from feedstock url')
            pkg_name = repo.url.split('/')[-1].split('-feedstock')[0].lower()
        pkg_index[pkg_name] = repo.full_name

    with open(filename, 'w') as f:
        json.dump(pkg_index, f)
        print('feedstocks index written to {}'.format(filename))


def _extract_package_name(meta):
    """Extract package name from meta.yaml"""
    content = env.from_string(meta.decode('utf8')).render(os=os)
    meta = ruamel.yaml.load(content, ruamel.yaml.RoundTripLoader)
    return meta['package']['name'].lower()


if __name__ == '__main__':
    cli()

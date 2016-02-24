# (c) 2016 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# constructor is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
"""
fcp (fetch conda packages) module
"""
from __future__ import print_function, division, absolute_import

import os
import sys
from os.path import isdir, isfile, join

from conda.utils import md5_file
from conda.fetch import fetch_index, fetch_pkg
from conda.plan import add_defaults_to_specs
from conda.resolve import Resolve


dists = None
index = None


def read_packages(packages):
    global dists

    res = []
    for line in open(packages):
        line = line.strip()
        if line.startswith('#'):
            continue
        if '=' in line:
            res.append(line.replace('=', '-') + '.tar.bz2')
        else:
            res.append(line)
    dists = res


def resolve(info):
    global dists, index

    index = fetch_index(tuple('%s/%s/' % (url.rstrip('/'), info['platform'])
                              for url in info['channels']))
    specs = info['specs']
    r = Resolve(index)
    add_defaults_to_specs(r, [], specs)
    dists = list(r.solve(specs))

    sort_info = {}
    for d in dists:
        name, unused_version, unused_build = d.rsplit('-', 2)
        sort_info[name] = d.rsplit('.tar.bz2', 1)[0]

    dists = map(lambda d: d + '.tar.bz2', r.graph_sort(sort_info))


def move_python_first():
    global dists

    res = []
    for dist in dists:
        if dist.rsplit('-', 2)[0] == 'python':
            res.insert(0, dist)
        else:
            res.append(dist)
    dists = res


def show(info):
    print("""
name: %(name)s
version: %(version)s
platform: %(platform)s
""" % info)
    for fn in dists:
        print('    %s' % fn)


def check_dists():
    if len(dists) == 0:
        sys.exit('Error: no packages specified')
    for i, fn in enumerate(dists):
        if not fn.endswith('.tar.bz2'):
            sys.exit("Error: '%s' does not end with '.tar.bz2'" % fn)
        dist = fn[:-8]
        try:
            name, version, build = dist.rsplit('-', 2)
        except ValueError:
            sys.exit("Error: Not a valid package filename: '%s'" % fn)
        if i == 0 and name != 'python':
            sys.exit("Error: 'python' needs to be the first package specified")


def fetch(info):
    download_dir = info['_download_dir']
    if not isdir(download_dir):
        os.makedirs(download_dir)
    for fn in dists:
        path = join(download_dir, fn)
        if isfile(path) and md5_file(path) == index[fn]['md5']:
            continue
        print('fetching: %s' % fn)
        fetch_pkg(index[fn], download_dir)


def main(info, verbose=True):
    if 'specs' in info:
        resolve(info)
        sys.stdout.write('\n')
    elif 'packages' in info:
        read_packages(info['packages'])
    else:
        sys.exit("Error: neither 'specs' nor 'packages' defined")

    move_python_first()
    if verbose:
        show(info)
    check_dists()
    fetch(info)
    info['_dists'] = dists
    info['_dist0'] = dists[0]
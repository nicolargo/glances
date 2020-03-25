#!/usr/bin/env python

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Script which downloads exe and wheel files hosted on AppVeyor:
https://ci.appveyor.com/project/giampaolo/psutil
Copied and readapted from the original recipe of Ibarra Corretge'
<saghul@gmail.com>:
http://code.saghul.net/index.php/2015/09/09/
"""

from __future__ import print_function
import argparse
import errno
import multiprocessing
import os
import requests
import shutil
import sys

from concurrent.futures import ThreadPoolExecutor


BASE_URL = 'https://ci.appveyor.com/api'
PY_VERSIONS = ['2.7', '3.4', '3.5', '3.6', '3.7', '3.8']


def term_supports_colors(file=sys.stdout):
    try:
        import curses
        assert file.isatty()
        curses.setupterm()
        assert curses.tigetnum("colors") > 0
    except Exception:
        return False
    else:
        return True


if term_supports_colors():
    def hilite(s, ok=True, bold=False):
        """Return an highlighted version of 'string'."""
        attr = []
        if ok is None:  # no color
            pass
        elif ok:   # green
            attr.append('32')
        else:   # red
            attr.append('31')
        if bold:
            attr.append('1')
        return '\x1b[%sm%s\x1b[0m' % (';'.join(attr), s)
else:
    def hilite(s, *a, **k):
        return s


def safe_makedirs(path):
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno == errno.EEXIST:
            if not os.path.isdir(path):
                raise
        else:
            raise


def safe_rmtree(path):
    def onerror(fun, path, excinfo):
        exc = excinfo[1]
        if exc.errno != errno.ENOENT:
            raise

    shutil.rmtree(path, onerror=onerror)


def download_file(url):
    local_fname = url.split('/')[-1]
    local_fname = os.path.join('dist', local_fname)
    print(local_fname)
    safe_makedirs('dist')
    r = requests.get(url, stream=True)
    with open(local_fname, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:    # filter out keep-alive new chunks
                f.write(chunk)
    return local_fname


def get_file_urls(options):
    session = requests.Session()
    data = session.get(
        BASE_URL + '/projects/' + options.user + '/' + options.project)
    data = data.json()

    urls = []
    for job in (job['jobId'] for job in data['build']['jobs']):
        job_url = BASE_URL + '/buildjobs/' + job + '/artifacts'
        data = session.get(job_url)
        data = data.json()
        for item in data:
            file_url = job_url + '/' + item['fileName']
            urls.append(file_url)
    if not urls:
        sys.exit("no artifacts found")
    for url in sorted(urls, key=lambda x: os.path.basename(x)):
        yield url


def rename_27_wheels():
    # See: https://github.com/giampaolo/psutil/issues/810
    src = 'dist/psutil-4.3.0-cp27-cp27m-win32.whl'
    dst = 'dist/psutil-4.3.0-cp27-none-win32.whl'
    print("rename: %s\n        %s" % (src, dst))
    os.rename(src, dst)
    src = 'dist/psutil-4.3.0-cp27-cp27m-win_amd64.whl'
    dst = 'dist/psutil-4.3.0-cp27-none-win_amd64.whl'
    print("rename: %s\n        %s" % (src, dst))
    os.rename(src, dst)


def main(options):
    files = []
    safe_rmtree('dist')
    with ThreadPoolExecutor(max_workers=multiprocessing.cpu_count()) as e:
        for url in get_file_urls(options):
            fut = e.submit(download_file, url)
            files.append(fut.result())
    # 2 exes (32 and 64 bit) and 2 wheels (32 and 64 bit) for each ver.
    expected = len(PY_VERSIONS) * 4
    got = len(files)
    if expected != got:
        print(hilite("expected %s files, got %s" % (expected, got), ok=False),
              file=sys.stderr)
    rename_27_wheels()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='AppVeyor artifact downloader')
    parser.add_argument('--user', required=True)
    parser.add_argument('--project', required=True)
    args = parser.parse_args()
    main(args)

#!/usr/bin/python
# -*- coding: utf-8 -*-

import commands
import re
import sys
import os

os.environ['LANG']='C'

WORKDIR='./debuginfo_rpms'
DEBUG_FILES='debugfiles.txt'
flag_debug = False


def my_name():
    index = sys.argv[0].rindex('/');
    return sys.argv[0][index+1:]


THIS = my_name()


def usage():
    sys.exit(THIS + ' [corefile]\n')


def debug(message):
    if flag_debug:
        print(message)


def warn(message):
    print('warn: ' + message)


def parse_yum_error(output):
    """
    parses the error output from yum provides command to find repository name
    if error is found, returns its repository name
    otherwise, returns None
    """
    m = re.search(r'^.*yum-config-manager --disable (.+)$', output, flags=re.MULTILINE)
    if m != None:
        repo = m.group(1)
        if repo != None and repo != '':
            print('The repo {0} is not alive.'.format(repo))
            return repo
    m = re.search(r'^.+: Cannot retrieve repository metadata \(repomd.xml\) for repository: (.+). Please verify its path and try again$', output, flags=re.MULTILINE)
    if m != None:
        repo = m.group(1)
        if repo != None and repo != '':
            print('The repo {0} is not alive.'.format(repo))
            return repo
    return None


def get_unavail_repos():
    """
    ping repositories trying `yum/dnf info bash` and returns an unavailable repo list
    """
    print('detecting unavailable repos...')
    unavail_repos = []
    while True:
        command = 'yum --disablerepo=\'*\' --enablerepo=\'*debug*\' '
        command += ' '.join(['--disablerepo="{0}"'.format(r) for r in unavail_repos])
        command += ' info bash'
        print(command)
        (status, output) = commands.getstatusoutput(command)
        debug(output)
        debug(status)
        if status != 0:
            repo = parse_yum_error(output)
            if repo != None and repo != '':
                unavail_repos.append(repo)
            else:
                print('failed to find an unavailable repository')
                debug(output)
                sys.exit()
        else: # if status==0
            return unavail_repos
    

def is_fc24():
    revision = os.uname()[2]
    return revision.find('fc24') >= 0


def make_directory():
    if not os.path.exists(WORKDIR):
        os.makedirs(WORKDIR)


def get_debugfile_path(build_id):
    """
    convert build id to debug file path, i.e,
    get_debugfile_path('86fe5bc1f46b8f8aa9a7a479ff991900db93f720@0x7f71aab08248') == '/usr/lib/debug/.build-id/86/fe5bc1f46b8f8aa9a7a479ff991900db93f720'
    """
    if len(build_id.split('@')[0]) != 40:
        warn('build id must be 40 bytes length')
    return '/usr/lib/debug/.build-id/' + build_id[0:2] + '/' + build_id[2:40]


def get_debugfile_list():
    """
    """
    with open(DEBUG_FILES) as f:
        debugfiles = [line.rstrip() for line in f.readlines()
                      if re.match(r'/usr/lib/debug/.build-id/[a-z0-9]+/[a-z0-9]+', line) != None]
    return debugfiles


def get_debugfile_list_eu_unstrip(path_to_core):
    """
    get build-id invoking eu-unstrip -n --core=coredump
    TODO: it does not work. why?
    """
    command = "eu-unstrip -n --core=" + path_to_core
    out = commands.getoutput(command)
    lines = out.split('\n')
    ids = map(lambda x: x.split()[1], lines)
    list = map(get_debugfile_path, ids)
    return list


def get_download_command():
    """
    yum version:
    yum reinstall -y --enablerepo "*debug*" --downloadonly --downloaddir=./debuginfo_rpms /usr/lib/debug/.build-id/ff/246dbc378d5afc4885c6bc26d3190b76321a35

    dnf version:
    dnf download --disablerepo='*' --enablerepo='*debug*' --destdir=xxx /usr/lib/debug/.build-id/ff/246dbc378d5afc4885c6bc26d3190b76321a35
    """
    unavail_repos = get_unavail_repos()
    opt_unavail_repos = ' '.join(['--disablerepo="{0}"'.format(r) for r in unavail_repos])
    if (is_fc24()):
        command = 'dnf download --disablerepo="*" --enablerepo="*debug*"'
    else:
        command = 'yum reinstall -y --disablerepo="*" --enablerepo "*debug*" --downloadonly --downloaddir=.'
    command += ' ' + opt_unavail_repos
    command += ' ' + ' '.join(get_debugfile_list())
    #command += ' ' + ' '.join(get_debugfile_list(sys.argv[1]))
    return command

def download_debuginfo():
    """
    """
    command = get_download_command()
    os.chdir(WORKDIR)
    print command
    os.system(command)
    os.chdir('..')


def unpack_debuginfo():
    files = os.listdir(WORKDIR)
    for file in files:
        file = WORKDIR + '/' + file
        print file
        command = 'rpm2cpio ' + file + ' | cpio -idu'
        os.system(command)


if __name__ == '__main__':
    make_directory()
    download_debuginfo()
    unpack_debuginfo()
    sys.exit('\n=========\nrun ./opencore.sh')
#else:
#    pass

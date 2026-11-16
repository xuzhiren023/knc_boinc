#!/usr/bin/env python3
"""Check this project's anonymous-platform manifest against its package files."""
import pathlib
import re
import sys
import xml.etree.ElementTree as ET


def require(condition, message):
    if not condition:
        raise ValueError(message)


def one_text(node, tag):
    values = node.findall(tag)
    require(len(values) == 1 and values[0].text, 'expected one ' + tag)
    return values[0].text


def basename(name):
    require(re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.+-]*', name) is not None
            and name not in ('.', '..'), 'unsafe file name: ' + name)
    return name


def check(package):
    root = ET.parse(package / 'app_info.xml').getroot()
    require(root.tag == 'app_info', 'root must be app_info')
    require(len(root.findall('app')) == 1, 'expected one app')
    require(one_text(root.find('app'), 'name') == 'milkyway_nbody', 'wrong server app name')
    versions = root.findall('app_version')
    require(len(versions) == 1, 'expected one app_version')
    version = versions[0]
    for tag, value in [('app_name', 'milkyway_nbody'), ('version_num', '197'),
                       ('platform', 'windows_x86_64'), ('avg_ncpus', '1'), ('max_ncpus', '1')]:
        require(one_text(version, tag) == value, 'wrong ' + tag)
    require(not version.findall('plan_class') and not version.findall('coproc'),
            'package uses plain CPU plan, no coprocessor claim')
    declarations = {}
    for info in root.findall('file_info'):
        name = basename(one_text(info, 'name'))
        require(name.casefold() not in {n.casefold() for n in declarations}, 'duplicate file name: ' + name)
        declarations[name] = info
    actual = {p.name for p in package.iterdir() if p.name != 'app_info.xml'}
    require(set(declarations) == actual,
            'file inventory mismatch: missing={}, undeclared={}'.format(
                sorted(set(declarations) - actual), sorted(actual - set(declarations))))
    for name in declarations:
        file = package / name
        require(file.is_file() and not file.is_symlink() and file.stat().st_size > 0,
                'missing, empty or nonregular file: ' + name)
    refs = set()
    mains = []
    graphics = []
    for ref in version.findall('file_ref'):
        name = basename(one_text(ref, 'file_name'))
        require(name in declarations, 'undeclared file_ref: ' + name)
        require(name not in refs, 'duplicate file_ref: ' + name)
        refs.add(name)
        if name == 'knc_nbody_graphics.exe':
            require(one_text(ref, 'open_name') == 'graphics_app', 'graphics discovery requires open_name graphics_app')
        else:
            require(not ref.findall('open_name'), 'ordinary package files must not be renamed')
        if ref.findall('graphics_app'):
            require(len(ref.findall('graphics_app')) == 1, 'duplicate graphics_app')
            graphics.append(name)
        if ref.findall('main_program'):
            require(len(ref.findall('main_program')) == 1, 'duplicate main_program')
            mains.append(name)
        else:
            require(len(ref.findall('copy_file')) == 1, 'ordinary reads need copy_file: ' + name)
    require(refs == set(declarations), 'every package file needs a file_ref')
    require(graphics == ['knc_nbody_graphics.exe'], 'expected sole knc_nbody_graphics.exe graphics_app')
    require(len(declarations['knc_nbody_graphics.exe'].findall('executable')) == 1, 'graphics app must be executable')
    require(mains == ['knc_wrapper.exe'], 'expected knc_wrapper.exe as sole main_program')
    require(len(declarations['knc_wrapper.exe'].findall('executable')) == 1,
            'main_program must be executable')
    required = {'knc_wrapper.cfg.example', 'milkyway_nbody.mic', 'cygwin1.dll',
                'cyggcc_s-seh-1.dll', 'cygstdc++-6.dll', 'cygiconv-2.dll', 'cygintl-8.dll'}
    require(required <= set(declarations), 'required host/card/config files missing')
    require(any('.so' in n for n in declarations), 'card runtimes missing')
    print('PASS app_info.xml: one milkyway_nbody version, 1 host CPU, {} files, wrapper main_program'.format(len(refs)))


if __name__ == '__main__':
    try:
        require(len(sys.argv) == 2, 'usage: check_package.py PACKAGE_DIRECTORY')
        check(pathlib.Path(sys.argv[1]))
    except (ValueError, OSError, ET.ParseError) as error:
        print('FAIL package: ' + str(error), file=sys.stderr)
        sys.exit(1)

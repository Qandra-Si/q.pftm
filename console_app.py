# -*- encoding: utf-8 -*-
""" Console application tools and utils
"""
import sys
import getopt
import typing
from pathlib import Path

from __init__ import __version__


def print_version_screen():
    print('q.pftm {ver} - (c) 2023 qandra.si@gmail.com\n'
          'Released under the BEER-WARE LICENSE.\n'.format(ver=__version__))


def print_help_screen(exit_code: typing.Optional[int] = None):
    print('\n'
          '-h --help                   Print this help screen\n'
          '   --map=filename.log       Pathfinder log file\n'
          '   --verbose                Show additional information while working (verbose mode)'
          '-v --version                Print version info\n'
          '\n'
          'Usage: ./pftm --map=map_2.log\n'.
          format(app=sys.argv[0]))
    if exit_code is not None and isinstance(exit_code, int):
        sys.exit(exit_code)


def get_argv_prms(additional_longopts: typing.List[str] = None):
    # работа с параметрами командной строки, получение настроек запуска программы, как то: работа в offline-режиме,
    # имя пилота ранее зарегистрированного и для которого имеется аутентификационный токен, регистрация нового и т.д.
    res = {
        "map": 'map_1.log',
        "verbose_mode": False,
    }
    # для всех дополнительных (настраиваемых) длинных параметров запуска будет выдаваться список строк-значений, при
    # условии, что параметр содержит символ '=' в конце наименования, либо bool-значение в том случае, если не модержит
    if additional_longopts:
        for opt in additional_longopts:
            if opt[-1:] == '=':  # category=
                res[opt[:-1]]: typing.List[str] = []
            else:  # category
                res[opt]: bool = False
    # парсинг входных параметров командной строки
    exit_or_wrong_getopt = None
    print_version_only = False
    try:
        longopts = ["help", "version", "map=", "verbose"]
        if additional_longopts:
            longopts.extend(additional_longopts)
        opts, args = getopt.getopt(sys.argv[1:], "hv", longopts)
    except getopt.GetoptError:
        exit_or_wrong_getopt = 2

    if exit_or_wrong_getopt is None:
        for opt, arg in opts:  # noqa
            if opt in ('-h', "--help"):
                exit_or_wrong_getopt = 0
                break
            elif opt in ('-v', "--version"):
                exit_or_wrong_getopt = 0
                print_version_only = True
                break
            elif opt in "--verbose":
                res["verbose_mode"] = True
            elif opt in "--map":
                res["map"] = arg
            elif opt.startswith('--') and (opt[2:]+'=' in additional_longopts):
                res[opt[2:]].append(arg)
            elif opt.startswith('--') and opt[2:] in additional_longopts:
                res[opt[2:]] = True
        # д.б. либо указано имя, либо флаг регистрации нового пилота
        # упразднено: if (len(res["character_names"]) == 0) == (res["signup_new_character"] == False):
        # упразднено:     exit_or_wrong_getopt = 0

    if exit_or_wrong_getopt is not None:
        print_version_screen()
        if print_version_only:
            sys.exit(exit_or_wrong_getopt)
        print_help_screen(exit_or_wrong_getopt)

    return res

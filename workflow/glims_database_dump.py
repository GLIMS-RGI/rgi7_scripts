#!/usr/bin/env python3

# Use the web services to download the whole database or subset

import os
import sys
import time
import urllib.request
import json
import argparse


def print_arg_summary(args):
    """Print summary of command-line arguments."""
    print("Arguments object:")
    print(args)


def setup_argument_parser():
    ''' setup_argument_parser -- define command-line args
    '''
    global_extent = ' -179.9,-89.9,179.9,89.9'

    def_env = 'production'
    def_extent = global_extent
    def_file_format = 'shapefile'
    def_nunataks = 'RGI'
    def_archive = 'zip'
    def_outdir = '.'
    def_proto = 'http'
    def_tries = 9999
    def_mode = 'glims'
    def_time = '2000-09-01'

    """Set up command line options.  -h or --help for help is automatic"""
    p = argparse.ArgumentParser()
    p.add_argument('-a', '--archive_type', choices=['zip', 'tar'], default='zip',
            help='Archive type.  Default:  {}'.format(def_archive))
    p.add_argument('-d', '--output_dir_root', default=def_outdir,
            help='Output directory.  Default:  {}'.format(def_outdir))
    p.add_argument('-D', '--debug', action='store_true', help='Debug mode. Selects small region in Mexico')
    p.add_argument('-c', '--clause', default=def_extent, type=str,
            help='"Clause".  See help for "download_type".  Default extent: {}'.format(def_extent))
    p.add_argument('-e', '--env', default=def_env, type=str, choices=['production','blue','qa','staging','integration'],
            help='Environment.  Default:  {}'.format(def_env))
    p.add_argument('-f', '--file_format', choices=['shapefile', 'kml', 'gmt'],
            default=def_file_format, help='File format. Default:  {}'.format(def_file_format))
    p.add_argument('-m', '--mode', default=def_mode, choices=['rgi', 'glims'],
            help='Download mode: RGI versus GLIMS.  Default:  {}'.format(def_mode))
    p.add_argument('-n', '--nunataks', default=def_nunataks, choices=['RGI', 'GLIMS'],
            help='Data model: holes (RGI) versus polys (GLIMS).  Default:  {}'.format(def_nunataks))
    p.add_argument('-o', '--outfile', help='Output file name')
    p.add_argument('-p', '--protocol', choices=['http', 'https'],
            help='http or https. Default: {}'.format(def_proto), default=def_proto)
    p.add_argument('-R', '--tries', type=int, default=def_tries,
            help="Number of tries (repeats) before giving up. Default: {}".format(def_tries))
    p.add_argument('-t', '--download_type', default='extent', choices=['extent', 'id'],
            help='Download mode. When "extent", clause should be geographic extent'
            ' (bounding box) as W,S,E,N.  When "id", clause should be list of GLIMS'
            ' glacier IDs, e.g. "G213061E61274N,G214815E61138N".\n\nIf the West'
            ' coordinate in the extent is negative, put the whole argument in'
            ' single quotes and insert a leading space, like'
            ' -c \' -179.9,-89.9,179.9,89.9\'')

    p.add_argument('-T', '--time', default=def_time,
            help='Target time (date in ISO format) for RGI-like map. Default: {}'.format(def_time))

    p.add_argument('-q', '--quiet',   action='store_true', default=False,
            help="Quiet mode.  Don't print status messages")
    return(p)


def issue_order(server, args):

    test_extent = '-98.66,19.14,-98.62,19.20'   # Mexican volcano glaciers

    params = []
    params.append('download_type=' + args.download_type)
    if args.debug:
        params.append('clause=' + test_extent)
    else:
        params.append('clause=' + args.clause.strip())
    params.append('archive_type=' + args.archive_type)
    params.append('file_format=' + args.file_format)
    params.append('data_model=' + args.nunataks)
    params.append('glims_v_rgi=' + args.mode)
    params.append('rgidate=' + args.time)

    param_string = '&'.join(params)
    data_order_url = args.protocol + '://' + server + '/downloadprepare?' + param_string

    print("Issuing order to downloadprepare service at URL:")
    print(data_order_url)

    try:
        with urllib.request.urlopen(data_order_url) as response:
            json_return = response.read()
            print("Response:  ", json_return)
    except Exception as e:
        print(e)
        print("Couldn't get information from", data_order_url)
        sys.exit(1)

    info = json.loads(json_return)
    filename = info['filename']
    return filename


def poll_readiness(server, filename, period=2, tries=3600, protocol='http'):
    ''' poll_readiness -- periodically poll the file readiness service

        Inputs:
            period:     sleep time, in seconds
            tries:      number of total tries before giving up
        Returns:
            the full path on the server of the file to download
    '''

    url = protocol + '://' + server + '/downloadfileready?filename=' + filename

    try_num = 1
    while try_num < tries:
        try:
            with urllib.request.urlopen(url) as response:
                json_return = response.read()
        except:
            print("Couldn't poll", url)
            sys.exit(1)

        poll_result = json.loads(json_return)
        ready_flag = poll_result['ready']
        print("Try #{:4d}:  {}.  File name:  {}".format(try_num, ready_flag, filename))
        if ready_flag is True:
            break
        else:
            try_num += 1
            time.sleep(period)

    return poll_result['filename']


def do_download(server, filebasename, args):
    ''' do_download -- pass filename to downloadfile service
    '''
    url = args.protocol + '://' + server + '/downloadfile?filename=' + filebasename

    if args.outfile:
        outname = args.outfile
    else:
        outname = filebasename

    if args.output_dir_root:
        dest = os.path.join(args.output_dir_root, outname)
    else:
        dest = outname

    print("Retrieving file to ", dest)
    urllib.request.urlretrieve(url, dest)


if __name__ == '__main__':
    p = setup_argument_parser()
    args = p.parse_args()

    servers = {
            'production': 'www.glims.org/services',
            'blue': 'blue.glims-services.apps.int.nsidc.org',
            'integration': 'integration.glims-services.apps.int.nsidc.org',
            'qa': 'qa.glims-services.apps.int.nsidc.org',
            'staging': 'staging.glims-services.apps.int.nsidc.org',
            }

    server = servers[args.env]

    filebasename = issue_order(server, args)
    poll_readiness(server, filebasename, period=2, tries=args.tries)    # returns when file is ready
    do_download(server, filebasename)

#!/usr/bin/env python3

# Use the web services to download the whole database or subset

import argparse
import json
import os
import sys
import time
import urllib.request

import requests
from requests.auth import HTTPBasicAuth


def get_noauth_session(environment_uri: str):
    session = requests.session()
    session.headers = {"User-Agent": "GLIMS-client", "Referer": "glims.console"}
    return session


def get_authenticated_session(environment_uri: str, username: str, password: str):
    session = requests.session()
    session.headers = {"User-Agent": "GLIMS-client", "Referer": "glims.console"}
    auth_cred = HTTPBasicAuth(username, password)
    auth_url = f"https://{environment_uri}/auth"
    glims_resp = session.get(auth_url, timeout=10, allow_redirects=False)
    auth_resp = session.get(
        glims_resp.url, auth=auth_cred, allow_redirects=False, timeout=10
    )
    if not auth_resp.ok:  # type: ignore
        print(f"Authentication with Earthdata Login failed with:\n{auth_resp.text}")
        return None
    else:
        print("Authentication succeeded")

    glims_session = session.get(
        auth_resp.headers["Location"], auth=auth_cred, allow_redirects=True
    )
    if not (glims_session.ok):
        print("NSIDC GLIMS could not authenticate with EDL")

    return session


def print_arg_summary(args):
    """Print summary of command-line arguments."""
    print("Arguments object:")
    print(args)


def setup_argument_parser():
    """setup_argument_parser -- define command-line args"""
    global_extent = " -179.9,-89.9,179.9,89.9"

    def_env = "production"
    def_extent = global_extent
    def_file_format = "shapefile"
    def_nunataks = "RGI"
    def_archive = "zip"
    def_outdir = "."
    def_proto = "https"
    def_tries = 9999
    def_mode = "glims"
    def_time = "2000-09-01"

    """Set up command line options.  -h or --help for help is automatic"""
    p = argparse.ArgumentParser()

    p.add_argument(
        "-a",
        "--archive_type",
        choices=["zip", "tar"],
        default="zip",
        help="Archive type.  Default:  {}".format(def_archive),
    )
    p.add_argument(
        "-c",
        "--clause",
        default=def_extent,
        type=str,
        help='"Clause".  See help for "download_type".  Default extent: {}'.format(
            def_extent
        ),
    )
    p.add_argument(
        "-d",
        "--output_dir_root",
        default=def_outdir,
        help="Output directory.  Default:  {}".format(def_outdir),
    )
    p.add_argument(
        "-D",
        "--debug",
        action="store_true",
        help="Debug mode. Selects small region in Mexico",
    )
    p.add_argument(
        "-e",
        "--env",
        default=def_env,
        type=str,
        choices=["production", "blue", "qa", "staging", "integration"],
        help="Environment.  Default:  {}".format(def_env),
    )
    p.add_argument(
        "-f",
        "--file_format",
        choices=["shapefile", "kml", "gmt"],
        default=def_file_format,
        help="File format. Default:  {}".format(def_file_format),
    )
    p.add_argument(
        "-m",
        "--mode",
        default=def_mode,
        choices=["rgi", "glims"],
        help="Download mode: RGI versus GLIMS.  Default:  {}".format(def_mode),
    )
    p.add_argument(
        "-n",
        "--nunataks",
        default=def_nunataks,
        choices=["RGI", "GLIMS"],
        help="Data model: holes (RGI) versus polys (GLIMS).  Default:  {}".format(
            def_nunataks
        ),
    )
    p.add_argument("-o", "--outfile", help="Output file name")
    p.add_argument(
        "-p",
        "--protocol",
        choices=["http", "https"],
        help="http or https. Default: {}".format(def_proto),
        default=def_proto,
    )
    p.add_argument(
        "-R",
        "--tries",
        type=int,
        default=def_tries,
        help="Number of tries (repeats) before giving up. Default: {}".format(
            def_tries
        ),
    )
    p.add_argument(
        "-t",
        "--download_type",
        default="extent",
        choices=["extent", "id"],
        help='Download mode. When "extent", clause should be geographic extent'
        ' (bounding box) as W,S,E,N.  When "id", clause should be list of GLIMS'
        ' glacier IDs, e.g. "G213061E61274N,G214815E61138N".  If the West'
        " coordinate in the extent is negative, put the whole argument in"
        " single quotes and insert a leading space, like"
        " -c ' -179.9,-89.9,179.9,89.9'",
    )
    p.add_argument(
        "-T",
        "--time",
        default=def_time,
        help="Target time (date in ISO format) for RGI-like map. Default: {}".format(
            def_time
        ),
    )
    p.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=False,
        help="Quiet mode.  Don't print status messages",
    )
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-u",
        "--user",
        type=str,
        help="Specify credentials as 'edl_user:edl_password'",
    )
    group.add_argument(
        "-N",
        "--netrc",
        action="store_true",
        help='Use the credentials in the ".netrc" file in the home directory',
    )
    group.add_argument(
        "-X",
        "--noauth",
        action="store_true",
        help="Don't use Earthdata Login (for pre-EDL use)",
    )

    return p


def issue_order(server, session, args):

    test_extent = "-98.66,19.14,-98.62,19.20"  # Mexican volcano glaciers

    params = {}
    params["download_type"] = args.download_type
    if args.debug:
        params["clause"] = test_extent
    else:
        params["clause"] = args.clause.strip()
    params["archive_type"] = args.archive_type
    params["file_format"] = args.file_format
    params["data_model"] = args.nunataks
    params["glims_v_rgi"] = args.mode
    params["rgidate"] = args.time

    data_order_url = args.protocol + "://" + server + "/downloadprepare"

    try:
        # with urllib.request.urlopen(data_order_url) as response:
        #   print("'response' type:", type(response))
        #   json_return = response.read()
        #   print("Response:  ", json_return)
        r = session.get(data_order_url, params=params)
        print("Issued order to downloadprepare service using requests.get.  URL is:")
        print(r.url)
        print("Status code: ", r.status_code)
        info = r.json()
    except Exception as e:
        print("Exception:", e)
        print("Couldn't get information from", data_order_url)
        sys.exit(1)

    # info = json.loads(json_return)
    filename = info["filename"]
    return filename


def poll_readiness(server, session, filename, protocol, period=2, tries=3600):
    """poll_readiness -- periodically poll the file readiness service

    Inputs:
        period:     sleep time, in seconds
        tries:      number of total tries before giving up
    Returns:
        the full path on the server of the file to download
    """

    url = protocol + "://" + server + "/downloadfileready?filename=" + filename

    try_num = 1
    while try_num < tries:
        try:
            # use session
            with urllib.request.urlopen(url) as response:
                json_return = response.read()
        except:
            print("Couldn't poll", url)
            sys.exit(1)

        poll_result = json.loads(json_return)
        ready_flag = poll_result["ready"]
        print("Try #{:4d}:  {}.  File name:  {}".format(try_num, ready_flag, filename))
        if ready_flag is True:
            break
        else:
            try_num += 1
            time.sleep(period)

    return poll_result["filename"]


def get_credentials(args, host):
    """
    get_credentials -- get credentials from .netrc or command line
    """
    if args.user:
        return args.user.split(":")
    elif args.netrc:
        import netrc

        try:
            net_rc = netrc.netrc()
            (login, account, pw) = net_rc.authenticators(host)
            return (login, pw)
        except:
            print(
                "Couldn't find credentials in .netrc file. Quitting.", file=sys.stderr
            )
            sys.exit(1)


def do_download(args, server, session, filebasename):
    """do_download -- pass filename to downloadfile service"""
    url = args.protocol + "://" + server + "/downloadfile?filename=" + filebasename

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


if __name__ == "__main__":
    p = setup_argument_parser()
    args = p.parse_args()

    glims_servers = {
        "production": "www.glims.org/services",
        "blue": "blue.glims-services.apps.int.nsidc.org",
        "integration": "integration.glims.org/services",
        "qa": "qa.glims-services.apps.int.nsidc.org",
        "staging": "staging.glims-services.apps.int.nsidc.org",
    }

    urs_server = "urs.earthdata.nasa.gov"

    server = glims_servers[args.env]

    if not args.noauth:
        # Get credentials from command-line or .netrc file
        credentials = get_credentials(args, urs_server)

        auth_session = get_authenticated_session(server, credentials[0], credentials[1])
        print("auth_session: ", auth_session)  # DEBUG

        if auth_session is None:
            print("Authentication failed.", file=sys.stderr)
            sys.exit(1)
    else:
        auth_session = get_noauth_session(server)

    filebasename = issue_order(server, auth_session, args)
    poll_readiness(
        server, auth_session, filebasename, period=2, tries=args.tries
    )  # returns when file is ready
    do_download(server, auth_session, filebasename)

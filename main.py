# -*- coding: utf-8 -*-
#!/usr/bin/python

import sys
import math
import argparse
from requests import Session
from tqdm import tqdm, trange
from config import *
from user import User
import pathlib
from jinja2 import Environment, FileSystemLoader, select_autoescape

tamplates = Environment(loader=FileSystemLoader(pathlib.Path(__file__).parent / "tamplates"), autoescape=select_autoescape())

def doRequest(session, url, ignore_errors=False):
    r = session.get(url)
    if r.status_code == 200 or ignore_errors:  # success
        return r

    print('ERROR (please copy and paste in the issue)')
    print(r.json())
    print(r.status_code)
    return ''


def book_request(session, offset=25, limit=10, order="createdAt:DESC",verbose=False):
    data = {} # using dict insted of list because u can own a book more than once (Effective DevOps with AWS)
    url = BASE_URL + PRODUCTS_ENDPOINT.format(order=order, offset=offset, limit=limit)
    if verbose:
        print(url)
    r = doRequest(session, url)
    data.update({i["productId"]: i for i in r.json().get('data', []) })
    if len(data) != limit:
        print("Packt loves it to send you more books than you asked for")

    return url, r, data


def get_books(session, offset=0, limit=25, is_verbose=False, is_quiet=False):
        url, r, data = book_request(session, offset, limit=min(25, limit))
        print(f'You have {str(r.json()["count"])} books')
        if limit > 25 and len(data) < limit:
            print("Getting list of books...")
            data.update(book_request(session, offset=25 + offset)[2])
        return list(data.values())[:limit]


def get_url_book(session, book_id, format):
    url = BASE_URL + URL_BOOK_ENDPOINT.format(book_id=book_id, format=format)
    return doRequest(session, url).json().get('data', '')


def get_book_file_types(session, book_id):
    url = BASE_URL + URL_BOOK_TYPES_ENDPOINT.format(book_id=book_id)
    return doRequest(session, url).json()['data'][0].get('fileTypes', [])
        


# TODO: i'd like that this functions be async and download faster
def download_book(session ,filename: pathlib.Path, url):
    print(f"Starting to download {filename.name}")

    with filename.open("wb") as f:
        r = session.get(url, stream=True)
        total = r.headers.get('content-length')
        if total is None:
            f.write(r.content)
        else:
            for chunk in tqdm(r.iter_content(chunk_size=1024), total=math.ceil(int(total)//1024), unit='KB', unit_scale=True):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
            print(f"Finished {filename.name}")


def move_current_files(root: pathlib.Path, book):
    sub_dir: pathlib.Path = root / book
    sub_dir.mkdir(parents=True, exist_ok=True)
    for f in root.glob(f"{book}.*"):
        try:
            if (sub_dir / f.name).exists():
                f.rename(sub_dir / f.with_stem(f"{f.stem}_1"))
            else:
                f.rename(sub_dir / f.name)
        except ValueError as e:
            print(e)
            print('Skipping')


def make_readme(args, session, book_details, book_name):
    params = {**book_details}
    if ENABLE_REVIEWS:
        params["reviews"] = doRequest(session, BASE_URL + URL_REVIEWS_ENDPOINT.format(book_id=book_details["productId"]), ignore_errors=True).json()
    if ENABLE_TOC:
        params["toc"] = doRequest(session, BASE_STATIC_URL + URL_TOC_ENDPOINT.format(book_id=book_details["productId"])).json()
    if ENABLE_AUTHOR_LOOKUP:
        params["authors_details"] = []
        for author in book_details.get("authors", []):
            params["authors_details"].append(doRequest(session, BASE_STATIC_URL + URL_AUTHOR_ENDPOINT.format(id=author)).json())
    file: pathlib.Path = args.root_directory / book_name /"README.md"
    file.write_text(tamplates.get_template('readme.md.jinja').render(**params, readUrlFull=BASE_WEBREADER_URL + book_details['readUrl']))


def parse_args():
    parser = argparse.ArgumentParser(allow_abbrev=True, epilog="This Program takes advantage of an buck in Packt's API to download your books more efficiently. In Case you dont get all your books they have probably fixed it")
    parser.add_argument("--version", action="version", version="%(prog)s 2.0_dev00", help=argparse.SUPPRESS) # works
    parser.add_argument('-e', '--email', help='Your email', required=True) # works
    parser.add_argument('-p', '--password',
                        help='Your password', required=True) # works
    parser.add_argument('-d', '--directory',
                        help='Directory to save your books',  dest="root_directory", default="./media", type=lambda d: pathlib.Path(d).expanduser()) # works
    parser.add_argument('-b', '--book-file-types', help='Book file types to download',
                        choices=("pdf", "mobi", "epub", "code"), nargs='*', default=("pdf",), action="extend") # works
    parser.add_argument('-s', '--separate', help='Separate books into subdirectories',
                         action='store_true') # works
    parser.add_argument("-r", "--readme", help="Creates a readme.md for each book", action='store_true') # works
    parser.add_argument('--debug', help=argparse.SUPPRESS, action='store_true')

    parser.add_argument("-i", "--ids", help='Book ids', nargs='+') # works

    parser.add_argument('-o', '--order', help='Order', default=("createdAt:DESC")) # works
    parser.add_argument('--offset', help='Offset', default=0, type=int) # works 
    parser.add_argument('-l', '--limit', help='Limit', default=25, type=int) # works

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', help='Verbose',
                        action='store_true') # works
    group.add_argument('-q', '--quiet', help='Quiet',
                       action='store_true') # works


    args = parser.parse_args()

    args.root_directory.mkdir(parents=True, exist_ok=True)

    args.book_file_types = set(args.book_file_types)

    if args.readme and not args.separate:
        print("--readme requires --separate")
        sys.exit(1)
    
    if args.ids and (args.offset != 0 or args.limit != 25 or args.order != "createdAt:DESC"):
        print(f"It's seems you are trying to use --ids with --offset, --limit or --order\n--offset, --limit and --order are ignored")
    
    if args.quiet:
        global tqdm
        global trange
        tqdm = lambda x, **kwargs: x
        trange = lambda x, **kwargs: range(x)

    return args


def doBook(args, session, book_id, book_name = None):
    if not book_name or args.readme:
        book_details = doRequest(session, BASE_STATIC_URL + URL_SUMMARY_ENDPOINT.format(book_id=book_id)).json()
        book_name = book_details["title"].replace(' ', '_').replace('.', '_').replace(':', '_').replace('/', '')
    if args.separate:
        filename = args.root_directory / book_name
        filename.mkdir(parents=True, exist_ok=True)
        move_current_files(args.root_directory, book_name)
    else:
        filename = args.root_directory 
    for file_type in args.book_file_types & set(get_book_file_types(session, book_id)):
        filename: pathlib.Path = filename / f"{book_name}.{file_type if file_type != 'code' else 'zip'}"
        url = get_url_book(session, book_id, file_type)
        if not filename.exists():
            download_book(session, filename, url)
        elif args.verbose:
            tqdm.write(f'{filename.name} already exists, skipping.')
    if args.readme:
        make_readme(args, session,book_details, book_name)

def download_by_ids(args, session):
    for id in args.ids:
        doBook(args, session, id)

def download_by_query(args, session):
    books = get_books(session, offset=args.offset, limit=args.limit, is_verbose=args.verbose, is_quiet=args.quiet)
    print('Downloading books...')
    if not args.quiet:
        books_iter = tqdm(books, unit='Book')
    else:
        books_iter = books
    for book in books_iter:
        doBook(args, session, book['productId'], book['productName'].replace(' ', '_').replace('.', '_').replace(':', '_').replace('/', ''))
        


def main():
    args = parse_args()

    # create Session
    session = Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
    }
    if args.debug:
        session.proxies = {
            "http": "http://127.0.0.1:8080",
            "https": "http://127.0.0.1:8080"
        }
        session.verify = "./mitmproxy-ca-cert.pem"

    session.auth = User(args.email, args.password, session=session)
    
    if args.ids:
        download_by_ids(args, session)
    else:
        download_by_query(args, session)


if __name__ == '__main__':
    main()

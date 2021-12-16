# -*- coding: utf-8 -*-
#!/usr/bin/python

import sys
import math
import argparse
from requests import Session
from tqdm import tqdm, trange
from config import *
from user import User
import requests
import pathlib


# TODO: I should do a function that his only purpose is to request and return data
def book_request(session, offset=0, limit=10, verbose=False):
    data = []
    url = BASE_URL + PRODUCTS_ENDPOINT.format(offset=offset, limit=limit)
    if verbose:
        print(url)
    r = session.get(url)
    data += r.json().get('data', [])

    return url, r, data


def get_books(user, offset=0, limit=10, is_verbose=False, is_quiet=False):
    '''
        Request all your books, return json with info of all your books
        Params
        ...
        header : str
        offset : int
        limit : int
            how many book wanna get by request
    '''
    # TODO: given x time jwt expired and should refresh the header, user.refresh_header()

    url, r, data = book_request(user, offset, limit)

    print(f'You have {str(r.json()["count"])} books')
    print("Getting list of books...")

    if not is_quiet:
        pages_list = trange(r.json()['count'] // limit, unit='Pages')
    else:
        pages_list = range(r.json()['count'] // limit)
    for i in pages_list:
        offset += limit
        data += book_request(user, offset, limit, is_verbose)[2]
    return data


def get_url_book(session, book_id, format='pdf'):
    '''
        Return url of the book to download
    '''

    url = BASE_URL + URL_BOOK_ENDPOINT.format(book_id=book_id, format=format)
    r = session.get(url)

    if r.status_code == 200:  # success
        return r.json().get('data', '')


    print('ERROR (please copy and paste in the issue)')
    print(r.json())
    print(r.status_code)
    return ''


def get_book_file_types(session, book_id):
    '''
        Return a list with file types of a book
    '''

    url = BASE_URL + URL_BOOK_TYPES_ENDPOINT.format(book_id=book_id)
    r = session.get(url)

    if (r.status_code == 200):  # success
        return r.json()['data'][0].get('fileTypes', [])

    print('ERROR (please copy and paste in the issue)')
    print(r.json())
    print(r.status_code)
    return []


# TODO: i'd like that this functions be async and download faster
def download_book(filename: pathlib.Path, url):
    '''
        Download your book
    '''
    print(f"Starting to download {filename.name}")

    with filename.open("wb") as f:
        r = requests.get(url, stream=True)
        total = r.headers.get('content-length')
        if total is None:
            f.write(r.content)
        else:
            # TODO: read more about tqdm
            for chunk in tqdm(r.iter_content(chunk_size=1024), total=math.ceil(int(total)//1024), unit='KB', unit_scale=True):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            print(f"Finished {filename.name}")


def make_zip(filename: pathlib.Path):
    if filename.suffix == '.code':
        filename.rename(filename.with_suffix('.zip'))


def move_current_files(root: pathlib.Path, book):
    sub_dir: pathlib.Path = root / book
    sub_dir.mkdir(parents=True, exist_ok=True)
    for f in root.glob(f"{book}.*"):
        try:
            if (sub_dir / f.name).exists():
                f.rename((sub_dir / f.stem).with_stem(f"{f.stem}_1").with_suffix(f.suffix))
            else:
                f.rename(sub_dir / f.name)
        except ValueError as e:
            print(e)
            print('Skipping')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--email', help='Your email', required=False)
    parser.add_argument('-p', '--password',
                        help='Your password', required=False)
    parser.add_argument('-d', '--directory',
                        help='Directory to save your books',  dest="root_directory", default="./media", type=lambda d: pathlib.Path(d).expanduser())
    parser.add_argument('-b', '--book-file-types', help='Book file types to download',
                        choices=("pdf", "mobi", "epub", "code"), nargs='*', default="pdf")
    parser.add_argument('-s', '--separate', help='Separate books by type',
                         action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', help='Verbose',
                        action='store_true')
    group.add_argument('-q', '--quiet', help='Quiet',
                       action='store_true')


    args = parser.parse_args()

    # create Session
    session = Session()
    session.headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 " +
        "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
    }
    # create user with his properly header
    session.auth = User(args.email, args.password, session=session)
    args.root_directory.mkdir(parents=True, exist_ok=True)

    # get all your books
    books = get_books(session, is_verbose=args.verbose, is_quiet=args.quiet)
    print('Downloading books...')
    if not args.quiet:
        books_iter = tqdm(books, unit='Book')
    else:
        books_iter = books
    for book in books_iter:
        # get the different file type of current book
        file_types = get_book_file_types(session, book['productId'])
        for file_type in file_types:
            # check if the file type entered is available by the current book
            if file_type in args.book_file_types:
                book_name = book['productName'].replace(' ', '_').replace(
                    '.', '_').replace(':', '_').replace('/', '')
                if args.separate:
                    filename = args.root_directory/f"{book_name}/{book_name}.{file_type}"
                    move_current_files(args.root_directory, book_name)
                else:
                    filename = args.root_directory / f"{book_name}.{file_type}"
                # get url of the book to download
                url = get_url_book(session, book['productId'], file_type)
                if not filename.exists() and not pathlib.Path(filename.stem + ".zip").exists():
                    download_book(filename, url)
                    make_zip(filename)
                else:
                    if args.verbose:
                        tqdm.write(f'{filename.name} already exists, skipping.')


if __name__ == '__main__':
    main()

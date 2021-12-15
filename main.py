# -*- coding: utf-8 -*-
#!/usr/bin/python

from __future__ import print_function
import os
import sys
import glob
import math
import argparse
import requests
from tqdm import tqdm, trange
from config import BASE_URL, PRODUCTS_ENDPOINT, URL_BOOK_TYPES_ENDPOINT, URL_BOOK_ENDPOINT
from user import User


# TODO: I should do a function that his only purpose is to request and return data
def book_request(user, offset=0, limit=10, verbose=False):
    data = []
    url = BASE_URL + PRODUCTS_ENDPOINT.format(offset=offset, limit=limit)
    if verbose:
        print(url)
    r = requests.get(url, headers=user.get_header())
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


def get_url_book(user, book_id, format='pdf'):
    '''
        Return url of the book to download
    '''

    url = BASE_URL + URL_BOOK_ENDPOINT.format(book_id=book_id, format=format)
    r = requests.get(url, headers=user.get_header())

    if r.status_code == 200:  # success
        return r.json().get('data', '')

    elif r.status_code == 401:  # jwt expired
        user.refresh_header()  # refresh token
        get_url_book(user, book_id, format)  # call recursive

    print('ERROR (please copy and paste in the issue)')
    print(r.json())
    print(r.status_code)
    return ''


def get_book_file_types(user, book_id):
    '''
        Return a list with file types of a book
    '''

    url = BASE_URL + URL_BOOK_TYPES_ENDPOINT.format(book_id=book_id)
    r = requests.get(url, headers=user.get_header())

    if (r.status_code == 200):  # success
        return r.json()['data'][0].get('fileTypes', [])

    elif (r.status_code == 401):  # jwt expired
        user.refresh_header()  # refresh token
        get_book_file_types(user, book_id, format)  # call recursive

    print('ERROR (please copy and paste in the issue)')
    print(r.json())
    print(r.status_code)
    return []


# TODO: i'd like that this functions be async and download faster
def download_book(filename, url):
    '''
        Download your book
    '''
    print(f"Starting to download {filename.split('/')[-1]}")

    with open(filename, 'wb') as f:
        r = requests.get(url, stream=True)
        total = r.headers.get('content-length')
        if total is None:
            f.write(r.content)
        else:
            total = int(total)
            # TODO: read more about tqdm
            for chunk in tqdm(r.iter_content(chunk_size=1024), total=math.ceil(total//1024), unit='KB', unit_scale=True):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
            print(f"Finished {filename.split('/')[-1]}")


def make_zip(filename):
    if filename[-4:] == 'code':
        os.replace(filename, filename[:-4] + 'zip')


def move_current_files(root, book):
    sub_dir = f'{root}/{book}'
    does_dir_exist(sub_dir)
    for f in glob.iglob(sub_dir + '.*'):
        try:
            os.rename(f, f'{sub_dir}/{book}' + f[f.index('.'):])
        except OSError:
            os.rename(f, f'{sub_dir}/{book}' + '_1' + f[f.index('.'):])
        except ValueError as e:
            print(e)
            print('Skipping')


def does_dir_exist(directory):
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
        except Exception as e:
            print(e)
            sys.exit(2)


def main():
    # thanks to https://github.com/ozzieperez/packtpub-library-downloader/blob/master/downloader.py

    parser = argparse.ArgumentParser(
        usage="Usage: main.py -e <email> -p <password> [-d <directory> -b <book file types> -s -v -q]")
    parser.add_argument('-e', '--email', help='Your email', required=True)
    parser.add_argument('-p', '--password',
                        help='Your password', required=True)
    parser.add_argument('-d', '--directory',
                        help='Directory to save your books', required=False, dest="root_directory", type=lambda d: os.path.expanduser(d) if '~' in d else os.path.abspath(d))
    parser.add_argument('-b', '--book-file-types', help='Book file types to download',
                        required=False, choices=("pdf", "mobi", "epub", "code"), nargs='*', default="pdf")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', help='Verbose',
                       required=False, action='store_true')
    group.add_argument('-q', '--quiet', help='Quiet',
                       required=False, action='store_true')

    parser.add_argument('-s', '--separate', help='Separate books by type',
                        required=False, action='store_true')

    args = parser.parse_args()

    # create user with his properly header
    user = User(args.email, args.password)
    print(args)
    # get all your books
    books = get_books(user, is_verbose=args.verbose, is_quiet=args.quiet)
    print('Downloading books...')
    if not args.quiet:
        books_iter = tqdm(books, unit='Book')
    else:
        books_iter = books
    for book in books_iter:
        # get the different file type of current book
        file_types = get_book_file_types(user, book['productId'])
        for file_type in file_types:
            # check if the file type entered is available by the current book
            if file_type in args.book_file_types:
                book_name = book['productName'].replace(' ', '_').replace(
                    '.', '_').replace(':', '_').replace('/', '')
                if args.separate:
                    filename = f'{args.root_directory}/{book_name}/{book_name}.{file_type}'
                    move_current_files(args.root_directory, book_name)
                else:
                    filename = f'{args.root_directory}/{book_name}.{file_type}'
                # get url of the book to download
                url = get_url_book(user, book['productId'], file_type)
                if not os.path.exists(filename) and not os.path.exists(filename.replace('.code', '.zip')):
                    download_book(filename, url)
                    make_zip(filename)
                else:
                    if args.verbose:
                        tqdm.write(f'{filename} already exists, skipping.')


if __name__ == '__main__':
    main()

# author	:	Sanket Khedekar sakh3719@colorado.edu
# name	    :	webproxy.py
# purpose	:   Proxy server.
# date	    :	2017.11.8 10.43
# version	:	1.0

import socket
import threading
import sys
import os
import datetime
import hashlib
import logging
import time
import argparse
import requests
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

logging.basicConfig(filename="log_webproxy.txt", level=logging.DEBUG, format='%(message)s')
cache_delete = []
cache_etag = []


# Server Class
class ServerSide:
    def __init__(self, server_port, cache_time):
        self.size = 65535
        self.threads = []
        self.host = "127.0.0.1"
        self.port = server_port
        self.cache_timeout = cache_time

    def create_socket(self):
        try:
            # Create an INET, STREAM socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Use different port if the port is in use
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            # bind the socket to a host, and a port
            sock.bind((self.host, self.port))
            # queue up as many as 10 connect requests
            sock.listen(10)
            self.sock = sock
            logging.debug("Listening on Port " + str(self.port) + "...")
            # Call process function
            self.process()
        except socket.error as msg:
            if self.sock:
                self.sock.close()
            logging.debug("Could not open socket: " + str(msg))
            sys.exit(1)
        except KeyboardInterrupt:
            logging.debug("Closing Socket gracefully")
            sys.exit(0)

    def process(self):
        thread_count = 1

        # Start - Delete all files from cache folder
        try:
            current_path = os.getcwd()
            cache_folder = current_path + "\\cache\\"
            cache_dir = os.path.dirname(cache_folder)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            files = os.listdir(cache_folder)
            for file in files:
                os.remove(cache_folder + "\\" + file)
        except Exception:
            print("Files Deleted")
        # End - Delete all files from cache folder

        print("Proxy server started...")
        cache_thread = threading.Thread(target=ServerSide.cache_deletefile, args=(self,))
        cache_thread.setDaemon(True)
        self.threads.append(cache_thread)
        cache_thread.start()
        while True:
            try:
                conn, addr = self.sock.accept()
                logging.debug("Connection: " + str(conn))
                if conn:
                    thread = MultipleThread(conn, addr, thread_count, self.cache_timeout)
                    thread.setDaemon(True)
                    self.threads.append(thread)
                    thread.start()
                    dtime = datetime.datetime.now()
                    logging.debug("\nThread:" + str(thread_count) + " Start Time: " + str(dtime))

                    dtime = datetime.datetime.now()
                    logging.debug("Thread:" + str(thread_count) + " Close Time: " + str(dtime))
                    thread_count = thread_count + 1
                    for thread in self.threads:
                        if not thread.isAlive():
                            thread.join()
                            self.threads.remove(thread)
                else:
                    conn.close()
                    break
            except Exception as e:
                # print("Process Exit Exception" + str(e))
                continue

    def cache_deletefile(self):
        while True:
            try:
                end_sec = int(time.time())
                if len(cache_delete) > 0:
                    for cache in cache_delete:
                        start_sec = int(cache.split('###')[0])
                        if end_sec < start_sec:
                            break
                        else:
                            cache_delete.remove(cache)
                            cache_etag.append(cache)
                            # print("File removed: " + str(delete_filename))
                            if len(cache_delete) > 0:
                                break
            except Exception as e:
                # print("Cache Delete: Exit Exception" + str(e))
                continue

    def prefetch_linkthread(self, prefetch_url):
        try:
            # print("Link Thread function called")
            parsed_url = urlparse(prefetch_url)
            webserver = parsed_url.hostname
            port = parsed_url.port
            if port is None:
                port = 80

            current_path = os.getcwd()
            m = hashlib.md5()
            m.update(prefetch_url.encode('utf-8'))
            cache_filename = m.hexdigest() + ".cache"

            cache_folder = current_path + "\\cache\\"
            cache_dir = os.path.dirname(cache_folder)
            if not os.path.exists(cache_dir):
                os.makedirs(cache_dir)
            cache_savepath = cache_folder + cache_filename

            request = "GET " + prefetch_url + " HTTP / 1.0\r\n\r\n"

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            webserverip = socket.gethostbyname(webserver)
            sock.connect((webserverip, port))
            sock.sendall(request.encode())
            data_store = b''
            while True:
                sock.settimeout(5)
                try:
                    response = sock.recv(2048)
                    if response:
                        data_store += response
                    else:
                        break
                except socket.timeout:
                    break

            private = False
            no_store = False
            no_cache = False
            etag = ""
            if self.cache_timeout is not None:
                max_age = int(cache_timeout)
            else:
                max_age = 0
            cache_max_age = -1
            for resp_line in data_store.split(b'\r\n'):
                if b'Cache-Control' in resp_line:
                    cache_control_value = str(resp_line.split(b':')[1].decode()).strip()
                    if "private" in cache_control_value:
                        private = True
                    else:
                        private = False

                    if "no-store" in cache_control_value:
                        no_store = True
                    else:
                        no_store = False

                    if "no-cache" in cache_control_value:
                        no_cache = True
                    else:
                        no_cache = False

                    cache_property = cache_control_value.split(",")
                    for cache_property_line in cache_property:
                        if "max-age" in cache_property_line.strip():
                            cache_max_age = int(str(cache_property_line.strip().split("=")[1]))
                            break
                        else:
                            cache_max_age = -1

                    if self.cache_timeout is not None:
                        if cache_max_age != -1 and int(self.cache_timeout) < cache_max_age:
                            max_age = int(self.cache_timeout)
                        elif cache_max_age != -1 and cache_max_age:
                            max_age = cache_max_age
                        else:
                            max_age = 0
                    else:
                        if cache_max_age != -1 and cache_max_age:
                            max_age = cache_max_age
                        else:
                            max_age = 0

                    # print("Prefetch File: " + str(prefetch_url) + "\nCache Property Line: " + str(cache_control_value) + "\nPrivate: " + str(private) + "\nNo-store: " + str(no_store) + "\nNo-cache: " + str(no_cache) + "\nCache Max Age: " + str(cache_max_age) + "\nMax-Age: " + str(max_age))
                    break

            for resp_line in data_store.split(b'\r\n'):
                if b'ETag' in resp_line:
                    e = re.findall('"(.*)"', resp_line.decode())
                    etag = str(e[0])
                    break

            if cache_filename and private is False and no_store is False:
                write_file = open(cache_savepath, 'wb')
                write_file.write(data_store)
                write_file.close()
                start_sec = int(time.time()) + int(max_age)
                cd = str(start_sec) + "###" + str(cache_filename) + "###" + str(etag)
                cache_delete.append(cd)
                cache_delete.sort()
                # print("Prefetch File Saved: " + str(prefetch_url) + "Cache Name: " + str(cache_filename))

            sock.close()
        except socket.gaierror:
            print("A")
            # print("Error in Prefetch")
        except Exception as e:
            print("B")
            # print("Error in Prefetch Exception" + str(e))

    def error400(self):
        http_response = "HTTP/1.1 400 Bad Request\r\n\r\n"
        http_response += "<html><body><h2>400 Bad Request</h2><br /></body></html>"
        return http_response.encode()

    def error501(self):
        logging.debug("501 Error")
        http_response = "HTTP/1.1 501 Not Implemented\r\nContent-Type: text/html\r\nContent-Length: 300\r\n\r\n"
        http_response += "<html><body><h2>501 Not Implemented</h2><br /></body></html>"
        return http_response.encode()


# MultiThreading Class
class MultipleThread(threading.Thread):
    def __init__(self, conn, addr, thread, cache_time):
        threading.Thread.__init__(self)
        self.threads = []
        self.conn = conn
        self.addr = addr
        self.thr = thread
        self.size = 65535
        self.cache_timeout = cache_time

    def run(self):
        try:
            request = self.conn.recv(2048)
            if request:
                request = request.decode('unicode_escape').encode('utf-8')
                line = request.decode().split('\n')[0]
                method = line.split(' ')[0]
                url = line.split(' ')[1]
                http = str(request.decode().split()[2]).strip()
                data = requests.get(url)
                links = []

                if not os.path.isfile("blocked.txt"):
                    write_file = open("blocked.txt", "w")
                    write_file.write("")
                    write_file.close()

                block_file = open("blocked.txt")
                if url in block_file.read():
                    print("Block site File")
                    http_response = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: 300\r\nConnection: close\r\n\r\n"
                    http_response += "<html><title>No access</title><body><h2>Site Blocked because of Text Pokemon</h2><br /></body></html>"
                    self.conn.sendall(http_response.encode())
                    self.conn.close()

                elif "pokemon" in url.lower():
                    print("Pokemon in URL")
                    http_response = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: 300\r\nConnection: close\r\n\r\n"
                    http_response += "<html><title>Pokemon Found</title><body><h2>Text Pokemon found in URL</h2><br /></body></html>"
                    self.conn.sendall(http_response.encode())
                    self.conn.close()
                    write_file = open("blocked.txt", "a+")
                    write_file.write(url + "\n")
                    write_file.close()

                elif "pokemon" in data.text.lower():
                    print("Pokemon in Content")
                    http_response = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\nContent-Length: 300\r\nConnection: close\r\n\r\n"
                    http_response += "<html><title>Pokemon Found</title><body><h2>Text Pokemon found in Content</h2><br /></body></html>"
                    self.conn.sendall(http_response.encode())
                    self.conn.close()
                    write_file = open("blocked.txt", "a+")
                    write_file.write(url + "\n")
                    write_file.close()

                elif http not in ['HTTP/1.0', 'HTTP/1.1', 'HTTP/1.2']:
                    error_response = server.error400()
                    self.conn.sendall(error_response)
                    self.conn.close()

                elif http not in ['HTTP/1.0']:
                    error_response = server.error501()
                    self.conn.sendall(error_response)
                    self.conn.close()

                elif method == "GET":
                    parsed_url = urlparse(url)
                    webserver = parsed_url.hostname
                    port = parsed_url.port
                    if port is None:
                        port = 80

                    current_path = os.getcwd()
                    m = hashlib.md5()
                    m.update(url.encode('utf-8'))
                    cache_filename = str(m.hexdigest() + ".cache")

                    cache_folder = current_path + "\\cache\\"
                    cache_dir = os.path.dirname(cache_folder)
                    if not os.path.exists(cache_dir):
                        os.makedirs(cache_dir)

                    cache_savepath = cache_folder + cache_filename
                    cache_present = 0
                    for cache in cache_delete:
                        filename = str(cache.split('###')[1])
                        if cache_filename == filename and os.path.isfile(cache_savepath):
                            print("From Cache: Local Machine")
                            read_file = open(cache_savepath, "rb")
                            for line in read_file:
                                self.conn.sendall(line)
                            read_file.close()
                            self.conn.close()
                            cache_present = 1
                            break

                    if cache_present == 0 and os.path.isfile(cache_savepath):
                        header = {}
                        for etag in cache_etag:
                            filename = str(etag.split('###')[1])
                            if len(etag) > 2:
                                etag = str(etag.split('###')[2])
                                if cache_filename == filename and os.path.isfile(cache_savepath):
                                    header['If-None-Match'] = str(etag)
                                    r = requests.get(url, headers=header)
                                    if str(r.status_code) == "304":
                                        print("Revalidation")
                                        if os.path.isfile(cache_savepath):
                                            print("Revalidation: Local Machine")
                                            read_file = open(cache_savepath, "rb")
                                            for line in read_file:
                                                self.conn.sendall(line)
                                            read_file.close()
                                            self.conn.close()
                                            cache_present = 1
                                        break

                    if cache_present == 0:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        webserverip = socket.gethostbyname(webserver)
                        sock.connect((webserverip, port))
                        sock.sendall(request)
                        print("From Site")
                        data_store = b''
                        while True:
                            sock.settimeout(5)
                            try:
                                response = sock.recv(2048)
                                if response:
                                    data_store += response
                                else:
                                    break
                            except socket.timeout:
                                break

                        private = False
                        no_store = False
                        no_cache = False
                        etag = ""
                        if self.cache_timeout is not None:
                            max_age = int(cache_timeout)
                        else:
                            max_age = 0
                        cache_max_age = -1
                        for resp_line in data_store.split(b'\r\n'):
                            if b'Cache-Control' in resp_line:
                                cache_control_value = str(resp_line.split(b':')[1].decode()).strip()

                                if "private" in cache_control_value:
                                    private = True
                                else:
                                    private = False

                                if "no-store" in cache_control_value:
                                    no_store = True
                                else:
                                    no_store = False

                                if "no-cache" in cache_control_value:
                                    no_cache = True
                                else:
                                    no_cache = False

                                cache_property = cache_control_value.split(",")
                                for cache_property_line in cache_property:
                                    if "max-age" in cache_property_line.strip():
                                        cache_max_age = int(str(cache_property_line.strip().split("=")[1]))
                                        break
                                    else:
                                        cache_max_age = -1

                                if self.cache_timeout is not None:
                                    if cache_max_age != -1 and int(self.cache_timeout) < cache_max_age:
                                        max_age = int(self.cache_timeout)
                                    elif cache_max_age != -1 and cache_max_age:
                                        max_age = cache_max_age
                                    else:
                                        max_age = 0
                                else:
                                    if cache_max_age != -1 and cache_max_age:
                                        max_age = cache_max_age
                                    else:
                                        max_age = 0

                                # print("Main File: " + str(url) + "\nCache Property Line: " + str(cache_control_value) + "\nPrivate: " + str(private) + "\nNo-store: " + str(no_store) + "\nNo-cache: " + str(no_cache) + "\nCache Max Age: " + str(cache_max_age) + "\nMax-Age: " + str(max_age))
                                break

                        for resp_line in data_store.split(b'\r\n'):
                            if b'ETag' in resp_line:
                                e = re.findall('"(.*)"', resp_line.decode())
                                if len(e) > 0:
                                    etag = str(e[0])
                                    break
                                else:
                                    etag = ""

                        if cache_filename and private is False and no_store is False:
                            write_file = open(cache_savepath, 'wb')
                            write_file.write(data_store)
                            write_file.close()
                            start_sec = int(time.time()) + int(max_age)
                            cd = str(start_sec) + "###" + str(cache_filename) + "###" + str(etag)
                            cache_delete.append(cd)
                            cache_delete.sort()

                        self.conn.sendall(data_store)
                        sock.close()
                        self.conn.close()

                    try:
                        soup = BeautifulSoup(data.text, "html.parser")
                        for link in soup.findAll('a'):
                            links.append(link.get('href'))

                        if len(links) > 0:
                            for link in links:
                                link_parse = urlparse(link)
                                if not link_parse.netloc:
                                    link_parse = url
                                    prefetch_url = link_parse + link
                                else:
                                    prefetch_url = link
                                if urlparse(prefetch_url):
                                    link_thread = threading.Thread(target=ServerSide.prefetch_linkthread, args=(self, prefetch_url,))
                                    link_thread.setDaemon(True)
                                    self.threads.append(link_thread)
                                    link_thread.start()
                    except Exception:
                        print("C")

                else:
                    # print("Exit Method: " + str(method))
                    error_response = server.error400()
                    self.conn.sendall(error_response)
                    self.conn.close()

            else:
                # print("Exit Request: No Request")
                self.conn.close()

        except socket.timeout:
            # print("Exit Timeout: Socket Timeout")
            self.conn.close()

        except socket.gaierror:
            # print("Error")
            error_response = server.error400()
            self.conn.sendall(error_response)
            self.conn.close()

        except requests.exceptions.ConnectionError:
            error_response = server.error400()
            self.conn.sendall(error_response)
            self.conn.close()

        except Exception as e:
            # print("Exit Exception: " + str(e))
            self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="--- Webserver ---")
    parser.add_argument("PortNo", type=int, help="Please enter Port No")
    parser.add_argument("--c", type=int, help="Please enter timout for cache")
    args = parser.parse_args()
    port = int(args.PortNo)
    cache_timeout = args.c
    if port < 1025 or port > 65535:
        print("Please enter port no between 1025 and 65535 inclusive")
        sys.exit()

    server = ServerSide(port, cache_timeout)
    server.create_socket()

# Web_Proxy_Server
Simple Web Proxy Server for handling traffic between client and server.

---------------------------------------------------------------------------------------------------
Objective:
---------------------------------------------------------------------------------------------------
Simple Web Proxy Server for handling traffic between client and server.
Handling HTTP version 1.0 only.

---------------------------------------------------------------------------------------------------
Background:
---------------------------------------------------------------------------------------------------
Handling request between Client and server thriugh proxy.
Handle multiple request.
Handling errors in the code.
Logging the file instead of printing.

---------------------------------------------------------------------------------------------------
Implementation:
---------------------------------------------------------------------------------------------------
Implementation Details
Set the proxy settings in the browser so that it can take the request to the proxy.
port should be between 1025 and 65535
User is given the optional cache timout.

If there is error then they are handled by one of the following error handling request:
HTTP 400 Error
If the path is invalid, then the error will be handled by error400 function.
If the http version is other than HTTP1.0, HTTP1.1, then the error will be handled by error400 function.

HTTP 501 Error
If the method is used different other than GET, then the error will be handled by error501 function.

Web Proxy:
The client request for the page, the request is passed through the proxy.
If the request is valid, then it checks for the blocking content i.e Pokemon
If the blocked.txt contains the url, the 400 error is send and the connection is closed.
If the url is not present then it check for pokemon in url and content. If it is found, the site is blocked.
If there is no pokemon string present in it, then the request is send to the server via proxy.
The data is fetched and cached in the local machine for specific amount of time.
If the time is not specified then the max-age time is taken into consideration.
If the time of cache expires, the file from the list is removed.

When there is same request, the data is taken from the cache for faster browsing.
If the cache is expired, it revalidates the content.

Link Prefetch:
If there are links present in the request page, then all the pages are cached.
If the user clicks on the link which is cached, the data is given from the cached else it is fetched from the server.

---------------------------------------------------------------------------------------------------
Requirement:
---------------------------------------------------------------------------------------------------
Python v3.6.2

webproxy.py

Log files will be created for webproxy
Block list will be created
server:		log_webproxy.txt
Block site: blocked.txt

---------------------------------------------------------------------------------------------------
IDE for Development:
---------------------------------------------------------------------------------------------------
Pycharm
Terminal window inside pycharm for running program.

---------------------------------------------------------------------------------------------------
Instruction for running program:
---------------------------------------------------------------------------------------------------
webproxy.py

Client:
Browser or Telnet
---------------------------------------------------------------------------------------------------

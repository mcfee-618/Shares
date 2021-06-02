import http.server
class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''Handle HTTP requests by returning a fixed 'page'.'''
    # Page to send back.
    Page = '''\
            <html>
            <body>
            <p>Hello, web1!</p>
            </body>
            </html>
'''
    # Handle a GET request.
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(self.Page)))
        print(self._headers_buffer)
        print(222)
        self.end_headers()
        self.wfile.write(self.Page.encode("utf-8"))
#----------------------------------------------------------------------
if __name__ == '__main__':
    serverAddress = ('0.0.0.0', 8082)
    server = http.server.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()

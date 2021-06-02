import http.server

class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''Handle HTTP requests by returning a fixed 'page'.'''
    # Page to send back.
    template = '''\
            <html>
            <body>
            <p>name:{name}</p>
            <p>password:{password}</p>
            </body>
            </html>
'''
    # Handle a GET request.
    def do_GET(self):
        self.send_response(200)
        page = self.create_page()
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))
        
    def create_page(self):
        data = {
            "name":"fpx",
            "password":"123456"
        }
        return self.template.format(**data)
        
#----------------------------------------------------------------------
if __name__ == '__main__':
    serverAddress = ('0.0.0.0', 8082)
    server = http.server.HTTPServer(serverAddress, RequestHandler)
    server.serve_forever()
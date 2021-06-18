import os
import subprocess,traceback
import http.server

## 服务器内部错误
class ServerException(Exception):
    pass


class RequestHandler(http.server.BaseHTTPRequestHandler):
    '''Handle HTTP requests by returning a fixed 'page'.'''  
          
    def do_GET(self):
        try:
            path = self.path[1:]
            ## index
            if not path:
                return self.index()
            paths = path.split("/")
            if len(paths)!=2 or paths[0] not in ["static","cgi"]:
                raise ServerException("path error")
            ## static
            path = f"{paths[0]}/{paths[1]}"
            self.check_file_exists(path)
            if paths[0] == "static":
                content = self.handle_static(path)
            ## cgi
            else:
                content = self.handle_cgi(path)
            self.send_content(content)
        except ServerException as e:
            msg = traceback.format_exc()
            self.handle_error(msg)
             
    def handle_static(self,path):
        with open(path,"r") as fp:
            lines = fp.readlines()
        content = ""
        for line in lines:
            content += f"{line}\n"
        return content
            
    def handle_cgi(self,path):
        result = subprocess.check_output(["python3", path], shell = False)
        return str(result, encoding = "utf-8")
    
    def handle_error(self,msg):
        page = self.create_page(msg)
        self.send_content(page,status_code=500)
  
    def index(self):
        page = self.create_page("index")
        self.send_content(page)
    
    def create_page(self,page_name):
        html_str = f"<html><body><p>{page_name}</p></body></html>"
        return html_str
    
    def send_content(self,page,status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(page)))
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))
        
    def check_file_exists(self,path):
        if not os.path.exists(path):
            raise ServerException(f"file {path} not exists")
        
if __name__ == '__main__':
    serverAddress = ('0.0.0.0', 8082)
    request_handler = RequestHandler
    server = http.server.HTTPServer(serverAddress, request_handler)
    server.serve_forever()
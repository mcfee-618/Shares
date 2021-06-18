import subprocess
output = subprocess.check_output(["python3", "cgi_test.py"], shell = False)
print(output)
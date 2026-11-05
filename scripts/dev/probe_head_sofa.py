import pathlib, subprocess
head = subprocess.run(['git','show','HEAD:assets/template.html'], capture_output=True).stdout.decode('utf-8')
p=head.find('w.rotation.x=-.13}')
print(repr(head[p-600:p+600])[:3000])

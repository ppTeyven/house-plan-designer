import pathlib, subprocess, difflib
head = subprocess.run(['git','show','HEAD:assets/template.html'], capture_output=True).stdout.decode('utf-8')
cur = pathlib.Path('assets/template.html').read_text(encoding='utf-8')
print(len(head), len(cur))
sm = difflib.SequenceMatcher(None, head, cur, autojunk=False)
for tag,i1,i2,j1,j2 in sm.get_opcodes():
    if tag != 'equal':
        print(tag, i1, i2, j1, j2)
        print('HEAD :', repr(head[max(0,i1-120):i2+120])[:1500])
        print('CUR  :', repr(cur[max(0,j1-120):j2+120])[:1500])
        print('---')

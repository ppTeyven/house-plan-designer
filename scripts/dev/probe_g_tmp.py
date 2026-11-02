t = open('assets/template.html', encoding='utf-8').read()
i = t.find('setPointerCapture(n.pointerId)')
print(t[max(0,i-2600):i+2600].replace('\n',' ')[:5400])

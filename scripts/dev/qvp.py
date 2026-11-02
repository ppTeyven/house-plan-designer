# -*- coding: utf-8 -*-
t = open('assets/template.html', encoding='utf-8').read()
i = t.find('try{skyFade(1)}catch(e){}')
print(repr(t[i-120:i+120]))

import requests
u = "https://onlineservices.proteantech.in/paam/endUserRegisterContact.html"
t = requests.get(u, timeout=30).text
open('.pan_page.html','w',encoding='utf-8').write(t)
print('saved', len(t))

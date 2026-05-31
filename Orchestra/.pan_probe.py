import requests, re
u = "https://onlineservices.proteantech.in/paam/endUserRegisterContact.html"
t = requests.get(u, timeout=30).text
print('len', len(t))
print('applicationType', 'applicationType' in t)
print('mobileNumber', 'mobileNumber' in t)
print('txtDOB', 'txtDOB' in t)
print('recaptcha', 'recaptcha' in t.lower())
names = sorted(set(re.findall(r"name=[\"']([^\"']+)[\"']", t)))
ids = sorted(set(re.findall(r"id=[\"']([^\"']+)[\"']", t)))
print('NAMES')
for n in names:
    if any(k in n.lower() for k in ['app', 'cat', 'title', 'first', 'last', 'sur', 'dob', 'email', 'mobile', 'captcha', 'otp', 'consent', 'country', 'state']):
        print(n)
print('IDS')
for i in ids:
    if any(k in i.lower() for k in ['app', 'cat', 'title', 'first', 'last', 'sur', 'dob', 'email', 'mobile', 'captcha', 'otp', 'consent', 'country', 'state']):
        print(i)

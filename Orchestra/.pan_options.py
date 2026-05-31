import re
html = open('.pan_page.html', encoding='utf-8').read()
for sid in ['type','cat_applicant1']:
    m = re.search(rf'<select[^>]*id="{sid}"[^>]*>(.*?)</select>', html, re.S|re.I)
    print('\nSELECT', sid)
    if not m:
        print('not found')
        continue
    block = m.group(1)
    opts = re.findall(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', block, re.S|re.I)
    for v,t in opts:
        txt = re.sub(r'<.*?>','',t).strip()
        print(f'value={v!r} text={txt!r}')

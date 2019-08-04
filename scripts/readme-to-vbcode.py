#!/usr/bin/env python

import re

from markdown import markdown
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


with open('README.md') as f:
    ashtml = markdown(f.read())

driver = webdriver.Chrome()
driver.get('http://www.seabreezecomputers.com/html2bbcode/')

textarea = driver.find_element_by_name('textbox')
textarea.clear()
textarea.send_keys(ashtml)

elem = driver.find_element_by_xpath('//input[@name="codetype"][@value="vbcode"]')
elem.click()

elem = driver.find_element_by_xpath('//input[@name="option"][@value="code"]')
elem.click()

elem = driver.find_element_by_name('Convert')
elem.click()

vbcode = textarea.get_attribute('value')
driver.close()

vbcode = vbcode.strip()
vbcode = '\n'.join(vbcode.split('\n')[1:]).strip()
vbcode = re.sub('\n\n+', '\n\n', vbcode)
vbcode = re.sub('\n([a-z])', r' \1', vbcode)
vbcode = re.sub('\n(\[url)', r' \1', vbcode)
vbcode = vbcode.replace('&gt;', '>')
vbcode = vbcode.split('\n')
vhindex = vbcode.index([l for l in vbcode if 'Version History' in l][0])
vbcode.insert(vhindex + 2, '[SPOILER]')
vbcode.append('[/SPOILER]')
vbcode = '\n'.join(vbcode)
print(vbcode)

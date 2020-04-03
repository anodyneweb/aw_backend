import requests
import json

URL = "http://ec2-3-6-144-180.ap-south-1.compute.amazonaws.com:8000"

sess = requests.Session()
dd = sess.post(url=URL + "/api/token/", data={"email": "email_id_here",
                                              "password": "password"})
data = json.loads(dd.text)
# Fetching Key
access_key = data.get('access')
header = {'Authorization': 'Bearer %s' % access_key}
# TO GET
data = sess.get(url=URL + "/api/industry/", headers=header)
print(json.loads(data.text))
# TO POST
data = sess.post(url=URL + "/api/industry/", headers=header,
                 data={
                     # request payload
                 })

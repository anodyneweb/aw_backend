import requests
import json
# https://www.django-rest-framework.org/api-guide/routers/#defaultrouter
URL = "http://ec2-3-6-144-180.ap-south-1.compute.amazonaws.com"

sess = requests.Session()
dd = sess.post(url=URL + "/api/token/", data={"email": "", "password": ""})
data = json.loads(dd.text)
# Fetching Key
access_key = data.get('access')
header = {'Authorization': 'Bearer %s' % access_key}
# TO GET
data = sess.get(url=URL + "/api/industry/", headers=header)
# print(json.loads(data.text))
# TO POST

# data = sess.post(url=URL + "/api/industry/", headers=header,
#                  data={
#                      request payload
# })

# print(sess.delete(
#     url=URL + "/api/industry/%s" % 'f441293d-c5fe-4117-a80d-15c241188b89',
#     headers=header))

import logging
import os
import pysftp


def send2server(f):
    conn = pysftp.Connection(host="3.6.144.180", username="ftpuser",
                            password="ftpuser")
    # print(dir(conn))
    directory_structure = conn.listdir_attr()

    # Print data
    # for attr in directory_structure:
    #     print(attr.filename, attr)
    conn.put(f) # to upload file
    conn.close()


print(send2server('/Users/sagarsharma/Documents/project/aw_backend/anodyne/prefix_sampl_file_200213093859.csv'))

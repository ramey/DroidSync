""" Helper module for SSH2 library"""

import logging
import stat
import os
import paramiko

from utils import DSException
from utils import droidsync_logger

class Connector(object):
    """ Main connector class
        Attriues:
            key (str): the private key to be used to ssh
            host (str): the host address of the remote server
            port (int): Port number to use for ssh
            user (str): User name to login as
            password (str): password to use
            key_password (str): password to unlock the private key
    """
    def __init__(self, key, host, port, user, password, key_password):
        self.user = user
        self.password = password
        try:
            self.key = paramiko.RSAKey.from_private_key_file(key, password=key_password)
        except Exception as err:
            raise DSException('Not able to load the specified key: ', err)
        client = paramiko.Transport((host, port))
        client.connect(username=self.user, password=self.password, pkey=self.key)
        self.sftp = paramiko.sftp_client.SFTPClient.from_transport(client)
        droidsync_logger.setLevel(logging.INFO)

    def check_dest_dir(self, target):
        """Check about the destination folder

            Check whether the folder exists on the remote host
            is not create one
            
            Arg:
                target (str): target folder address
        """
        sftp = self.sftp
        try:
            is_dir = stat.S_ISDIR(sftp.stat(target).st_mode)
            if not is_dir:
                sftp.remove(target)
                sftp.mkdir(target)
        except IOError:
            sftp.mkdir(target)

    def get_files_list(self, target):
        """ Get lsit of files from remote host"""
        return self.sftp.listdir(target)

    def remove(self, target, file_name):
        """Remove a particular file on target host"""
        sftp = self.sftp        
        target_path = os.path.join(target, file_name)
        if stat.S_ISDIR(sftp.stat(target_path).st_mode):
            for name in self.sftp.listdir(target_path):
                self.remove(target_path, name)
            sftp.rmdir(target_path)
        else:
            sftp.remove(target_path)
    
    def check_target(self, source_path, target_path):
        """ Check the source and destination for the diff in files

            Args:
                source_path(str): source path on local host
                target_path(str): destination path on remote host 
        """
        sftp = self.sftp
        try:
            target_attr = sftp.stat(target_path)
            if os.path.isfile(source_path):
                if stat.S_ISDIR(target_attr.st_mode):
                    sftp.rmdir(target_path)
                    sftp.put(source_path, target_path)
                elif stat.S_ISREG(target_attr.st_mode):
                    if self.should_update(source_path, target_attr):
                        sftp.put(source_path, target_path)
                else:
                    droidsync_logger.info("%s is neither a file nor directory" %target_path)
            elif os.path.isdir(source_path):
                if stat.S_ISREG(target_attr.st_mode):
                    sftp.remove(target_path)
                    sftp.mkdir(target_path)
                elif stat.S_ISDIR(target_attr.st_mode):
                    for file in os.listdir(source_path):
                        self.check_target(os.path.join(source_path, file), os.path.join(target_path, file))
            else:
                droidsync_logger.info('%s neither a file nor directory' % source_path)
        except IOError:
            if os.path.isfile(source_path):
                sftp.put(source_path, target_path)
            elif os.path.isdir(source_path):
                sftp.mkdir(target_path)
                for file in os.listdir(source_path):
                    sftp.put(os.path.join(source_path, file), os.path.join(target_path, file))
            else:
                droidsync_logger.info('%s neither a file nor directory' % source_path)
 
    @staticmethod
    def should_update(source, target):
        """Static method to check whether a file should be updated or not"""
        try:
            src_st = os.stat(source)
            src_sz = src_st.st_size
            src_mt = src_st.st_mtime
        except:
            droidsync_logger.error("Error reading: %s" % source)
            return False
        target_sz = target.st_size
        target_mt = target.st_mtime
        return target_sz != src_sz or target_mt != src_mt